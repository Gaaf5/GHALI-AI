from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any
from app.tools.solubility_data import aqueous_solubility, SOURCE_SOLUBILITY_CURVES

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
    "citric_acid": {"kind":"acid","phase":"solid","particle_size_um":500,"blend_t95_s":240.0,"mw":192.12,"density":1.54,"solubility_g_100ml":59,"cp":1.20},
    "sulfuric_acid": {"kind":"acid","mw":98.079,"density":1.84,"solubility_g_100ml":None,"cp":1.40},
    "nitric_acid": {"kind":"acid","mw":63.012,"density":1.41,"solubility_g_100ml":None,"cp":1.45},
    "phosphoric_acid": {"kind":"acid","phase":"liquid","concentration_wt_pct":85.0,"mw":97.994,"density":1.685,"solubility_g_100ml":None,"cp":1.35,"blend_t95_s":90.0},
    "phosphoric_acid_food_grade": {"kind":"acid","phase":"liquid","concentration_wt_pct":85.0,"mw":97.994,"density":1.685,"solubility_g_100ml":None,"cp":1.35,"blend_t95_s":90.0},
    "monoethanolamine": {"kind":"solvent","phase":"liquid","mw":61.083,"density":1.012,"solubility_g_100ml":None,"cp":2.7,"blend_t95_s":60.0},
    "zinc_sulfate": {"kind":"salt","phase":"solid","mw":161.44,"density":3.8,"solubility_g_100ml":22.0,"cp":0.8},
    "seaweed_extract": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3},
    "aqua_amin": {"kind":"organic","phase":"liquid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"blend_t95_s":120.0},
    "ammonium_sulfite": {"kind":"salt","phase":"solid","mw":116.14,"density":1.41,"solubility_g_100ml":None,"cp":1.2},
    "boric_acid": {"kind":"acid","phase":"solid","mw":61.83,"density":1.435,"solubility_g_100ml":4.72,"cp":1.0},
    "amino_acid_80": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3},
    "amino_acid_40": {"kind":"organic","phase":"liquid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"blend_t95_s":120.0},
    "tkp_00_33_66": {"kind":"fertilizer","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.1},
    "mkpi_00_58_38": {"kind":"fertilizer","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.1},
    "potassium_hydroxide": {"kind":"base","phase":"solid","mw":56.106,"density":2.044,"solubility_g_100ml":None,"cp":1.2},
    "potassium_humate": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3},
    "sodium_benzoate": {"kind":"preservative","phase":"solid","mw":144.11,"density":1.5,"solubility_g_100ml":None,"cp":1.2},
    "sodium_edta": {"kind":"chelate","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.2},
    "calcium_sodium_edta": {"kind":"chelate","phase":"solid","mw":374.27,"density":1.0,"solubility_g_100ml":None,"cp":1.2},
    "lisiveg": {"kind":"organic","phase":"liquid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"blend_t95_s":120.0},
}
ARABIC_NAMES = {
    "urea":"اليوريا","map":"MAP","dap":"DAP","mkp":"MKP","sop":"SOP","nop":"نترات البوتاسيوم",
    "ammonium_nitrate":"نترات الأمونيوم","ammonium_sulfate":"كبريتات الأمونيوم",
    "urea_phosphate":"فوسفات اليوريا","potassium_chloride":"كلوريد البوتاسيوم",
    "magnesium_sulfate":"كبريتات المغنيسيوم","calcium_nitrate":"نترات الكالسيوم",
    "water":"الماء","ethanol":"الإيثانول","isopropanol":"الأيزوبروبانول",
    "methanol":"الميثانول","acetone":"الأسيتون","glycerol":"الجليسرول","phosphoric_acid":"حمض الفوسفوريك 85%",
    "phosphoric_acid_food_grade":"حمض الفوسفوريك Food Grade 85%","monoethanolamine":"MEA مونو إيثانول أمين",
    "zinc_sulfate":"سلفات الزنك","seaweed_extract":"Sea Weed Extract","aqua_amin":"Aqua Amin",
    "ammonium_sulfite":"أمونيوم سلفيت","boric_acid":"بوريك أسيد","amino_acid_80":"Amino Acid 80%",
    "amino_acid_40":"Amino Acid 40%","tkp_00_33_66":"TKP 00-33-66","mkpi_00_58_38":"MKPI 00-58-38",
    "potassium_hydroxide":"KOH هيدروكسيد البوتاسيوم","potassium_humate":"بوتاسيوم هيوميت / هيوميك أسيد",
    "sodium_benzoate":"بنزوات الصوديوم","sodium_edta":"Sodium EDTA","calcium_sodium_edta":"Calcium EDTA",
    "lisiveg":"Lisiveg",
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
        sol20,sol_source,sol_url,sol_quality=_solubility_g_per_100g_water(key,20)
        out.append({"id":key,"name":ARABIC_NAMES.get(key,key.replace("_"," ").title()),
                    "kind":v["kind"],"mw":v["mw"],"density":v["density"],
                    "solubility_g_100ml":v["solubility_g_100ml"],"solubility_g_per_100g_water_20c":sol20,
                    "solubility_source":sol_source,"solubility_source_url":sol_url,"solubility_quality":sol_quality,"cp":v["cp"]})
    return out

SOLUBILITY_CURVES = SOURCE_SOLUBILITY_CURVES

def _solubility_g_per_100g_water(material: str, temp_c: float) -> tuple[float|None,str,str,str]:
    data=aqueous_solubility(material,temp_c)
    if data:
        return data["value_g_per_100g_water"],data["source"],data["url"],data["quality"]
    curve=SOLUBILITY_CURVES.get(material)
    if curve:
        return None,f"source data range is {curve['points'][0][0]:g}–{curve['points'][-1][0]:g} °C",curve.get("url",""),curve.get("quality","reference")
    return None,"no source-backed curve available","","unavailable"

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
    liquid_mass=0.0; cp_total=0.0; dissolved={}; undissolved={}; dissolution_info={}; blend_info={}; solids=0.0
    solvent_volume_l=0.0; water_mass_total=0.0; first_water_time=None
    liquid_ids=set()
    for a in additions:
        mid=resolve(a.get("material","")); mass=max(0.0,float(a.get("mass_g",0))); at=float(a.get("time_s",0))
        if mid not in MATERIALS: raise ValueError(f"Unknown lab material: {a.get('material')}")
        data=MATERIALS[mid]
        if data.get("phase","solid")=="liquid" or data.get("kind")=="solvent":
            liquid_ids.add(mid)
            if data.get("kind")=="solvent":
                solvent_volume_l += mass / max(data["density"],1e-9) / 1000.0
                if mid=="water":
                    water_mass_total += mass
                    first_water_time=at if first_water_time is None else min(first_water_time,at)
    warnings=[]; events=[]; rate_index=_mix_factor(rpm,volume)
    solid_ids={resolve(a.get("material","")) for a in additions
               if MATERIALS.get(resolve(a.get("material","")),{}).get("phase", "liquid" if MATERIALS.get(resolve(a.get("material","")),{}).get("kind")=="solvent" else "solid")=="solid"}
    if len(solid_ids)>1:
        warnings.append("Multi-solute solubility is not additive: each value is a single-solute reference. Mixed-solution phase equilibria and salting-out/synergistic effects require measured multicomponent data.")
    if water_mass_total <= 0 and solid_ids:
        warnings.append("No water was added: source-backed fertilizer solubility curves cannot be applied.")
    if any(x!="water" for x in liquid_ids if MATERIALS.get(x,{}).get("kind")=="solvent"):
        warnings.append("Solubility data are referenced to water; non-water solvent effects are not modeled.")
    if "phosphoric_acid" in liquid_ids:
        warnings.append("Phosphoric acid is modeled as an 85 wt% liquid reagent: its addition is a blending/homogenization step, not solid dissolution. Acid dilution is exothermic and should be added to water under controlled conditions.")
    for a in additions:
        mid=resolve(a.get("material","")); mass=max(0.0,float(a.get("mass_g",0))); at=float(a.get("time_s",0))
        data=MATERIALS[mid]
        phase=data.get("phase", "liquid" if data.get("kind")=="solvent" else "solid")
        if phase=="liquid" or data.get("kind")=="solvent":
            liquid_mass += mass; cp_total += mass*data["cp"]
            if data.get("blend_t95_s"):
                rpm_factor=0.25 if rpm<=0 else max(0.25,min(4.0,(rpm/300.0)**0.5))
                blend_t95=data["blend_t95_s"]/rpm_factor
                if mid=="phosphoric_acid" and first_water_time is not None and at < first_water_time:
                    warnings.append("Phosphoric acid was scheduled before water. For the modeled 85% acid handling workflow, water should be charged first and acid added into water under controlled mixing.")
                blend_info[mid]={"mass_g":mass,"concentration_wt_pct":data.get("concentration_wt_pct"),
                                 "blend_t95_estimate_s":blend_t95,
                                 "basis":"Engineering homogenization estimate; no source-backed universal mixing time exists for all vessels/feeds."}
            events.append({"time_s":at,"event":"add_liquid","material":mid,"mass_g":mass,
                            "concentration_wt_pct":data.get("concentration_wt_pct"),
                            "blend_t95_estimate_s":blend_info.get(mid,{}).get("blend_t95_estimate_s")})
            continue
        solids += mass
        if first_water_time is not None and at < first_water_time:
            warnings.append(f"{mid}: solid is scheduled before the first water addition; dissolution timing is not physically established.")
        particle_size=float(a.get("particle_size_um") or data.get("particle_size_um",500.0))
        particle_size=max(10.0,min(10000.0,particle_size))
        sol_ref, sol_source, sol_url, sol_quality=_solubility_g_per_100g_water(mid,temp)
        if sol_ref is None:
            warnings.append(f"{mid}: no source-backed water-solubility curve is available; dissolution capacity is not claimed.")
            capacity=0.0; dissolved_mass=0.0; time_to_95=None; kinetic_t95=None
        else:
            # Equilibrium comes from source-backed solubility. Time-to-dissolve is a separate
            # engineering screening model inspired by Noyes-Whitney: smaller particles and
            # stronger agitation increase interfacial mass transfer, while the concentration
            # approaches equilibrium asymptotically rather than jumping to it instantly.
            base_t95={"urea":120,"map":180,"dap":180,"mkp":240,"sop":300,"nop":150,
                      "ammonium_nitrate":120,"ammonium_sulfate":240,"urea_phosphate":180,
                      "potassium_chloride":240,"magnesium_sulfate":210,"calcium_nitrate":150,
                      "calcium_chloride":180,"magnesium_nitrate":180,"citric_acid":240}.get(mid,240.0)
            size_factor=math.sqrt(particle_size/500.0)
            rpm_factor=1.0 if rpm<=0 else max(0.25,min(4.0,(rpm/300.0)**0.5))
            temp_factor=max(0.45,min(2.2,math.exp(0.012*(temp-20))))
            kinetic_t95=base_t95*size_factor/rpm_factor/temp_factor
            k=math.log(20.0)/max(kinetic_t95,1.0)
            steps=max(20,min(600,int(max(1.0,duration-at)*2)+1))
            dt=max(0.25,(duration-at)/steps) if duration>at else 0.0
            dmass=0.0; time_to_95=None; t=at
            for _ in range(steps):
                t=min(duration,t+dt)
                water_now=sum(max(0.0,float(x.get("mass_g",0))) for x in additions
                              if resolve(x.get("material",""))=="water" and float(x.get("time_s",0))<=t)
                capacity_now=sol_ref*water_now/100.0
                equilibrium_now=min(mass,capacity_now)
                dmass += max(0.0,equilibrium_now-dmass)*(1-math.exp(-k*dt))
                if time_to_95 is None and equilibrium_now>=mass*0.95 and dmass>=mass*0.95:
                    time_to_95=t
            capacity=sol_ref*water_mass_total/100.0
            dissolved_mass=min(mass,max(0.0,dmass))
        remaining=max(0.0,mass-dissolved_mass)
        dissolved[mid]=dissolved.get(mid,0)+dissolved_mass
        undissolved[mid]=undissolved.get(mid,0)+remaining
        dissolution_info[mid]={"mass_g":mass,"capacity_g":round(capacity,6),
                              "particle_size_um":particle_size,
                              "kinetic_t95_estimate_s":kinetic_t95,
                              "kinetic_basis":"Noyes-Whitney-inspired engineering screening estimate; not experimentally calibrated for this product/particle grade.",
                              "solubility_g_per_100g_water":sol_ref,
                              "solubility_basis":"g solute / 100 g H2O",
                              "solubility_source":sol_source,
                              "solubility_source_url":sol_url,
                              "solubility_quality":sol_quality,
                              "water_mass_total_g":round(water_mass_total,6),
                              "final_dissolved_g":dissolved_mass,"final_pct":100*dissolved_mass/max(mass,1e-12),
                              "complete":mass<=capacity and dissolved_mass>=mass*0.95,
                              "time_to_95_s":time_to_95,"start_s":at,
                              "undissolved_g":remaining,"precipitated":False,"precipitated_g":0.0}
        if sol_ref is not None and mass>capacity:
            warnings.append(f"{mid}: source-backed equilibrium capacity is approximately {capacity:.1f} g at {temp:.1f} °C for {water_mass_total:.1f} g water; solid residue can remain.")
        events.append({"time_s":at,"event":"add_solid","material":mid,"mass_g":mass,
                       "particle_size_um":particle_size,"kinetic_t95_estimate_s":kinetic_t95})
    total_mass=liquid_mass+solids
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
        "liquid_blending":blend_info,
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
