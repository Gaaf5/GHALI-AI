from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any
from app.tools.solubility_data import aqueous_solubility, SOURCE_SOLUBILITY_CURVES
from app.knowledge.evidence import evidence_for
from app.tools.model_selector import select_activity_model
from app.tools.lab_quality import assess_simulation, next_experiments
from app.tools.phreeqc_adapter import discover_phreeqc
from app.tools.lab_reactions import build_reaction_timeline, build_chemical_state_machine

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
    "zinc_sulfate": {"kind":"salt","phase":"solid","mw":287.54,"density":1.97,"hydrate":"heptahydrate","solubility_g_100ml":54.0,"cp":0.8},
    "seaweed_extract": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"water_soluble":True,"solubility_quality":"product TDS qualitative","solubility_source":"Water-soluble seaweed extract product TDS; 100% soluble grade","solubility_source_url":"https://www.duofenagri.com/products/good-quality-bulk-water-soluble-seaweed-extract-fertilizer-powder","solubility_note":"Product-grade seaweed extracts vary; simulator uses complete-solubility claim only when the selected grade is specified as water-soluble."},
    "aqua_amin": {"kind":"organic","phase":"liquid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"blend_t95_s":120.0,"product_note":"Name is ambiguous. The US Aquamine product found publicly is liquid ammonium sulfate; exact composition is withheld in the SDS."},
    "aquamine_us_las": {"kind":"fertilizer","phase":"liquid","mw":132.14,"density":1.0,"solubility_g_100ml":None,"cp":1.2,"blend_t95_s":120.0,"product_note":"Aquamine Liquid Ammonium Sulfate, US product. Exact concentration/density must come from the product COA/SDS; not guessed."},
    "ammonium_sulfite": {"kind":"salt","phase":"solid","mw":116.14,"density":1.41,"solubility_g_100ml":60.8,"cp":1.2,"hydrate_note":"Reference is hydrate-sensitive."},
    "boric_acid": {"kind":"acid","phase":"solid","mw":61.83,"density":1.435,"solubility_g_100ml":4.72,"cp":1.0},
    "amino_acid_80": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"water_soluble":True,"solubility_quality":"product TDS qualitative","solubility_source":"Amino acid 80% fertilizer powder TDS; completely water-soluble grade","solubility_source_url":"https://www.natureagrotech.cn/wp-content/uploads/2023/02/10.Amino-acid-80.pdf","solubility_note":"80% fertilizer powder products are commonly specified as completely water-soluble; exact product grade should control."},
    "amino_acid_40": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"water_soluble":True,"solubility_quality":"product TDS qualitative","solubility_source":"Amino acid 40% fertilizer powder TDS; fully soluble grade","solubility_source_url":"https://www.mos-agro.com/products/amino-acids-fertilizers/powder/40-standard.html","solubility_note":"40% fertilizer powder products are commonly specified as fully soluble; exact product form/grade should control."},
    "tkp_00_33_66": {"kind":"fertilizer","phase":"solid","mw":212.27,"density":2.564,"solubility_g_100ml":98.5,"cp":1.1},
    "mkpi_00_58_38": {"kind":"fertilizer","phase":"solid","mw":120.09,"density":1.0,"solubility_g_100ml":134.0,"cp":1.1,"water_soluble":True},
    "potassium_hydroxide": {"kind":"base","phase":"solid","mw":56.106,"density":2.044,"solubility_g_100ml":111.0,"cp":1.2},
    "potassium_humate": {"kind":"organic","phase":"solid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"water_soluble":True,"solubility_quality":"product-grade qualitative","solubility_source":"Potassium humate fertilizer grades advertised as completely water soluble; product composition varies","solubility_source_url":"https://www.seegrow.com.cn/productinfo/670049.html","solubility_note":"Commercial potassium humate grades vary; only 100% water-soluble grades should be treated as fully soluble."},
    "sodium_benzoate": {"kind":"preservative","phase":"solid","mw":144.11,"density":1.5,"solubility_g_100ml":63.0,"cp":1.2},
    "sodium_edta": {"kind":"chelate","phase":"solid","mw":372.24,"density":1.0,"hydrate":"dihydrate","solubility_g_100ml":108.0,"cp":1.2},
    "calcium_sodium_edta": {"kind":"chelate","phase":"solid","mw":374.27,"density":1.0,"solubility_g_100ml":None,"cp":1.2,"water_soluble":True,"solubility_note":"Water-soluble, but the public source found gives a 0.1 M preparation point rather than a saturation curve."},
    "lisiveg": {"kind":"organic","phase":"liquid","mw":None,"density":1.0,"solubility_g_100ml":None,"cp":1.3,"blend_t95_s":120.0,"product_note":"Plant-derived enzymatic protein hydrolysate technology. Project specification: N 4.66%, organic matter 40%, peptides/amino acids 29.1%; verify the exact batch COA before using density/solids values."},
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
    "aquamine_us_las":"Aquamine® Liquid Ammonium Sulfate (USA)","ammonium_sulfite":"أمونيوم سلفيت","boric_acid":"بوريك أسيد","amino_acid_80":"Amino Acid 80%",
    "amino_acid_40":"Amino Acid 40%","tkp_00_33_66":"TKP 00-33-66","mkpi_00_58_38":"MKPI 00-58-38",
    "potassium_hydroxide":"KOH هيدروكسيد البوتاسيوم","potassium_humate":"بوتاسيوم هيوميت / هيوميك أسيد",
    "sodium_benzoate":"بنزوات الصوديوم","sodium_edta":"Sodium EDTA","calcium_sodium_edta":"Calcium EDTA",
    "lisiveg":"Lisiveg",
}
ALIASES = {v.lower():k for k,v in ARABIC_NAMES.items()}
ALIASES.update({"ماء":"water","يوريا":"urea","كبريتات البوتاسيوم":"sop","سوب":"sop",
                "نترات البوتاسيوم":"nop","نوب":"nop","فوسفات اليوريا":"urea_phosphate",
                "كلوريد البوتاسيوم":"potassium_chloride","مذيب":"water",
                "mea":"monoethanolamine","مونو ايثانول امين":"monoethanolamine","مونو إيثانول أمين":"monoethanolamine",
                "sea weed":"seaweed_extract","seaweed":"seaweed_extract","اعشاب بحرية":"seaweed_extract","الأعشاب البحرية":"seaweed_extract",
                "سلفات الزنك":"zinc_sulfate","كبريتات الزنك":"zinc_sulfate","اكوا امين":"aquamine_us_las","أكوا أمين":"aquamine_us_las",
                "aquamine":"aquamine_us_las","ammonium sulfite":"ammonium_sulfite","امونيوم سلفيت":"ammonium_sulfite",
                "boric acid":"boric_acid","بوريك اسيد":"boric_acid","حمض البوريك":"boric_acid",
                "amino acid 80":"amino_acid_80","amino acid 40":"amino_acid_40","tkp":"tkp_00_33_66","mkpi":"mkpi_00_58_38",
                "koh":"potassium_hydroxide","k2oh":"potassium_hydroxide","هيوميك اسيد":"potassium_humate","هيوميك":"potassium_humate",
                "potassium humate":"potassium_humate","sodium edta":"sodium_edta","calcium edta":"calcium_sodium_edta",
                "lisiveg":"lisiveg","بنزوات الصوديوم":"sodium_benzoate"})
MIXING_COEFF = {"water":1.0,"ethanol":0.9,"isopropanol":0.9,"methanol":0.9,
                "acetone":0.8,"glycerol":1.2}
def resolve(name: str) -> str:
    key = str(name).strip().lower().replace(" ","_")
    return key if key in MATERIALS else ALIASES.get(str(name).strip().lower(), key)

def catalog():
    out=[]
    for key,v in MATERIALS.items():
        sol20,sol_source,sol_url,sol_quality=_solubility_g_per_100g_water(key,20)
        if sol20 is None and v.get("water_soluble"):
            sol_source=v.get("solubility_source","Product technical data: water-soluble grade")
            sol_url=v.get("solubility_source_url","")
            sol_quality=v.get("solubility_quality","product-spec qualitative")
        if sol20 is None and v.get("phase")=="liquid":
            sol_source=v.get("product_note","Liquid feed: dissolution equilibrium is not modeled.")
            sol_url=v.get("solubility_source_url","")
            sol_quality=v.get("solubility_quality","liquid-feed / blending")
        out.append({"id":key,"name":ARABIC_NAMES.get(key,key.replace("_"," ").title()),
                    "kind":v["kind"],"mw":v["mw"],"density":v["density"],
                    "solubility_g_100ml":v["solubility_g_100ml"],"solubility_g_per_100g_water_20c":sol20,
                    "solubility_source":sol_source,"solubility_source_url":sol_url,"solubility_quality":sol_quality,
                    "evidence":evidence_for(sol_url, quality=sol_quality, basis="g solute / 100 g H2O" if sol20 is not None else None, temperature_c=20 if sol20 is not None else None, product_specific=bool(v.get("water_soluble") or v.get("product_note"))),
                    "cp":v["cp"]})
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

def _shared_solvent_equilibrium(solid_rows, water_mass_g, temperature_c):
    """
    Shared-solvent screening model.

    Pure-water solubility is a ceiling for each material, not an independent
    capacity that can be spent simultaneously by every solute. Dissolved
    species from the other solutes occupy the same aqueous phase and reduce
    the effective capacity available to a given solid.

    This is deliberately an engineering screening model, not a replacement for
    a full electrolyte activity-coefficient / Pitzer-SIT equilibrium solver.
    The occupancy proxy is based on dissolved particle moles relative to water
    moles; it preserves the measured pure-water ceiling for a single-solute
    experiment and applies a shared-medium penalty only when other solutes are
    present.
    """
    if water_mass_g <= 0:
        return {}

    water_moles = water_mass_g / MATERIALS["water"]["mw"]
    states = {}
    for row in solid_rows:
        mid=row["material"]
        states[mid]={
            "mass_g":row["mass_g"],
            "pure_capacity_g":row.get("pure_capacity_g"),
            "dissolved_g":0.0,
            "qualitative":bool(row.get("qualitative")),
            "particle_count_factor":max(1.0,float(row.get("particle_count_factor",1.0))),
        }

    # Conservative shared-solvent saturation budget.
    # Solve one common saturation factor for the whole aqueous phase. This avoids
    # row-order dependence: simultaneous additions receive the same shared factor.
    # For each material i, dissolved_i = min(charged_i, pure_capacity_i * f).
    # The factor f is chosen so that the sum of normalized dissolved loads is <= 1.
    capacities={}
    for mid,state in states.items():
        cap=state.get("pure_capacity_g")
        if cap is None and state["qualitative"]:
            cap=state["mass_g"]
        capacities[mid]=max(float(cap or 0.0),0.0)

    def normalized_load(factor):
        load=0.0
        for mid,state in states.items():
            cap=capacities[mid]
            if cap<=0:
                continue
            load += min(state["mass_g"],cap*factor)/cap
        return load

    if normalized_load(1.0)<=1.0+1e-12:
        shared_factor=1.0
    else:
        lo,hi=0.0,1.0
        for _ in range(80):
            mid_factor=(lo+hi)/2.0
            if normalized_load(mid_factor)>1.0:
                hi=mid_factor
            else:
                lo=mid_factor
        shared_factor=lo

    for mid,state in states.items():
        cap=capacities[mid]
        state["dissolved_g"]=min(state["mass_g"],cap*shared_factor) if cap>0 else 0.0

    total_dissolved=sum(x["dissolved_g"] for x in states.values())
    total_capacity_load=normalized_load(shared_factor)
    out={}
    for mid,state in states.items():
        cap=capacities[mid]
        other_load=0.0
        for other,other_state in states.items():
            if other==mid:
                continue
            other_cap=capacities[other]
            if other_cap>0:
                other_load += other_state["dissolved_g"]/other_cap
        occupancy_factor=max(0.0,1.0-other_load)
        effective=cap*shared_factor
        out[mid]={
            "pure_capacity_g":state["pure_capacity_g"],
            "effective_capacity_g":effective,
            "dissolved_g":state["dissolved_g"],
            "other_solute_particle_ratio":other_load,
            "solvent_occupancy_factor":occupancy_factor,
            "shared_saturation_factor":shared_factor,
            "shared_saturation_load":total_capacity_load,
            "undissolved_g":max(0.0,state["mass_g"]-state["dissolved_g"]),
        }
    return {"materials":out,
            "water_mass_g":water_mass_g,
            "total_dissolved_solids_g":total_dissolved,
            "shared_solvent_model":"conservative shared saturation budget",
            "shared_saturation_load":total_capacity_load,
            "warning":"A conservative shared-solvent saturation budget is active. Pure-water solubility is not an independent solvent capacity for each material; later additions compete with the existing dissolved load. This is an engineering screening approximation, not a full multicomponent activity-coefficient model."}

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
    # Guard against corrupted/UI-scaled masses. The limit scales with vessel size
    # rather than silently clipping the user's charge. Repeated additions remain
    # valid when they occur at different times.
    max_addition_mass_g = max(1000.0, volume * 10000.0)
    total_charge_g = 0.0
    for a in additions:
        raw_mass = a.get("mass_g", 0)
        try:
            mass = float(raw_mass)
        except (TypeError, ValueError):
            raise ValueError("Every material mass must be a valid number.")
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError("Every material mass must be a finite number greater than 0 g.")
        if mass > max_addition_mass_g:
            raise ValueError(
                f"Material charge {mass:g} g is outside the physical input range for "
                f"this {volume:g} L vessel. Maximum per addition is {max_addition_mass_g:g} g."
            )
        total_charge_g += mass
    if total_charge_g > max_addition_mass_g * 4:
        raise ValueError(
            f"Total charged mass {total_charge_g:g} g is outside the configured vessel "
            f"range. Check for a duplicated or mis-scaled input."
        )
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
    # Build one shared equilibrium state for the whole aqueous phase. This is
    # intentionally done before individual dissolution kinetics so each solid
    # competes for the same solvent instead of receiving an independent water
    # capacity.
    solid_totals={}
    for a in additions:
        mid=resolve(a.get("material",""))
        data=MATERIALS[mid]
        phase=data.get("phase", "liquid" if data.get("kind")=="solvent" else "solid")
        if phase!="solid":
            continue
        mass=max(0.0,float(a.get("mass_g",0)))
        sol_ref, sol_source, sol_url, sol_quality=_solubility_g_per_100g_water(mid,temp)
        qualitative=sol_ref is None and bool(data.get("water_soluble"))
        if sol_ref is None and not qualitative:
            pure_capacity=None
        else:
            pure_capacity=(mass if qualitative else sol_ref*water_mass_total/100.0)
        # Approximate number of dissolved particles contributed per formula unit.
        # This is only a shared-solvent occupancy proxy; speciation is handled
        # separately by lab_chemistry.
        try:
            from app.tools.lab_chemistry import SPECIES
            particle_factor=max(1.0,sum(float(s.stoich) for s in SPECIES.get(mid,[])))
        except Exception:
            particle_factor=1.0
        if mid not in solid_totals:
            solid_totals[mid]={"mass_g":0.0,"pure_capacity_g":0.0 if pure_capacity is not None else None,
                               "qualitative":qualitative,"particle_count_factor":particle_factor}
        solid_totals[mid]["mass_g"] += mass
        if pure_capacity is not None and solid_totals[mid]["pure_capacity_g"] is not None:
            # Recompute from the aggregate mass at the same final water charge.
            if qualitative:
                solid_totals[mid]["pure_capacity_g"]=solid_totals[mid]["mass_g"]
            else:
                solid_totals[mid]["pure_capacity_g"]=sol_ref*water_mass_total/100.0
        else:
            solid_totals[mid]["pure_capacity_g"]=None
    # Build a stateful aqueous-phase ledger.
    #
    # IMPORTANT: this is deliberately NOT a final re-balancing of all charged
    # materials. Once material has dissolved, that dissolved amount remains part
    # of the current solution state and consumes the shared saturation budget.
    # A later solid therefore sees only the remaining budget. This directly models
    # the requested workflow: saturate MAP first, then add SOP -> SOP does not get
    # a fresh 1000 g-water capacity.
    solid_additions=[{
        "order":i,
        "material":resolve(a.get("material","")),
        "mass_g":max(0.0,float(a.get("mass_g",0))),
        "time_s":float(a.get("time_s",0)),
    } for i,a in enumerate(additions)
      if MATERIALS.get(resolve(a.get("material","")),{}).get("phase","solid")=="solid"]
    eq_times=sorted(set([0.0,duration]
                        +[x["time_s"] for x in solid_additions]
                        +[float(x.get("time_s",0)) for x in additions
                          if resolve(x.get("material",""))=="water"]))
    # At every addition event, solve a single shared aqueous-phase equilibrium
    # target for ALL active solids. A later salt is therefore allowed to displace
    # part of an earlier saturated solute instead of receiving fresh water capacity.
    solution_dissolved={}
    solution_charged={}
    shared_schedule={}
    kinetic_snapshots={}
    # Event-time snapshots are kept separately from equilibrium targets. This is
    # essential: the equilibrium target answers "where the phase wants to go",
    # while the kinetic snapshot answers "where the experiment has actually reached
    # by this time". The UI/AI must never collapse those two concepts into one number.
    for eq_t in eq_times:
        active_mass={}
        for x in solid_additions:
            if x["time_s"]<=eq_t:
                mid=x["material"]
                active_mass[mid]=active_mass.get(mid,0.0)+x["mass_g"]
        water_at_t=sum(max(0.0,float(x.get("mass_g",0))) for x in additions
                       if resolve(x.get("material",""))=="water"
                       and float(x.get("time_s",0))<=eq_t)

        pure_caps={}
        qualitative={}
        for mid,mass_active in active_mass.items():
            data=MATERIALS[mid]
            sol_t,src_t,url_t,qual_t=_solubility_g_per_100g_water(mid,temp)
            qualitative[mid]=sol_t is None and bool(data.get("water_soluble"))
            if sol_t is not None:
                pure_caps[mid]=max(0.0,sol_t*water_at_t/100.0)
            elif qualitative[mid]:
                # Product-TDS qualitative claim: use the current charge as a
                # screening ceiling, never as a universal saturation value.
                pure_caps[mid]=mass_active
            else:
                pure_caps[mid]=0.0

        # One common saturation factor is solved for the whole aqueous phase.
        # This is the key invariant: capacities are NOT additive across solutes.
        def normalized_load(factor):
            load=0.0
            for mid,mass_active in active_mass.items():
                cap=pure_caps.get(mid,0.0)
                if cap>0:
                    load += min(mass_active,cap*factor)/cap
            return load

        if not active_mass or normalized_load(1.0)<=1.0+1e-12:
            shared_factor=1.0
        else:
            lo,hi=0.0,1.0
            for _ in range(80):
                f=(lo+hi)/2.0
                if normalized_load(f)>1.0:
                    hi=f
                else:
                    lo=f
            shared_factor=lo

        # The equilibrium target may re-partition the dissolved phase when a new
        # material arrives. This explicitly permits precipitation of an earlier
        # saturated material and dissolution of a later material in the same water.
        solution_dissolved={}
        for mid,mass_active in active_mass.items():
            cap=pure_caps.get(mid,0.0)
            solution_dissolved[mid]=min(mass_active,cap*shared_factor) if cap>0 else 0.0
            solution_charged[mid]=mass_active

        load=normalized_load(shared_factor)
        materials={}
        for mid,mass_active in active_mass.items():
            cap=pure_caps.get(mid,0.0)
            diss=solution_dissolved.get(mid,0.0)
            other_load=0.0
            for other,other_diss in solution_dissolved.items():
                if other==mid: continue
                other_cap=pure_caps.get(other,0.0)
                if other_cap>0: other_load += other_diss/other_cap
            materials[mid]={
                "pure_capacity_g":cap if cap>0 else None,
                "effective_capacity_g":diss,
                "dissolved_g":diss,
                "other_solute_particle_ratio":other_load,
                "solvent_occupancy_factor":max(0.0,1.0-other_load),
                "shared_saturation_factor":shared_factor,
                "shared_saturation_load":load,
                "undissolved_g":max(0.0,mass_active-diss),
                "state_model":"stateful_shared_solution",
            }
        shared_schedule[eq_t]={
            "materials":materials,
            "water_mass_g":water_at_t,
            "total_dissolved_solids_g":sum(solution_dissolved.values()),
            "shared_solvent_model":"stateful shared solution ledger",
            "shared_saturation_load":load,
            "warning":"Stateful shared-solution screening: each addition is equilibrated against the entire existing aqueous phase. Later additions can force precipitation of earlier dissolved material and do not receive an independent pure-water capacity. This is an engineering heuristic, not a full activity-coefficient/speciation model."
        }
        # Equilibrium snapshot at this event time. It is intentionally stored with
        # explicit labels so downstream UI/AI can distinguish equilibrium target
        # from kinetic progress.
        kinetic_snapshots.setdefault(eq_t,{})
        for mid, st in materials.items():
            kinetic_snapshots[eq_t][mid]={
                "event_equilibrium_target_g":round(float(st.get("effective_capacity_g") or 0.0),6),
                "charged_g":round(float(active_mass.get(mid,0.0)),6),
                "equilibrium_undissolved_g":round(float(st.get("undissolved_g") or 0.0),6),
                "shared_saturation_factor":st.get("shared_saturation_factor"),
                "shared_saturation_load":st.get("shared_saturation_load"),
            }
    shared_eq=shared_schedule.get(duration,{"materials":{}})
    if shared_eq:
        warnings.append("Shared-solvent occupancy is active: dissolved materials compete for the same aqueous phase; individual pure-water solubility ceilings are not added independently.")
        warnings.append("Time-resolved equilibrium is active: each addition is evaluated against the solution state that exists at that time; later additions can force re-precipitation or re-dissolution of earlier solids.")
    solid_ids={resolve(a.get("material","")) for a in additions
               if MATERIALS.get(resolve(a.get("material","")),{}).get("phase", "liquid" if MATERIALS.get(resolve(a.get("material","")),{}).get("kind")=="solvent" else "solid")=="solid"}
    if len(solid_ids)>1:
        warnings.append("Multicomponent solution: pure-water solubility values are reference ceilings only; mixed-solution activity/common-ion effects are evaluated separately.")
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
        # Capacity at the moment this material enters the vessel. Future
        # additions are intentionally excluded from its initial dissolution state.
        prior_eq_times=[et for et in shared_schedule if et<=at]
        addition_eq_time=max(prior_eq_times) if prior_eq_times else 0.0
        addition_eq=shared_schedule.get(addition_eq_time,{"materials":{}})
        shared_state=addition_eq.get("materials",{}).get(mid,{}) if addition_eq else {}
        final_state=shared_eq.get("materials",{}).get(mid,{}) if shared_eq else {}
        total_mid_mass=solid_totals.get(mid,{}).get("mass_g",mass)
        allocation_ratio=mass/max(total_mid_mass,1e-12)
        pure_capacity_total=shared_state.get("pure_capacity_g")
        effective_capacity_total=shared_state.get("effective_capacity_g")
        if sol_ref is not None and effective_capacity_total is not None:
            capacity=max(0.0,float(effective_capacity_total)*allocation_ratio)
            pure_capacity=max(0.0,float(pure_capacity_total or 0.0)*allocation_ratio)
        elif sol_ref is None and data.get("water_soluble"):
            capacity=mass
            pure_capacity=mass
        else:
            capacity=0.0
            pure_capacity=0.0
        final_capacity=final_state.get("effective_capacity_g") if final_state else None
        if final_capacity is not None:
            final_capacity=max(0.0,float(final_capacity)*allocation_ratio)
        peak_dissolved=0.0
        if sol_ref is None and data.get("water_soluble"):
            if water_mass_total <= 0:
                warnings.append(f"{mid}: product is described as water-soluble, but no water was charged; dissolution is not claimed.")
                capacity=0.0; dissolved_mass=0.0; time_to_95=None; kinetic_t95=None
            else:
                # Product/TDS-level claim, not a saturation curve. Treat the selected
                # grade as dissolvable at the current dilution, but do not invent a
                # temperature-dependent equilibrium limit.
                capacity=mass
                base_t95={"seaweed_extract":240,"amino_acid_80":240,"amino_acid_40":240,
                          "potassium_humate":300,"calcium_sodium_edta":300}.get(mid,240.0)
                size_factor=math.sqrt(particle_size/500.0)
                rpm_factor=1.0 if rpm<=0 else max(0.25,min(4.0,(rpm/300.0)**0.5))
                temp_factor=max(0.45,min(2.2,math.exp(0.006*(temp-20))))
                kinetic_t95=base_t95*size_factor/rpm_factor/temp_factor
                k=math.log(20.0)/max(kinetic_t95,1.0)
                steps=max(20,min(600,int(max(1.0,duration-at)*2)+1))
                dt=max(0.25,(duration-at)/steps) if duration>at else 0.0
                dmass=0.0; time_to_95=None; t=at
                for _ in range(steps):
                    t=min(duration,t+dt)
                    dmass += max(0.0,mass-dmass)*(1-math.exp(-k*dt))
                    if time_to_95 is None and dmass>=mass*0.95:
                        time_to_95=t
                dissolved_mass=min(mass,max(0.0,dmass))
                warnings.append(f"{mid}: fully-water-soluble product claim used; no universal saturation curve was available for this commercial grade.")
                sol_source=data.get("solubility_source","Product technical data: water-soluble grade")
                sol_url=data.get("solubility_source_url","")
                sol_quality=data.get("solubility_quality","product-spec qualitative")
        elif sol_ref is None:
            warnings.append(f"{mid}: no source-backed water-solubility curve is available; dissolution capacity is not claimed.")
            capacity=0.0; dissolved_mass=0.0; time_to_95=None; kinetic_t95=None
        else:
            # Separate equilibrium capacity from dissolution kinetics.  The equilibrium
            # ceiling answers "can this amount dissolve?"; kinetics answers "how much
            # has dissolved by the requested experiment time?".  A fixed t95 must never
            # turn a thermodynamically soluble small charge into an equilibrium residue.
            size_factor=math.sqrt(500.0/max(particle_size,10.0))
            rpm_factor=1.0 if rpm<=0 else max(0.25,min(4.0,(rpm/300.0)**0.5))
            temp_factor=max(0.45,min(2.2,math.exp(0.012*(temp-20))))
            base_rate={"urea":0.030,"map":0.022,"dap":0.022,"mkp":0.018,"sop":0.014,
                       "nop":0.030,"ammonium_nitrate":0.032,"ammonium_sulfate":0.018,
                       "urea_phosphate":0.022,"potassium_chloride":0.018,"magnesium_sulfate":0.020,
                       "calcium_nitrate":0.026,"calcium_chloride":0.022,"magnesium_nitrate":0.022,
                       "citric_acid":0.018}.get(mid,0.018)
            # Low-loading charges have a larger concentration driving force (Cs-C).
            # Scale the engineering mass-transfer rate by the square-root of the
            # charged/equilibrium loading ratio. This keeps near-saturated charges
            # close to the base material rate while allowing small dilute charges
            # to dissolve substantially faster.
            loading_ratio=min(1.0,mass/max(capacity,1e-9))
            driving_force_factor=min(6.0,1.0/math.sqrt(max(loading_ratio,1e-9)))
            k=base_rate*size_factor*rpm_factor*temp_factor*driving_force_factor
            equilibrium_fraction=min(1.0,capacity/max(mass,1e-9))
            kinetic_t95=math.log(20.0)/max(k,1e-9) if equilibrium_fraction>=0.95 else None
            # Piecewise time-dependent dissolution/precipitation.  The target
            # equilibrium is allowed to change whenever a later addition changes the
            # shared solution.  This is intentionally a first-order engineering
            # relaxation model, not a full transient electrolyte calculation.
            dmass=0.0
            peak_dissolved=0.0
            time_to_95=None
            event_times=sorted(set([at,duration]
                                   +[float(et) for et in shared_schedule if at < float(et) <= duration]))
            for interval_start,interval_end in zip(event_times,event_times[1:]):
                dt_total=max(0.0,interval_end-interval_start)
                if dt_total<=0:
                    continue
                probe_t=interval_start+1e-9
                prior_times=[et for et in shared_schedule if float(et)<=probe_t]
                state_time=max(prior_times) if prior_times else 0.0
                interval_state=shared_schedule.get(state_time,{"materials":{}})
                interval_material=interval_state.get("materials",{}).get(mid,{})
                target_capacity=interval_material.get("effective_capacity_g")
                if target_capacity is None:
                    target_capacity=0.0
                target_capacity=max(0.0,min(mass,float(target_capacity)*allocation_ratio))

                # Recompute the mass-transfer rate against the current equilibrium
                # target.  A lower target causes precipitation; a higher target causes
                # re-dissolution. Both processes use the same first-order relaxation
                # approximation, with loading relative to the interval target.
                interval_loading=min(1.0,mass/max(target_capacity,1e-9))
                interval_drive=min(6.0,1.0/math.sqrt(max(interval_loading,1e-9)))
                k_interval=base_rate*size_factor*rpm_factor*temp_factor*interval_drive
                dmass += (target_capacity-dmass)*(1-math.exp(-k_interval*dt_total))
                # After ~5 time constants the engineering kinetic model treats the
                # target as reached; retaining a tiny exponential tail would create
                # artificial milligram residues in long, fully soluble runs.
                tau=1.0/max(k_interval,1e-12)
                if target_capacity >= mass and dt_total >= 5.0*tau:
                    dmass=target_capacity
                dmass=max(0.0,min(mass,dmass))
                peak_dissolved=max(peak_dissolved,dmass)
                snap=kinetic_snapshots.setdefault(interval_end,{})
                snap.setdefault(mid,{})
                snap[mid]["kinetic_dissolved_g"]=round(float(dmass),6)
                snap[mid]["kinetic_undissolved_g"]=round(max(0.0,mass-dmass),6)
                snap[mid]["pre_event_equilibrium_target_g"]=round(float(target_capacity),6)
                snap[mid]["kinetic_state"]="transient"
                snap[mid]["time_s"]=float(interval_end)

                # A 95% crossing only counts if the final equilibrium can still
                # sustain 95% after all later additions have arrived.
                final_probe=shared_schedule.get(duration,{"materials":{}}).get("materials",{}).get(mid,{})
                final_probe_capacity=final_probe.get("effective_capacity_g")
                final_probe_capacity=(0.0 if final_probe_capacity is None else
                                      max(0.0,float(final_probe_capacity)*allocation_ratio))
                if time_to_95 is None and final_probe_capacity>=mass*0.95 and dmass>=mass*0.95:
                    time_to_95=interval_end

            dissolved_mass=min(mass,max(0.0,dmass))
            final_capacity=final_state.get("effective_capacity_g") if final_state else None
            if final_capacity is not None:
                final_capacity=max(0.0,float(final_capacity)*allocation_ratio)
            if final_capacity is not None and final_capacity < mass:
                warnings.append(f"{mid}: final mixed-solution equilibrium capacity is {final_capacity:.1f} g; later additions can force additional re-precipitation of earlier dissolved material.")
            elif capacity >= mass:
                warnings.append(f"{mid}: equilibrium is fully dissolvable at the moment of addition; final residue is controlled by later mixed-equilibrium changes and kinetics.")
            else:
                warnings.append(f"{mid}: equilibrium capacity at addition is below the charged mass; undissolved solid remains available for later dissolution only if the mixed-solution capacity subsequently increases.")
        remaining=max(0.0,mass-dissolved_mass)
        dissolved[mid]=dissolved.get(mid,0)+dissolved_mass
        undissolved[mid]=undissolved.get(mid,0)+remaining
        dissolution_info[mid]={"mass_g":mass,"capacity_g":round(capacity,6),
                              "particle_size_um":particle_size,
                              "kinetic_t95_estimate_s":kinetic_t95,
                              "kinetic_tau_estimate_s":None if kinetic_t95 is None else kinetic_t95/math.log(20.0),
                              "equilibrium_max_pct":round(100.0*(1.0 if (sol_ref is None and data.get("water_soluble")) else min(1.0,capacity/max(mass,1e-9))),6),
                              "loading_ratio":round(min(1.0,mass/max(capacity,1e-9)),6),
                              "kinetic_basis":"Noyes-Whitney-inspired engineering screening estimate with concentration-driving-force scaling; not experimentally calibrated for this product/particle grade.",
                              "solubility_g_per_100g_water":sol_ref,
                              "pure_water_capacity_g":round(pure_capacity,6),
                              "mixed_solution_effective_capacity_g":round(capacity,6),
                              "equilibrium_capacity_at_addition_g":round(capacity,6),
                              "final_mixed_equilibrium_capacity_g":round(final_capacity,6) if final_capacity is not None else None,
                              "equilibrium_state_time_s":addition_eq_time,
                              "other_solute_particle_ratio":shared_state.get("other_solute_particle_ratio"),
                              "solvent_occupancy_factor":shared_state.get("solvent_occupancy_factor",1.0),
                              "shared_saturation_factor_at_addition":shared_state.get("shared_saturation_factor"),
                              "shared_saturation_load_at_addition":shared_state.get("shared_saturation_load"),
                              "final_shared_saturation_factor":final_state.get("shared_saturation_factor") if final_state else None,
                              "final_shared_saturation_load":final_state.get("shared_saturation_load") if final_state else None,
                              "final_shared_capacity_remaining":(max(0.0,1.0-float(final_state.get("shared_saturation_load",0.0))) if final_state and final_state.get("shared_saturation_load") is not None else None),
                              "state_model":shared_state.get("state_model","stateful_shared_solution"),
                              "solubility_basis":"g solute / 100 g H2O",
                              "solubility_source":sol_source,
                              "solubility_source_url":sol_url,
                              "solubility_quality":sol_quality,
                              "evidence":evidence_for(sol_url, quality=sol_quality, basis="g solute / 100 g H2O" if sol_ref is not None else None, temperature_c=temp if sol_ref is not None else None, product_specific=bool(data.get("water_soluble") or data.get("product_note"))),
                              "water_mass_total_g":round(water_mass_total,6),
                              "final_dissolved_g":dissolved_mass,"final_pct":100*dissolved_mass/max(mass,1e-12),
                              "peak_dissolved_g":round(peak_dissolved,6),
                              "reprecipitated_g":round(max(0.0,peak_dissolved-dissolved_mass),6),
                              "complete":(final_capacity is None and mass<=capacity or final_capacity is not None and final_capacity>=mass) and dissolved_mass>=mass*0.95,
                              "time_to_95_s":time_to_95,"start_s":at,
                              "undissolved_g":remaining,"precipitated":False,"precipitated_g":0.0}
        if sol_ref is not None and mass>capacity:
            warnings.append(f"{mid}: pure-water capacity is approximately {pure_capacity:.1f} g, but mixed-solution effective capacity is approximately {capacity:.1f} g after accounting for dissolved material already occupying the shared aqueous phase; solid residue can remain.")
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
    aqueous_volume_l=(water_mass_total/max(MATERIALS["water"]["density"],1e-9)/1000.0) if water_mass_total>0 else volume
    chemistry=analyze_chemistry(experiment,dissolved,MATERIALS,aqueous_volume_l)

    # Feed equilibrium precipitation back into the global mass balance. The chemistry
    # layer returns material-level dissolved masses after Ksp removal; the virtual
    # lab must expose the same state, otherwise the chemistry screen and mass balance
    # would disagree.
    precip_state=(chemistry.get("precipitation_equilibrium") or {}).get("dissolved_g") or {}
    precip_delta={}
    for mid,old_mass in list(dissolved.items()):
        new_mass=max(0.0,float(precip_state.get(mid,old_mass)))
        delta=max(0.0,float(old_mass)-new_mass)
        if delta>1e-8:
            precip_delta[mid]=delta
            dissolved[mid]=new_mass
            undissolved[mid]=undissolved.get(mid,0.0)+delta
            info=dissolution_info.get(mid)
            if info:
                info["final_dissolved_g"]=new_mass
                info["final_pct"]=100.0*new_mass/max(float(info.get("mass_g",old_mass)),1e-12)
                info["reprecipitated_g"]=float(info.get("reprecipitated_g",0.0))+delta
                info["precipitated"]=True
                info["precipitated_g"]=float(info.get("precipitated_g",0.0))+delta
                info["complete"]=False
    if precip_delta:
        for p in (chemistry.get("precipitation_equilibrium") or {}).get("events",[]):
            events.append({"time_s":duration,"event":"precipitation","material":p["product"],
                           "mass_g":round(sum(precip_delta.values()),6),
                           "precipitated_mol":p.get("precipitated_mol",0.0),
                           "Q_over_Ksp_before":p.get("Q_over_Ksp_before")})
        # Re-analyze the actual final aqueous phase so pH, ionic strength and Ksp
        # screens describe the same mass-balanced state returned to the UI.
        chemistry=analyze_chemistry(experiment,dissolved,MATERIALS,aqueous_volume_l)
        warnings.append("Ksp precipitation was fed back into the final mass balance; reported dissolved/undissolved masses include the predicted precipitated solid.")
    warnings.extend(chemistry.get("warnings",[]))
    dissolved_total=sum(dissolved.values())
    quality=assess_simulation({
        "mass_balance":{
            "input_g":sum(max(0.0,float(a.get("mass_g",0))) for a in additions
                         if resolve(a.get("material",""))!="water"
                         and MATERIALS.get(resolve(a.get("material","")),{}).get("phase","solid")=="solid"),
            "dissolved_solids_g":dissolved_total,
            "undissolved_solids_g":sum(undissolved.values()),
        },
        "solid_input_g":sum(max(0.0,float(a.get("mass_g",0))) for a in additions
                           if resolve(a.get("material",""))!="water"
                           and MATERIALS.get(resolve(a.get("material","")),{}).get("phase","solid")=="solid"),
        "dissolution":dissolution_info,
        "chemistry":chemistry,
        "warnings":warnings,
    }, bool(discover_phreeqc().get("available")))
    reaction_timeline=build_reaction_timeline(additions, chemistry, kinetic_snapshots)
    chemical_state_machine=build_chemical_state_machine(reaction_timeline, chemistry)
    # Make the state ledger explicit in the API. This is the source of truth for
    # the visual timeline and for the AI review/planner; it prevents the frontend
    # from reconstructing chemistry from presentation-only fields.
    state_timeline={str(t):{mid:dict(state) for mid,state in states.items()} for t,states in sorted(kinetic_snapshots.items(), key=lambda x: float(x[0]))}
    return {
        "status":"SIMULATED","confidence":confidence,"model":"GHALI Virtual Lab v3",
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
        "reaction_timeline":reaction_timeline,
        "chemical_state_machine":chemical_state_machine,
        "state_timeline":state_timeline,
        "warnings":warnings,"events":events,
        "input_additions":[dict(a) for a in additions],
        "quality":quality,
        "next_experiments":next_experiments({
            "conditions":{"temperature_c":temp,"rpm":rpm,"duration_s":duration},
            "input_additions":[dict(a) for a in additions],
        }),
        "note":"Simulation is a screening model. Chemistry rules require validated property data and laboratory calibration before production use."
    }


def sweep(base_experiment: dict[str, Any], grid: dict[str, list[Any]]) -> dict[str, Any]:
    """Run a deterministic Cartesian parameter sweep over the virtual lab.

    The default objective is maximum dissolved solids fraction, with lower
    undissolved mass as the tie-breaker. Every run retains its input conditions
    and full simulation result so the planner can later learn from the sweep.
    """
    keys=list(grid or {})
    values=[list(grid[k]) for k in keys]
    runs=[]
    import itertools
    for combo in itertools.product(*values):
        exp=dict(base_experiment)
        for key,value in zip(keys,combo):
            exp[key]=value
        result=simulate(exp)
        dissolved=float(result.get("mass_balance",{}).get("dissolved_solids_g",0.0))
        undissolved=float(result.get("mass_balance",{}).get("undissolved_solids_g",0.0))
        score=dissolved/(dissolved+undissolved) if dissolved+undissolved>0 else 0.0
        runs.append({"parameters":{k:v for k,v in zip(keys,combo)},"score":score,"result":result})
    best=max(runs,key=lambda x:(x["score"],-x["result"].get("conditions",{}).get("temperature_c",0))) if runs else None
    return {"runs":len(runs),"parameters":keys,"results":runs,"best":best,
            "objective":"maximize dissolved-solids fraction; tie-break by lower temperature"}

__all__=["MATERIALS","catalog","resolve","simulate","sweep"]
