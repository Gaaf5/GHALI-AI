from __future__ import annotations
from typing import Any

# Reaction/speciation display layer. It deliberately distinguishes dissociation
# from actual acid-base/precipitation reactions.
SPECIES = {
    "water": {"formula":"H₂O","kind":"molecule","label":"Water"},
    "map": {"formula":"NH₄H₂PO₄","kind":"salt","label":"MAP"},
    "dap": {"formula":"(NH₄)₂HPO₄","kind":"salt","label":"DAP"},
    "mkp": {"formula":"KH₂PO₄","kind":"salt","label":"MKP"},
    "sop": {"formula":"K₂SO₄","kind":"salt","label":"SOP"},
    "urea": {"formula":"CO(NH₂)₂","kind":"molecule","label":"Urea"},
    "ammonium_sulfate": {"formula":"(NH₄)₂SO₄","kind":"salt","label":"Ammonium sulfate"},
    "potassium_chloride": {"formula":"KCl","kind":"salt","label":"KCl"},
    "potassium_hydroxide": {"formula":"KOH","kind":"base","label":"KOH"},
    "boric_acid": {"formula":"H₃BO₃","kind":"weak_acid","label":"Boric acid"},
    "zinc_sulfate": {"formula":"ZnSO₄·7H₂O","kind":"salt","label":"Zinc sulfate heptahydrate"},
}

DISSOCIATION = {
    "map": ["NH₄⁺", "H₂PO₄⁻"],
    "dap": ["NH₄⁺", "NH₄⁺", "HPO₄²⁻"],
    "mkp": ["K⁺", "H₂PO₄⁻"],
    "sop": ["K⁺", "K⁺", "SO₄²⁻"],
    "ammonium_sulfate": ["NH₄⁺", "NH₄⁺", "SO₄²⁻"],
    "potassium_chloride": ["K⁺", "Cl⁻"],
    "potassium_hydroxide": ["K⁺", "OH⁻"],
    "zinc_sulfate": ["Zn²⁺", "SO₄²⁻"],
}

def _species_key(item: str) -> str:
    return item.strip().lower().replace(" ", "_").replace("-", "_")

def build_reaction_timeline(additions: list[dict[str, Any]], chemistry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    chemistry = chemistry or {}
    timeline = []
    aqueous = ["H₂O"]
    ordered = sorted(additions, key=lambda x: (float(x.get("time_s", 0)), int(x.get("order", 999999))))
    for i, a in enumerate(ordered):
        material = _species_key(str(a.get("material", "")))
        info = SPECIES.get(material, {"formula": material, "kind":"unknown","label":material})
        t = float(a.get("time_s", 0))
        step = {
            "time_s": t,
            "order": int(a.get("order", i + 1)),
            "event": "addition",
            "material": material,
            "display": info["formula"],
            "mass_g": float(a.get("mass_g", 0)),
            "phase_before": list(aqueous),
            "dissociation": list(DISSOCIATION.get(material, [])),
            "species_after": list(aqueous),
            "reactions": [],
            "status": "screening",
        }
        if material == "water":
            if "H₂O" not in aqueous:
                aqueous.append("H₂O")
            step["species_after"] = list(aqueous)
            step["description"] = "Water added: solvent is represented as H₂O."
        else:
            diss = DISSOCIATION.get(material)
            if diss:
                for sp in diss:
                    if sp not in aqueous:
                        aqueous.append(sp)
                step["species_after"] = list(aqueous)
                step["description"] = f"{info['formula']} dissolves and dissociates into its principal ions."
            else:
                aqueous.append(info["formula"])
                step["species_after"] = list(aqueous)
                step["description"] = f"{info['formula']} is represented as an undetailed dissolved species pending validated speciation data."
        timeline.append(step)

    # Attach actual calculated species when available; never invent missing values.
    ph = chemistry.get("ph_estimate") or {}
    calculated = ph.get("species_mol_L") if isinstance(ph, dict) else None
    if isinstance(calculated, dict):
        for step in timeline:
            step["calculated_species_mol_L"] = {k: float(v) for k, v in calculated.items() if float(v) > 1e-12}
    precip = chemistry.get("precipitation_equilibrium") or {}
    events = precip.get("events") if isinstance(precip, dict) else []
    if isinstance(events, list):
        for pe in events:
            product = str(pe.get("product", ""))
            timeline.append({
                "time_s": float(pe.get("time_s", 0)),
                "order": 999999,
                "event": "precipitation",
                "material": product,
                "display": product,
                "mass_g": None,
                "phase_before": [],
                "dissociation": [],
                "species_after": [],
                "reactions": [f"Predicted precipitation: {product}"],
                "status": "predicted",
            })
    return sorted(timeline, key=lambda x: (x["time_s"], x["order"], x["event"]))

__all__ = ["build_reaction_timeline"]
