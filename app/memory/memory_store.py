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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.connection.commit()

    def add(self, content, category="general", importance=1):
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.connection.execute(
            "INSERT INTO memories (category, content, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (category, content.strip(), importance, now, now),
        )
        self.connection.commit()
        return cursor.lastrowid

    def find_similar(self, content, category=None):
        normalized = " ".join(content.lower().split())
        if not normalized:
            return []
        if category:
            rows = self.connection.execute(
                "SELECT id, category, content, importance, created_at, updated_at FROM memories WHERE category = ?",
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
            "SELECT id, category, content, importance, created_at, updated_at FROM memories"
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

