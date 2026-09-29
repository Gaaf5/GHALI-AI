from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Species:
    formula: str
    charge: int
    family: str
    stoich: float = 1.0

SPECIES={
 "urea":[Species("CO(NH2)2",0,"urea")],
 "map":[Species("NH4+",1,"ammonium"),Species("H2PO4-",-1,"phosphate")],
 "dap":[Species("NH4+",1,"ammonium",2),Species("HPO4--",-2,"phosphate")],
 "mkp":[Species("K+",1,"potassium"),Species("H2PO4-",-1,"phosphate")],
 "sop":[Species("K+",1,"potassium",2),Species("SO4--",-2,"sulfate")],
 "nop":[Species("K+",1,"potassium"),Species("NO3-",-1,"nitrate")],
 "ammonium_nitrate":[Species("NH4+",1,"ammonium"),Species("NO3-",-1,"nitrate")],
 "ammonium_sulfate":[Species("NH4+",1,"ammonium",2),Species("SO4--",-2,"sulfate")],
 "urea_phosphate":[Species("urea",0,"urea"),Species("H2PO4-",-1,"phosphate")],
 "potassium_chloride":[Species("K+",1,"potassium"),Species("Cl-",-1,"chloride")],
 "calcium_nitrate":[Species("Ca++",2,"calcium"),Species("NO3-",-1,"nitrate",2)],
 "calcium_chloride":[Species("Ca++",2,"calcium"),Species("Cl-",-1,"chloride",2)],
 "magnesium_sulfate":[Species("Mg++",2,"magnesium"),Species("SO4--",-2,"sulfate")],
 "magnesium_nitrate":[Species("Mg++",2,"magnesium"),Species("NO3-",-1,"nitrate",2)],
 "zinc_sulfate":[Species("Zn++",2,"zinc"),Species("SO4--",-2,"sulfate")],
 "ammonium_sulfite":[Species("NH4+",1,"ammonium",2),Species("SO3--",-2,"sulfite")],
 "tkp_00_33_66":[Species("K+",1,"potassium",3),Species("PO4---",-3,"phosphate")],
 "mkpi_00_58_38":[Species("K+",1,"potassium"),Species("H2PO3-",-1,"phosphite")],
 "potassium_hydroxide":[Species("K+",1,"potassium"),Species("OH-",-1,"hydroxide")],
 "sodium_benzoate":[Species("Na+",1,"sodium"),Species("benzoate",-1,"benzoate")],
 "boric_acid":[Species("H3BO3",0,"boric_acid")],
}

SOLUBILITY_PRODUCTS={
 ("Ca++","SO4--"):("CaSO4","low","Calcium sulfate precipitation is a compatibility risk."),
 ("Ca++","H2PO4-"):("calcium phosphate family","low","Calcium-phosphate precipitation is a compatibility risk."),
 ("Ca++","HPO4--"):("calcium phosphate family","low","Calcium-phosphate precipitation is a compatibility risk."),
 ("Mg++","HPO4--"):("magnesium phosphate family","medium","Magnesium-phosphate precipitation may occur depending on pH/concentration."),
 ("Ca++","CO3--"):("CaCO3","low","Calcium carbonate precipitation is a compatibility risk."),
}
KSP_RULES=[
 {"product":"CaSO4","ions":{"Ca++":1,"SO4--":1},"ksp":4.93e-5,"source":"25 C reference Ksp for CaSO4","product_mw":136.14,"equation":"Ca²⁺ + SO₄²⁻ ⇌ CaSO₄(s)",
  "kinetics":{"model":"gypsum_relative_growth_screen","supersaturation_order":2.0,
              "activation_energy_kj_mol":62.76,"reference_temperature_c":25.0,
              "source":"CaSO4·2H2O crystal-growth studies: second-order supersaturation dependence and 15.0±0.5 kcal/mol activation energy; relative screening only"}},
 {"product":"CaHPO4","ions":{"Ca++":1,"HPO4--":1},"ksp":7.0e-7,"source":"25 C reference Ksp for CaHPO4","product_mw":136.06,"equation":"Ca²⁺ + HPO₄²⁻ ⇌ CaHPO₄(s)",
  "kinetics":{"model":"generic_relative_precipitation_screen","supersaturation_order":1.0,
              "reference_temperature_c":25.0,
              "source":"No validated GHALI mineral-specific kinetic constants loaded; generic PHREEQC-style screening only"}},
]
def ions_for(material, mass_g):
    rows=SPECIES.get(material,[])
    return [{"formula":x.formula,"charge":x.charge,"family":x.family,
             "stoich":x.stoich,"source_mass_g":mass_g} for x in rows]

def compatibility(materials):
    ions=[]
    for name,mass in materials.items():
        ions.extend(ions_for(name,mass))
    risks=[]
    for i,a in enumerate(ions):
        for b in ions[i+1:]:
            hit=SOLUBILITY_PRODUCTS.get((a["formula"],b["formula"])) or SOLUBILITY_PRODUCTS.get((b["formula"],a["formula"]))
            if hit:
                risks.append({"ions":[a["formula"],b["formula"]],"product":hit[0],
                              "risk":hit[1],"message":hit[2]})
    return risks

def ionic_strength(ion_moles_per_l):
    rows=ion_moles_per_l.values() if isinstance(ion_moles_per_l,dict) else ion_moles_per_l
    return 0.5*sum(float(v["moles_per_l"])*(int(v["charge"])**2)
                   for v in rows if v.get("charge") is not None)

def davies_gamma(charge, ionic_strength, temperature_c=25.0):
    I=max(0.0,float(ionic_strength))
    z=abs(int(charge))
    if z==0 or I<=0: return 1.0
    # Davies is a 25 C aqueous screening model; temperature correction is
    # intentionally not invented because the required dielectric data are absent.
    if I>0.5: return None
    s=math.sqrt(I)
    log10_gamma=-0.509*(z*z)*(s/(1.0+s)-0.30*I)
    return 10**log10_gamma

def _ion_molarities(dissolved_g, material_data, solution_volume_l):
    out={}
    volume=max(float(solution_volume_l or 0),1e-9)
    for name,mass in dissolved_g.items():
        data=material_data.get(name,{})
        mw=data.get("mw")
        if not mw or mw<=0: continue
        formula_moles=float(mass)/float(mw)
        for sp in SPECIES.get(name,[]):
            mol_l=formula_moles*sp.stoich/volume
            row=out.setdefault(sp.formula,{"charge":sp.charge,"family":sp.family,"moles_per_l":0.0})
            row["moles_per_l"]+=mol_l
    return out
def ksp_screen(ions, gammas):
    out=[]
    for rule in KSP_RULES:
        if not all(name in ions for name in rule["ions"]):
            continue
        basis="activity" if all(gammas.get(name) is not None for name in rule["ions"]) else "concentration"
        q=1.0
        for name,power in rule["ions"].items():
            value=float(ions[name]["moles_per_l"])
            if basis=="activity":
                value*=float(gammas[name])
            q*=value**power
        ratio=q/rule["ksp"] if rule["ksp"] else float("inf")
        out.append({"product":rule["product"],"Q":q,"Ksp":rule["ksp"],"Q_over_Ksp":ratio,
                    "status":"PRECIPITATION_LIKELY" if ratio>1 else "BELOW_KSP",
                    "basis":basis,"source":rule["source"]})
    return out

def multicomponent_screen(experiment, dissolved_g, material_data, solution_volume_l):
    ions=_ion_molarities(dissolved_g,material_data,solution_volume_l)
    I=ionic_strength(ions)
    gammas={}
    for formula,row in ions.items():
        gammas[formula]=davies_gamma(row["charge"],I,float(experiment.get("temperature_c",25)))
    sources={}
    for material in dissolved_g:
        for sp in SPECIES.get(material,[]):
            sources.setdefault(sp.formula,[]).append(material)
    common=[]
    for ion,materials in sources.items():
        if len(materials)>1:
            common.append({"material":" + ".join(materials),"common_ions":[ion]})
    flags=[]
    if I>0.5:
        flags.append("Ionic strength exceeds 0.5 mol/L; Davies activity coefficients are disabled because this concentration is outside the reliable range of this screening model.")
    elif I>0.1:
        flags.append("Ionic strength is above 0.1 mol/L; activity-coefficient estimates are increasingly model-dependent.")
    if common:
        flags.append("Common-ion effects are present; pure-water solubility is not the mixed-solution equilibrium value and may be lower for sparingly soluble phases.")
    ksp=ksp_screen(ions,gammas)
    if any(x["status"]=="PRECIPITATION_LIKELY" for x in ksp):
        flags.append("At least one known Ksp reference is exceeded; precipitation is thermodynamically indicated by this screening pair.")
    return {"mode":"multicomponent activity/common-ion/Ksp screening","ionic_strength_mol_L":round(I,6),
            "solution_volume_l":round(solution_volume_l,6),"ions":ions,
            "activity_coefficients":gammas,"common_ion_materials":common,
            "known_ksp_screen":ksp,"quantitative_equilibrium_closed":False,"flags":flags,
            "basis":"Davies activity-coefficient screening at 25 C plus explicit common-ion detection. Full multicomponent equilibrium requires validated Ksp/interaction parameters and pH/speciation data."}

# Analytical totals used for pH/speciation. These are intentionally separate from
# the simple SPECIES map above: equilibrium speciation changes the ionic forms.
ANALYTICAL_COMPONENTS={
 "map":{"phosphate":1,"ammonium":1},
 "dap":{"phosphate":1,"ammonium":2},
 "mkp":{"phosphate":1,"potassium":1},
 "sop":{"sulfate":1,"potassium":2},
 "nop":{"nitrate":1,"potassium":1},
 "ammonium_nitrate":{"ammonium":1,"nitrate":1},
 "ammonium_sulfate":{"ammonium":2,"sulfate":1},
 "urea_phosphate":{"phosphate":1},
 "potassium_chloride":{"chloride":1,"potassium":1},
 "calcium_nitrate":{"calcium":1,"nitrate":2},
 "calcium_chloride":{"calcium":1,"chloride":2},
 "magnesium_sulfate":{"magnesium":1,"sulfate":1},
 "magnesium_nitrate":{"magnesium":1,"nitrate":2},
 "zinc_sulfate":{"zinc":1,"sulfate":1},
 "ammonium_sulfite":{"ammonium":2,"sulfite":1},
 "tkp_00_33_66":{"phosphate":1,"potassium":3},
 "mkpi_00_58_38":{"phosphite":1,"potassium":1},
 "potassium_hydroxide":{"strong_oh":1,"potassium":1},
 "sodium_benzoate":{"benzoate":1,"sodium":1},
 "boric_acid":{"borate_total":1},
}

# pKa values are 25 C reference values. Temperature correction is not invented;
# the result is therefore a screening speciation estimate outside 25 C.
PRACTICAL_PKA={
 "phosphate":(2.148,7.198,12.35),
 "ammonium":(9.25,),
 "sulfite":(1.8,7.2),
 "phosphite":(1.3,6.7),
 "borate":(9.24,),
 "benzoate":(4.20,),
}
STRONG_CHARGE={"potassium":1,"sodium":1,"calcium":2,"magnesium":2,"zinc":2,
               "nitrate":-1,"chloride":-1,"sulfate":-2}

def _totals_from_dissolved(dissolved_g, material_data, volume_l):
    totals={}
    for mid,mass in dissolved_g.items():
        mw=material_data.get(mid,{}).get("mw")
        if not mw or mw<=0: continue
        mol_l=float(mass)/float(mw)/max(volume_l,1e-12)
        for component,stoich in ANALYTICAL_COMPONENTS.get(mid,{}).items():
            totals[component]=totals.get(component,0.0)+mol_l*float(stoich)
    return totals

def _fraction_weak_acid(pH, pKas):
    h=10.0**(-pH)
    ks=[10.0**(-p) for p in pKas]
    if len(ks)==1:
        ka=ks[0]; return [h/(h+ka), ka/(h+ka)]
    if len(ks)==2:
        k1,k2=ks
        den=h*h+k1*h+k1*k2
        return [h*h/den,k1*h/den,k1*k2/den]
    k1,k2,k3=ks
    den=h**3+k1*h*h+k1*k2*h+k1*k2*k3
    return [h**3/den,k1*h*h/den,k1*k2*h/den,k1*k2*k3/den]

def _speciation_charge_balance(pH, totals, ionic_strength=0.0):
    h=10.0**(-pH)
    oh=10.0**(-(14.0-pH))
    charge= h-oh
    species={}
    # Strong ions.
    for comp,z in STRONG_CHARGE.items():
        c=totals.get(comp,0.0)
        charge += z*c
        species[comp]=c
    # Weak systems: charge is calculated from distribution at this pH.
    if totals.get("phosphate",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["phosphate"])
        vals=[totals["phosphate"]*x for x in f]
        species.update({"H3PO4":vals[0],"H2PO4-":vals[1],
                        "HPO4--":vals[2],"PO4---":vals[3]})
        charge += -vals[1]-2*vals[2]-3*vals[3]
    if totals.get("ammonium",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["ammonium"])
        nh4,nh3=totals["ammonium"]*f[0],totals["ammonium"]*f[1]
        species.update({"NH4+":nh4,"NH3":nh3})
        charge += nh4
    if totals.get("sulfite",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["sulfite"])
        vals=[totals["sulfite"]*x for x in f]
        species.update({"H2SO3":vals[0],"HSO3-":vals[1],"SO3--":vals[2]})
        charge += -vals[1]-2*vals[2]
    if totals.get("phosphite",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["phosphite"])
        vals=[totals["phosphite"]*x for x in f]
        species.update({"H3PO3":vals[0],"H2PO3-":vals[1],"HPO3--":vals[2]})
        charge += -vals[1]-2*vals[2]
    if totals.get("borate",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["borate"])
        hb3,bo3=totals["borate"]*f[0],totals["borate"]*f[1]
        species.update({"H3BO3":hb3,"B(OH)4-":bo3})
        charge += -bo3
    if totals.get("benzoate",0)>0:
        f=_fraction_weak_acid(pH,PRACTICAL_PKA["benzoate"])
        hb,benz=totals["benzoate"]*f[0],totals["benzoate"]*f[1]
        species.update({"benzoic_acid":hb,"benzoate-":benz})
        charge += -benz
    # Strong base is represented by its conjugate cation (for KOH this is K+);
    # the water OH- term above then closes the electroneutrality equation.
    # Do not add strong_oh as a second negative ion or KOH would cancel itself.
    return charge,species

def pH_speciation(dissolved_g, material_data, volume_l, temperature_c=25.0):
    totals=_totals_from_dissolved(dissolved_g,material_data,volume_l)
    if not totals:
        return {"status":"not_available","reason":"No dissolved analytical components available."}
    # Bracket the electroneutrality root over the aqueous pH range.
    grid=[2.0+i*0.05 for i in range(241)]
    vals=[_speciation_charge_balance(p,totals)[0] for p in grid]
    best=min(range(len(grid)),key=lambda i:abs(vals[i]))
    root=grid[best]
    for a,b,fa,fb in zip(grid[:-1],grid[1:],vals[:-1],vals[1:]):
        if fa==0 or fa*fb<0:
            lo,hi=a,b
            for _ in range(70):
                mid=(lo+hi)/2
                fm=_speciation_charge_balance(mid,totals)[0]
                if fa*fm<=0:
                    hi=mid;fb=fm
                else:
                    lo=mid;fa=fm
            root=(lo+hi)/2
            break
    residual,species=_speciation_charge_balance(root,totals)
    return {"status":"screening","pH":round(root,5),"charge_balance_residual_mol_L":residual,
            "analytical_totals_mol_L":totals,"species_mol_L":species,
            "basis":"Charge-balance speciation with 25 C reference pKa values; activity corrections are not folded into pKa here.",
            "temperature_c":temperature_c}

def _source_ion_inventory(dissolved_g, material_data, ion_name, volume_l):
    rows=[]
    for mid,mass in dissolved_g.items():
        mw=material_data.get(mid,{}).get("mw")
        if not mw: continue
        for sp in SPECIES.get(mid,[]):
            if sp.formula==ion_name:
                rows.append((mid,float(mass)/float(mw)*sp.stoich))
    return rows

def _ksp_ratio_from_moles(ion_moles, volume_l, rule, gammas=None):
    q=1.0
    for name,power in rule["ions"].items():
        c=max(0.0,ion_moles.get(name,0.0))/max(volume_l,1e-12)
        if gammas and gammas.get(name) is not None:
            c*=gammas[name]
        q*=c**power
    return q/max(rule["ksp"],1e-300)

def precipitation_equilibrium(dissolved_g, material_data, volume_l, temperature_c=25.0):
    current={k:max(0.0,float(v)) for k,v in dissolved_g.items()}
    events=[]
    # Iterate because removing one solid phase can change the driving force for another.
    for _ in range(12):
        ions=_ion_molarities(current,material_data,volume_l)
        I=ionic_strength(ions)
        gammas={n:davies_gamma(r["charge"],I,temperature_c) for n,r in ions.items()}
        changed=False
        for rule in KSP_RULES:
            if not all(n in ions for n in rule["ions"]): continue
            ratio=_ksp_ratio_from_moles(
                {n:ions[n]["moles_per_l"]*volume_l for n in ions},
                volume_l,rule,gammas if I<=0.5 else None)
            if ratio<=1.000001: continue
            product_moles=max(0.0,min(
                _source_ion_inventory(current,material_data,next(iter(rule["ions"])),volume_l)[0][1]
                if _source_ion_inventory(current,material_data,next(iter(rule["ions"])),volume_l) else 0.0,
                1e9))
            # Find the product amount that brings Q/Ksp to approximately one.
            lo,hi=0.0,product_moles
            for _b in range(70):
                x=(lo+hi)/2
                test={}
                for n in rule["ions"]:
                    total=sum(m for _,m in _source_ion_inventory(current,material_data,n,volume_l))
                    test[n]=max(0.0,total-x*rule["ions"][n])
                rtest=_ksp_ratio_from_moles(test,volume_l,rule,gammas if I<=0.5 else None)
                if rtest>1: lo=x
                else: hi=x
            precip=max(0.0,(lo+hi)/2)
            if precip<=1e-12: continue
            consumed={}
            for ion,stoich in rule["ions"].items():
                need=precip*stoich
                sources=_source_ion_inventory(current,material_data,ion,volume_l)
                total=sum(m for _,m in sources)
                if total<=0: continue
                for mid,available in sources:
                    consumed[mid]=consumed.get(mid,0.0)+need*(available/total)*material_data[mid]["mw"]
            for mid,mass in consumed.items():
                current[mid]=max(0.0,current[mid]-mass)
            events.append({"product":rule["product"],"precipitated_mol":precip,
                           "precipitated_mass_g":precip*float(rule.get("product_mw",0.0)),
                           "Q_over_Ksp_before":ratio,"basis":"activity" if I<=0.5 else "concentration",
                           "equation":rule.get("equation"),"ksp":rule.get("ksp"),"source":rule.get("source")})
            changed=True
        if not changed: break
    return {"dissolved_g":current,"events":events,
            "model":"iterative Ksp precipitation screen with mass-balance removal"}


def _kinetic_model_parameters(product, temperature_c, rpm):
    """Return a relative, source-scoped precipitation kinetic multiplier.

    The multiplier is dimensionless and anchored to the existing engineering
    t95 screen at 25 C and 300 rpm. It is not an absolute mineral rate constant.
    """
    rule=next((r for r in KSP_RULES if r.get("product")==product), {})
    kin=rule.get("kinetics") or {}
    order=float(kin.get("supersaturation_order",1.0))
    tref=float(kin.get("reference_temperature_c",25.0))
    ea_kj=kin.get("activation_energy_kj_mol")
    temp_factor=1.0
    if ea_kj is not None:
        R=8.314462618e-3  # kJ mol^-1 K^-1
        tk=max(1.0,float(temperature_c)+273.15)
        tr=max(1.0,tref+273.15)
        temp_factor=math.exp(-(float(ea_kj)/R)*(1.0/tk-1.0/tr))
        temp_factor=max(0.05,min(30.0,temp_factor))
    rpm_factor=1.0 if rpm<=0 else max(0.35,min(3.0,(float(rpm)/300.0)**0.5))
    return {
        "model":kin.get("model","generic_relative_precipitation_screen"),
        "supersaturation_order":order,
        "activation_energy_kj_mol":ea_kj,
        "temperature_factor":temp_factor,
        "rpm_factor":rpm_factor,
        "source":kin.get("source"),
    }


def precipitation_kinetic_timeline(kinetic_snapshots, material_data, solution_volume_l,
                                   temperature_c=25.0, rpm=300.0):
    """Apply a time-resolved precipitation overlay to kinetic dissolution snapshots.

    This is an engineering screening layer, not a validated crystal-growth model.
    It detects the first sampled crossing of Q/Ksp > 1, estimates the crossing time
    between snapshots, then relaxes toward the Ksp-limited state instead of removing
    the full equilibrium amount instantaneously. The overlay keeps a cumulative
    precipitation ledger and writes the adjusted dissolved state back to snapshots.

    The rate is intentionally expressed as a tunable screening parameter. Literature
    shows that induction and growth depend strongly on supersaturation, temperature,
    surfaces/seeding, vessel material, additives, and mixing; therefore no universal
    precipitation rate constant is invented here.
    """
    snapshots = {
        float(t): {str(mid): dict(state) for mid, state in (rows or {}).items()}
        for t, rows in (kinetic_snapshots or {}).items()
    }
    times = sorted(
        t for t, rows in snapshots.items()
        if any(
            isinstance(s, dict)
            and (
                s.get("kinetic_dissolved_g") is not None
                or s.get("event_equilibrium_target_g") is not None
            )
            for s in rows.values()
        )
    )
    if not times:
        return {"snapshots": snapshots, "events": [], "cumulative_precipitated_g": {},
                "final_dissolved_g": {}, "model": "no kinetic snapshots available"}

    cumulative_removed = {}
    previous_ratios = {}
    previous_time = None
    events = []

    # A deliberately conservative generic screening t95. It is NOT a material
    # property. Stirring modifies the mixing/mass-transfer environment only.
    rpm_factor = 1.0 if rpm <= 0 else max(0.35, min(3.0, (float(rpm) / 300.0) ** 0.5))
    screening_t95_s = 300.0 / rpm_factor
    k95 = math.log(20.0) / max(screening_t95_s, 1e-9)

    for t in times:
        rows = snapshots[t]
        baseline = {}
        for mid, state in rows.items():
            if not isinstance(state, dict):
                continue
            if state.get("kinetic_dissolved_g") is not None:
                baseline[mid] = max(0.0, float(state.get("kinetic_dissolved_g", 0.0)))
            elif state.get("event_equilibrium_target_g") is not None:
                # A newly added solid has zero dissolved mass at the instant it
                # enters the vessel unless a measured kinetic snapshot says otherwise.
                baseline[mid] = 0.0
        current = {
            mid: max(0.0, mass - cumulative_removed.get(mid, 0.0))
            for mid, mass in baseline.items()
        }

        ions = _ion_molarities(current, material_data, solution_volume_l)
        I = ionic_strength(ions)
        gammas = {n: davies_gamma(r["charge"], I, temperature_c) for n, r in ions.items()}
        screens = ksp_screen(ions, gammas)
        dt = max(0.0, 0.0 if previous_time is None else t - previous_time)

        for screen in screens:
            product = str(screen["product"])
            ratio = float(screen.get("Q_over_Ksp", 0.0))
            prior = previous_ratios.get(product)
            crossing_time = None
            if ratio > 1.0:
                if prior is not None and prior <= 1.0 and dt > 0:
                    # Linear interpolation is only an estimate of the first
                    # crossing between two sampled states.
                    frac = (1.0 - prior) / max(ratio - prior, 1e-12)
                    frac = max(0.0, min(1.0, frac))
                    crossing_time = previous_time + frac * dt
                elif prior is None:
                    crossing_time = t
                else:
                    crossing_time = previous_time

                equilibrium = precipitation_equilibrium(
                    current, material_data, solution_volume_l, temperature_c
                )
                target = equilibrium.get("dissolved_g", current)
                potential_removed = {
                    mid: max(0.0, float(current.get(mid, 0.0)) -
                            float(target.get(mid, current.get(mid, 0.0))))
                    for mid in current
                }
                potential_removed = {mid: val for mid, val in potential_removed.items()
                                     if val > 1e-12}

                if potential_removed:
                    effective_dt=max(0.0,t-float(crossing_time or t))
                    kinetic_params=_kinetic_model_parameters(product,temperature_c,rpm)
                    ss_order=float(kinetic_params.get("supersaturation_order") or 1.0)
                    # The mineral-specific exponent changes the relative rate only;
                    # the absolute rate remains anchored to the engineering t95 screen.
                    rate_multiplier=max(0.0,min(25.0,(max(ratio,1.0)**ss_order-1.0)))
                    rate_multiplier*=float(kinetic_params.get("temperature_factor") or 1.0)
                    rate_multiplier*=float(kinetic_params.get("rpm_factor") or 1.0)
                    fraction=1.0-math.exp(-k95*max(0.05,rate_multiplier)*effective_dt)
                    fraction=max(0.0,min(1.0,fraction))
                    before_current=dict(current)
                    for mid, possible in potential_removed.items():
                        removed=min(possible, possible*fraction)
                        current[mid]=max(0.0,current[mid]-removed)
                        cumulative_removed[mid]=cumulative_removed.get(mid,0.0)+removed

                    eq_event=next(
                        (x for x in equilibrium.get("events", [])
                         if str(x.get("product"))==product), {}
                    )
                    removed_product_mass = float(eq_event.get("precipitated_mass_g") or 0.0) * fraction
                    actual_ions = _ion_molarities(current, material_data, solution_volume_l)
                    actual_I = ionic_strength(actual_ions)
                    actual_gammas = {
                        n: davies_gamma(r["charge"], actual_I, temperature_c)
                        for n, r in actual_ions.items()
                    }
                    after_ratio = next(
                        (float(x.get("Q_over_Ksp", 0.0))
                         for x in ksp_screen(actual_ions, actual_gammas)
                         if str(x.get("product")) == product),
                        None
                    )
                    events.append({
                        "time_s": float(t),
                        "estimated_crossing_time_s": round(float(crossing_time), 6)
                            if crossing_time is not None else None,
                        "event": "precipitation_kinetic",
                        "material": product,
                        "mass_g": round(removed_product_mass, 9),
                        "precipitated_mass_g": round(removed_product_mass, 9),
                        "precipitated_mol": (
                            removed_product_mass / float(eq_event.get("precipitated_mass_g") or 1.0)
                            * float(eq_event.get("precipitated_mol") or 0.0)
                            if eq_event.get("precipitated_mass_g") else None
                        ),
                        "Q_over_Ksp_before": round(ratio, 9),
                        "Q_over_Ksp_after": round(after_ratio, 9) if after_ratio is not None else None,
                        "ksp": screen.get("Ksp"),
                        "basis": screen.get("basis"),
                        "equation": KSP_RULES[[r["product"] for r in KSP_RULES].index(product)].get("equation")
                            if product in [r["product"] for r in KSP_RULES] else None,
                        "source": screen.get("source"),
                        "kinetic_fraction": round(fraction, 9),
                        "screening_t95_s": round(screening_t95_s, 6),
                        "kinetic_model": kinetic_params.get("model"),
                        "supersaturation_order": round(ss_order, 6),
                        "temperature_factor": round(float(kinetic_params.get("temperature_factor") or 1.0), 6),
                        "rpm_factor": round(float(kinetic_params.get("rpm_factor") or 1.0), 6),
                        "activation_energy_kj_mol": kinetic_params.get("activation_energy_kj_mol"),
                        "kinetic_model_source": kinetic_params.get("source"),
                        "model_scope": "mineral-specific relative screening; absolute rate not experimentally calibrated",
                    })

        # Persist the adjusted event-time aqueous state and the precipitation ledger.
        for mid, state in rows.items():
            if not isinstance(state, dict):
                continue
            if mid in current:
                base = float(state.get("kinetic_dissolved_g", 0.0))
                adjusted = float(current[mid])
                state["pre_precipitation_kinetic_dissolved_g"] = round(base, 6)
                state["kinetic_dissolved_g"] = round(adjusted, 6)
                state["kinetic_undissolved_g"] = round(
                    max(0.0, float(state.get("charged_g", 0.0)) - adjusted), 6
                )
                state["precipitated_from_material_g"] = round(
                    max(0.0, base - adjusted), 6
                )
        if events:
            rows["__precipitation_ledger__"] = {
                "events_at_time": [dict(e) for e in events if float(e["time_s"]) == float(t)],
                "cumulative_precipitated_material_g": {
                    k: round(v, 9) for k, v in cumulative_removed.items()
                },
            }

        # Recompute the ratio from the adjusted state for the next crossing test.
        adjusted_ions = _ion_molarities(current, material_data, solution_volume_l)
        adjusted_I = ionic_strength(adjusted_ions)
        adjusted_gammas = {
            n: davies_gamma(r["charge"], adjusted_I, temperature_c)
            for n, r in adjusted_ions.items()
        }
        for s in ksp_screen(adjusted_ions, adjusted_gammas):
            previous_ratios[str(s["product"])] = float(s.get("Q_over_Ksp", 0.0))
        previous_time = t

    final_dissolved = {}
    if times:
        last = snapshots[times[-1]]
        final_dissolved = {
            mid: float(state.get("kinetic_dissolved_g", 0.0))
            for mid, state in last.items()
            if isinstance(state, dict) and state.get("kinetic_dissolved_g") is not None
        }
    return {
        "snapshots": snapshots,
        "events": events,
        "cumulative_precipitated_g": {k: round(v, 9) for k, v in cumulative_removed.items()},
        "final_dissolved_g": final_dissolved,
        "model": "time-resolved Q/Ksp crossing + kinetic relaxation to Ksp-limited state",
        "screening_parameters": {
            "screening_t95_s": round(screening_t95_s, 6),
            "rpm_factor": round(rpm_factor, 6),
            "basis": "supersaturation-dependent engineering screening; not a validated mineral-specific rate law",
        },
    }


def analyze(experiment, dissolved_g, material_data=None, solution_volume_l=None,
           apply_precipitation=True):
    material_data=material_data or {}
    volume=max(float(solution_volume_l or experiment.get("working_volume_l",1)),1e-9)
    temp=float(experiment.get("temperature_c",25))
    risks=compatibility(dissolved_g)
    ph=pH_speciation(dissolved_g,material_data,volume,temp)
    multi=multicomponent_screen(experiment,dissolved_g,material_data,volume)

    # Re-run the known Ksp screen using pH-resolved HPO4 when available.
    if ph.get("status")=="screening":
        ions=dict(multi.get("ions",{}))
        sp=ph.get("species_mol_L",{})
        for formula in ("H3PO4","H2PO4-","HPO4--","PO4---","NH4+","NH3",
                        "HSO3-","SO3--","H3BO3","B(OH)4-","benzoate-"):
            if formula in sp:
                charge={"H3PO4":0,"H2PO4-":-1,"HPO4--":-2,"PO4---":-3,
                        "NH4+":1,"NH3":0,"HSO3-":-1,"SO3--":-2,
                        "H3BO3":0,"B(OH)4-":-1,"benzoate-":-1}[formula]
                ions[formula]={"charge":charge,"family":"speciated","moles_per_l":sp[formula]}
        I=ionic_strength(ions)
        gammas={n:davies_gamma(row["charge"],I,temp) for n,row in ions.items()}
        ksp=ksp_screen(ions,gammas)
        multi["pH_resolved_ksp_screen"]=ksp
        multi["ionic_strength_mol_L"]=round(I,6)
        multi["activity_coefficients"]=gammas
        multi["ions"]=ions

    precip=precipitation_equilibrium(dissolved_g,material_data,volume,temp)
    precipitated=precip.get("events",[])
    if precipitated and apply_precipitation:
        risks=compatibility(precip["dissolved_g"])
        multi=multicomponent_screen(experiment,precip["dissolved_g"],material_data,volume)
        messages=["Ksp precipitation was applied with mass-balance removal to the dissolved phase."]
    elif precipitated:
        messages=["Ksp precipitation is thermodynamically indicated, but the time-resolved kinetic state was preserved; the equilibrium result is reported separately."]
    else:
        messages=[]
    messages += [x["message"] for x in risks]+multi["flags"]
    if ph.get("status")=="screening":
        if abs(float(ph.get("charge_balance_residual_mol_L",0)))>1e-5:
            messages.append("pH charge-balance residual is above the screening tolerance; composition/speciation data are incomplete.")
    return {"compatibility_risks":risks,
            "precipitation_screen":(
                "PRECIPITATION_APPLIED" if precipitated and apply_precipitation
                else "KINETIC_STATE_SUPERSATURATED" if precipitated
                else ("RISK_DETECTED" if risks else "NO_RULE_TRIGGERED")
            ),
            "multicomponent":multi,
            "ph_estimate":ph,
            "ionic_strength":{"value_mol_L":multi["ionic_strength_mol_L"],"status":"screening"},
            "actual_dissolved_g":{k:float(v) for k,v in dissolved_g.items()},
            "equilibrium_dissolved_g":{k:float(v) for k,v in precip.get("dissolved_g",dissolved_g).items()},
            "precipitation_equilibrium":precip,
            "warnings":messages,
            "note":"Chemistry layer now performs analytical mass-balance speciation, low-ionic-strength activity screening, common-ion detection and iterative Ksp precipitation with material mass removal. Davies is not used as a high-ionic-strength model; concentrated fertilizer solutions require validated SIT/Pitzer/product interaction data."}

__all__=["analyze","compatibility","ions_for","ionic_strength","davies_gamma","multicomponent_screen","precipitation_equilibrium","precipitation_kinetic_timeline"]
