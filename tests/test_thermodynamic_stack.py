from app.knowledge.chemical_mapping import get_mapping, element_totals
from app.knowledge.thermo_db import build_seed_tdb
from app.tools.phreeqc_generator import build_input
from app.tools.phreeqc_adapter import discover_phreeqc, run_phreeqc

def test_map_identity_and_elements():
    m=get_mapping("map")
    assert m["formula"]=="NH4H2PO4"
    totals=element_totals("map",115.03)
    assert abs(totals["N"]-1)<1e-9 and abs(totals["P"]-1)<1e-9

def test_tdb_seed_has_provenance():
    a=build_seed_tdb().audit()
    assert a["ready"] and a["species"]>=10 and not a["missing_provenance"]

def test_phreeqc_input_is_element_balanced():
    r=build_input([{"material":"map","mass_g":115.03},{"material":"sop","mass_g":174.26}],1.0)
    assert "N 1" in r["input"] and "P 1" in r["input"] and "K 2" in r["input"]
    assert "S 1" in r["input"]
    assert not r["unsupported"]

def test_phreeqc_missing_is_explicit_not_fake():
    d=discover_phreeqc()
    if not d["available"]:
        r=run_phreeqc("SOLUTION 1\n pH 7\nEND\n")
        assert r["status"]=="unavailable"
