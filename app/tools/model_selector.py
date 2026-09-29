from __future__ import annotations
from typing import Any

def select_activity_model(ionic_strength_m: float | None, phreeqc_available: bool) -> dict[str,Any]:
    """Select a defensible activity model without pretending the fallback is equivalent."""
    I=0.0 if ionic_strength_m is None else max(0.0,float(ionic_strength_m))
    if phreeqc_available:
        if I >= 0.5: model="Pitzer"; reason="high ionic strength / concentrated electrolyte"
        elif I >= 0.1: model="SIT"; reason="moderate ionic strength; explicit interaction terms preferred"
        else: model="PHREEQC ion-association"; reason="dilute aqueous solution"
        return {"engine":"PHREEQC","activity_model":model,"ionic_strength_m":I,"reason":reason,"confidence":"model-selected"}
    return {"engine":"screening_shared_solution","activity_model":"engineering shared-solution approximation",
            "ionic_strength_m":I,"reason":"PHREEQC runtime unavailable; no thermodynamic result is fabricated","confidence":"screening"}

def water_analysis_to_molal(analysis: dict[str,float], water_kg: float=1.0) -> dict[str,float]:
    """Convert common water-analysis mg/L values to mol/kgw (approximately at dilute density)."""
    mw={"Ca":40.078,"Mg":24.305,"Na":22.990,"K":39.0983,"NH4":18.039,"Cl":35.45,"SO4":96.06,
        "HCO3":61.016,"CO3":60.008,"NO3":62.0049,"F":18.998,"PO4":94.971,"SiO2":60.0843,
        "Fe":55.845,"Zn":65.38,"B":10.81}
    out={}
    for key,value in (analysis or {}).items():
        if key not in mw: continue
        out[key]=max(0.0,float(value))/1000.0/mw[key]/max(float(water_kg),1e-12)
    return out
