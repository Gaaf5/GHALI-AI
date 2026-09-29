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

ACID_BASE_NETWORK = {
    "phosphate": ["H₃PO₄ ⇌ H₂PO₄⁻ + H⁺", "H₂PO₄⁻ ⇌ HPO₄²⁻ + H⁺", "HPO₄²⁻ ⇌ PO₄³⁻ + H⁺"],
    "ammonium": ["NH₄⁺ ⇌ NH₃ + H⁺"],
    "sulfate": ["HSO₄⁻ ⇌ SO₄²⁻ + H⁺"],
    "sulfite": ["H₂SO₃ ⇌ HSO₃⁻ + H⁺", "HSO₃⁻ ⇌ SO₃²⁻ + H⁺"],
    "phosphite": ["H₃PO₃ ⇌ H₂PO₃⁻ + H⁺", "H₂PO₃⁻ ⇌ HPO₃²⁻ + H⁺"],
    "borate": ["H₃BO₃ + H₂O ⇌ B(OH)₄⁻ + H⁺"],
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

def build_reaction_timeline(additions: list[dict[str, Any]], chemistry: dict[str, Any] | None = None, state_snapshots: dict[Any, Any] | None = None) -> list[dict[str, Any]]:
    chemistry = chemistry or {}
    state_snapshots = state_snapshots or {}
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
            "label": info.get("label", material),
            "action": f"+ {info.get('label', material)}",
            "mass_g": float(a.get("mass_g", 0)),
            "phase_before": list(aqueous),
            "dissociation": list(DISSOCIATION.get(material, [])),
            "dissociation_equation": (f"{info['formula']} → {' + '.join(DISSOCIATION[material])}" if material in DISSOCIATION else None),
            "species_after": list(aqueous),
            "reactions": [],
            "acid_base_network": [],
            "status": "screening",
        }
        if material == "water":
            if "H₂O" not in aqueous:
                aqueous.append("H₂O")
            step["species_after"] = list(aqueous)
            step["description"] = "Water added: solvent is represented as H₂O."
        else:
            if material in {"map", "dap", "mkp", "urea_phosphate"}:
                step["acid_base_network"] += list(ACID_BASE_NETWORK["phosphate"])
            if material in {"map", "dap", "ammonium_sulfate", "ammonium_sulfite"}:
                step["acid_base_network"] += list(ACID_BASE_NETWORK["ammonium"])
            if material in {"sop", "ammonium_sulfate", "zinc_sulfate"}:
                step["acid_base_network"] += list(ACID_BASE_NETWORK["sulfate"])
            if material == "ammonium_sulfite":
                step["acid_base_network"] += list(ACID_BASE_NETWORK["sulfite"])
            if material == "boric_acid":
                step["acid_base_network"] += list(ACID_BASE_NETWORK["borate"])
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
        # Attach the deterministic event-time state. Prefer the exact event-time
        # snapshot; never manufacture an intermediate concentration from the final state.
        snap = state_snapshots.get(t) or state_snapshots.get(float(t)) or {}
        step["state_snapshot"] = snap
        if material in snap:
            step["material_state"] = dict(snap[material])
        timeline.append(step)

    # Attach actual calculated species when available; never invent missing values.
    ph = chemistry.get("ph_estimate") or {}
    calculated = ph.get("species_mol_L") if isinstance(ph, dict) else None
    if isinstance(calculated, dict):
        final_species = {k: float(v) for k, v in calculated.items() if float(v) > 1e-12}
        for step in timeline:
            if step.get("event") == "addition":
                step["final_calculated_species_mol_L"] = final_species
                step["calculation_scope"] = "final aqueous state; not an event-time snapshot"
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
