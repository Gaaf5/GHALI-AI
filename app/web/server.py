import json
import os
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from app.brain.brain import Brain
from app.database import Database, seed_default_raw_materials
from app.knowledge.store import KnowledgeStore
from app.llm.factory import create_llm
from app.memory import MemoryManager
from app.tools.formulation import solve_named_formulation
from app.web.auth import AuthManager

ROOT=Path(__file__).resolve().parent; STATIC=ROOT/'static'; STATE=None
class GHALIServer:
    def __init__(self):
        self.db=Database(); self.db.create_tables()
        if not self.db.list_raw_materials(): seed_default_raw_materials(self.db)
        self.memory=MemoryManager(); self.knowledge=KnowledgeStore(); self.brain=Brain(create_llm(),self.knowledge,self.memory)
        self.auth=AuthManager(self.db)
        self.auth.ensure_admin(os.getenv('GHALI_ADMIN_USER','ghaly'),os.getenv('GHALI_ADMIN_PASSWORD',''))
    def close(self): self.memory.close(); self.db.close()

def jb(data): return json.dumps(data,ensure_ascii=False).encode('utf-8')
class Handler(BaseHTTPRequestHandler):
    server_version='GHALI/0.4'
    def send_data(self,status,data,ctype='application/json; charset=utf-8'):
        body=data if isinstance(data,bytes) else data.encode(); self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
    def token(self):
        raw=self.headers.get('Cookie','');
        for part in raw.split(';'):
            if part.strip().startswith('ghali_session='): return part.strip().split('=',1)[1]
        return ''
    def user(self): return STATE.auth.user(self.token())
    def require(self,service):
        u=self.user()
        if not u: self.send_data(401,jb({'error':'Authentication required'})); return None
        if not STATE.auth.allowed(u,service): self.send_data(403,jb({'error':'Permission denied'})); return None
        return u

    def require_admin(self):
        u=self.require('admin')
        if not u: return None
        return u
    def do_GET(self):
        path=urlparse(self.path).path or '/'
        try:
            if self.path.strip()=='/' or path=='/': return self.send_data(200,(STATIC/'index.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/setup':
                owner_login=os.getenv('GHALI_OWNER_TAILSCALE_LOGIN','').strip().lower()
                ts_login=self.headers.get('Tailscale-User-Login','').strip().lower()
                if not owner_login or ts_login!=owner_login: return self.send_data(403,'Owner setup is available only from the authorized Tailscale identity','text/plain; charset=utf-8')
                if STATE.auth.list_users(): return self.send_data(403,'Setup already completed','text/plain; charset=utf-8')
                return self.send_data(200,b'''<!doctype html><meta name=viewport content=width=device-width><title>GHALI Setup</title><style>body{font:16px sans-serif;max-width:420px;margin:60px auto;padding:20px}input,button{width:100%;padding:12px;margin:8px 0;box-sizing:border-box}</style><h1>GHALI AI Setup</h1><p>Create the owner account. This page is available only from the local computer.</p><form method=post action=/api/setup><input name=username value=ghaly required><input name=password type=password minlength=8 placeholder='Owner password (8+ chars)' required><input name=confirm type=password minlength=8 placeholder='Confirm password' required><button>Create owner account</button></form>''','text/html; charset=utf-8')
            if path.startswith('/static/'):
                f=STATIC/path.removeprefix('/static/')
                if f.is_file() and f.resolve().is_relative_to(STATIC.resolve()): return self.send_data(200,f.read_bytes(),'text/css; charset=utf-8' if f.suffix=='.css' else 'application/javascript; charset=utf-8')
                return self.send_data(404,'Not found','text/plain; charset=utf-8')
            if path=='/api/me':
                u=self.user()
                admin_control=bool(u and u.get('role')=='admin')
                return self.send_data(200,jb(({'authenticated':True,**u,'admin_control':admin_control}) if u else {'authenticated':False}))
            if path=='/healthz':
                return self.send_data(200,jb({'ok':True,'app':'GHALI AI'}))
            if path=='/api/status':
                u=self.require('chat');
                if not u:return
                return self.send_data(200,jb(STATE.status()))
            if path=='/api/materials':
                u=self.require('materials');
                if not u:return
                return self.send_data(200,jb(STATE.db.list_raw_materials()))
            if path=='/api/knowledge':
                u=self.require('knowledge');
                if not u:return
                return self.send_data(200,jb(STATE.knowledge.list_documents()))
            if path=='/api/admin/users':
                u=self.require_admin();
                if not u:return
                return self.send_data(200,jb(STATE.auth.list_users()))
            if not path.startswith('/api/') and not path.startswith('/static/'):
                return self.send_data(200,(STATIC/'index.html').read_bytes(),'text/html; charset=utf-8')
            return self.send_data(404,jb({'error':'Not found','path':path,'raw':self.path}))
        except Exception as e: return self.send_data(500,jb({'error':str(e)}))
    def do_POST(self):
        path=urlparse(self.path).path or '/'
        try:
            d=self.body()
            if path=='/api/setup':
                owner_login=os.getenv('GHALI_OWNER_TAILSCALE_LOGIN','').strip().lower()
                ts_login=self.headers.get('Tailscale-User-Login','').strip().lower()
                if not owner_login or ts_login!=owner_login: return self.send_data(403,jb({'error':'Owner setup is available only from the authorized Tailscale identity'}))
                if STATE.auth.list_users(): return self.send_data(403,jb({'error':'Setup already completed'}))
                u=str(d.get('username','ghaly')).strip(); pw=str(d.get('password','')); cp=str(d.get('confirm',''))
                if len(pw)<8 or pw!=cp: return self.send_data(400,jb({'error':'Password must match and be at least 8 characters'}))
                STATE.auth.create_admin(u,pw); return self.send_data(200,b'<script>alert("Owner account created. You can now sign in.");location="/"</script>','text/html; charset=utf-8')
            if path=='/api/login':
                token=STATE.auth.login(str(d.get('username','')),str(d.get('password','')))
                if not token:return self.send_data(401,jb({'error':'Invalid username or password'}))
                self.send_data(200,jb({'ok':True}),); self._last_token=token; return
            if path=='/api/logout':
                STATE.auth.logout(self.token()); return self.send_data(200,jb({'ok':True}))
            if path=='/api/chat':
                if not self.require('chat'):return
                msg=str(d.get('message','')).strip()
                if not msg:return self.send_data(400,jb({'error':'Message is required'}))
                return self.send_data(200,jb({'reply':STATE.brain.think(msg)}))
            if path=='/api/formulate':
                if not self.require('formulation'):return
                r=solve_named_formulation(str(d['target']),float(d['batch_kg']),list(d['materials']),float(d.get('tolerance_pct',.2)),d.get('limits') or {},d.get('objective')); return self.send_data(200,jb(r))
            if path=='/api/materials':
                if not self.require('materials_admin'):return
                STATE.db.upsert_raw_material(d['name'],float(d.get('n_pct',0)),float(d.get('p2o5_pct',0)),float(d.get('k2o_pct',0)),d.get('moisture_pct'),d.get('assay_pct'),d.get('source','user'),bool(d.get('active',True))); return self.send_data(200,jb(STATE.db.list_raw_materials()))
            if path=='/api/materials/alias':
                if not self.require('materials_admin'):return
                STATE.db.add_raw_material_alias(d['material'],d['alias']); return self.send_data(200,jb({'ok':True}))
            if path=='/api/admin/users':
                if not self.require_admin():return
                STATE.auth.create_user(str(d['username']),str(d['password']),str(d.get('permissions','chat'))); return self.send_data(200,jb(STATE.auth.list_users()))
            if path=='/api/admin/permissions':
                if not self.require_admin():return
                STATE.auth.set_permissions(int(d['id']),str(d.get('permissions','chat'))); return self.send_data(200,jb({'ok':True}))
            if path=='/api/admin/active':
                if not self.require_admin():return
                STATE.auth.set_active(int(d['id']),bool(d.get('active',True))); return self.send_data(200,jb({'ok':True}))
            return self.send_data(404,jb({'error':'Not found'}))
        except (KeyError,ValueError,TypeError) as e:return self.send_data(400,jb({'error':str(e)}))
        except Exception as e:return self.send_data(500,jb({'error':str(e)}))
    def end_headers(self):
        if hasattr(self,'_last_token'): self.send_header('Set-Cookie',f'ghali_session={self._last_token}; Path=/; HttpOnly; SameSite=Lax; Secure'); del self._last_token
        super().end_headers()
    def status(self):
        model=getattr(STATE.brain.llm,'model','unknown')
        return {'app':'GHALI AI','version':'0.3.0','model':model,'materials':len(STATE.db.list_raw_materials()),'knowledge':len(STATE.knowledge.list_documents()),'memory':STATE.memory.count()}

    def log_message(self,*a): pass


def run(host='127.0.0.1',port=8765):
    global STATE
    STATE=GHALIServer()
    httpd=ThreadingHTTPServer((host,port),Handler)
    print(f'GHALI AI UI: http://{host}:{port}')
    try: httpd.serve_forever()
    finally: httpd.server_close(); STATE.close()
