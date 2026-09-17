from __future__ import annotations
import itertools
from typing import Mapping
from scipy.optimize import linprog
from app.database import Database, seed_default_raw_materials

NUTRIENTS=("N","P2O5","K2O")
RAW_MATERIALS={
"urea":{"N":46.0,"P2O5":0.0,"K2O":0.0},"map":{"N":12.0,"P2O5":61.0,"K2O":0.0},
"mkp":{"N":0.0,"P2O5":52.0,"K2O":34.0},"sop":{"N":0.0,"P2O5":0.0,"K2O":50.0},
"nop":{"N":13.5,"P2O5":0.0,"K2O":46.0},"potassium nitrate":{"N":13.5,"P2O5":0.0,"K2O":46.0},
"ammonium nitrate":{"N":34.0,"P2O5":0.0,"K2O":0.0},"ammonium sulfate":{"N":21.0,"P2O5":0.0,"K2O":0.0},
"urea phosphate":{"N":17.0,"P2O5":44.0,"K2O":0.0},"bentonite":{"N":0.0,"P2O5":0.0,"K2O":0.0},
"xanthan gum":{"N":0.0,"P2O5":0.0,"K2O":0.0}}

def _parse_grade(target):
    parts=target.strip().replace("–","-").replace("—","-").split("-")
    if len(parts)!=3: raise ValueError("Target grade must look like N-P2O5-K2O")
    try:return tuple(float(x.strip()) for x in parts)
    except ValueError as e:raise ValueError("Target grade must contain numeric N-P2O5-K2O values") from e

def _bounds(names,batch,limits):
    out=[]
    for n in names:
        cfg=(limits or {}).get(n,{}) or {}; lo=float(cfg.get("min_kg",0) or 0); hi=cfg.get("max_kg",None)
        hi=batch if hi in (None,"") else float(hi)
        if lo<0 or hi<0 or lo>hi: raise ValueError(f"Invalid min/max for {n}")
        out.append((lo,min(hi,batch)))
    return out

def _nutrient_matrix(names,mats,batch):
    return [[float(mats[n].get(k,0))/batch for n in names] for k in NUTRIENTS]

def _exact(names,mats,target,batch,tol,limits,objective):
    A=_nutrient_matrix(names,mats,batch); Aub=[];bub=[]
    for row,t in zip(A,target):
        Aub += [row,[-v for v in row]]; bub += [t+tol,-(t-tol)]
    c=[0.0]*len(names)
    if objective and objective[0] in names:c[names.index(objective[0])]=-1.0 if objective[1]=="max" else 1.0
    r=linprog(c,A_ub=Aub,b_ub=bub,A_eq=[[1.0]*len(names)],b_eq=[batch],bounds=_bounds(names,batch,limits),method="highs")
    return list(r.x) if r.success else None

def _closest(names,mats,target,batch,limits):
    n=len(names);A=_nutrient_matrix(names,mats,batch);c=[0.0]*n+[1.0]*3;Aub=[];bub=[]
    for i,(row,t) in enumerate(zip(A,target)):
        coeff=row+[0.0,0.0,0.0]
        r1=coeff[:];r1[n+i]-=1;Aub.append(r1);bub.append(t)
        r2=[-v for v in coeff];r2[n+i]-=1;Aub.append(r2);bub.append(-t)
    r=linprog(c,A_ub=Aub,b_ub=bub,A_eq=[[1.0]*n+[0.0]*3],b_eq=[batch],
              bounds=_bounds(names,batch,limits)+[(0,None)]*3,method="highs")
    return list(r.x[:n]) if r.success else None

def _grades(names,masses,mats,batch):
    total={k:0.0 for k in NUTRIENTS}
    for n,m in zip(names,masses):
        for k in NUTRIENTS:total[k]+=m*float(mats[n].get(k,0))/100.0
    return {k:total[k]/batch*100.0 for k in NUTRIENTS}

def _result(status,masses,batch,target,achieved,tol,objective,reason=None):
    return {"status":status,"reason":reason,"tolerance_pct":tol,
            "target_range":{k:{"target":target[i],"min":target[i]-tol,"max":target[i]+tol} for i,k in enumerate(NUTRIENTS)},
            "materials":{n:float(m) for n,m in masses.items() if m>1e-7},"batch_kg":float(batch),
            "target":dict(zip(NUTRIENTS,target)),"achieved":achieved,
            "deviation":{k:achieved[k]-target[i] for i,k in enumerate(NUTRIENTS)},
            "objective":{"material":objective[0],"direction":objective[1]} if objective else None}

def solve_formulation(target_n,target_p2o5,target_k2o,batch_kg,materials,tolerance=0.2,limits=None,objective=None):
    if batch_kg<=0:raise ValueError("batch_kg must be positive")
    target=(float(target_n),float(target_p2o5),float(target_k2o));names=list(dict(materials).keys())
    x=_exact(names,materials,target,batch_kg,float(tolerance),limits,objective)
    if x is not None:return _result("FEASIBLE",dict(zip(names,x)),batch_kg,target,_grades(names,x,materials,batch_kg),float(tolerance),objective)
    x=_closest(names,materials,target,batch_kg,limits)
    if x is None:raise ValueError("No formulation can satisfy the batch mass and the supplied material min/max limits.")
    return _result("NOT_FEASIBLE",dict(zip(names,x)),batch_kg,target,_grades(names,x,materials,batch_kg),float(tolerance),objective,
                   "The requested formulation cannot be reached with the selected materials and limits. The closest achievable formulation is shown below.")

def suggest_additions(selected,all_materials,target,batch,tolerance=0.2,limits=None,max_results=5):
    selected=list(dict.fromkeys(selected));available=[n for n in all_materials if n not in selected];out=[]
    def test(add):
        names=selected+list(add)
        try:
            r=solve_formulation(*target,batch,{n:all_materials[n] for n in names},tolerance,limits)
            err=sum(abs(r["achieved"][k]-target[i]) for i,k in enumerate(NUTRIENTS))
            return {"add":list(add),"status":r["status"],"error":0.0 if r["status"]=="FEASIBLE" else err,"achieved":r["achieved"],"materials":r["materials"]}
        except Exception:return None
    for n in available:
        r=test([n])
        if r:out.append(r)
    out.sort(key=lambda x:(x["status"]!="FEASIBLE",x["error"]))
    if not any(x["status"]=="FEASIBLE" for x in out):
        for a,b in itertools.combinations(available,2):
            r=test([a,b])
            if r:out.append(r)
        out.sort(key=lambda x:(x["status"]!="FEASIBLE",x["error"]))
    return out[:max_results]

def solve_named_formulation(target,batch_kg,material_names,tolerance=0.2,limits=None,objective=None):
    tn,tp,tk=_parse_grade(target);db=Database()
    try:
        db.create_tables()
        if not db.list_raw_materials(active_only=True):seed_default_raw_materials(db)
        selected={};unknown=[]
        for raw in material_names:
            row=db.resolve_raw_material(raw)
            if not row:unknown.append(raw);continue
            selected[row["name"]]={"N":float(row["n_pct"]),"P2O5":float(row["p2o5_pct"]),"K2O":float(row["k2o_pct"])}
        if unknown:raise ValueError("Unknown or inactive raw material(s): "+", ".join(unknown))
        if not selected:raise ValueError("At least one active raw material is required")
        cl={}
        for name,cfg in (limits or {}).items():
            row=db.resolve_raw_material(name)
            if row:cl[row["name"]]=cfg
        obj=None
        if objective and objective.get("material"):
            row=db.resolve_raw_material(objective["material"])
            if not row:raise ValueError("Optimization material was not found")
            direction=str(objective.get("direction","max")).lower()
            if direction not in ("min","max"):raise ValueError("Objective direction must be min or max")
            obj=(row["name"],direction)
            if obj[0] not in selected:raise ValueError("Optimization material must be selected")
        result=solve_formulation(tn,tp,tk,batch_kg,selected,tolerance,cl,obj)
        if result["status"]=="NOT_FEASIBLE":
            rows=db.list_raw_materials(active_only=True)
            allm={r["name"]:{"N":float(r["n_pct"]),"P2O5":float(r["p2o5_pct"]),"K2O":float(r["k2o_pct"])} for r in rows}
            result["suggestions"]=suggest_additions(list(selected),allm,(tn,tp,tk),batch_kg,tolerance,cl)
        return result
    finally:db.close()
