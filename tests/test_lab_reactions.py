from app.tools.lab_reactions import build_reaction_timeline


def test_timeline_preserves_addition_order_and_action():
    r = build_reaction_timeline([
        {"material": "sop", "mass_g": 50, "time_s": 20, "order": 3},
        {"material": "water", "mass_g": 1000, "time_s": 0, "order": 1},
        {"material": "map", "mass_g": 100, "time_s": 5, "order": 2},
    ])
    assert [x["material"] for x in r[:3]] == ["water", "map", "sop"]
    assert r[1]["action"] == "+ MAP"


def test_map_dissociation_equation_is_explicit():
    r = build_reaction_timeline([{"material": "map", "mass_g": 100, "time_s": 0}])
    assert r[0]["dissociation_equation"] == "NH₄H₂PO₄ → NH₄⁺ + H₂PO₄⁻"
    assert "H₂PO₄⁻" in r[0]["species_after"]


def test_final_species_are_labeled_as_final_not_event_snapshot():
    r = build_reaction_timeline(
        [{"material": "map", "mass_g": 100, "time_s": 0}],
        {"ph_estimate": {"species_mol_L": {"NH₄⁺": 0.2, "H₂PO₄⁻": 0.2}}},
    )
    assert r[0]["final_calculated_species_mol_L"]["NH₄⁺"] == 0.2
    assert "not an event-time snapshot" in r[0]["calculation_scope"]
