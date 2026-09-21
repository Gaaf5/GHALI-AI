from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any

# Digital-lab data are engineering approximations, not physical measurements.
# Every result carries a confidence class and model provenance.
MATERIALS = {
    "water": {"kind":"solvent","mw":18.015,"density":0.997,"solubility_g_100ml":None,"cp":4.18},
    "ethanol": {"kind":"solvent","mw":46.069,"density":0.789,"solubility_g_100ml":None,"cp":2.44},
    "isopropanol": {"kind":"solvent","mw":60.096,"density":0.785,"solubility_g_100ml":None,"cp":2.68},
    "methanol": {"kind":"solvent","mw":32.042,"density":0.792,"solubility_g_100ml":None,"cp":2.51},
    "acetone": {"kind":"solvent","mw":58.08,"density":0.784,"solubility_g_100ml":None,"cp":2.15},
    "glycerol": {"kind":"solvent","mw":92.094,"density":1.261,"solubility_g_100ml":None,"cp":2.43},
    "urea": {"kind":"fertilizer","mw":60.06,"density":1.33,"solubility_g_100ml":108,"cp":1.50},
    "map": {"kind":"fertilizer","mw":115.03,"density":1.80,"solubility_g_100ml":40,"cp":1.20},
    "dap": {"kind":"fertilizer","mw":132.06,"density":1.62,"solubility_g_100ml":59,"cp":1.25},
    "mkp": {"kind":"fertilizer","mw":136.09,"density":2.34,"solubility_g_100ml":22.6,"cp":1.10},
    "sop": {"kind":"fertilizer","mw":174.26,"density":2.66,"solubility_g_100ml":12,"cp":1.05},
    "nop": {"kind":"fertilizer","mw":101.10,"density":2.11,"solubility_g_100ml":31.6,"cp":1.10},
    "ammonium_nitrate": {"kind":"fertilizer","mw":80.04,"density":1.72,"solubility_g_100ml":190,"cp":1.70},
    "ammonium_sulfate": {"kind":"fertilizer","mw":132.14,"density":1.77,"solubility_g_100ml":76,"cp":1.20},
    "urea_phosphate": {"kind":"fertilizer","mw":115.05,"density":1.85,"solubility_g_100ml":50,"cp":1.20},
    "potassium_chloride": {"kind":"fertilizer","mw":74.55,"density":1.98,"solubility_g_100ml":34.2,"cp":1.05},
    "magnesium_sulfate": {"kind":"salt","mw":120.37,"density":1.68,"solubility_g_100ml":71,"cp":1.15},
    "calcium_nitrate": {"kind":"fertilizer","mw":164.09,"density":1.90,"solubility_g_100ml":129,"cp":1.30},
    "calcium_chloride": {"kind":"salt","mw":110.98,"density":2.15,"solubility_g_100ml":74.5,"cp":1.05},
    "magnesium_nitrate": {"kind":"salt","mw":148.31,"density":1.46,"solubility_g_100ml":125,"cp":1.15},
    "citric_acid": {"kind":"acid","mw":192.12,"density":1.54,"solubility_g_100ml":59,"cp":1.20},
    "sulfuric_acid": {"kind":"acid","mw":98.079,"density":1.84,"solubility_g_100ml":None,"cp":1.40},
    "nitric_acid": {"kind":"acid","mw":63.012,"density":1.41,"solubility_g_100ml":None,"cp":1.45},
    "phosphoric_acid": {"kind":"acid","mw":97.994,"density":1.88,"solubility_g_100ml":None,"cp":1.35},
}
ARABIC_NAMES = {
    "urea":"اليوريا","map":"MAP","dap":"DAP","mkp":"MKP","sop":"SOP","nop":"نترات البوتاسيوم",
    "ammonium_nitrate":"نترات الأمونيوم","ammonium_sulfate":"كبريتات الأمونيوم",
    "urea_phosphate":"فوسفات اليوريا","potassium_chloride":"كلوريد البوتاسيوم",
    "magnesium_sulfate":"كبريتات المغنيسيوم","calcium_nitrate":"نترات الكالسيوم",
    "water":"الماء","ethanol":"الإيثانول","isopropanol":"الأيزوبروبانول",
    "methanol":"الميثانول","acetone":"الأسيتون","glycerol":"الجليسرول",
}
ALIASES = {v.lower():k for k,v in ARABIC_NAMES.items()}
ALIASES.update({"ماء":"water","يوريا":"urea","كبريتات البوتاسيوم":"sop","سوب":"sop",
                "نترات البوتاسيوم":"nop","نوب":"nop","فوسفات اليوريا":"urea_phosphate",
                "كلوريد البوتاسيوم":"potassium_chloride","مذيب":"water"})
MIXING_COEFF = {"water":1.0,"ethanol":0.9,"isopropanol":0.9,"methanol":0.9,
                "acetone":0.8,"glycerol":1.2}
def resolve(name: str) -> str:
    key = str(name).strip().lower().replace(" ","_")
    return key if key in MATERIALS else ALIASES.get(str(name).strip().lower(), key)

def catalog():
    out=[]
    for key,v in MATERIALS.items():
        out.append({"id":key,"name":ARABIC_NAMES.get(key,key.replace("_"," ").title()),
                    "kind":v["kind"],"mw":v["mw"],"density":v["density"],
                    "solubility_g_100ml":v["solubility_g_100ml"],"cp":v["cp"]})
    return out

def _temp_factor(temp_c: float) -> float:
    # Smooth engineering approximation: modest solubility increase with temperature.
    return max(0.55, min(2.6, 1.0 + 0.0045*(temp_c-20.0)))

def _mix_factor(rpm: float, volume_l: float, viscosity=1.0) -> float:
    rpm=max(0.0,float(rpm)); volume=max(0.1,float(volume_l))
    power=(rpm/300.0)**1.35 / (volume**0.12 * max(viscosity,0.2))
    return max(0.0,min(3.5,power))

def simulate(experiment: dict[str,Any]) -> dict[str,Any]:
    vessel=experiment.get("vessel",{}) or {}
    temp=float(experiment.get("temperature_c",20))
    rpm=float(experiment.get("rpm",300))
    duration=float(experiment.get("duration_s",60))
    volume=float(vessel.get("working_volume_l",experiment.get("solvent_volume_l",1)))
    additions=experiment.get("additions",[]) or []
    if volume<=0 or duration<0 or rpm<0: raise ValueError("Volume, duration and rpm must be non-negative/positive.")
    if temp < -50 or temp > 180: raise ValueError("Virtual lab temperature range is -50 to 180 C.")
    solvent_mass=0.0; cp_total=0.0; dissolved={}; undissolved={}; dissolution_info={}; solids=0.0
    warnings=[]; events=[]; rate_index=_mix_factor(rpm,volume)
    for a in additions:
        mid=resolve(a.get("material","")); mass=max(0.0,float(a.get("mass_g",0)))
        if mid not in MATERIALS: raise ValueError(f"Unknown lab material: {a.get('material')}")
        solvent = MATERIALS[mid]["kind"]=="solvent"
        if solvent:
            m=mass; solvent_mass += m; cp_total += m*MATERIALS[mid]["cp"]
            events.append({"time_s":float(a.get("time_s",0)),"event":"add_solvent","material":mid,"mass_g":m})
            continue
        solids += mass
        base=MATERIALS[mid]["solubility_g_100ml"]
        capacity=float("inf") if base is None else base*volume*10.0*_temp_factor(temp)
        # Mixing accelerates approach to equilibrium; it does not change equilibrium solubility.
        k=(0.006 + 0.018*rate_index) * math.exp(0.010*(temp-20))
        effective_time=max(0.0,duration-float(a.get("time_s",0)))
        fraction=1-math.exp(-k*effective_time)
        equilibrium=min(mass,capacity)
        dissolved_mass=equilibrium*(1-math.exp(-k*effective_time))
        # If the dose is below equilibrium, the same kinetic model approaches complete dissolution.
        if mass <= capacity: dissolved_mass=mass*fraction
        remaining=max(0.0,mass-dissolved_mass)
        dissolved[mid]=dissolved.get(mid,0)+dissolved_mass
        undissolved[mid]=undissolved.get(mid,0)+remaining
        time_to_95=None if equilibrium < mass*0.95 else (-math.log(0.05)/max(k,1e-12))+float(a.get("time_s",0))
        dissolution_info[mid]={"mass_g":mass,"capacity_g":capacity if math.isfinite(capacity) else None,
                              "final_dissolved_g":dissolved_mass,"final_pct":100*dissolved_mass/max(mass,1e-12),
                              "complete":mass<=capacity and dissolved_mass>=mass*0.95,
                              "time_to_95_s":time_to_95,"start_s":float(a.get("time_s",0)),
                              "undissolved_g":remaining,"precipitated":False,"precipitated_g":0.0}
        if base is not None and mass>capacity:
            warnings.append(f"{mid}: equilibrium solubility capacity is approximately {capacity:.1f} g at {temp:.1f} C; solid residue can remain.")
        events.append({"time_s":float(a.get("time_s",0)),"event":"add_solid","material":mid,"mass_g":mass})
    total_mass=solvent_mass+solids
    dissolved_total=sum(dissolved.values())
    uniformity=max(0.0,min(99.9,100*(1-math.exp(-rate_index*duration/45))))
    density=total_mass/max(volume*1000,1e-9)
    if rpm<80 and duration<30: warnings.append("Low agitation/time: concentration gradients may remain.")
    if temp>80: warnings.append("High temperature: treat vapor pressure/material compatibility as a separate safety check.")
    if temp>100 and any(MATERIALS[resolve(a.get("material",""))]["kind"]=="solvent" for a in additions):
        warnings.append("Boiling/volatility may dominate above the solvent's boiling range; this model does not simulate pressure.")
    confidence="screening"
    from app.tools.lab_chemistry import analyze as analyze_chemistry
    chemistry=analyze_chemistry(experiment,dissolved)
    warnings.extend(x["message"] for x in chemistry["compatibility_risks"])
    return {
        "status":"SIMULATED","confidence":confidence,"model":"GHALI Virtual Lab v2",
        "conditions":{"temperature_c":temp,"rpm":rpm,"duration_s":duration,"working_volume_l":volume,
                      "mixing_index":round(rate_index,4)},
        "mass_balance":{"input_g":round(total_mass,6),"dissolved_solids_g":round(dissolved_total,6),
                        "undissolved_solids_g":round(sum(undissolved.values()),6)},
        "dissolved_g":{k:round(v,6) for k,v in dissolved.items()},
        "undissolved_g":{k:round(v,6) for k,v in undissolved.items() if v>1e-8},
        "dissolution":dissolution_info,
        "estimated_density_g_ml":round(density,6),
        "mixing_uniformity_pct":round(uniformity,3),
        "chemistry":chemistry,
        "warnings":warnings,"events":events,
        "note":"Simulation is a screening model. Chemistry rules require validated property data and laboratory calibration before production use."
    }
def sweep(base: dict[str,Any], variables: dict[str,list[float]], max_runs=250000) -> dict[str,Any]:
    import itertools
    keys=list(variables)
    values=[list(variables[k]) for k in keys]
    total=1
    for v in values: total*=len(v)
    if total>max_runs: raise ValueError(f"Sweep has {total} runs; maximum is {max_runs}.")
    results=[]; best=None
    for combo in itertools.product(*values):
        exp=dict(base)
        for k,v in zip(keys,combo):
            exp[k]=v
        r=simulate(exp)
        score=(r["mass_balance"]["undissolved_solids_g"],-r["mixing_uniformity_pct"])
        item={"variables":dict(zip(keys,combo)),"undissolved_g":r["mass_balance"]["undissolved_solids_g"],
              "uniformity_pct":r["mixing_uniformity_pct"],"warnings":len(r["warnings"])}
        results.append(item)
        if best is None or score<best[0]: best=(score,item)
    return {"runs":total,"best":best[1] if best else None,"results":results}

def million_case_benchmark() -> dict[str,Any]:
    # Deterministic numerical benchmark: one million lightweight state evaluations.
    n=1_000_000; checksum=0.0
    for i in range(n):
        rpm=50+(i%951)
        temp=5+(i%116)
        t=5+(i%596)
        mix=_mix_factor(rpm,10)
        checksum += 1-math.exp(-(0.006+0.018*mix)*math.exp(.010*(temp-20))*t)
    return {"runs":n,"checksum":round(checksum,6),"engine":"vector-free deterministic benchmark"}
__all__=["MATERIALS","catalog","resolve","simulate","sweep","million_case_benchmark"]