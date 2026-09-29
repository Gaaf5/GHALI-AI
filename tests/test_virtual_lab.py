from app.tools.lab import catalog, simulate, sweep
def test_catalog_contains_core_fertilizers_and_solvents():
    ids={x["id"] for x in catalog()}
    assert {"urea","map","mkp","sop","nop","water","ethanol","isopropanol"} <= ids
def test_mass_balance_is_conserved():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,"duration_s":120,
                "additions":[{"material":"water","mass_g":10000},{"material":"sop","mass_g":100}]})
    assert abs(r["mass_balance"]["input_g"]-10100)<1e-9
    assert abs(r["mass_balance"]["dissolved_solids_g"]+r["mass_balance"]["undissolved_solids_g"]-100)<1e-6
def test_sop_uses_actual_water_mass():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,"duration_s":1200,
                "additions":[{"material":"water","mass_g":1000},{"material":"sop","mass_g":1000}]})
    assert abs(r["dissolution"]["sop"]["capacity_g"]-111.0)<1e-6
    assert r["dissolution"]["sop"]["undissolved_g"]>888.9
def test_high_agitation_and_time_can_reach_dissolution_capacity():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":40,"rpm":500,"duration_s":600,
                "additions":[{"material":"water","mass_g":10000},{"material":"sop","mass_g":1000}]})
    assert r["dissolved_g"]["sop"]>999
    assert sum(r["undissolved_g"].values())<1e-6
def test_later_addition_uses_shared_solution_not_fresh_water_capacity():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,"duration_s":1200,
                "additions":[{"material":"water","mass_g":1000,"time_s":0},
                            {"material":"map","mass_g":374,"time_s":0},
                            {"material":"sop","mass_g":100,"time_s":600}]})
    # MAP saturates the shared aqueous phase first; adding SOP later changes the
    # common equilibrium and forces MAP to re-precipitate. SOP does not receive a
    # fresh pure-water capacity.
    assert r["dissolved_g"]["map"] < 374
    assert r["dissolved_g"]["sop"] < 100
    assert r["dissolution"]["map"]["reprecipitated_g"] > 0
    assert r["dissolution"]["sop"]["final_mixed_equilibrium_capacity_g"] < 100
    assert "600.0" in r["state_timeline"]
    assert r["state_timeline"]["600.0"]["map"]["event_equilibrium_target_g"] < 374
    assert r["state_timeline"]["600.0"]["map"]["pre_event_equilibrium_target_g"] >= 374


def test_event_time_delays_dissolution():
    fast=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,"duration_s":120,
                   "additions":[{"material":"water","mass_g":1000,"time_s":0},{"material":"sop","mass_g":100,"time_s":0}]})
    late=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,"duration_s":120,
                   "additions":[{"material":"water","mass_g":1000,"time_s":0},{"material":"sop","mass_g":100,"time_s":119}]})
    assert fast["dissolved_g"]["sop"]>late["dissolved_g"]["sop"]
def test_sweep_count():
    r=sweep({"vessel":{"working_volume_l":10},"duration_s":60,
             "additions":[{"material":"water","mass_g":10000},{"material":"sop","mass_g":100}]},
            {"rpm":[100,300,500],"temperature_c":[20,40]})
    assert r["runs"]==6
    assert r["best"] is not None
from app.tools.lab_chemistry import compatibility, ionic_strength
def test_calcium_sulfate_compatibility_risk_is_flagged():
    risks=compatibility({"calcium_nitrate":100,"sop":100})
    assert any("CaSO4"==x["product"] for x in risks)
def test_ionic_strength_calculation():
    assert abs(ionic_strength([{"moles_per_l":1,"charge":1},{"moles_per_l":1,"charge":-1}])-1.0)<1e-9
