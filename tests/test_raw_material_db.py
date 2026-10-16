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


def test_reseeding_preserves_user_edited_raw_material_composition():
    from tempfile import TemporaryDirectory
    from pathlib import Path

    with TemporaryDirectory() as temp_dir:
        db = Database(Path(temp_dir) / "raw-material-test.sqlite")
        db.create_tables()
        seed_default_raw_materials(db)
        db.upsert_raw_material("urea", n_pct=44.5, p2o5_pct=1.2, k2o_pct=0.4,
                               moisture_pct=0.8, assay_pct=98.5, source="user")
        seed_default_raw_materials(db)
        row = db.get_raw_material("urea")
        db.close()
    assert row["n_pct"] == 44.5
    assert row["p2o5_pct"] == 1.2
    assert row["k2o_pct"] == 0.4
    assert row["moisture_pct"] == 0.8
    assert row["assay_pct"] == 98.5
    assert row["source"] == "user"


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
