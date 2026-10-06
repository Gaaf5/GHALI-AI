from __future__ import annotations
from typing import Any
from app.tools.lab import resolve, MATERIALS, _solubility_g_per_100g_water
from app.tools.manufacturing import compatibility_screen

def _f(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return default

def assess_liquid_formulation(payload: dict[str,Any], raw_materials=None) -> dict[str,Any]:
    rows=payload.get("materials") or []
    density=_f(payload.get("density_g_ml"))
    batch_kg=_f(payload.get("batch_kg"))
    target_volume_l=_f(payload.get("target_volume_l"))
    temp=_f(payload.get("temperature_c"),25.0)
    target_ph=payload.get("target_ph")
    if batch_kg<=0: raise ValueError("Batch mass must be greater than 0 kg.")
    if density<=0: raise ValueError("Final product density is required and must be greater than 0 g/mL.")
    if density<0.8 or density>2.2: raise ValueError("Final product density is outside the configured liquid-fertilizer screening range (0.8–2.2 g/mL).")
    if not rows: raise ValueError("Add at least one raw material.")
    total=0.0
    materials=[]
    for r in rows:
        name=str(r.get("material","")).strip()
        kg=_f(r.get("kg"))
        if not name or kg<=0: raise ValueError("Every raw material needs a name and positive kg.")
        total+=kg
        key=resolve(name)
        materials.append({"name":name,"key":key,"kg":kg})
    water=sum(x["kg"] for x in materials if x["key"]=="water")
    if total<=0: raise ValueError("Total formulation mass must be positive.")
    if target_volume_l<=0: target_volume_l=batch_kg/density
    ww=lambda kg: kg/total*100
    nutrient={"N":0.0,"P2O5":0.0,"K2O":0.0,"S":0.0,"Mg":0.0,"Cl":0.0}
    n_forms={"nitrate":0.0,"ammoniacal":0.0,"urea":0.0}
    lookup={str(x.get("name","")).strip().lower():x for x in (raw_materials or [])}
    warnings=[]; errors=[]; material_rows=[]
    for x in materials:
        db=lookup.get(x["name"].lower())
        if db is None:
            # normalized fallback
            db=next((z for z in (raw_materials or []) if str(z.get("name","")).lower()==x["key"].lower()),None)
        for k,field in [("N","n_pct"),("P2O5","p2o5_pct"),("K2O","k2o_pct"),("S","s_pct"),("Mg","mg_pct"),("Cl","chlorine_pct")]:
            nutrient[k]+=x["kg"]*_f(db.get(field) if db else 0)/100
        n_forms["nitrate"]+=x["kg"]*_f(db.get("n_nitrate_pct") if db else 0)/100
        n_forms["ammoniacal"]+=x["kg"]*_f(db.get("n_ammoniacal_pct") if db else 0)/100
        n_forms["urea"]+=x["kg"]*_f(db.get("n_urea_pct") if db else 0)/100
        sol=None; source=""
        try:
            sol,source,_,quality=_solubility_g_per_100g_water(x["key"],temp)
        except Exception:
            quality="unavailable"
        if sol is not None and water>0:
            capacity=sol*water/100
            ratio=x["kg"]/capacity if capacity>0 else 999
            if ratio>1:
                warnings.append(f"{x['name']}: charged amount is above the pure-water solubility capacity at {temp:g} °C; precipitation/crystallization risk is high.")
            elif ratio>0.8:
                warnings.append(f"{x['name']}: charge is close to the pure-water solubility ceiling at {temp:g} °C; cooling margin may be small.")
        material_rows.append({
            "material":x["name"],"kg":x["kg"],"ww_pct":ww(x["kg"]),
            "wv_pct":ww(x["kg"])*density,
            "solubility_g_per_100g_water":sol,"solubility_source":source
        })
    target={"N":nutrient["N"]/total*100,"P2O5":nutrient["P2O5"]/total*100,"K2O":nutrient["K2O"]/total*100}
    target_wv={k:v*density for k,v in target.items()}
    compatibility=compatibility_screen([x["name"] for x in materials])
    for w in compatibility: warnings.append(w)
    ionic_load=(nutrient["Cl"]/total*100)+(nutrient["S"]/total*100)*1.5
    if nutrient["Cl"]/total*100>10: warnings.append("Chloride loading is high; corrosion/material compatibility and salting-out risk should be checked.")
    if nutrient["S"]/total*100>15: warnings.append("Sulfur loading is high; sulfate precipitation risk should be evaluated against calcium/magnesium.")
    if water/total<0.25: warnings.append("Water is below 25% w/w of the charge; this is a concentrated formulation and requires a strong crystallization/viscosity check.")
    if target_ph is not None:
        ph=_f(target_ph)
        if ph<2 or ph>11: warnings.append("Target pH is outside the preferred screening range 2–11; confirm material stability and corrosion limits.")
    # Conservative CT screening: derive a floor from source solubility curves only.
    ct=None
    ct_status="NOT DETERMINED — physical cooling test required"
    if water>0:
        limiting=[]
        for x in materials:
            try:
                s25,_,_,_= _solubility_g_per_100g_water(x["key"],25)
                s5,_,_,_= _solubility_g_per_100g_water(x["key"],5)
                if s25 is not None and s5 is not None:
                    loading=x["kg"]/water*100
                    if loading>s5: limiting.append(x["name"])
            except Exception: pass
        if limiting:
            ct_status="HIGH CRYSTALLIZATION RISK ON COOLING — limiting materials: "+", ".join(limiting)
    # Mixing sequence: water first, low-solubility solids before high concentration, acids/bases separated.
    def seq_score(x):
        key=x["key"]
        if key=="water": return 0
        if MATERIALS.get(key,{}).get("kind")=="acid": return 30
        if MATERIALS.get(key,{}).get("kind")=="base": return 40
        return 10
    sequence=sorted(materials,key=lambda x:(seq_score(x), -x["kg"]))
    readiness="READY FOR LAB SCREENING"
    if errors: readiness="BLOCKED"
    elif any("HIGH" in w or "precipitation/crystallization risk is high" in w for w in warnings): readiness="REVIEW — HIGH RISK"
    elif warnings: readiness="REVIEW — PRECAUTIONS REQUIRED"
    return {
        "product":payload.get("product_name","Liquid NPK sample"),
        "readiness":readiness,"batch_kg":batch_kg,"density_g_ml":density,
        "estimated_volume_l":batch_kg/density,"target_volume_l":target_volume_l,
        "temperature_c":temp,"total_charge_kg":total,"water_kg":water,
        "formula_ww":target,"formula_wv":target_wv,
        "nitrogen_forms_pct":{"nitrate_N":n_forms["nitrate"]/total*100,"ammoniacal_N":n_forms["ammoniacal"]/total*100,"urea_N":n_forms["urea"]/total*100},
        "secondary":{"S_pct":nutrient["S"]/total*100,"Mg_pct":nutrient["Mg"]/total*100,"Cl_pct":nutrient["Cl"]/total*100},
        "materials":material_rows,"compatibility_warnings":compatibility,
        "warnings":warnings,"errors":errors,
        "addition_sequence":[x["name"] for x in sequence],
        "ct":{"status":ct_status,"value_c":ct,"method":"Do not assign an exact CT from a pure-water solubility table. Confirm by cooling the final product under controlled conditions and record the first persistent crystal/cloud point; repeat on warming to check reversibility."},
        "stability_plan":[
            {"time":"0 h","tests":["appearance","pH","density","temperature","clarity"]},
            {"time":"24 h","tests":["sediment/crystals","pH","density","clarity"]},
            {"time":"48 h","tests":["sediment/crystals","pH","density","clarity"]},
            {"time":"5 °C","tests":["crystallization/cloud point","sediment"]},
            {"time":"25 °C","tests":["recovery after cooling","clarity","sediment"]},
        ],
        "note":"Engineering screening only. Mixed-liquid fertilizer behavior depends on actual raw-material grade, water chemistry, concentration, temperature, pH, and addition order. Exact CT, long-term stability, and compatibility must be confirmed experimentally."
    }
