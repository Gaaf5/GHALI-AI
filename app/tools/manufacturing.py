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

def compatibility_screen(material_names):
    names={str(x).strip().lower() for x in (material_names or [])}
    warnings=[]
    def has(*terms):
        return any(any(term in n for term in terms) for n in names)
    if has("calcium nitrate","calcium") and has("map","mkp","phosphate","urea phosphate"):
        warnings.append("Compatibility screen: calcium + phosphate combination can form low-solubility calcium phosphates; validate the specific grade and process moisture.")
    if has("calcium nitrate","calcium") and has("sop","potassium sulfate","sulfate"):
        warnings.append("Compatibility screen: calcium + sulfate combination can form sparingly soluble calcium sulfate under humid/wet conditions; validate storage and process conditions.")
    if has("magnesium sulfate","mgso4") and has("phosphate","map","mkp"):
        warnings.append("Compatibility screen: magnesium sulfate + concentrated phosphate systems may show caking or localized precipitation when moisture is present; validate the actual formulation.")
    if has("ammonium nitrate") and has("urea"):
        warnings.append("Process screen: ammonium nitrate/urea blends can be highly hygroscopic; moisture control and storage compatibility must be verified.")
    return warnings

def validate_formulation(result, material_rows=None):
    warnings=[]
    errors=[]
    warnings.extend(compatibility_screen((result.get("materials") or {}).keys()))
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
    audit["compatibility_warnings"]=compatibility_screen((result.get("materials") or {}).keys())
    audit["warnings"].extend(audit["compatibility_warnings"])
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

def qc_limits_from_formulation(formulation):
    formulation=formulation or {}
    result=formulation.get("result") if isinstance(formulation.get("result"),dict) else formulation
    target=result.get("target") or formulation.get("target") or {}
    if isinstance(target,str):
        parts=[x.strip() for x in target.replace("/","-").split("-")]
        try: target={k:float(v) for k,v in zip(("N","P2O5","K2O"),parts)}
        except (TypeError,ValueError): target={}
    explicit=result.get("limits") or formulation.get("limits") or {}
    tol=_f(result.get("tolerance_pct", formulation.get("tolerance_pct", 0.2)))
    out={}
    for key in ("N","P2O5","K2O"):
        if key in explicit and isinstance(explicit[key],dict):
            c=explicit[key]; out[key]={"min":_f(c.get("min")) if c.get("min") is not None else None,"max":_f(c.get("max")) if c.get("max") is not None else None}
        elif key in target:
            x=_f(target[key]); out[key]={"min":round(x-tol,6),"max":round(x+tol,6)}
    return out

def batch_release_state(batch, formulation=None, qc_results=None):
    if not batch: return {"status":"BLOCKED","releasable":False,"reasons":["Production batch not found."]}
    reasons=[]; planned=_f(batch.get("planned_kg")); actual=_f(batch.get("actual_kg")); status=str(batch.get("status") or "planned").lower()
    if planned<=0: reasons.append("Planned production quantity is missing.")
    if actual<=0 or status not in {"completed","released"}: reasons.append("Production actuals are not completed.")
    theoretical=batch.get("theoretical") or {}
    actuals=batch.get("actual") or {}
    if theoretical and actual>0:
        missing=[str(k) for k in theoretical if _f(actuals.get(k))<=0]
        if missing: reasons.append("Missing actual quantities: " + ", ".join(missing[:8]))
        variance=batch.get("variance") or {}
        outliers=[]
        for name,v in variance.items():
            pct=v.get("delta_pct") if isinstance(v,dict) else None
            if pct is not None and abs(_f(pct))>5: outliers.append(str(name))
        if outliers: reasons.append("Material variance exceeds +/-5%: " + ", ".join(outliers[:8]))
    qc=list(qc_results or []); latest=qc[0] if qc else None
    if not latest: reasons.append("No QC result has been recorded.")
    elif str(latest.get("status","" )).upper()!="PASS": reasons.append("Latest QC result did not pass.")
    yield_pct=actual*100/planned if planned else 0
    if planned and (yield_pct < 95 or yield_pct > 105): reasons.append(f"Production yield {yield_pct:.2f}% is outside the 95-105% release band.")
    return {"status":"HOLD","releasable":False,"reasons":reasons,"yield_pct":round(yield_pct,4)} if reasons else {"status":"RELEASED","releasable":True,"reasons":[],"yield_pct":round(yield_pct,4)}

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
