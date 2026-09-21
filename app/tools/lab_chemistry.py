from __future__ import annotations
from dataclasses import dataclass
import math

# Rule-based chemistry layer. It intentionally reports "screening" unless
# parameters are backed by validated experimental data.
@dataclass(frozen=True)
class Species:
    formula: str
    charge: int
    family: str

SPECIES={
 "urea":[Species("CO(NH2)2",0,"urea")],
 "map":[Species("NH4+",1,"ammonium"),Species("H2PO4-",-1,"phosphate")],
 "dap":[Species("NH4+",1,"ammonium"),Species("HPO4--",-2,"phosphate")],
 "mkp":[Species("K+",1,"potassium"),Species("H2PO4-",-1,"phosphate")],
 "sop":[Species("K+",1,"potassium"),Species("SO4--",-2,"sulfate")],
 "nop":[Species("K+",1,"potassium"),Species("NO3-",-1,"nitrate")],
 "ammonium_nitrate":[Species("NH4+",1,"ammonium"),Species("NO3-",-1,"nitrate")],
 "ammonium_sulfate":[Species("NH4+",1,"ammonium"),Species("SO4--",-2,"sulfate")],
 "urea_phosphate":[Species("urea",0,"urea"),Species("H2PO4-",-1,"phosphate")],
 "potassium_chloride":[Species("K+",1,"potassium"),Species("Cl-",-1,"chloride")],
 "calcium_nitrate":[Species("Ca++",2,"calcium"),Species("NO3-",-1,"nitrate")],
 "calcium_chloride":[Species("Ca++",2,"calcium"),Species("Cl-",-1,"chloride")],
 "magnesium_sulfate":[Species("Mg++",2,"magnesium"),Species("SO4--",-2,"sulfate")],
 "magnesium_nitrate":[Species("Mg++",2,"magnesium"),Species("NO3-",-1,"nitrate")],
}
SOLUBILITY_PRODUCTS={
 ("Ca++","SO4--"):("CaSO4","low", "Calcium sulfate precipitation is a compatibility risk."),
 ("Ca++","H2PO4-"):("calcium phosphate family","low", "Calcium-phosphate precipitation is a compatibility risk."),
 ("Ca++","HPO4--"):("calcium phosphate family","low", "Calcium-phosphate precipitation is a compatibility risk."),
 ("Mg++","HPO4--"):("magnesium phosphate family","medium", "Magnesium-phosphate precipitation may occur depending on pH/concentration."),
 ("Ca++","CO3--"):("CaCO3","low", "Calcium carbonate precipitation is a compatibility risk."),
}
def ions_for(material, mass_g):
    rows=SPECIES.get(material,[])
    return [{"formula":x.formula,"charge":x.charge,"family":x.family,"source_mass_g":mass_g} for x in rows]

def compatibility(materials):
    ions=[]
    for name,mass in materials.items():
        ions.extend(ions_for(name,mass))
    risks=[]
    for i,a in enumerate(ions):
        for b in ions[i+1:]:
            pair=(a["formula"],b["formula"])
            rev=(b["formula"],a["formula"])
            hit=SOLUBILITY_PRODUCTS.get(pair) or SOLUBILITY_PRODUCTS.get(rev)
            if hit:
                risks.append({"ions":[a["formula"],b["formula"]],"product":hit[0],
                              "risk":hit[1],"message":hit[2]})
    return risks

def ionic_strength(ion_moles_per_l):
    return 0.5*sum(float(v["moles_per_l"])*(int(v["charge"])**2)
                   for v in ion_moles_per_l if v.get("charge") is not None)

def estimate_pH(ions):
    # Only broad family screening; not a thermodynamic pH solver.
    acid=sum(v.get("moles_per_l",0) for v in ions if v.get("family")=="phosphate")
    base=sum(v.get("moles_per_l",0) for v in ions if v.get("family")=="ammonium")
    if acid and base: return {"range":[4.0,8.0],"confidence":"screening"}
    return {"range":[5.0,9.0],"confidence":"screening"}

def analyze(experiment, dissolved_g):
    risks=compatibility(dissolved_g)
    return {"compatibility_risks":risks,
            "precipitation_screen":"RISK_DETECTED" if risks else "NO_RULE_TRIGGERED",
            "ph_estimate":{"range":[4.0,9.0],"confidence":"screening"},
            "ionic_strength":{"status":"requires_molar_concentrations"},
            "note":"Absence of a rule trigger is not proof of compatibility. Thermodynamic equilibrium, activity coefficients, pH, temperature and kinetics require validated property data."}
__all__=["analyze","compatibility","ions_for","ionic_strength"]