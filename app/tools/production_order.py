import json
from io import BytesIO
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

def build_production_order(payload):
    payload = payload or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.sheet_view.showGridLines = False
    white = PatternFill("solid", fgColor="FFFFFF")
    thin = Side(style="thin", color="000000")
    medium = Side(style="medium", color="000000")
    dashed = Side(style="dashed", color="000000")
    F = lambda bold=False, italic=False, size=10: Font(name="Times New Roman", size=size, bold=bold, italic=italic)
    C = Alignment(horizontal="center", vertical="center")
    L = Alignment(horizontal="left", vertical="center")
    def put(a,v=None,b=False,al=None,bd=None,nf=None,fill=True,it=False,sz=10):
        c=ws[a]; c.value=v; c.font=F(b,it,sz); c.alignment=al or L
        if bd: c.border=bd
        if nf: c.number_format=nf
        if fill: c.fill=white
        return c
    def tb(top=medium,bottom=dashed):
        return Border(left=medium,right=medium,top=top,bottom=bottom)
    for col,w in {"A":8.27,"B":21.72,"C":36.20,"D":11.45,"E":13.45,"F":10.55}.items():
        ws.column_dimensions[col].width=w
    for r,h in {1:17.4,3:15.6,5:15.6,15:13.95,17:13.95,39:13.95}.items():
        ws.row_dimensions[r].height=h
    fmt1=r'#,##0.0_);[Red]\(#,##0.0\)'
    fmt2='#,##0.00'
    fmt0='#,##0'

    put("B1","Manaseer Natural Solutions MNS Factory",True,L,None,None,True,False,14)
    put("A3","Production Report",True,L,None,None,True,False,12)
    put("A4","Date: "+str(payload.get("date") or date.today().strftime("%d/%m/%Y")),True)
    put("B6","Formula:-",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    formula=payload.get("formula","")
    if isinstance(formula,dict):
        formula=f"{formula.get('N',0)}-{formula.get('P2O5',formula.get('P',0))}-{formula.get('K2O',formula.get('K',0))}"
    put("C6",formula,True,C,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("D6",payload.get("color",""))

    batch=float(payload.get("batch_kg") or 0)
    required=float(payload.get("required_ton") or 0)
    batches=float(payload.get("batches") or ((required*1000/batch) if batch else 1))
    put("B9","Kg / batch:-",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("C9",batch,False,C,Border(left=thin,right=thin,top=thin,bottom=thin),fmt0)
    put("D9",payload.get("client",""))
    put("B10","Order no.:-",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("C10",payload.get("order_no",""),False,C,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("D10",payload.get("brand") or payload.get("bag_type",""),True)
    put("B11","Required quantity(ton)",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("C11",required,False,C,Border(left=thin,right=thin,top=thin,bottom=thin),fmt2)
    put("B12","No. of batches:-",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("C12",batches,False,C,Border(left=thin,right=thin,top=thin,bottom=thin),fmt2)
    put("B13","Kg produced:-",True,None,Border(left=thin,right=thin,top=thin,bottom=thin))
    put("C13","=C9*C12",False,C,Border(left=thin,right=thin,top=thin,bottom=thin),fmt0)

    for i,h in enumerate(["Silo no.","Raw material","Kg / ton","Kg / batch","Total theo.","Total actual"],1):
        put(f"{chr(64+i)}16",h,True,C,Border(left=medium,right=medium,top=medium,bottom=Side(style=None)))
    for i,v in enumerate(["","Basis 1000Kg","","","kg","kg"],1):
        put(f"{chr(64+i)}17",v,True,C,Border(left=medium,right=medium,top=Side(style=None),bottom=medium))

    mats=payload.get("materials") or {}
    if not isinstance(mats,dict): mats={}
    def norm(x): return " ".join(str(x).strip().lower().split())
    additive_names={"red color","foom silica","mgso4 33%","mgso4","aquamine","fe eddha 6%","disper chlorophy","te-mix","te- mix edta","te mix","te-mix edta"}
    raw=[]; add={}
    for name,kg in mats.items():
        if norm(name) in additive_names: add[norm(name)]=float(kg or 0)
        else: raw.append((str(name),float(kg or 0)))
    n=max(6,len(raw)); extra=n-6
    if extra: ws.insert_rows(24,extra)
    rs,re=18,17+n; sub=re+1
    for r in range(rs,re+1):
        for c in range(1,7):
            x=ws.cell(r,c); x.font=F(); x.border=tb(); x.alignment=C if c>=3 else L
    for r,(name,kg) in enumerate(raw,rs):
        put(f"B{r}",name,False,L,tb(),None,False)
        put(f"C{r}",kg*1000/batch if batch else 0,False,C,tb(),fmt1,False)
        put(f"D{r}",f"=C{r}*$C$9/1000",False,C,tb(),fmt2,False)
        put(f"E{r}",f"=D{r}*$C$12",False,C,tb(),fmt2,False)
        put(f"F{r}","",False,C,tb(),fmt2,False)
    put(f"B{sub}","Sub total:-",True,L,tb(dashed,medium))
    put(f"C{sub}",f"=SUM(C{rs}:C{re})",False,C,tb(dashed,medium),fmt1)
    put(f"D{sub}",f"=C{sub}*$C$9/1000",False,C,tb(dashed,medium),fmt2)
    put(f"E{sub}",f"=SUM(E{rs}:E{re})",False,C,tb(dashed,medium),fmt2)
    put(f"F{sub}","",False,C,tb(dashed,medium),fmt2)

    add_title=sub+2; add_start=add_title+1
    add_rows=[
        ("Red Color",float(payload.get("color_qty") or add.get("red color",0))),
        ("Foom Silica",float(payload.get("foom_silica") or add.get("foom silica",0))),
        ("MgSO4 33%",add.get("mgso4 33%",add.get("mgso4",0))),
        ("Aquamine",add.get("aquamine",0)),
        ("Fe EDDHA 6%",add.get("fe eddha 6%",0)),
        ("Disper Chlorophy",add.get("disper chlorophy",0)),
        ("TE- MIX EDTA",float(payload.get("te_mix_kg_per_ton") or 0)),
    ]
    add_end=add_start+len(add_rows)-1; total=add_end+1
    put(f"B{add_title}","Additives:-",True,L,tb(medium,dashed))
    for r,(name,val) in enumerate(add_rows,add_start):
        put(f"A{r}","",False,L,tb(),None,True)
        put(f"B{r}",name,name in {"Foom Silica","MgSO4 33%","TE- MIX EDTA"},L,tb())
        put(f"C{r}",val,True,C,tb(),fmt2)
        put(f"D{r}",f"=C{r}*$C$9/1000",False,C,tb(),fmt2)
        put(f"E{r}",f"=D{r}*$C$12",False,C,tb(),fmt2)
        put(f"F{r}","",False,C,tb(),fmt2)
    put(f"B{total}","Total",True,L,Border(left=medium,right=medium,top=medium,bottom=medium))
    put(f"C{total}",f"=SUM(C{sub}:C{add_end})",False,C,Border(left=medium,right=medium,top=medium,bottom=medium),fmt2)
    put(f"D{total}",f"=C{total}*$C$9/1000",False,C,Border(left=medium,right=medium,top=medium,bottom=medium),fmt2)
    put(f"E{total}",f"=SUM(E{sub}:E{add_end})",False,C,Border(left=medium,right=medium,top=medium,bottom=medium),fmt2)
    put(f"F{total}","",False,C,Border(left=medium,right=medium,top=medium,bottom=medium),fmt2)

    r41=total+2
    for rr,label in [(r41,"Total No. of bags produced (20Kg)"),(r41+1,"type of bags"),(r41+2,"No. of pallets Produced :-"),(r41+3,"No. of bags per pallet:-")]:
        for c in range(1,4):
            put(f"{chr(64+c)}{rr}","",False,L,Border(left=dashed,right=dashed,top=dashed,bottom=dashed))
        put(f"A{rr}",label)
    put(f"E{r41}","Marks")
    put(f"B{r41+1}",payload.get("bag_type",""))
    r47=r41+6
    for rr,label in [(r47,"Total production ="),(r47+1,"Reusable waste ="),(r47+2,"waste ="),(r47+3,"total working hours =")]:
        put(f"A{rr}",label,False,L,Border(left=dashed,right=dashed,top=dashed,bottom=dashed))
    put(f"D{r47}","Kg"); put(f"D{r47+1}","Kg"); put(f"D{r47+2}","Kg")
    put(f"E{r47+1}","Invesible waste ="); put(f"E{r47+2}","Defect (%) =")

    r52=r41+11
    put(f"A{r52}","Brackdown details",True)
    for c,v in enumerate(["No.","Description","","","","Stopping Hours"],1):
        put(f"{chr(64+c)}{r52+1}",v,False,L,Border(left=thin,right=dashed,top=thin,bottom=dashed))
    put(f"A{r52+5}","Control room",True,L,None,None,False,True)
    put(f"F{r52+5}","Plant Manager",True,L,None,None,False,True)
    put(f"A{r52+6}","supervisor sign.",True,L,None,None,False,True)

    ws.print_area=f"A1:H{r52+6}"
    ws.page_setup.orientation="portrait"; ws.page_setup.paperSize=1
    ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=None
    ws.page_margins.left=.75; ws.page_margins.right=.75; ws.page_margins.top=.5; ws.page_margins.bottom=.5
    ws.freeze_panes="A16"
    out=BytesIO(); wb.save(out); return out.getvalue()
