import json
from pathlib import Path
from config import SAMPLE_TRIPLES_PATH
from graph.neo4j_connection import Neo4jConnection
from graph.entity_resolution import entity_id
from graph.schema import create_constraints

def load_triples(path=SAMPLE_TRIPLES_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    triples = data["triples"] if isinstance(data, dict) else data
    required = {"subject","subject_type","predicate","object","object_type","evidence"}
    for i,t in enumerate(triples):
        missing = required - set(t)
        if missing: raise ValueError(f"Triple {i} missing: {sorted(missing)}")
    return triples

def import_triples(db, triples):
    create_constraints(db)
    # WARNING: clears Entity nodes; use a dedicated demo database only.
    db.run("MATCH (e:Entity) DETACH DELETE e")
    for t in triples:
        params = {
          "sid":entity_id(t["subject"],t["subject_type"]), "sname":t["subject"], "stype":t["subject_type"],
          "oid":entity_id(t["object"],t["object_type"]), "oname":t["object"], "otype":t["object_type"],
          "predicate":t["predicate"], "evidence":t["evidence"],
          "confidence":float(t.get("confidence",1.0)),
          "qualifiers":json.dumps(t.get("qualifiers",{}),ensure_ascii=False), "source":t.get("source","unknown")
        }
        db.run("""
        MERGE (s:Entity {entity_id:$sid})
          ON CREATE SET s.name=$sname, s.entity_type=$stype
        MERGE (o:Entity {entity_id:$oid})
          ON CREATE SET o.name=$oname, o.entity_type=$otype
        MERGE (s)-[r:FACT {predicate:$predicate,evidence:$evidence,source:$source}]->(o)
        SET r.confidence=$confidence, r.qualifiers_json=$qualifiers
        """, params)
    return len(triples)

def main():
    db=Neo4jConnection()
    try:
        db.verify()
        count=import_triples(db,load_triples())
        print(f"Imported {count} illustrative facts into Neo4j.")
        print("In Neo4j Browser: MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 50")
    finally: db.close()
if __name__=="__main__": main()
