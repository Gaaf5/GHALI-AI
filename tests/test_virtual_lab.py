from app.tools.lab import catalog, simulate, sweep

def test_catalog_contains_core_fertilizers_and_solvents():
    ids={x["id"] for x in catalog()}
    assert {"urea","map","mkp","sop","nop","water","ethanol","isopropanol"} <= ids

def test_mass_balance_is_conserved():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,
                "duration_s":120,"additions":[{"material":"water","mass_g":10000},
                {"material":"sop","mass_g":100}]})
    assert abs(r["mass_balance"]["input_g"]-10100) < 1e-9
    assert abs(r["mass_balance"]["dissolved_solids_g"]+
               r["mass_balance"]["undissolved_solids_g"]-100) < 1e-6

def test_high_agitation_and_time_can_reach_dissolution_capacity():
    r=simulate({"vessel":{"working_volume_l":10},"temperature_c":40,"rpm":500,
                "duration_s":600,"additions":[{"material":"water","mass_g":10000},
                {"material":"sop","mass_g":1000}]})
    assert r["dissolved_g"]["sop"] > 999
    assert sum(r["undissolved_g"].values()) < 1e-6

def test_event_time_delays_dissolution():
    fast=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,
                   "duration_s":120,"additions":[{"material":"sop","mass_g":100,
                   "time_s":0}]})
    late=simulate({"vessel":{"working_volume_l":10},"temperature_c":20,"rpm":300,
                   "duration_s":120,"additions":[{"material":"sop","mass_g":100,
                   "time_s":119}]})
    assert fast["dissolved_g"]["sop"] > late["dissolved_g"]["sop"]

def test_sweep_count():
    r=sweep({"vessel":{"working_volume_l":10},"duration_s":60,
             "additions":[{"material":"water","mass_g":10000},{"material":"sop","mass_g":100}]},
            {"rpm":[100,300,500],"temperature_c":[20,40]})
    assert r["runs"] == 6
    assert r["best"] is not None

from app.tools.lab_chemistry import compatibility, ionic_strength

def test_calcium_sulfate_compatibility_risk_is_flagged():
    risks=compatibility({"calcium_nitrate":100,"sop":100})
    assert any("CaSO4"==x["product"] for x in risks)

def test_ionic_strength_calculation():
    assert abs(ionic_strength([{"moles_per_l":1,"charge":1},{"moles_per_l":1,"charge":-1}])-1.0)<1e-9
