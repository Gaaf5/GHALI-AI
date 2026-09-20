import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path="data/ghali.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'confirmed',
                source TEXT NOT NULL DEFAULT 'manual',
                confidence REAL NOT NULL DEFAULT 1.0,
                use_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._migrate()
        self.connection.commit()

    def _migrate(self):
        cols = {r[1] for r in self.connection.execute("PRAGMA table_info(memories)").fetchall()}
        additions = {
            "status": "ALTER TABLE memories ADD COLUMN status TEXT NOT NULL DEFAULT 'confirmed'",
            "source": "ALTER TABLE memories ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'",
            "confidence": "ALTER TABLE memories ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0",
            "use_count": "ALTER TABLE memories ADD COLUMN use_count INTEGER NOT NULL DEFAULT 0",
        }
        for name, sql in additions.items():
            if name not in cols:
                self.connection.execute(sql)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS memory_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            importance INTEGER NOT NULL DEFAULT 2,
            confidence REAL NOT NULL DEFAULT 0.5,
            source TEXT NOT NULL DEFAULT 'conversation',
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )""")

    def add(self, content, category="general", importance=1, source="manual", confidence=1.0, status="confirmed"):
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.connection.execute(
            "INSERT INTO memories (category, content, importance, status, source, confidence, use_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (category, content.strip(), importance, status, source, float(confidence), now, now),
        )
        self.connection.commit()
        return cursor.lastrowid

    def add_candidate(self, content, category="general", importance=2, confidence=0.5, source="conversation"):
        now = datetime.now(timezone.utc).isoformat()
        cur = self.connection.execute(
            "INSERT INTO memory_candidates(content, category, importance, confidence, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (content.strip(), category, importance, float(confidence), source, now),
        )
        self.connection.commit()
        return cur.lastrowid

    def candidates(self, limit=50):
        return self.connection.execute(
            "SELECT id, category, content, importance, confidence, source, created_at, status FROM memory_candidates WHERE status='pending' ORDER BY confidence DESC, created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def resolve_candidate(self, candidate_id, accept=True):
        row = self.connection.execute("SELECT * FROM memory_candidates WHERE id=?", (candidate_id,)).fetchone()
        if not row:
            return None
        memory_id = self.add(row[1], row[2], row[3], row[5], row[4], "confirmed") if accept else None
        self.connection.execute("UPDATE memory_candidates SET status=? WHERE id=?", ("accepted" if accept else "rejected", candidate_id))
        self.connection.commit()
        return memory_id

    def find_similar(self, content, category=None):
        normalized = " ".join(content.lower().split())
        if not normalized:
            return []
        if category:
            rows = self.connection.execute(
                "SELECT id, category, content, importance, created_at, updated_at FROM memories WHERE status='confirmed' AND category = ?",
                (category,),
            ).fetchall()
        else:
            rows = self.list(100)
        return [row for row in rows if " ".join(row[2].lower().split()) == normalized]

    def search(self, query, limit=5):
        terms = [term.lower() for term in query.split() if len(term) > 2]
        if not terms:
            return []
        rows = self.connection.execute(
            "SELECT id, category, content, importance, created_at, updated_at FROM memories WHERE status='confirmed'"
        ).fetchall()
        scored = []
        for row in rows:
            text = row[2].lower()
            matched = sum(term in text for term in terms)
            if matched:
                score = (matched / len(terms)) * 5 + min(row[3], 5)
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], -item[1][3], item[1][0]))
        return [row for _, row in scored[:limit]]

    def list(self, limit=50):
        return self.connection.execute(
            "SELECT id, category, content, importance, created_at, updated_at FROM memories ORDER BY importance DESC, updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def delete(self, memory_id):
        self.connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.connection.commit()

    def count(self):
        return self.connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def get(self, memory_id):
        return self.connection.execute(
            "SELECT id, category, content, importance, created_at, updated_at FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()

    def close(self):
        self.connection.close()

