import json
import os
import time
import threading
from io import BytesIO
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from app.brain.brain import Brain
from app.database import Database, seed_default_raw_materials
from app.database.raw_materials import ensure_extended_nutrient_metadata
from app.knowledge.store import KnowledgeStore
from app.llm.factory import create_llm
from app.memory import MemoryManager
from app.tools.formulation import solve_named_formulation, analyze_blend_quantities
from app.tools.coa import build_certificate_of_analysis
from app.tools.lab import catalog as lab_catalog, simulate as lab_simulate
from app.knowledge.evidence import registry as evidence_registry
from app.tools.equilibrium_engine import engine_status
from app.knowledge.chemical_mapping import get_mapping, mapped_materials
from app.knowledge.thermo_db import build_seed_tdb
from app.tools.phreeqc_generator import build_input as build_phreeqc_input
from app.tools.phreeqc_adapter import discover_phreeqc, run_phreeqc
from app.tools.model_selector import select_activity_model, water_analysis_to_molal
from app.tools.manufacturing import production_readiness, build_theoretical_batch, material_variance, batch_kpis, qc_status, workflow_state, qc_limits_from_formulation, batch_release_state
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
        ensure_extended_nutrient_metadata(self.db)
        self.memory=MemoryManager(); self.knowledge=KnowledgeStore(); self.brain=Brain(create_llm(),self.knowledge,self.memory)
        self.auth=AuthManager(self.db)
        self.auth.ensure_admin(os.getenv('GHALI_ADMIN_USER','ghaly'),os.getenv('GHALI_ADMIN_PASSWORD',''))
    def close(self): self.memory.close(); self.db.close()
    def status(self):
        model=getattr(self.brain.llm,'model','unknown')
        return {'app':'GHALI AI','version':'0.4.0','model':model,'materials':len(self.db.list_raw_materials()),'knowledge':len(self.knowledge.list_documents()),'memory':self.memory.count()}

def jb(data): return json.dumps(data,ensure_ascii=False).encode('utf-8')

def build_production_order(payload):
    from openpyxl import Workbook
    def excel_value(value):
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        return value
    def formula_value(value):
        if isinstance(value, dict):
            n=value.get('N'); p=value.get('P2O5', value.get('P')); k=value.get('K2O', value.get('K'))
            if n is not None and p is not None and k is not None:
                return f'{n}-{p}-{k}'
        return excel_value(value)
    from openpyxl.styles import Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb=Workbook(); ws=wb.active; ws.title='Production Order'
    ws.sheet_view.showGridLines=False
    widths={1:13,2:28,3:15,4:15,5:15,6:15,7:16}
    for col,w in widths.items(): ws.column_dimensions[get_column_letter(col)].width=w
    thin=Side(style='thin',color='808080')
    border=Border(left=thin,right=thin,top=thin,bottom=thin)
    bold=Font(bold=True)
    title=Font(bold=True,size=16)
    center=Alignment(horizontal='center',vertical='center',wrap_text=True)
    left=Alignment(horizontal='left',vertical='center',wrap_text=True)

    ws.merge_cells('B1:F1'); ws['B1']='Manaseer Natural Solutions MNS Factory'; ws['B1'].font=title; ws['B1'].alignment=center
    ws['A3']='Production Report'; ws['A3'].font=Font(bold=True,size=14)
    ws['A4']='Date: '+str(payload.get('date') or date.today().strftime('%d/%m/%Y'))
    ws['B6']='Formula:-'; ws['C6']=formula_value(payload.get('formula',''))
    ws['B9']='Kg / batch:-'; ws['C9']=float(payload.get('batch_kg') or 0)
    ws['B10']='Order no.:-'; ws['C10']=payload.get('order_no','')
    ws['B11']='Required quantity(ton)'; ws['C11']=float(payload.get('required_ton') or 0)
    ws['B12']='No. of batches:-'; ws['C12']=float(payload.get('batches') or 1)
    ws['B13']='Kg produced:-'; ws['C13']='=C9*C12'
    for c in ['B6','B9','B10','B11','B12','B13']: ws[c].font=bold

    ws['A16']='Silo no.'; ws['B16']='Raw material'; ws['C16']='Kg / ton'; ws['D16']='Kg / batch'; ws['E16']='Total theo.'; ws['F16']='Total actual'
    ws['C17']='Basis 1000Kg'; ws['E17']='kg'; ws['F17']='kg'
    for row in range(16,18):
        for col in range(1,7): ws.cell(row,col).border=border; ws.cell(row,col).font=bold; ws.cell(row,col).alignment=center

    materials=payload.get('materials') or {}
    row=18
    for name,kg in materials.items():
        kg=float(kg or 0)
        ws.cell(row,2,excel_value(name)); ws.cell(row,3,kg*1000/max(float(payload.get('batch_kg') or 1),1))
        ws.cell(row,4,kg); ws.cell(row,5,f'=D{row}*$C$12'); ws.cell(row,6,f'=E{row}')
        row+=1
    while row<=23:
        ws.cell(row,5,f'=D{row}*$C$12'); row+=1
    ws['B24']='Sub total:-'; ws['C24']='=SUM(C18:C23)'; ws['D24']='=SUM(D18:D23)'; ws['E24']='=SUM(E18:E23)'; ws['F24']='=SUM(F18:F23)'

    ws['B26']='Additives:-'; ws['B26'].font=bold
    additives=[('Red Color',payload.get('color_qty',0)),('Foom Silica',payload.get('foom_silica',0)),('MgSO4 33%',0),('Aquamine',0),('Fe EDDHA 6%',0),('Disper Chlorophy',0),('TE- MIX EDTA',payload.get('te_mix_kg_per_ton',0))]
    row=27
    for name,kg_ton in additives:
        ws.cell(row,2,name); ws.cell(row,3,float(kg_ton or 0)); ws.cell(row,4,f'=C{row}*$C$9/1000'); ws.cell(row,5,f'=D{row}*$C$12'); row+=1
    while row<=38:
        ws.cell(row,4,f'=C{row}*$C$9/1000'); ws.cell(row,5,f'=D{row}*$C$12'); row+=1
    ws['B39']='Total'; ws['C39']='=SUM(C24:C38)'; ws['D39']='=SUM(D24:D38)'; ws['E39']='=SUM(E24:E38)'; ws['F39']='=SUM(F24:F38)'
    for row in list(range(18,25))+list(range(27,40)):
        for col in range(1,7): ws.cell(row,col).border=border; ws.cell(row,col).alignment=left
    ws['A41']='Total No. of bags produced (20Kg)'; ws['E41']='Marks'
    ws['A42']='type of bags'; ws['B42']=payload.get('bag_type','')
    ws['A43']='No. of pallets Produced :-'; ws['B43']=''
    ws['A44']='No. of bags per pallet:-'; ws['B44']=''
    ws['A47']='Total production ='; ws['D47']='Kg'
    ws['A48']='Reusable waste ='; ws['D48']='Kg'; ws['E48']='Invesible waste ='
    ws['A49']='waste ='; ws['D49']='Kg'; ws['E49']='Defect (%) ='
    ws['A50']='total working hours ='
    ws['A52']='Brackdown details'; ws['A53']='No.'; ws['B53']='Description'; ws['F53']='Stopping Hours'
    ws['A57']='Control room'; ws['F57']='Plant Manager'; ws['A58']='supervisor sign.'
    for row in [41,42,43,44,47,48,49,50,52,53,57,58]:
        for col in range(1,7): ws.cell(row,col).border=border; ws.cell(row,col).alignment=left
    ws.print_area='A1:F58'; ws.page_setup.orientation='portrait'; ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=1
    ws.freeze_panes='A16'
    out=BytesIO(); wb.save(out); return out.getvalue()

# Standard P.O. layout overrides the legacy builder above.
from app.tools.production_order import build_production_order

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
            if path=='/api/manufacturing/overview':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(STATE.db.manufacturing_overview(u['id'])))
            if path=='/api/formulations':
                u=self.require('formulation')
                if not u:return
                return self.send_data(200,jb(STATE.db.list_formulations(u['id'])))
            if path.startswith('/api/production-batches/'):
                u=self.require('formulation')
                if not u:return
                try: bid=int(path.rsplit('/',1)[1])
                except ValueError:return self.send_data(400,jb({'error':'Invalid batch id'}))
                batch=STATE.db.get_production_batch(u['id'],bid)
                if not batch:return self.send_data(404,jb({'error':'Production batch not found'}))
                batch['qc_results']=STATE.db.list_qc_results(u['id'],bid)
                formulation=STATE.db.get_formulation(u['id'],batch.get('formulation_id')) if batch.get('formulation_id') else None
                batch['qc_limits']=qc_limits_from_formulation(formulation or {})
                batch['release']=batch_release_state(batch,formulation,batch['qc_results'])
                return self.send_data(200,jb(batch))
            if path=='/api/qc-results':
                u=self.require('formulation')
                if not u:return
                return self.send_data(200,jb(STATE.db.list_qc_results(u['id'])))
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
                u=self.require('formulation')
                if not u:return
                r=solve_named_formulation(str(d['target']),float(d['batch_kg']),list(d['materials']),float(d.get('tolerance_pct',.2)),d.get('limits') or {},d.get('objective'),d.get('fixed_kg') or {})
                rows=STATE.db.list_raw_materials()
                r['readiness']=production_readiness(r,rows)
                fid,fno=STATE.db.save_formulation(u['id'],d.get('target'),float(d['batch_kg']),r.get('materials') or {},r,r.get('status','draft'))
                r['formulation_id']=fid; r['formulation_no']=fno
                return self.send_data(200,jb(r))
            if path=='/api/analyze-blend':
                if not self.require('formulation'):return
                quantities=d.get('materials') or {}
                if not isinstance(quantities,dict): return self.send_data(400,jb({'error':'materials must be an object of material name -> kg'}))
                r=analyze_blend_quantities(quantities)
                return self.send_data(200,jb(r))
            if path=='/api/reverse-coa':
                if not self.require('formulation'):return
                try:
                    body=build_certificate_of_analysis(d if isinstance(d,dict) else {})
                    filename='Certificate_of_Analysis.xlsx'
                    self.send_response(200)
                    self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers(); self.wfile.write(body)
                except Exception as exc:
                    return self.send_data(500,jb({'error':'Could not create Certificate of Analysis','detail':str(exc)[:300]}))
                return
            if path=='/api/production-order':
                if not self.require('formulation'):return
                try:
                    payload=d if isinstance(d,dict) else {}
                    body=build_production_order(payload)
                    filename='Production_Order.xlsx'
                    self.send_response(200)
                    self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers(); self.wfile.write(body)
                except Exception as exc:
                    return self.send_data(500,jb({'error':'Could not create Production Order','detail':str(exc)[:300]}))
                return
            if path=='/api/manufacturing/overview':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(STATE.db.manufacturing_overview(u['id'])))
            if path=='/api/manufacturing/readiness':
                if not self.require('formulation'):return
                result=d.get('result') or {}
                return self.send_data(200,jb(production_readiness(result,STATE.db.list_raw_materials())))
            if path=='/api/production-batch':
                u=self.require('formulation')
                if not u:return
                formulation=d.get('formulation')
                formulation_id=d.get('formulation_id')
                if not formulation and formulation_id:
                    saved=STATE.db.get_formulation(u['id'],int(formulation_id))
                    if not saved:return self.send_data(404,jb({'error':'Formulation not found'}))
                    formulation=saved.get('result') or saved
                theoretical=build_theoretical_batch(formulation or d)
                import uuid
                batch_no=str(d.get('batch_no') or ('BATCH-'+uuid.uuid4().hex[:8].upper()))
                planned=float(d.get('planned_kg') or (formulation or {}).get('batch_kg') or 0)
                if planned<=0:return self.send_data(400,jb({'error':'Planned production quantity must be positive'}))
                bid=STATE.db.save_production_batch(u['id'],batch_no,formulation_id,d.get('order_no',''),planned,theoretical)
                return self.send_data(200,jb({'batch_id':bid,'batch_no':batch_no,'theoretical':theoretical}))
            if path=='/api/production-batch/actuals':
                u=self.require('formulation')
                if not u:return
                actuals=d.get('actuals') or {}
                variance=STATE.db.update_production_actuals(u['id'],int(d['batch_id']),actuals,d.get('actual_total'),str(d.get('status','completed')))
                row=STATE.db.cursor.execute("SELECT planned_kg,actual_kg FROM production_batches WHERE id=? AND user_id=?",(int(d['batch_id']),u['id'])).fetchone()
                return self.send_data(200,jb({'variance':variance,'kpis':batch_kpis(row['planned_kg'],row['actual_kg'],variance)}))
            if path=='/api/qc-result':
                u=self.require('formulation')
                if not u:return
                bid=int(d['batch_id'])
                batch=STATE.db.get_production_batch(u['id'],bid)
                if not batch:return self.send_data(404,jb({'error':'Production batch not found'}))
                formulation=STATE.db.get_formulation(u['id'],batch.get('formulation_id')) if batch.get('formulation_id') else None
                results=d.get('results') or {}
                limits=qc_limits_from_formulation(formulation or {})
                if d.get('limits'): limits=d.get('limits')
                audit=qc_status(results,limits)
                qid=STATE.db.save_qc_result(u['id'],bid,str(d.get('sample_id','')),results,audit['status'],str(d.get('notes','')))
                release=batch_release_state(batch,formulation,STATE.db.list_qc_results(u['id'],bid))
                return self.send_data(200,jb({'qc_id':qid,'limits':limits,**audit,'release':release}))
            if path=='/api/production-batch-po':
                u=self.require('formulation')
                if not u:return
                try:
                    bid=int(d.get('batch_id'))
                    batch=STATE.db.get_production_batch(u['id'],bid)
                    if not batch:return self.send_data(404,jb({'error':'Production batch not found'}))
                    payload={
                        'order_no':batch.get('production_order_no') or batch.get('batch_no'),
                        'batch_kg':batch.get('planned_kg') or 0,
                        'base_kg':batch.get('planned_kg') or 0,
                        'materials':batch.get('theoretical') or {},
                    }
                    if batch.get('formulation_id'):
                        formulation=STATE.db.get_formulation(u['id'],batch['formulation_id'])
                        if formulation:
                            result=formulation.get('result') or {}
                            payload.update({
                                'formula':result.get('target') or formulation.get('target'),
                                'base_kg':formulation.get('batch_kg') or batch.get('planned_kg') or 0,
                                'materials':result.get('materials') or batch.get('theoretical') or {},
                                'te_mix_kg_per_ton':((result.get('materials') or {}).get('TE-MIX',0)*1000/(formulation.get('batch_kg') or 1)),
                            })
                    body=build_production_order(payload)
                    self.send_response(200)
                    self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition',f'attachment; filename="Production_Order_{batch.get("batch_no")}.xlsx"')
                    self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
                except Exception as exc:
                    return self.send_data(500,jb({'error':'Could not create Production Order','detail':str(exc)[:300]}))
                return
            if path=='/api/production-batch-coa':
                u=self.require('formulation')
                if not u:return
                try:
                    bid=int(d.get('batch_id'))
                    batch=STATE.db.get_production_batch(u['id'],bid)
                    if not batch:return self.send_data(404,jb({'error':'Production batch not found'}))
                    payload={}
                    if batch.get('formulation_id'):
                        formulation=STATE.db.get_formulation(u['id'],batch['formulation_id'])
                        if formulation: payload.update(formulation.get('result') or {})
                    qc=STATE.db.list_qc_results(u['id'],bid,1)
                    if qc:
                        payload['achieved']={**(payload.get('achieved') or {}),**(qc[0].get('results') or {})}
                    body=build_certificate_of_analysis(payload)
                    self.send_response(200)
                    self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition','attachment; filename="Certificate_of_Analysis.xlsx"')
                    self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
                except Exception as exc:
                    return self.send_data(500,jb({'error':'Could not create Certificate of Analysis','detail':str(exc)[:300]}))
                return
            if path=='/api/qc-coa':
                if not self.require('formulation'):return
                try:
                    body=build_certificate_of_analysis(d if isinstance(d,dict) else {})
                    filename='Certificate_of_Analysis.xlsx'
                    self.send_response(200)
                    self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
                    self.send_header('Content-Length',str(len(body)))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers(); self.wfile.write(body)
                except Exception as exc:
                    return self.send_data(500,jb({'error':'Could not create Certificate of Analysis','detail':str(exc)[:300]}))
                return
            if path=='/api/workflow-state':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(workflow_state(d.get('formulation'),d.get('production'),d.get('qc'))))
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
                    "outside the evidence quality. Audit the state_timeline as the primary experiment ledger: verify "
                    "that later additions do not receive an independent pure-water capacity, and flag any apparent "
                    "increase/decrease in dissolved mass as a state transition that must be explained by equilibrium "
                    "repartitioning, kinetics, precipitation, or redissolution. Never infer an event-time species "
                    "concentration from the final state. Clearly distinguish source-backed facts, model estimates, and "
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
                    'state_timeline':result.get('state_timeline'),
                    'reaction_timeline':result.get('reaction_timeline'),
                    'warnings':result.get('warnings'),
                    'events':result.get('events'),
                    'quality':result.get('quality'),
                    'next_experiments':result.get('next_experiments'),
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
            if path=='/api/lab/engine':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(engine_status()))
            if path=='/api/lab/chemical-mapping':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb({'materials':mapped_materials(), 'tdb_audit':build_seed_tdb().audit()}))
            if path=='/api/lab/model-selection':
                u=self.require('chat')
                if not u:return
                d0=d.get('water_analysis') or {}
                molal=water_analysis_to_molal(d0,float(d.get('water_kg',1.0)))
                # Charge-weighted ionic-strength estimate from the explicit ions we know.
                charges={'Ca':2,'Mg':2,'Na':1,'K':1,'NH4':1,'Cl':-1,'SO4':-2,'HCO3':-1,'CO3':-2,'NO3':-1,'F':-1,'PO4':-3,'Fe':2,'Zn':2}
                I=0.0
                for k,m in molal.items(): I += 0.5*m*(charges.get(k,0)**2)
                return self.send_data(200,jb(select_activity_model(I,bool(discover_phreeqc().get('available')))))
            if path=='/api/lab/phreeqc':
                u=self.require('chat')
                if not u:return
                try:
                    water_kg=float(d.get('water_kg',1.0))
                    result=build_phreeqc_input(list(d.get('additions') or []),water_kg,
                                               float(d.get('temperature_c',25.0)),float(d.get('pH',7.0)))
                    result['engine_discovery']=discover_phreeqc()
                    if bool(d.get('execute')):
                        result['execution']=run_phreeqc(result['input'],database=d.get('database'))
                    return self.send_data(200,jb(result))
                except (ValueError,TypeError) as e:
                    return self.send_data(400,jb({'error':str(e)}))
            if path=='/api/lab/experiments':
                u=self.require('chat')
                if not u:return
                return self.send_data(200,jb(STATE.db.list_lab_experiments(u['id'])))
            if path=='/api/materials':
                if not self.require('materials_admin'):return
                STATE.db.upsert_raw_material(d['name'],float(d.get('n_pct',0)),float(d.get('p2o5_pct',0)),float(d.get('k2o_pct',0)),d.get('moisture_pct'),d.get('assay_pct'),d.get('source','user'),bool(d.get('active',True)),float(d.get('s_pct',0)),float(d.get('n_nitrate_pct',0)),float(d.get('n_ammoniacal_pct',0)),float(d.get('n_urea_pct',0)),d.get('trace_elements') or {},float(d.get('mg_pct',0)),float(d.get('chlorine_pct',0))); return self.send_data(200,jb(STATE.db.list_raw_materials()))
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
