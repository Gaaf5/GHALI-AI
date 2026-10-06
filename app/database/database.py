import sqlite3
import json
from pathlib import Path

from app.core.settings import DATABASE_PATH


class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or DATABASE_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.execute("PRAGMA foreign_keys=ON")
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
            s_pct REAL NOT NULL DEFAULT 0,
            n_nitrate_pct REAL NOT NULL DEFAULT 0,
            n_ammoniacal_pct REAL NOT NULL DEFAULT 0,
            n_urea_pct REAL NOT NULL DEFAULT 0,
            trace_elements_json TEXT NOT NULL DEFAULT '{}',
            mg_pct REAL NOT NULL DEFAULT 0,
            chlorine_pct REAL NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'project',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_raw_materials_active ON raw_materials(active);
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES auth_users(id)
        );
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON conversation_messages(conversation_id, id);
        CREATE TABLE IF NOT EXISTS lab_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT 'Virtual experiment',
            input_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            validated INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES auth_users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_lab_experiments_user ON lab_experiments(user_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS formulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            formulation_no TEXT NOT NULL UNIQUE,
            target_json TEXT NOT NULL,
            batch_kg REAL NOT NULL,
            materials_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES auth_users(id)
        );
        CREATE TABLE IF NOT EXISTS production_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            batch_no TEXT NOT NULL UNIQUE,
            formulation_id INTEGER,
            production_order_no TEXT,
            planned_kg REAL NOT NULL DEFAULT 0,
            actual_kg REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'planned',
            theoretical_json TEXT NOT NULL DEFAULT '{}',
            actual_json TEXT NOT NULL DEFAULT '{}',
            variance_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES auth_users(id),
            FOREIGN KEY(formulation_id) REFERENCES formulations(id)
        );
        CREATE TABLE IF NOT EXISTS qc_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            batch_id INTEGER NOT NULL,
            sample_id TEXT NOT NULL DEFAULT '',
            results_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES auth_users(id),
            FOREIGN KEY(batch_id) REFERENCES production_batches(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS raw_material_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_material_id INTEGER NOT NULL,
            alias TEXT NOT NULL UNIQUE,
            FOREIGN KEY(raw_material_id) REFERENCES raw_materials(id)
        );
        """)
        # Lightweight migration for databases created before nutrient-form tracking.
        existing={r[1] for r in self.cursor.execute("PRAGMA table_info(raw_materials)").fetchall()}
        migrations={
            "s_pct":"ALTER TABLE raw_materials ADD COLUMN s_pct REAL NOT NULL DEFAULT 0",
            "n_nitrate_pct":"ALTER TABLE raw_materials ADD COLUMN n_nitrate_pct REAL NOT NULL DEFAULT 0",
            "n_ammoniacal_pct":"ALTER TABLE raw_materials ADD COLUMN n_ammoniacal_pct REAL NOT NULL DEFAULT 0",
            "n_urea_pct":"ALTER TABLE raw_materials ADD COLUMN n_urea_pct REAL NOT NULL DEFAULT 0",
            "trace_elements_json":"ALTER TABLE raw_materials ADD COLUMN trace_elements_json TEXT NOT NULL DEFAULT '{}'",
            "mg_pct":"ALTER TABLE raw_materials ADD COLUMN mg_pct REAL NOT NULL DEFAULT 0",
            "chlorine_pct":"ALTER TABLE raw_materials ADD COLUMN chlorine_pct REAL NOT NULL DEFAULT 0",
        }
        for column,sql in migrations.items():
            if column not in existing:self.cursor.execute(sql)
        self.connection.commit()

    def upsert_raw_material(self, name, n_pct=0, p2o5_pct=0, k2o_pct=0,
                            moisture_pct=None, assay_pct=None, source="project",
                            active=True, s_pct=0, n_nitrate_pct=0,
                            n_ammoniacal_pct=0, n_urea_pct=0, trace_elements=None, mg_pct=0, chlorine_pct=0):
        self.cursor.execute("""
            INSERT INTO raw_materials
                (name,n_pct,p2o5_pct,k2o_pct,moisture_pct,assay_pct,s_pct,
                 n_nitrate_pct,n_ammoniacal_pct,n_urea_pct,trace_elements_json,mg_pct,chlorine_pct,source,active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                n_pct=excluded.n_pct,p2o5_pct=excluded.p2o5_pct,k2o_pct=excluded.k2o_pct,
                moisture_pct=excluded.moisture_pct,assay_pct=excluded.assay_pct,
                s_pct=excluded.s_pct,n_nitrate_pct=excluded.n_nitrate_pct,
                n_ammoniacal_pct=excluded.n_ammoniacal_pct,n_urea_pct=excluded.n_urea_pct,
                trace_elements_json=excluded.trace_elements_json,mg_pct=excluded.mg_pct,
                chlorine_pct=excluded.chlorine_pct,source=excluded.source,
                active=excluded.active,updated_at=CURRENT_TIMESTAMP
        """, (name,n_pct,p2o5_pct,k2o_pct,moisture_pct,assay_pct,s_pct,
              n_nitrate_pct,n_ammoniacal_pct,n_urea_pct,
              json.dumps(trace_elements or {},ensure_ascii=False),mg_pct,chlorine_pct,source,int(active)))
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

    def create_conversation(self, user_id, title="New chat"):
        self.cursor.execute("INSERT INTO conversations(user_id,title) VALUES(?,?)", (user_id, title.strip() or "New chat"))
        self.connection.commit()
        return self.cursor.lastrowid

    def list_conversations(self, user_id):
        rows = self.cursor.execute("SELECT id,title,created_at,updated_at FROM conversations WHERE user_id=? ORDER BY updated_at DESC,id DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, conversation_id, user_id):
        row = self.cursor.execute("SELECT * FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone()
        return dict(row) if row else None

    def get_messages(self, conversation_id, user_id, limit=24):
        rows = self.cursor.execute("SELECT m.role,m.content,m.created_at FROM conversation_messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.conversation_id=? AND c.user_id=? ORDER BY m.id DESC LIMIT ?", (conversation_id, user_id, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def add_message(self, conversation_id, user_id, role, content):
        if not self.get_conversation(conversation_id, user_id): raise ValueError("Conversation not found")
        self.cursor.execute("INSERT INTO conversation_messages(conversation_id,role,content) VALUES(?,?,?)", (conversation_id, role, content))
        self.cursor.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?", (conversation_id, user_id))
        self.connection.commit()

    def rename_conversation(self, conversation_id, user_id, title):
        self.cursor.execute("UPDATE conversations SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?", (title.strip() or "New chat", conversation_id, user_id))
        self.connection.commit()

    def delete_conversation(self, conversation_id, user_id):
        self.cursor.execute("DELETE FROM conversation_messages WHERE conversation_id=? AND conversation_id IN (SELECT id FROM conversations WHERE user_id=?)", (conversation_id, user_id))
        self.cursor.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
        self.connection.commit()

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

    def save_lab_experiment(self, user_id, name, input_data, result_data, validated=False, notes=''):
        import json
        self.cursor.execute(
            "INSERT INTO lab_experiments(user_id,name,input_json,result_json,validated,notes) VALUES(?,?,?,?,?,?)",
            (user_id, name.strip() or 'Virtual experiment', json.dumps(input_data,ensure_ascii=False),
             json.dumps(result_data,ensure_ascii=False), int(bool(validated)), notes)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def list_lab_experiments(self, user_id, limit=30):
        import json
        rows=self.cursor.execute(
            "SELECT id,name,input_json,result_json,validated,notes,created_at FROM lab_experiments WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id,int(limit))).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            d['input']=json.loads(d.pop('input_json'))
            d['result']=json.loads(d.pop('result_json'))
            out.append(d)
        return out

    def save_formulation(self, user_id, target, batch_kg, materials, result, status='draft'):
        import uuid
        no='FORM-'+uuid.uuid4().hex[:8].upper()
        self.cursor.execute(
            "INSERT INTO formulations(user_id,formulation_no,target_json,batch_kg,materials_json,result_json,status) VALUES(?,?,?,?,?,?,?)",
            (user_id,no,json.dumps(target,ensure_ascii=False),float(batch_kg),json.dumps(materials,ensure_ascii=False),
             json.dumps(result,ensure_ascii=False),status))
        self.connection.commit()
        return self.cursor.lastrowid, no

    def get_formulation(self, user_id, formulation_id):
        import json
        row=self.cursor.execute("SELECT id,formulation_no,target_json,batch_kg,materials_json,result_json,status,created_at FROM formulations WHERE id=? AND user_id=?",(int(formulation_id),user_id)).fetchone()
        if not row:return None
        d=dict(row)
        d["target"]=json.loads(d.pop("target_json") or "{}")
        d["materials"]=json.loads(d.pop("materials_json") or "{}")
        d["result"]=json.loads(d.pop("result_json") or "{}")
        return d

    def list_formulations(self, user_id, limit=50):
        import json
        rows=self.cursor.execute("SELECT id,formulation_no,target_json,batch_kg,materials_json,result_json,status,created_at FROM formulations WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,int(limit))).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            d["target"]=json.loads(d.pop("target_json") or "{}")
            d["materials"]=json.loads(d.pop("materials_json") or "{}")
            d["result"]=json.loads(d.pop("result_json") or "{}")
            out.append(d)
        return out

    def get_production_batch(self, user_id, batch_id):
        import json
        row=self.cursor.execute("SELECT * FROM production_batches WHERE id=? AND user_id=?",(int(batch_id),user_id)).fetchone()
        if not row:return None
        d=dict(row)
        for key in ("theoretical_json","actual_json","variance_json"):
            d[key[:-5]]=json.loads(d.pop(key) or "{}")
        return d

    def list_qc_results(self, user_id, batch_id=None, limit=50):
        import json
        if batch_id is None:
            rows=self.cursor.execute("SELECT * FROM qc_results WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,int(limit))).fetchall()
        else:
            rows=self.cursor.execute("SELECT * FROM qc_results WHERE user_id=? AND batch_id=? ORDER BY id DESC LIMIT ?",(user_id,int(batch_id),int(limit))).fetchall()
        out=[]
        for r in rows:
            d=dict(r); d["results"]=json.loads(d.pop("results_json") or "{}"); out.append(d)
        return out

    def save_production_batch(self, user_id, batch_no, formulation_id, order_no, planned_kg, theoretical):
        self.cursor.execute(
            "INSERT INTO production_batches(user_id,batch_no,formulation_id,production_order_no,planned_kg,theoretical_json) VALUES(?,?,?,?,?,?)",
            (user_id,batch_no,formulation_id,order_no,float(planned_kg),json.dumps(theoretical,ensure_ascii=False)))
        self.connection.commit()
        return self.cursor.lastrowid

    def update_production_actuals(self, user_id, batch_id, actuals, actual_total=None, status='completed'):
        row=self.cursor.execute("SELECT * FROM production_batches WHERE id=? AND user_id=?",(int(batch_id),user_id)).fetchone()
        if not row: raise ValueError("Production batch not found")
        theoretical=json.loads(row["theoretical_json"] or '{}')
        actual_total=float(actual_total if actual_total is not None else sum(float(v) for v in actuals.values()))
        variance={}
        for name in set(theoretical)|set(actuals):
            t=float(theoretical.get(name,0)); a=float(actuals.get(name,0))
            variance[name]={"theoretical_kg":t,"actual_kg":a,"delta_kg":a-t,"delta_pct":(a-t)*100/t if t else None}
        self.cursor.execute("UPDATE production_batches SET actual_kg=?,actual_json=?,variance_json=?,status=? WHERE id=? AND user_id=?",
                            (actual_total,json.dumps(actuals,ensure_ascii=False),json.dumps(variance,ensure_ascii=False),status,int(batch_id),user_id))
        self.connection.commit()
        return variance

    def save_qc_result(self, user_id, batch_id, sample_id, results, status='approved', notes=''):
        self.cursor.execute("INSERT INTO qc_results(user_id,batch_id,sample_id,results_json,status,notes) VALUES(?,?,?,?,?,?)",
                            (user_id,int(batch_id),sample_id,json.dumps(results,ensure_ascii=False),status,notes))
        self.connection.commit()
        return self.cursor.lastrowid

    def release_production_batch(self, user_id, batch_id):
        row=self.cursor.execute("SELECT id,status FROM production_batches WHERE id=? AND user_id=?",(int(batch_id),user_id)).fetchone()
        if not row: raise ValueError("Production batch not found")
        self.cursor.execute("UPDATE production_batches SET status='released' WHERE id=? AND user_id=?",(int(batch_id),user_id))
        self.connection.commit()
        return True

    def manufacturing_overview(self, user_id):
        import json
        f=self.cursor.execute("SELECT COUNT(*) n FROM formulations WHERE user_id=?",(user_id,)).fetchone()["n"]
        b=self.cursor.execute("SELECT COUNT(*) n FROM production_batches WHERE user_id=?",(user_id,)).fetchone()["n"]
        q=self.cursor.execute("SELECT COUNT(*) n FROM qc_results WHERE user_id=?",(user_id,)).fetchone()["n"]
        recent=self.cursor.execute("SELECT id,batch_no,production_order_no,planned_kg,actual_kg,status,variance_json FROM production_batches WHERE user_id=? ORDER BY id DESC LIMIT 10",(user_id,)).fetchall()
        return {"formulations":f,"batches":b,"qc_results":q,"recent_batches":[dict(x) for x in recent]}

    def close(self):
        self.connection.close()

