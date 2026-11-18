import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from validators import stable_hash

class DailyBudgetExceeded(RuntimeError):
    pass

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class KGStore:
    def __init__(self, db_path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), timeout=60)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_key TEXT PRIMARY KEY,
            source_index INTEGER NOT NULL,
            chunk_id TEXT,
            source TEXT,
            crop TEXT,
            metadata_json TEXT NOT NULL,
            page_content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            model TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            triple_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS triples (
            triple_id TEXT PRIMARY KEY,
            chunk_key TEXT NOT NULL,
            subject TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            object_type TEXT NOT NULL,
            evidence TEXT NOT NULL,
            confidence REAL NOT NULL,
            qualifiers_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chunk_key) REFERENCES chunks(chunk_key)
        );

        CREATE TABLE IF NOT EXISTS rejected_triples (
            rejected_id TEXT PRIMARY KEY,
            chunk_key TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            reason TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chunk_key) REFERENCES chunks(chunk_key)
        );

        CREATE TABLE IF NOT EXISTS api_request_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utc_day TEXT NOT NULL,
            created_at TEXT NOT NULL,
            model TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_api_ledger_day ON api_request_ledger(utc_day);
        CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject);
        CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
        CREATE INDEX IF NOT EXISTS idx_triples_chunk ON triples(chunk_key);
        """)
        self.conn.commit()
        # Carry forward benchmark attempts already spent on 2026-10-26.
        import config
        today = datetime.now(timezone.utc).date().isoformat()
        if today == config.LEGACY_REQUESTS_DAY:
            existing = self.conn.execute(
                "SELECT COUNT(*) FROM api_request_ledger WHERE utc_day=?", (today,)
            ).fetchone()[0]
            if existing == 0:
                with self.conn:
                    self.conn.executemany(
                        "INSERT INTO api_request_ledger (utc_day, created_at, model) VALUES (?, ?, ?)",
                        [(today, utc_now(), "previous-benchmark-attempt") for _ in range(config.LEGACY_REQUESTS_USED)]
                    )

    def reserve_api_attempt(self, daily_limit):
        """Atomically count an attempt before sending it; retries count too."""
        day = datetime.now(timezone.utc).date().isoformat()
        now = utc_now()
        with self.conn:
            used = self.conn.execute(
                "SELECT COUNT(*) FROM api_request_ledger WHERE utc_day=?", (day,)
            ).fetchone()[0]
            if used >= daily_limit:
                raise DailyBudgetExceeded(
                    f"Daily OpenRouter request budget reached: {used}/{daily_limit} UTC. Resume after the UTC day resets."
                )
            self.conn.execute(
                "INSERT INTO api_request_ledger (utc_day, created_at, model) VALUES (?, ?, ?)",
                (day, now, "pending")
            )
            return used + 1

    def request_usage(self):
        day = datetime.now(timezone.utc).date().isoformat()
        used = self.conn.execute(
            "SELECT COUNT(*) FROM api_request_ledger WHERE utc_day=?", (day,)
        ).fetchone()[0]
        return {"utc_day": day, "attempts": used}

    def register_chunks(self, chunks):
        with self.conn:
            for chunk in chunks:
                self.conn.execute("""
                    INSERT OR IGNORE INTO chunks
                    (chunk_key, source_index, chunk_id, source, crop,
                     metadata_json, page_content, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    chunk["chunk_key"], chunk["source_index"],
                    str(chunk["metadata"].get("chunk_id", "")),
                    str(chunk["metadata"].get("source", "")),
                    str(chunk["metadata"].get("crop", chunk["metadata"].get("category", ""))),
                    json.dumps(chunk["metadata"], ensure_ascii=False, default=str),
                    chunk["page_content"]
                ))

    def get_pending_chunks(self, retry_failed=True):
        # A process killed during inference can leave a row in "processing".
        # Treat it as pending on the next launch so Ctrl+C/crashes are resumable.
        statuses = ("pending", "processing", "failed") if retry_failed else ("pending", "processing")
        marks = ",".join("?" for _ in statuses)
        rows = self.conn.execute(
            f"SELECT * FROM chunks WHERE status IN ({marks}) ORDER BY source_index",
            statuses
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_processing(self, chunk_key, model):
        with self.conn:
            self.conn.execute("""
                UPDATE chunks SET status='processing', model=?,
                attempts=attempts+1, error=NULL WHERE chunk_key=?
            """, (model, chunk_key))

    def save_success(self, chunk, triples, rejected, model):
        metadata = json.loads(chunk["metadata_json"])
        now = utc_now()
        with self.conn:
            for triple in triples:
                identity = {
                    "chunk_key": chunk["chunk_key"],
                    "subject": triple["subject"].casefold().strip(),
                    "subject_type": triple["subject_type"],
                    "predicate": triple["predicate"],
                    "object": triple["object"].casefold().strip(),
                    "object_type": triple["object_type"],
                    "evidence": triple["evidence"].casefold().strip(),
                    "qualifiers": triple["qualifiers"]
                }
                triple_id = stable_hash(json.dumps(
                    identity, sort_keys=True, ensure_ascii=False
                ))
                self.conn.execute("""
                    INSERT OR IGNORE INTO triples
                    (triple_id, chunk_key, subject, subject_type, predicate,
                     object, object_type, evidence, confidence, qualifiers_json,
                     metadata_json, model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    triple_id, chunk["chunk_key"], triple["subject"],
                    triple["subject_type"], triple["predicate"],
                    triple["object"], triple["object_type"],
                    triple["evidence"], triple["confidence"],
                    json.dumps(triple["qualifiers"], ensure_ascii=False),
                    json.dumps(metadata, ensure_ascii=False, default=str),
                    model, now
                ))

            for rejected_item in rejected:
                rejected_identity = json.dumps({
                    "chunk_key": chunk["chunk_key"],
                    "index": rejected_item.get("index"),
                    "reason": rejected_item.get("reason"),
                    "raw": rejected_item.get("raw"),
                }, sort_keys=True, ensure_ascii=False, default=str)
                self.conn.execute("""
                    INSERT OR IGNORE INTO rejected_triples
                    (rejected_id, chunk_key, item_index, reason, raw_json, metadata_json, model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stable_hash(rejected_identity), chunk["chunk_key"],
                    int(rejected_item.get("index", -1)), str(rejected_item.get("reason", "")),
                    json.dumps(rejected_item.get("raw"), ensure_ascii=False, default=str),
                    json.dumps(metadata, ensure_ascii=False, default=str), model, now
                ))

            self.conn.execute("""
                UPDATE chunks SET status='done', triple_count=?, rejected_count=?,
                error=NULL, processed_at=?, model=? WHERE chunk_key=?
            """, (
                len(triples), len(rejected), now, model, chunk["chunk_key"]
            ))

    def mark_failed(self, chunk_key, error):
        with self.conn:
            self.conn.execute("""
                UPDATE chunks SET status='failed', error=? WHERE chunk_key=?
            """, (str(error)[:4000], chunk_key))

    def stats(self):
        chunks = self.conn.execute("""
            SELECT status, COUNT(*) AS n FROM chunks GROUP BY status
        """).fetchall()
        triples = self.conn.execute("SELECT COUNT(*) FROM triples").fetchone()[0]
        rejected = self.conn.execute(
            "SELECT COALESCE(SUM(rejected_count),0) FROM chunks"
        ).fetchone()[0]
        return {
            "chunks": {r["status"]: r["n"] for r in chunks},
            "total_chunks": sum(r["n"] for r in chunks),
            "triples": triples,
            "rejected": rejected
        }

    def fetch_triples(self):
        rows = self.conn.execute("""
            SELECT t.*, c.source_index, c.chunk_id, c.source, c.crop
            FROM triples t JOIN chunks c ON t.chunk_key=c.chunk_key
            ORDER BY c.source_index, t.triple_id
        """).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["qualifiers"] = json.loads(item.pop("qualifiers_json"))
            item["metadata"] = json.loads(item.pop("metadata_json"))
            result.append(item)
        return result

    def fetch_chunk_status(self):
        return [dict(r) for r in self.conn.execute("""
            SELECT source_index, chunk_id, source, crop, status, attempts,
                   triple_count, rejected_count, error, processed_at
            FROM chunks ORDER BY source_index
        """).fetchall()]

    def fetch_rejected(self):
        rows = self.conn.execute("""
            SELECT r.*, c.source_index, c.chunk_id, c.source, c.crop
            FROM rejected_triples r JOIN chunks c ON r.chunk_key=c.chunk_key
            ORDER BY c.source_index, r.item_index
        """).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["raw"] = json.loads(item.pop("raw_json"))
            item["metadata"] = json.loads(item.pop("metadata_json"))
            result.append(item)
        return result

    def close(self):
        self.conn.close()

    def mark_pending(self, chunk_key, error=None):
        with self.conn:
            self.conn.execute(
                "UPDATE chunks SET status='pending', error=? WHERE chunk_key=?",
                (str(error)[:4000] if error else None, chunk_key)
            )
