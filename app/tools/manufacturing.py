from __future__ import annotations
import math
from collections import defaultdict

def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def material_variance(theoretical, actual):
    names=set(theoretical or {})|set(actual or {})
    out={}
    for name in sorted(names):
        t=_f((theoretical or {}).get(name)); a=_f((actual or {}).get(name))
        out[name]={
            "theoretical_kg":round(t,6),
            "actual_kg":round(a,6),
            "delta_kg":round(a-t,6),
            "delta_pct":round((a-t)*100/t,4) if t else None,
        }
    return out

def validate_formulation(result, material_rows=None):
    warnings=[]
    errors=[]
    result=result or {}
    if result.get("status")!="FEASIBLE":
        errors.append("Formulation is not feasible within the selected tolerance.")
    batch=_f(result.get("batch_kg"))
    if batch<=0:
        errors.append("Batch mass must be positive.")
    nutrients=result.get("achieved") or {}
    target=result.get("target") or {}
    for key in ("N","P2O5","K2O"):
        if key in target and key in nutrients:
            delta=_f(nutrients[key])-_f(target[key])
            tol=_f(result.get("tolerance_pct",0))
            if abs(delta)>tol+1e-9:
                errors.append(f"{key} is outside the allowed deviation.")
    rows={str(r.get("name","")).lower():r for r in (material_rows or [])}
    for name,qty in (result.get("materials") or {}).items():
        q=_f(qty)
        row=rows.get(str(name).lower(),{})
        moisture=row.get("moisture_pct")
        assay=row.get("assay_pct")
        if moisture is not None and _f(moisture)>3:
            warnings.append(f"{name}: moisture is {moisture}% and may affect mass balance.")
        if assay is not None and _f(assay)<95:
            warnings.append(f"{name}: assay is {assay}% and should be confirmed against the batch COA.")
        if q>batch:
            errors.append(f"{name}: quantity exceeds total batch mass.")
    bd=result.get("nutrient_breakdown") or {}
    if _f(bd.get("chlorine_pct_of_product"))>15:
        warnings.append("High chloride load: verify crop/product specification and chloride tolerance.")
    if _f(bd.get("sulfur_pct_of_product"))>20:
        warnings.append("High sulfur load: verify product specification.")
    if _f(bd.get("magnesium_pct_of_product"))>10:
        warnings.append("High magnesium load: verify product specification.")
    return {"valid":not errors,"errors":errors,"warnings":warnings}

def production_readiness(result, material_rows=None):
    audit=validate_formulation(result,material_rows)
    readiness="READY" if audit["valid"] and not audit["warnings"] else ("REVIEW" if audit["valid"] else "BLOCKED")
    return {**audit,"readiness":readiness}

def build_theoretical_batch(result):
    return {str(k):_f(v) for k,v in (result.get("materials") or {}).items() if _f(v)>1e-9}
def batch_kpis(planned_kg, actual_kg, variance):
    planned=_f(planned_kg); actual=_f(actual_kg)
    return {
        "planned_kg":planned,
        "actual_kg":actual,
        "yield_pct":round(actual*100/planned,4) if planned else None,
        "mass_variance_kg":round(actual-planned,6),
        "material_variance":variance or {},
    }

def qc_status(results, limits=None):
    limits=limits or {}
    failures=[]
    for key, value in (results or {}).items():
        if key not in limits:
            continue
        cfg=limits[key] or {}
        x=_f(value)
        if cfg.get("min") is not None and x<_f(cfg["min"]):
            failures.append(f"{key} below minimum")
        if cfg.get("max") is not None and x>_f(cfg["max"]):
            failures.append(f"{key} above maximum")
    return {"status":"PASS" if not failures else "FAIL","failures":failures}

def workflow_state(formulation=None, production=None, qc=None):
    if not formulation:
        return {"stage":"FORMULATION","next":"Create formulation"}
    if not production:
        return {"stage":"PRODUCTION_ORDER","next":"Create production order"}
    if not qc:
        return {"stage":"QC","next":"Enter QC results"}
    return {"stage":"COA","next":"Generate certificate of analysis"}
def normalize_trace_ppm(trace_pct):
    return {str(k):round(_f(v)*10000,6) for k,v in (trace_pct or {}).items()}

def formulation_summary(result):
    bd=result.get("nutrient_breakdown") or {}
    return {
        "grade":result.get("target"),
        "achieved":result.get("achieved"),
        "batch_kg":_f(result.get("batch_kg")),
        "materials":result.get("materials") or {},
        "chloride_pct":_f(bd.get("chlorine_pct_of_product")),
        "sulfur_pct":_f(bd.get("sulfur_pct_of_product")),
        "magnesium_pct":_f(bd.get("magnesium_pct_of_product")),
        "trace_ppm":normalize_trace_ppm(bd.get("trace_elements_pct_of_product")),
    }
