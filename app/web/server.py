import json
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from app.brain.brain import Brain
from app.database import Database, seed_default_raw_materials
from app.knowledge.store import KnowledgeStore
from app.llm.factory import create_llm
from app.memory import MemoryManager
from app.tools.formulation import solve_named_formulation
from app.tools.lab import catalog as lab_catalog, simulate as lab_simulate
from app.knowledge.evidence import registry as evidence_registry
from app.web.auth import AuthManager

ROOT=Path(__file__).resolve().parent; STATIC=ROOT/'static'; STATE=None
MAX_BODY_BYTES=1_048_576
LOGIN_WINDOW=15*60
LOGIN_MAX_FAILURES=5
LOGIN_ATTEMPTS={}
LOGIN_LOCK=threading.Lock()
class GHALIServer:
    def __init__(self):
        self.db=Database(); self.db.create_tables()
        if not self.db.list_raw_materials(): seed_default_raw_materials(self.db)
        self.memory=MemoryManager(); self.knowledge=KnowledgeStore(); self.brain=Brain(create_llm(),self.knowledge,self.memory)
        self.auth=AuthManager(self.db)
        self.auth.ensure_admin(os.getenv('GHALI_ADMIN_USER','ghaly'),os.getenv('GHALI_ADMIN_PASSWORD',''))
    def close(self): self.memory.close(); self.db.close()
    def status(self):
        model=getattr(self.brain.llm,'model','unknown')
        return {'app':'GHALI AI','version':'0.4.0','model':model,'materials':len(self.db.list_raw_materials()),'knowledge':len(self.knowledge.list_documents()),'memory':self.memory.count()}

def jb(data): return json.dumps(data,ensure_ascii=False).encode('utf-8')
class Handler(BaseHTTPRequestHandler):
    server_version='GHALI/0.4'
    def send_data(self,status,data,ctype='application/json; charset=utf-8'):
        body=data if isinstance(data,bytes) else data.encode(); self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY'); self.send_header('Referrer-Policy','strict-origin-when-cross-origin'); self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'");
        if self.headers.get('X-Forwarded-Proto','').lower()=='https' or self.headers.get('Host','').endswith('.onrender.com'): self.send_header('Strict-Transport-Security','max-age=31536000; includeSubDomains');
        self.end_headers(); self.wfile.write(body)
    def body(self):
        try: n=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ValueError('Invalid Content-Length')
        if n<0 or n>MAX_BODY_BYTES: raise ValueError('Request body too large')
        raw=self.rfile.read(n) or b'{}'
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            # Some clients/proxies can concatenate JSON objects into one request body.
            # Accept that specific case by decoding consecutive object values and merging them.
            # Other malformed JSON remains a hard 400 error.
            text=raw.decode('utf-8-sig').lstrip()
            decoder=json.JSONDecoder()
            try:
                first,pos=decoder.raw_decode(text)
                values=[first]
                while text[pos:].strip():
                    tail=text[pos:]
                    stripped=tail.lstrip()
                    nxt,used=decoder.raw_decode(stripped)
                    values.append(nxt)
                    pos += len(tail) - len(stripped) + used
                if len(values)>1 and all(isinstance(v,dict) for v in values):
                    merged={}
                    for value in values: merged.update(value)
                    return merged
            except (UnicodeDecodeError,json.JSONDecodeError):
                pass
            raise exc
    def same_origin(self):
        origin=self.headers.get('Origin','').strip()
        if not origin: return True
        host=self.headers.get('Host','').strip()
        return origin in {f'https://{host}',f'http://{host}'}
    def client_ip(self):
        return self.headers.get('X-Forwarded-For',self.client_address[0]).split(',')[0].strip()
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
                setup_enabled=os.getenv('GHALI_ENABLE_SETUP','false').lower() in {'1','true','yes','on'}
                local_client=self.client_address[0] in {'127.0.0.1','::1'}
                if not setup_enabled or not local_client: return self.send_data(403,'Owner setup is disabled','text/plain; charset=utf-8')
                if STATE.auth.list_users(): return self.send_data(403,'Setup already completed','text/plain; charset=utf-8')
                return self.send_data(200,b'''<!doctype html><meta name=viewport content=width=device-width><title>GHALI Setup</title><style>body{font:16px sans-serif;max-width:420px;margin:60px auto;padding:20px}input,button{width:100%;padding:12px;margin:8px 0;box-sizing:border-box}</style><h1>GHALI AI Setup</h1><p>Create the owner account. This page is available only from the local computer.</p><form method=post action=/api/setup><input name=username value=ghaly required><input name=password type=password minlength=8 placeholder='Owner password (8+ chars)' required><input name=confirm type=password minlength=8 placeholder='Confirm password' required><button>Create owner account</button></form>''','text/html; charset=utf-8')
            if path.startswith('/static/'):
                f=STATIC/path.removeprefix('/static/')
                if f.is_file() and f.resolve().is_relative_to(STATIC.resolve()):
                    mime={'.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.ico':'image/x-icon'}.get(f.suffix.lower(),'application/octet-stream')
                    return self.send_data(200,f.read_bytes(),mime)
                return self.send_data(404,'Not found','text/plain; charset=utf-8')
            if path=='/api/me':
                u=self.user()
                admin_control=bool(u and u.get('role')=='admin')
                if u:
                    safe={k:v for k,v in u.items() if k!='password_hash'}
                    return self.send_data(200,jb({'authenticated':True,**safe,'admin_control':admin_control}))
                return self.send_data(200,jb({'authenticated':False}))
            if path=='/healthz':
                return self.send_data(200,jb({'ok':True,'app':'GHALI AI'}))
            if path=='/api/status':
                u=self.require('chat');
                if not u:return
                return self.send_data(200,jb(STATE.status()))
            if path=='/api/conversations':
                u=self.require('chat');
                if not u:return
                return self.send_data(200,jb(STATE.db.list_conversations(u['id'])))
            if path.startswith('/api/conversations/'):
                u=self.require('chat');
                if not u:return
                cid=int(path.rsplit('/',1)[1]); conv=STATE.db.get_conversation(cid,u['id'])
                if not conv:return self.send_data(404,jb({'error':'Conversation not found'}))
                return self.send_data(200,jb({'conversation':conv,'messages':STATE.db.get_messages(cid,u['id'])}))
            if path=='/api/materials':
                u=self.require('materials');
                if not u:return
                return self.send_data(200,jb(STATE.db.list_raw_materials()))
            if path=='/api/knowledge':
                u=self.require('knowledge');
                if not u:return
                docs=[]
                for path_item in STATE.knowledge.list_documents():
                    meta=STATE.knowledge.get_metadata(path_item)
                    docs.append({'title':meta.get('title',path_item.stem),'source':meta.get('source','project'),'type':meta.get('type','text'),'file':path_item.name})
                return self.send_data(200,jb(docs))
            if path=='/api/memory/candidates':
                u=self.require('chat')
                if not u:return
                rows=STATE.memory.store.candidates()
                return self.send_data(200,jb([dict(r) for r in rows]))
            if path=='/api/admin/users':
                u=self.require_admin();
                if not u:return
                return self.send_data(200,jb(STATE.auth.list_users()))
            if not path.startswith('/api/') and not path.startswith('/static/'):
                return self.send_data(200,(STATIC/'index.html').read_bytes(),'text/html; charset=utf-8')
            return self.send_data(404,jb({'error':'Not found','path':path,'raw':self.path}))
        except Exception:
            return self.send_data(500,jb({'error':'Internal server error'}))
    def do_POST(self):
        path=urlparse(self.path).path or '/'
        try:
            if not self.same_origin(): return self.send_data(403,jb({'error':'Cross-origin request blocked'}))
            d=self.body()
            if path=='/api/setup':
                setup_enabled=os.getenv('GHALI_ENABLE_SETUP','false').lower() in {'1','true','yes','on'}
                local_client=self.client_address[0] in {'127.0.0.1','::1'}
                if not setup_enabled or not local_client: return self.send_data(403,jb({'error':'Owner setup is disabled'}))
                if STATE.auth.list_users(): return self.send_data(403,jb({'error':'Setup already completed'}))
                u=str(d.get('username','ghaly')).strip(); pw=str(d.get('password','')); cp=str(d.get('confirm',''))
                if len(pw)<8 or pw!=cp: return self.send_data(400,jb({'error':'Password must match and be at least 8 characters'}))
                STATE.auth.create_admin(u,pw); return self.send_data(200,b'<script>alert("Owner account created. You can now sign in.");location="/"</script>','text/html; charset=utf-8')
            if path=='/api/conversations':
                u=self.require('chat')
                if not u:return
                title=str(d.get('title','New chat')).strip() or 'New chat'
                cid=STATE.db.create_conversation(u['id'],title)
                return self.send_data(200,jb({'id':cid,'title':title}))
            if path.startswith('/api/conversations/') and path.endswith('/rename'):
                u=self.require('chat')
                if not u:return
                cid=int(path.split('/')[-2]); STATE.db.rename_conversation(cid,u['id'],str(d.get('title','New chat')))
                return self.send_data(200,jb({'ok':True}))
            if path.startswith('/api/conversations/') and path.endswith('/delete'):
                u=self.require('chat')
                if not u:return
                cid=int(path.split('/')[-2]); STATE.db.delete_conversation(cid,u['id'])
                return self.send_data(200,jb({'ok':True}))
            if path=='/api/login':
                now=time.time(); ip=self.client_ip()
                with LOGIN_LOCK:
                    attempts=[t for t in LOGIN_ATTEMPTS.get(ip,[]) if now-t<LOGIN_WINDOW]
                    if len(attempts)>=LOGIN_MAX_FAILURES: return self.send_data(429,jb({'error':'Too many login attempts. Try again later.'}))
                token=STATE.auth.login(str(d.get('username','')),str(d.get('password','')))
                if not token:
                    with LOGIN_LOCK: LOGIN_ATTEMPTS[ip]=attempts+[now]
                    return self.send_data(401,jb({'error':'Invalid username or password'}))
                with LOGIN_LOCK: LOGIN_ATTEMPTS.pop(ip,None)
                self._last_token=token
                return self.send_data(200,jb({'ok':True}))
            if path=='/api/logout':
                STATE.auth.logout(self.token()); return self.send_data(200,jb({'ok':True}))
            if path=='/api/memory/candidates/resolve':
                u=self.require('chat')
                if not u:return
                cid=int(d.get('id',0)); accept=bool(d.get('accept',False))
                mid=STATE.memory.store.resolve_candidate(cid,accept)
                return self.send_data(200,jb({'ok':mid is not None if accept else True,'memory_id':mid}))
            if path=='/api/chat':
                u=self.require('chat')
                if not u:return
                msg=str(d.get('message','')).strip()
                if not msg:return self.send_data(400,jb({'error':'Message is required'}))
                cid=int(d.get('conversation_id') or 0)
                if not cid: cid=STATE.db.create_conversation(u['id'], msg[:55])
                history=STATE.db.get_messages(cid,u['id'])
                reply=STATE.brain.think(msg, history=history)
                STATE.db.add_message(cid,u['id'],'user',msg)
                STATE.db.add_message(cid,u['id'],'assistant',reply)
                return self.send_data(200,jb({'reply':reply,'conversation_id':cid}))
            if path=='/api/formulate':
                if not self.require('formulation'):return
                r=solve_named_formulation(str(d['target']),float(d['batch_kg']),list(d['materials']),float(d.get('tolerance_pct',.2)),d.get('limits') or {},d.get('objective')); return self.send_data(200,jb(r))
            if path=='/api/lab/run':
                u=self.require('chat')
                if not u:return
                result=lab_simulate(d)
                exp_id=STATE.db.save_lab_experiment(u['id'],str(d.get('name','Virtual experiment')),d,result)
                result['experiment_id']=exp_id
                return self.send_data(200,jb(result))
            if path=='/api/lab/ai-review':
                u=self.require('chat')
                if not u:return
                result=d.get('result') or {}
                if not isinstance(result,dict): return self.send_data(400,jb({'error':'Simulation result is required'}))
                prompt=(
                    "You are GHALI-AI's chemistry review layer. Review the supplied virtual fertilizer-mixing "
                    "simulation, but NEVER replace its deterministic numbers, invent solubility data, or claim "
                    "thermodynamic certainty. Check only logical consistency: mass balance, sequential addition, "
                    "shared aqueous phase, saturation, precipitation/common-ion warnings, and whether a result is "
                    "outside the evidence quality. Clearly distinguish source-backed facts, model estimates, and "
                    "uncertainty. If the deterministic engine says a later material has zero capacity because the "
                    "shared solution is saturated, explain that this is the simulator's conservative screening rule; "
                    "do not turn it into a universal physical law. Return concise Arabic with sections: الحكم، "
                    "ما هو منطقي، ما يحتاج حذر، والتجربة المقترحة للتحقق."
                )
                compact=json.dumps({
                    'conditions':result.get('conditions'),
                    'mass_balance':result.get('mass_balance'),
                    'dissolved_g':result.get('dissolved_g'),
                    'undissolved_g':result.get('undissolved_g'),
                    'dissolution':result.get('dissolution'),
                    'chemistry':result.get('chemistry'),
                    'warnings':result.get('warnings'),
                    'events':result.get('events'),
                },ensure_ascii=False)[:30000]
                try:
                    review=STATE.brain.llm.chat([{'role':'system','content':prompt},
                                                 {'role':'user','content':compact}])
                except Exception as exc:
                    return self.send_data(503,jb({'error':'AI review unavailable','detail':str(exc)[:240]}))
                return self.send_data(200,jb({'review':review,'mode':'constrained_ai_review'}))
            if path=='/api/lab/materials':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(lab_catalog()))
            if path=='/api/lab/sources':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb({'sources':evidence_registry(), 'policy':{
                    'no_uncited_numbers':True,
                    'principle':'Every source-backed laboratory number must retain source, basis, temperature/range and evidence class.',
                    'model_note':'Product TDS data are grade-specific; pure-water solubility is not a mixed-fertilizer equilibrium model.'
                }}))
            if path=='/api/lab/experiments':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(STATE.db.list_lab_experiments(u['id'])))
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
        except (KeyError,ValueError,TypeError,json.JSONDecodeError) as e:return self.send_data(400,jb({'error':str(e)}))
        except Exception:
            return self.send_data(500,jb({'error':'Internal server error'}))
    def end_headers(self):
        if hasattr(self,'_last_token'):
            secure = self.headers.get('X-Forwarded-Proto','').lower() == 'https' or self.headers.get('Host','').endswith('.onrender.com')
            cookie = f'ghali_session={self._last_token}; Path=/; HttpOnly; SameSite=Lax' + ('; Secure' if secure else '')
            self.send_header('Set-Cookie', cookie)
            del self._last_token
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
