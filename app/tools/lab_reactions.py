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
        # Explicitly expose equilibrium displacement caused by this addition.
        # The affected material is often an EARLIER addition: e.g. SOP added at
        # t=600 s can lower MAP's dissolved equilibrium target. Therefore inspect
        # every material in the exact event snapshot, not only the newly added one.
        for affected_material, ms in snap.items():
            if not isinstance(ms, dict):
                continue
            before = ms.get("pre_event_equilibrium_target_g")
            after = ms.get("event_equilibrium_target_g")
            if before is None or after is None or abs(float(after) - float(before)) <= 1e-6:
                continue
            affected_info = SPECIES.get(str(affected_material), {"formula":str(affected_material), "label":str(affected_material)})
            delta = float(after) - float(before)
            direction = "redissolution" if delta > 0 else "re-precipitation"
            timeline.append({
                "time_s": t,
                "order": int(a.get("order", i + 1)) + 0.1,
                "event": "equilibrium_shift",
                "material": str(affected_material),
                "display": affected_info["formula"],
                "label": affected_info.get("label", str(affected_material)),
                "action": "↔ " + direction,
                "mass_g": abs(delta),
                "phase_before": list(aqueous),
                "dissociation": [],
                "dissociation_equation": "dissolved ⇌ solid",
                "species_after": list(aqueous),
                "reactions": [f"Shared-solution equilibrium shift: {before:.2f} g → {after:.2f} g dissolved"],
                "acid_base_network": [],
                "status": "deterministic_screening",
                "material_state": dict(ms),
                "description": f"The addition changes the shared equilibrium for {affected_info.get('label', affected_material)}: {before:.2f} g → {after:.2f} g dissolved ({direction}).",
            })

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

def build_chemical_state_machine(timeline: list[dict[str, Any]], chemistry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build an explicit chemistry-state ledger from deterministic timeline data.

    The machine never upgrades a display heuristic into a chemical reaction.
    Each stage carries a scope so event-time state is not confused with final-state
    speciation or predicted precipitation.
    """
    chemistry = chemistry or {}
    states: list[dict[str, Any]] = []
    for step in timeline:
        event = step.get("event")
        t = float(step.get("time_s", 0))
        material = str(step.get("material", ""))
        label = str(step.get("label", material))
        if event == "addition":
            states.append({
                "time_s": t, "stage": "input", "material": material,
                "label": label, "scope": "event-time",
                "status": "observed_input", "description": f"{label} enters the vessel."
            })
            ms = step.get("material_state") or {}
            if material != "water":
                if ms.get("kinetic_dissolved_g") is not None:
                    states.append({
                        "time_s": t, "stage": "dissolution", "material": material,
                        "label": label, "scope": "event-time kinetic snapshot",
                        "status": "deterministic", "dissolved_g": float(ms["kinetic_dissolved_g"]),
                        "undissolved_g": (float(ms["charged_g"]) - float(ms["kinetic_dissolved_g"])) if ms.get("charged_g") is not None else None,
                    })
                elif ms.get("event_equilibrium_target_g") is not None:
                    states.append({
                        "time_s": t, "stage": "dissolution", "material": material,
                        "label": label, "scope": "event-time equilibrium target; not measured kinetic state",
                        "status": "equilibrium_target", "target_dissolved_g": float(ms["event_equilibrium_target_g"]),
                        "undissolved_g": (float(ms["charged_g"]) - float(ms["event_equilibrium_target_g"])) if ms.get("charged_g") is not None else None,
                    })
            diss = step.get("dissociation") or []
            if diss:
                states.append({
                    "time_s": t, "stage": "dissociation", "material": material,
                    "label": label, "scope": "chemical representation",
                    "status": "principal_ions", "species": list(diss),
                    "equation": step.get("dissociation_equation")
                })
            networks = step.get("acid_base_network") or []
            if networks:
                states.append({
                    "time_s": t, "stage": "acid_base_network", "material": material,
                    "label": label, "scope": "candidate equilibrium network",
                    "status": "not_event_time_speciation", "equilibria": list(networks)
                })
            if material != "water" and step.get("final_calculated_species_mol_L"):
                states.append({
                    "time_s": t, "stage": "speciation", "material": material,
                    "label": label, "scope": "final aqueous state; not event-time snapshot",
                    "status": "calculated", "species_mol_L": dict(step["final_calculated_species_mol_L"])
                })
        elif event == "equilibrium_shift":
            ms = step.get("material_state") or {}
            states.append({
                "time_s": t, "stage": "equilibrium_repartition", "material": material,
                "label": label, "scope": "event-time deterministic screening",
                "status": "re-precipitation" if "re-precipitation" in str(step.get("action")) else "redissolution",
                "before_target_g": ms.get("pre_event_equilibrium_target_g"),
                "after_target_g": ms.get("event_equilibrium_target_g"),
                "shift_g": step.get("mass_g"),
                "equation": "dissolved ⇌ solid"
            })
        elif event == "precipitation":
            states.append({
                "time_s": t, "stage": "precipitation", "material": material,
                "label": label, "scope": "predicted by deterministic chemistry screen",
                "status": "predicted", "reaction": (step.get("reactions") or [None])[0]
            })
    return states

__all__ = ["build_reaction_timeline", "build_chemical_state_machine"]
