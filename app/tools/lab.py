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
    # K2SO4: about 11.1 g/100 mL water at 20 °C; ~12 g/100 mL at 25 °C.
    "sop": {"kind":"fertilizer","mw":174.26,"density":2.66,"solubility_g_100ml":11.1,"cp":1.05},
    "nop": {"kind":"fertilizer","mw":101.10,"density":2.11,"solubility_g_100ml":31.6,"cp":1.10},
    "ammonium_nitrate": {"kind":"fertilizer","mw":80.04,"density":1.72,"solubility_g_100ml":190,"cp":1.70},
    "ammonium_sulfate": {"kind":"fertilizer","mw":132.14,"density":1.77,"solubility_g_100ml":76,"cp":1.20},
    "urea_phosphate": {"kind":"fertilizer","mw":115.05,"density":1.85,"solubility_g_100ml":50,"cp":1.20},
    "potassium_chloride": {"kind":"fertilizer","mw":74.55,"density":1.98,"solubility_g_100ml":34.2,"cp":1.05},
    "magnesium_sulfate": {"kind":"salt","mw":246.47,"density":1.68,"solubility_g_100ml":71,"cp":1.15,"hydrate":"heptahydrate"},
    "calcium_nitrate": {"kind":"fertilizer","mw":236.15,"density":1.896,"solubility_g_100ml":129,"cp":1.30,"hydrate":"tetrahydrate"},
    "calcium_chloride": {"kind":"salt","mw":110.98,"density":2.15,"solubility_g_100ml":74.5,"cp":1.05},
    "magnesium_nitrate": {"kind":"salt","mw":256.41,"density":1.46,"solubility_g_100ml":125,"cp":1.15,"hydrate":"hexahydrate"},
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
        sol20,sol_source,sol_url=_solubility_g_per_100g_water(key,20) if "SOLUBILITY_CURVES" in globals() else (None,"","")
        out.append({"id":key,"name":ARABIC_NAMES.get(key,key.replace("_"," ").title()),
                    "kind":v["kind"],"mw":v["mw"],"density":v["density"],
                    "solubility_g_100ml":v["solubility_g_100ml"],"solubility_g_per_100g_water_20c":sol20,
                    "solubility_source":sol_source,"solubility_source_url":sol_url,"cp":v["cp"]})
    return out

SOLUBILITY_CURVES = {
    # Basis: g solute / 100 g water. Values are reference data; interpolation only within sourced ranges.
    "urea": {"points":[(0,66.7),(20,108.0),(40,167.0),(60,251.0),(80,400.0),(100,733.0)],"source":"Fertilizer-grade reference: about 108 g/100 g water at 20 °C; practical fertigation data report about 105 kg/100 L at 20 °C","url":"https://www.dpird.nsw.gov.au/agriculture/water/irrigation/crops/fertigation"},
    "map": {"points":[(0,22.7),(20,37.1),(25,40.4)],"source":"EPA PPRTV / NLM at 25 °C; fertilizer product specification at 20 °C","url":"https://www.epa.gov/sites/default/files/2021-09/documents/diammoniumphosphate.pdf"},
    "dap": {"points":[(10,57.5),(25,69.5)],"source":"CRC/NLM: 57.5 g/100 mL water at 10 °C and 69.5 g/100 g water at 25 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Ammonium-Phosphate-Dibasic"},
    "mkp": {"points":[(20,18.0),(25,25.0),(90,83.5)],"source":"Ullmann/HSDB and CRC values for KH2PO4; 18 g/100 g water at 20 °C, 25 g/100 cc at 25 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/potassium%20dihydrogen%20orthophosphate"},
    "sop": {"points":[(0,7.4),(10,9.3),(20,11.1),(25,12.0),(30,13.0),(40,14.8),(60,18.2),(80,21.4),(90,22.9),(100,24.1)],"source":"PubChem/ICSC: 12 g/100 mL water at 25 °C; independent reference table gives 11.1 at 20 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Potassium-sulfate"},
    "nop": {"points":[(0,13.3),(10,20.9),(20,31.6),(30,45.8),(40,63.9),(50,85.5),(60,110.0),(70,138.0),(80,169.0),(90,202.0),(100,246.0)],"source":"KNO3 reference solubility data / PubChem","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Potassium-nitrate"},
    "ammonium_nitrate": {"points":[(0,118.3),(20,200.0),(100,871.0)],"source":"CRC/HSDB and ILO-WHO ICSC: 200 g/100 mL water at 20 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Ammonium-nitrate"},
    "potassium_chloride": {"points":[(0,27.6),(10,31.0),(20,34.0),(30,37.0),(40,40.0),(50,42.6)],"source":"Standard KCl solubility table; 34.0 g/100 mL water at 20 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Potassium-Chloride"},
    "ammonium_sulfate": {"points":[(0,70.6),(25,76.7),(100,103.8)],"source":"CRC/Merck values reported by PubChem: 70.6 g/100 g water at 0 °C, 76.7 at 25 °C, 103.8 at 100 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/6097028"},
    "magnesium_sulfate": {"points":[(20,71.0),(40,91.0)],"source":"MgSO4·7H2O reference data; hydrate explicitly modeled","url":"https://pubchem.ncbi.nlm.nih.gov/compound/magnesium-sulfate"},
    "calcium_nitrate": {"points":[(0,105.0),(20,129.0),(100,363.0)],"source":"Calcium nitrate tetrahydrate reference: 129 g/100 mL water at 20 °C","url":"https://www.sciencemadness.org/smwiki/index.php/Calcium_nitrate"},
    "calcium_chloride": {"points":[(0,59.5),(20,74.5),(25,81.3),(40,128.0),(60,137.0),(80,147.0),(100,159.0)],"source":"ICSC/CRC: 74.5 g/100 mL water at 20 °C; 81.3 g/100 g water at 25 °C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Calcium-Chloride"},
    "magnesium_nitrate": {"points":[(20,125.0)],"source":"Industrial fertilizer/technical reference: magnesium nitrate solubility 125 g/100 mL water","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Magnesium-nitrate"},
    "citric_acid": {"points":[(10,54.0),(20,59.2),(30,64.3),(40,68.6),(50,70.9),(60,73.5),(70,76.2),(80,78.8),(90,81.4),(100,84.0)],"source":"Merck/HSDB values reported by PubChem","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Citric-Acid"},
    "urea_phosphate": {"points":[(20,100.0)],"source":"EuroChem Aqualis UP Solub: 1000 g/L water at 20 °C","url":"https://www.eurochem-wsf.com/products/up-solub/"},
}

def _solubility_g_per_100g_water(material: str, temp_c: float) -> tuple[float|None,str,str]:
    curve=SOLUBILITY_CURVES.get(material)
    if not curve:
        return None,"no source-backed curve available",""
    pts=curve["points"]
    if temp_c < pts[0][0] or temp_c > pts[-1][0]:
        return None,f"source data range is {pts[0][0]:g}–{pts[-1][0]:g} °C",curve.get("url","")
    value=pts[0][1]
    for (t0,v0),(t1,v1) in zip(pts,pts[1:]):
        if t0 <= temp_c <= t1:
            f=0.0 if t1==t0 else (temp_c-t0)/(t1-t0)
            value=v0+(v1-v0)*f
            break
    return float(value),curve["source"],curve.get("url","")

def _mix_factor(rpm: float, volume_l: float, viscosity=1.0):
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
    if volume < 0.1 or volume > 1000: raise ValueError("Working volume must be between 0.1 and 1000 L.")
    if duration < 0 or duration > 86400: raise ValueError("Experiment time must be between 0 and 86400 s.")
    if rpm < 0 or rpm > 1800: raise ValueError("Agitation must be between 0 and 1800 RPM.")
    if temp < -50 or temp > 180: raise ValueError("Virtual lab temperature range is -50 to 180 C.")
    if any(float(a.get("time_s",0)) < 0 or float(a.get("time_s",0)) > duration for a in additions):
        raise ValueError("Every addition time must be within the experiment duration.")
    solvent_mass=0.0; cp_total=0.0; dissolved={}; undissolved={}; dissolution_info={}; solids=0.0
    solvent_volume_l=0.0; water_mass_total=0.0; first_solvent_time=None
    for a in additions:
        mid=resolve(a.get("material","")); mass=max(0.0,float(a.get("mass_g",0)))
        if mid in MATERIALS and MATERIALS[mid]["kind"]=="solvent":
            solvent_volume_l += mass / max(MATERIALS[mid]["density"],1e-9) / 1000.0
            if mid=="water": water_mass_total += mass
            at=float(a.get("time_s",0))
            first_solvent_time=at if first_solvent_time is None else min(first_solvent_time,at)
    warnings=[]; events=[]; rate_index=_mix_factor(rpm,volume)
    solid_ids={resolve(a.get("material","")) for a in additions if MATERIALS.get(resolve(a.get("material","")),{}).get("kind")!="solvent"}
    if len(solid_ids)>1:
        warnings.append("Multi-solute solubility is not additive: each value is a single-solute reference. Mixed-solution phase equilibria and salting-out/synergistic effects require measured multicomponent data.")
    if water_mass_total <= 0 and any(MATERIALS.get(resolve(a.get("material","")),{}).get("kind")!="solvent" for a in additions):
        warnings.append("No water was added: source-backed fertilizer solubility curves cannot be applied.")
    if any(MATERIALS.get(resolve(a.get("material","")),{}).get("kind")=="solvent" and resolve(a.get("material",""))!="water" for a in additions):
        warnings.append("Solubility data are currently referenced to water; non-water solvent effects are not modeled.")
    for a in additions:
        mid=resolve(a.get("material","")); mass=max(0.0,float(a.get("mass_g",0))); at=float(a.get("time_s",0))
        if mid not in MATERIALS: raise ValueError(f"Unknown lab material: {a.get('material')}")
        if MATERIALS[mid]["kind"]=="solvent":
            solvent_mass += mass; cp_total += mass*MATERIALS[mid]["cp"]
            events.append({"time_s":at,"event":"add_solvent","material":mid,"mass_g":mass})
            continue
        solids += mass
        if first_solvent_time is not None and at < first_solvent_time:
            warnings.append(f"{mid}: solid is scheduled before the first solvent addition; dissolution timing is not physically established.")
        sol_ref, sol_source, sol_url=_solubility_g_per_100g_water(mid,temp)
        if sol_ref is None:
            warnings.append(f"{mid}: no source-backed water-solubility curve is available; dissolution capacity is not claimed.")
            capacity=0.0; dissolved_mass=0.0; time_to_95=None
        else:
            # Solubility is a thermodynamic equilibrium property. Water mass, not vessel volume,
            # sets the saturation capacity. A short time-step model lets later water additions
            # increase capacity rather than pretending all water was present from t=0.
            k=(0.006 + 0.018*rate_index) * math.exp(0.004*(temp-20))
            steps=max(20,min(240,int(duration-at)+1))
            dt=max(0.25,(duration-at)/steps) if duration>at else 0.0
            dmass=0.0; time_to_95=None; t=at
            for _ in range(steps):
                t=min(duration,t+dt)
                water_now=sum(max(0.0,float(x.get("mass_g",0))) for x in additions
                              if resolve(x.get("material",""))=="water" and float(x.get("time_s",0))<=t)
                capacity_now=sol_ref*water_now/100.0
                equilibrium_now=min(mass,capacity_now)
                dmass += max(0.0,equilibrium_now-dmass)*(1-math.exp(-k*dt))
                if time_to_95 is None and dmass >= mass*0.95 and mass <= capacity_now:
                    time_to_95=t
            capacity=sol_ref*water_mass_total/100.0
            dissolved_mass=min(mass,max(0.0,dmass))
            if time_to_95 is None and mass <= capacity:
                time_to_95=duration
        remaining=max(0.0,mass-dissolved_mass)
        dissolved[mid]=dissolved.get(mid,0)+dissolved_mass
        undissolved[mid]=undissolved.get(mid,0)+remaining
        dissolution_info[mid]={"mass_g":mass,"capacity_g":round(capacity,6),
                              "solubility_g_per_100g_water":sol_ref,
                              "solubility_source":sol_source,
                              "solubility_source_url":sol_url,
                              "water_mass_total_g":round(water_mass_total,6),
                              "final_dissolved_g":dissolved_mass,"final_pct":100*dissolved_mass/max(mass,1e-12),
                              "complete":mass<=capacity and dissolved_mass>=mass*0.95,
                              "time_to_95_s":time_to_95,"start_s":at,
                              "undissolved_g":remaining,"precipitated":False,"precipitated_g":0.0}
        if sol_ref is not None and mass>capacity:
            warnings.append(f"{mid}: source-backed equilibrium capacity is approximately {capacity:.1f} g at {temp:.1f} °C for {water_mass_total:.1f} g water; solid residue can remain.")
        events.append({"time_s":at,"event":"add_solid","material":mid,"mass_g":mass})
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
                      "actual_solvent_volume_l":round(solvent_volume_l,6),
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
