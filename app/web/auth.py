import hashlib
import secrets
import time

SESSION_TTL = 60 * 60 * 24 * 7
PBKDF2_ROUNDS = 240000

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()
    return f"pbkdf2${PBKDF2_ROUNDS}${salt}${digest}"

def verify_password(password, encoded):
    try:
        _, rounds, salt, digest = encoded.split("$", 3)
        test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return secrets.compare_digest(test, digest)
    except Exception:
        return False

class AuthManager:
    def __init__(self, db):
        self.db=db; self.sessions={}
        self._ensure_schema()
    def _ensure_schema(self):
        self.db.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS auth_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', active INTEGER NOT NULL DEFAULT 1, permissions TEXT NOT NULL DEFAULT 'chat', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """)
        self.db.connection.commit()
    def ensure_admin(self, username, password):
        row=self.db.cursor.execute("SELECT id FROM auth_users WHERE role='admin' LIMIT 1").fetchone()
        if not row and username and password:
            self.db.cursor.execute("INSERT INTO auth_users(username,password_hash,role,permissions) VALUES(?,?,?,?)",(username,hash_password(password),'admin','*'))
            self.db.connection.commit()
    def create_admin(self,username,password):
        self.db.cursor.execute("INSERT INTO auth_users(username,password_hash,role,permissions) VALUES(?,?,?,?)",(username.strip(),hash_password(password),'admin','*')); self.db.connection.commit()
    def login(self, username, password):
        row=self.db.cursor.execute("SELECT * FROM auth_users WHERE lower(username)=lower(?) AND active=1",(username.strip(),)).fetchone()
        if not row or not verify_password(password,row['password_hash']): return None
        token=secrets.token_urlsafe(32); self.sessions[token]=(dict(row),time.time()+SESSION_TTL); return token
    def user(self, token):
        item=self.sessions.get(token)
        if not item: return None
        user,expires=item
        if expires<time.time(): self.sessions.pop(token,None); return None
        return user
    def logout(self,token): self.sessions.pop(token,None)
    def allowed(self,user,service):
        return bool(user and (user['role']=='admin' or service in user['permissions'].split(',')))
    def list_users(self):
        rows=self.db.cursor.execute("SELECT id,username,role,active,permissions,created_at FROM auth_users ORDER BY username").fetchall(); return [dict(r) for r in rows]
    def create_user(self,username,password,permissions):
        username=username.strip(); permissions=','.join(sorted(set(p.strip() for p in permissions.split(',') if p.strip())))
        if not username or len(password)<8: raise ValueError('Username required and password must be at least 8 characters')
        self.db.cursor.execute("INSERT INTO auth_users(username,password_hash,role,permissions) VALUES(?,?,?,?)",(username,hash_password(password),'user',permissions or 'chat')); self.db.connection.commit()
    def set_permissions(self,user_id,permissions):
        self.db.cursor.execute("UPDATE auth_users SET permissions=? WHERE id=? AND role!='admin'",(permissions,user_id)); self.db.connection.commit()
    def set_active(self,user_id,active):
        self.db.cursor.execute("UPDATE auth_users SET active=? WHERE id=? AND role!='admin'",(int(active),user_id)); self.db.connection.commit()
