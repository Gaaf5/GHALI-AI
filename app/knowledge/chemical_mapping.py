"""GHALI chemical identity -> elemental/species mapping.

Product materials are kept separate from pure-compound thermodynamic data.
A mapping is solver-ready only when formula/MW/hydrate identity are explicit.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Component:
    species: str
    charge: int
    stoich: float
    elements: dict[str, float]

@dataclass(frozen=True)
class MaterialMapping:
    material_id: str
    formula: str
    mw: float | None
    phase: str
    components: tuple[Component, ...]
    source_id: str
    confidence: str
    notes: str = ""

MAP = MaterialMapping("map", "NH4H2PO4", 115.03, "solid", (
    Component("NH4+", 1, 1, {"N":1,"H":4}),
    Component("H2PO4-", -1, 1, {"H":2,"P":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH")
DAP = MaterialMapping("dap", "(NH4)2HPO4", 132.06, "solid", (
    Component("NH4+", 1, 2, {"N":2,"H":8}),
    Component("HPO4--", -2, 1, {"H":1,"P":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH")
MKP = MaterialMapping("mkp", "KH2PO4", 136.09, "solid", (
    Component("K+", 1, 1, {"K":1}), Component("H2PO4-", -1, 1, {"H":2,"P":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH")
SOP = MaterialMapping("sop", "K2SO4", 174.26, "solid", (
    Component("K+", 1, 2, {"K":1}), Component("SO4--", -2, 1, {"S":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH")
NOP = MaterialMapping("nop", "KNO3", 101.10, "solid", (
    Component("K+", 1, 1, {"K":1}), Component("NO3-", -1, 1, {"N":1,"O":3}),
), "MANUFACTURER_TDS", "HIGH")
AMMONIUM_SULFATE = MaterialMapping("ammonium_sulfate", "(NH4)2SO4", 132.14, "solid", (
    Component("NH4+", 1, 2, {"N":1,"H":4}), Component("SO4--", -2, 1, {"S":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH")
KCL = MaterialMapping("potassium_chloride", "KCl", 74.55, "solid", (
    Component("K+", 1, 1, {"K":1}), Component("Cl-", -1, 1, {"Cl":1}),
), "MANUFACTURER_TDS", "HIGH")
CALCIUM_NITRATE = MaterialMapping("calcium_nitrate", "Ca(NO3)2", 236.15, "solid", (
    Component("Ca++", 2, 1, {"Ca":1}), Component("NO3-", -1, 2, {"N":1,"O":3}),
), "MANUFACTURER_TDS", "HIGH", "tetrahydrate product identity; MW is the hydrate MW.")
MAGNESIUM_SULFATE = MaterialMapping("magnesium_sulfate", "MgSO4·7H2O", 246.47, "solid", (
    Component("Mg++", 2, 1, {"Mg":1}), Component("SO4--", -2, 1, {"S":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH", "heptahydrate product identity; water of crystallization retained in MW.")
ZINC_SULFATE = MaterialMapping("zinc_sulfate", "ZnSO4·7H2O", 287.54, "solid", (
    Component("Zn++", 2, 1, {"Zn":1}), Component("SO4--", -2, 1, {"S":1,"O":4}),
), "MANUFACTURER_TDS", "HIGH", "heptahydrate product identity; water of crystallization retained in MW.")
MAPPINGS = {x.material_id:x for x in (
    MAP,DAP,MKP,SOP,NOP,AMMONIUM_SULFATE,KCL,CALCIUM_NITRATE,
    MAGNESIUM_SULFATE,ZINC_SULFATE,
)}

def get_mapping(material_id: str) -> dict[str, Any] | None:
    row=MAPPINGS.get(str(material_id).strip().lower())
    return asdict(row) if row else None

def element_totals(material_id: str, mass_g: float) -> dict[str, float]:
    row=MAPPINGS.get(str(material_id).strip().lower())
    if not row or not row.mw: return {}
    formula_moles=float(mass_g)/row.mw
    out: dict[str,float] = {}
    for comp in row.components:
        for element,n in comp.elements.items():
            out[element]=out.get(element,0.0)+formula_moles*n*comp.stoich
    return out

def mapped_materials() -> list[dict[str,Any]]:
    return [asdict(x) for x in MAPPINGS.values()]

__all__=["get_mapping","element_totals","mapped_materials","MAPPINGS"]
