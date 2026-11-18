import json
import os
import hashlib
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).resolve().parent
TRIPLES_FILE = Path(os.getenv(
    "TRIPLES_JSON",
    str(BASE_DIR.parent / "agri_kg_production" / "output" / "triples.json")
))

load_dotenv(BASE_DIR / ".env", override=True)

# Connect
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "triples")


def load_triples():
    with open(TRIPLES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("triples", "accepted_triples", "records", "data"):
            if isinstance(data.get(key), list):
                return data[key]

    raise ValueError("Could not find a list of triples in triples.json")


def prepare(row):
    subject = row.get("subject") or row.get("head")
    predicate = row.get("predicate") or row.get("relation")
    obj = row.get("object") or row.get("tail")

    if isinstance(subject, dict):
        subject = subject.get("name") or subject.get("text") or subject.get("value")
    if isinstance(obj, dict):
        obj = obj.get("name") or obj.get("text") or obj.get("value")

    if not all(isinstance(x, str) and x.strip()
               for x in (subject, predicate, obj)):
        return None

    subject_type = row.get("subject_type") or row.get("head_type") or "UNKNOWN"
    object_type = row.get("object_type") or row.get("tail_type") or "UNKNOWN"

    triple_id = row.get("triple_id") or hashlib.sha256(
        f"{subject}|{predicate}|{obj}".encode("utf-8")
    ).hexdigest()

    return {
        "triple_id": str(triple_id),
        "subject": subject.strip(),
        "subject_type": str(subject_type),
        "predicate": predicate.strip().upper().replace(" ", "_"),
        "object": obj.strip(),
        "object_type": str(object_type),
        "evidence": str(row.get("evidence") or ""),
        "confidence": float(row.get("confidence") or 0.0),
        "crop": str(row.get("crop") or ""),
        "source": str(row.get("source") or ""),
        "chunk_id": str(row.get("chunk_id") or ""),
        "metadata": json.dumps(row.get("metadata") or {}, ensure_ascii=False, default=str),
    }


def import_batch(tx, rows):
    result = tx.run("""
        UNWIND $rows AS row

        MERGE (s:Entity {entity_key:
            toLower(row.subject) + '|' + row.subject_type})
        ON CREATE SET
            s.name = row.subject,
            s.entity_type = row.subject_type

        MERGE (o:Entity {entity_key:
            toLower(row.object) + '|' + row.object_type})
        ON CREATE SET
            o.name = row.object,
            o.entity_type = row.object_type

        MERGE (s)-[r:FACT {triple_id: row.triple_id}]->(o)
        SET r.predicate = row.predicate,
            r.evidence = row.evidence,
            r.confidence = row.confidence,
            r.crop = row.crop,
            r.source = row.source,
            r.chunk_id = row.chunk_id,
            r.metadata_json = row.metadata

        RETURN count(r) AS imported
    """, rows=rows)

    return result.single()["imported"]


def main():
    raw = load_triples()
    rows = [prepare(x) for x in raw]
    rows = [x for x in rows if x is not None]

    print(f"Loaded records: {len(raw)}")
    print(f"Valid triples: {len(rows)}")

    total = 0

    with driver.session(database=DATABASE) as session:
        for start in range(0, len(rows), 500):
            batch = rows[start:start + 500]
            count = session.execute_write(import_batch, batch)
            total += count
            print(f"Imported batch: {min(start + 500, len(rows))}/{len(rows)}")

        stats = session.run("""
            MATCH (e:Entity)
            WITH count(e) AS entities
            MATCH ()-[r:FACT]->()
            RETURN entities, count(r) AS relationships
        """).single()

    print("\nIMPORT COMPLETE")
    print("Entities:", stats["entities"])
    print("Relationships:", stats["relationships"])


if __name__ == "__main__":
    try:
        main()
    finally:
        driver.close()
