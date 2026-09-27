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

def analyze(experiment, dissolved_g, material_data=None, solution_volume_l=None):
    material_data=material_data or {}
    risks=compatibility(dissolved_g)
    multi=multicomponent_screen(experiment,dissolved_g,material_data,solution_volume_l or experiment.get("working_volume_l",1))
    messages=[x["message"] for x in risks]+multi["flags"]
    return {"compatibility_risks":risks,
            "precipitation_screen":"RISK_DETECTED" if risks else "NO_RULE_TRIGGERED",
            "multicomponent":multi,
            "ph_estimate":{"status":"not_modeled","reason":"Reliable pH requires acid/base speciation, concentration, temperature and product-specific composition data; a fixed pH range is not reported."},
            "ionic_strength":{"value_mol_L":multi["ionic_strength_mol_L"],"status":"screening"},
            "warnings":messages,
            "note":"Mixed-solution equilibrium is screened with ionic strength, activity coefficients and common-ion detection. Absence of a rule trigger is not proof of compatibility."}

__all__=["analyze","compatibility","ions_for","ionic_strength","davies_gamma","multicomponent_screen"]
