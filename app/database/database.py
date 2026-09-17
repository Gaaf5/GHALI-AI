import sqlite3
from pathlib import Path

from app.core.settings import DATABASE_PATH


class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def create_tables(self):
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS raw_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            n_pct REAL NOT NULL DEFAULT 0,
            p2o5_pct REAL NOT NULL DEFAULT 0,
            k2o_pct REAL NOT NULL DEFAULT 0,
            moisture_pct REAL,
            assay_pct REAL,
            source TEXT NOT NULL DEFAULT 'project',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_raw_materials_active ON raw_materials(active);
        CREATE TABLE IF NOT EXISTS raw_material_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_material_id INTEGER NOT NULL,
            alias TEXT NOT NULL UNIQUE,
            FOREIGN KEY(raw_material_id) REFERENCES raw_materials(id)
        );
        """)
        self.connection.commit()

    def upsert_raw_material(self, name, n_pct=0, p2o5_pct=0, k2o_pct=0,
                            moisture_pct=None, assay_pct=None,
                            source="project", active=True):
        self.cursor.execute("""
            INSERT INTO raw_materials
                (name, n_pct, p2o5_pct, k2o_pct, moisture_pct, assay_pct, source, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                n_pct=excluded.n_pct, p2o5_pct=excluded.p2o5_pct,
                k2o_pct=excluded.k2o_pct, moisture_pct=excluded.moisture_pct,
                assay_pct=excluded.assay_pct, source=excluded.source,
                active=excluded.active, updated_at=CURRENT_TIMESTAMP
        """, (name, n_pct, p2o5_pct, k2o_pct, moisture_pct, assay_pct, source, int(active)))
        self.connection.commit()

    def list_raw_materials(self, active_only=True):
        sql = "SELECT * FROM raw_materials"
        if active_only:
            sql += " WHERE active=1"
        sql += " ORDER BY name"
        return [dict(row) for row in self.cursor.execute(sql).fetchall()]

    def get_raw_material(self, name):
        row = self.cursor.execute("SELECT * FROM raw_materials WHERE lower(name)=lower(?)", (name,)).fetchone()
        return dict(row) if row else None

    def add_raw_material_alias(self, material_name, alias):
        row = self.get_raw_material(material_name)
        if not row:
            raise ValueError(f"Raw material not found: {material_name}")
        self.cursor.execute(
            "INSERT OR REPLACE INTO raw_material_aliases(raw_material_id, alias) VALUES (?, ?)",
            (row["id"], alias.strip().lower()),
        )
        self.connection.commit()

    def resolve_raw_material(self, name):
        normalized = name.strip().lower()
        row = self.cursor.execute("""
            SELECT rm.* FROM raw_materials rm
            LEFT JOIN raw_material_aliases a ON a.raw_material_id = rm.id
            WHERE rm.active=1 AND (lower(rm.name)=? OR lower(a.alias)=?)
            LIMIT 1
        """, (normalized, normalized)).fetchone()
        return dict(row) if row else None

    def close(self):
        self.connection.close()

