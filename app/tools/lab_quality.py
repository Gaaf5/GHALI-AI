from __future__ import annotations
from typing import Any
import math
from app.tools.model_selector import select_activity_model
def assess_simulation(result: dict[str, Any], phreeqc_available: bool = False) -> dict[str, Any]:
    mb = result.get("mass_balance", {})
    inp = float(mb.get("input_g", 0.0))
    dissolved = float(mb.get("dissolved_solids_g", 0.0))
    undissolved = float(mb.get("undissolved_solids_g", 0.0))
    closure = dissolved + undissolved
    rel_error = abs(closure - inp) / max(inp, 1e-9)
    chemistry = result.get("chemistry") or {}
    ionic_raw = chemistry.get("ionic_strength", chemistry.get("ionic_strength_mol_L", 0.0))
    if isinstance(ionic_raw, dict):
        ionic = float(ionic_raw.get("mol_L", ionic_raw.get("M", ionic_raw.get("value_mol_L", ionic_raw.get("value", ionic_raw.get("ionic_strength_mol_L", 0.0))))) or 0.0)
    else:
        ionic = float(ionic_raw or 0.0)
    model = select_activity_model(ionic, phreeqc_available)
    warnings = list(result.get("warnings") or [])
    evidence = []
    for info in (result.get("dissolution") or {}).values():
        q = str(info.get("solubility_quality", "unavailable"))
        if q in {"unavailable", "unknown"}:
            evidence.append("missing")
        elif "qualitative" in q or "product" in q:
            evidence.append("qualitative")
        else:
            evidence.append("numeric")
    score = 100.0
    if rel_error > 1e-5: score -= 25.0
    if any(x == "missing" for x in evidence): score -= 25.0
    if any(x == "qualitative" for x in evidence): score -= 10.0
    if ionic >= 0.5 and not phreeqc_available: score -= 20.0
    if not chemistry.get("precipitation_equilibrium"): score -= 5.0
    confidence = "HIGH" if score >= 85 else "MEDIUM" if score >= 65 else "LOW"
    return {
        "confidence": confidence,
        "score": round(max(0.0, min(100.0, score)), 1),
        "mass_closure_g": round(closure, 8),
        "mass_closure_relative_error": round(rel_error, 8),
        "ionic_strength_m": round(ionic, 6),
        "activity_model": model,
        "evidence_summary": {
            "numeric": evidence.count("numeric"),
            "qualitative": evidence.count("qualitative"),
            "missing": evidence.count("missing"),
        },
        "limitations": warnings[-8:],
    }
def next_experiments(result: dict[str, Any]) -> list[dict[str, Any]]:
    cond = result.get("conditions") or {}
    base_temp = float(cond.get("temperature_c", 20.0))
    base_rpm = float(cond.get("rpm", 300.0))
    base_duration = float(cond.get("duration_s", 120.0))
    additions = result.get("input_additions") or []
    plans = []
    plans.append({
        "id": "temperature_sensitivity",
        "purpose": "Measure the temperature response of the mixed solution rather than assuming pure-water behavior.",
        "changes": {"temperature_c": round(base_temp + 10.0, 1)},
        "keep_constant": ["water charge", "addition order", "mass of every material", "RPM", "duration"],
    })
    plans.append({
        "id": "mixing_kinetics",
        "purpose": "Separate equilibrium limitation from mass-transfer limitation.",
        "changes": {"rpm": round(base_rpm * 1.5, 1), "duration_s": round(base_duration, 1)},
        "keep_constant": ["temperature", "water charge", "addition order", "material masses"],
    })
    if additions:
        first = additions[0]
        plans.append({
            "id": "order_sensitivity",
            "purpose": "Test whether addition order changes precipitation or final dissolved mass.",
            "changes": {"reverse_addition_order": True},
            "keep_constant": ["temperature", "water charge", "RPM", "duration", "total material masses"],
        })
    else:
        plans.append({
            "id": "water_blank",
            "purpose": "Establish a solvent/process blank before interpreting material effects.",
            "changes": {"additions": []},
            "keep_constant": ["temperature", "vessel", "RPM", "duration"],
        })
    return plans[:3]
__all__ = ["assess_simulation", "next_experiments"]
