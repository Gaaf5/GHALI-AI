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
 {"product":"CaSO4","ions":{"Ca++":1,"SO4--":1},"ksp":4.93e-5,"source":"25 C reference Ksp for CaSO4"},
 {"product":"CaHPO4","ions":{"Ca++":1,"HPO4--":1},"ksp":7.0e-7,"source":"25 C reference Ksp for CaHPO4"},
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
                           "Q_over_Ksp_before":ratio,"basis":"activity" if I<=0.5 else "concentration"})
            changed=True
        if not changed: break
    return {"dissolved_g":current,"events":events,
            "model":"iterative Ksp precipitation screen with mass-balance removal"}

def analyze(experiment, dissolved_g, material_data=None, solution_volume_l=None):
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
    if precipitated:
        risks=compatibility(precip["dissolved_g"])
        multi=multicomponent_screen(experiment,precip["dissolved_g"],material_data,volume)
        messages=["Ksp precipitation was applied with mass-balance removal to the dissolved phase."]
    else:
        messages=[]
    messages += [x["message"] for x in risks]+multi["flags"]
    if ph.get("status")=="screening":
        if abs(float(ph.get("charge_balance_residual_mol_L",0)))>1e-5:
            messages.append("pH charge-balance residual is above the screening tolerance; composition/speciation data are incomplete.")
    return {"compatibility_risks":risks,
            "precipitation_screen":"PRECIPITATION_APPLIED" if precipitated else ("RISK_DETECTED" if risks else "NO_RULE_TRIGGERED"),
            "multicomponent":multi,
            "ph_estimate":ph,
            "ionic_strength":{"value_mol_L":multi["ionic_strength_mol_L"],"status":"screening"},
            "precipitation_equilibrium":precip,
            "warnings":messages,
            "note":"Chemistry layer now performs analytical mass-balance speciation, low-ionic-strength activity screening, common-ion detection and iterative Ksp precipitation with material mass removal. Davies is not used as a high-ionic-strength model; concentrated fertilizer solutions require validated SIT/Pitzer/product interaction data."}

__all__=["analyze","compatibility","ions_for","ionic_strength","davies_gamma","multicomponent_screen"]
