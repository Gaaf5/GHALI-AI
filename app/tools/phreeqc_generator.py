"""Generate conservative PHREEQC input from GHALI material additions.

Only elemental totals with explicit material mappings are emitted. Commercial
products without a defensible molecular identity are rejected rather than
invented. The generated model is an aqueous speciation/batch-equilibrium
starting point, not a claim that PHREEQC knows the commercial product phase.
"""
from __future__ import annotations
from typing import Any
from app.knowledge.chemical_mapping import MAPPINGS, element_totals

def _fmt(x: float) -> str:
    return f"{float(x):.12g}"

def build_element_totals(additions: list[dict[str,Any]], water_kg: float = 1.0) -> dict[str,float]:
    totals={}
    for row in additions:
        mid=str(row.get("material","")).strip().lower()
        mass=float(row.get("mass_g",0.0))
        if mass<=0 or mid=="water": continue
        if mid not in MAPPINGS:
            continue
        for el,mol in element_totals(mid,mass).items():
            totals[el]=totals.get(el,0.0)+mol/max(water_kg,1e-12)
    return totals

def build_input(additions: list[dict[str,Any]], water_kg: float, temperature_c: float = 25.0,
                database: str = "phreeqc.dat", pH: float = 7.0, force_balance: str = "charge") -> dict[str,Any]:
    unsupported=sorted({str(x.get("material","")).strip().lower() for x in additions
                       if str(x.get("material","")).strip().lower() not in MAPPINGS and
                       str(x.get("material","")).strip().lower() != "water"})
    if unsupported:
        raise ValueError("No solver-safe chemical identity mapping for: " + ", ".join(unsupported))
    totals=build_element_totals(additions,water_kg)
    lines=[
        "TITLE GHALI-AI aqueous screening / elemental-total model",
        "SOLUTION 1",
        f"    temp {_fmt(temperature_c)}",
        f"    pH {_fmt(pH)} {force_balance}",
        "    units mol/kgw",
        "    water 1",
    ]
    # PHREEQC accepts element totals such as N, P, K, S, Ca, Mg, Zn, Cl.
    for el in ("N","P","K","S","Ca","Mg","Zn","Cl","Na","B"):
        if el in totals and totals[el]>0: lines.append(f"    {el} {_fmt(totals[el])}")
    lines += [
        "SELECTED_OUTPUT 1",
        "    -file ghali_selected.tsv",
        "    -reset false",
        "    -pH true",
        "    -ionic_strength true",
        "    -water true",
        "    -totals N P K S Ca Mg Zn Cl Na B",
        "    -activities H+ OH- NH4+ K+ Ca++ Mg++ SO4-- NO3- H2PO4- HPO4--",
        "    -saturation_indices gypsum anhydrite calcite",
        "END",
    ]
    return {"input":"\n".join(lines)+"\n","element_totals_mol_per_kgw":totals,
            "database":database,"unsupported":unsupported,
            "model":"element-total aqueous solution; commercial product phases are not assumed"}

def build_batch_input(additions: list[dict[str,Any]], water_kg: float, temperature_c: float = 25.0,
                      pH: float = 7.0) -> dict[str,Any]:
    return build_input(additions,water_kg,temperature_c,pH=pH)
