from app.database import Database, seed_default_raw_materials
from app.tools.formulation import solve_named_formulation


def test_database_is_seeded_with_core_materials():
    db = Database()
    db.create_tables()
    seed_default_raw_materials(db)
    rows = db.list_raw_materials()
    names = {row["name"] for row in rows}
    db.close()
    assert {"urea", "map", "sop", "bentonite"}.issubset(names)


def test_aliases_resolve_from_database():
    db = Database()
    db.create_tables()
    seed_default_raw_materials(db)
    row = db.resolve_raw_material("اليوريا")
    db.close()
    assert row is not None
    assert row["name"] == "urea"


def test_solver_uses_database_composition():
    db = Database()
    db.create_tables()
    seed_default_raw_materials(db)
    db.upsert_raw_material("test nitrogen", n_pct=40.0, source="unit-test")
    db.close()
    result = solve_named_formulation("40-0-0", 1000, ["test nitrogen"])
    assert result["status"] == "FEASIBLE"
    assert abs(result["materials"]["test nitrogen"] - 1000) < 1e-6


def test_inactive_material_is_rejected():
    db = Database()
    db.create_tables()
    seed_default_raw_materials(db)
    db.upsert_raw_material("inactive material", n_pct=40.0, active=False)
    db.close()
    try:
        solve_named_formulation("40-0-0", 1000, ["inactive material"])
    except ValueError as exc:
        assert "inactive" in str(exc).lower()
    else:
        raise AssertionError("Inactive material must not be accepted")
