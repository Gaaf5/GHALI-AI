from app.tools.liquid_formulation import assess_liquid_formulation


def test_catalog_water_is_not_misclassified_as_unknown():
    result = assess_liquid_formulation(
        {
            "product_name": "Water catalog regression test",
            "batch_kg": 100,
            "density_g_ml": 1.0,
            "materials": [{"material": "water", "kg": 100}],
        },
        raw_materials=[],
    )
    assert result["readiness"] != "BLOCKED"
    assert not any("Unknown raw material" in error for error in result["errors"])


def test_catalog_material_uses_database_nutrient_analysis():
    from app.database import Database, seed_default_raw_materials

    db = Database()
    db.create_tables()
    seed_default_raw_materials(db)
    raw_materials = db.list_raw_materials()
    db.close()
    result = assess_liquid_formulation(
        {
            "product_name": "Catalog nutrient mapping test",
            "batch_kg": 100,
            "density_g_ml": 1.1,
            "materials": [{"material": "water", "kg": 90}, {"material": "potassium_chloride", "kg": 10}],
        },
        raw_materials=raw_materials,
    )
    assert abs(result["formula_ww"]["K2O"] - 6.0) < 1e-8
    assert abs(result["secondary"]["Cl_pct"] - 4.73) < 1e-8


def test_mass_balance_is_reported_and_large_mismatch_blocks():
    result = assess_liquid_formulation(
        {
            "product_name": "Mass balance regression test",
            "batch_kg": 100,
            "density_g_ml": 1.2,
            "materials": [{"material": "water", "kg": 50}, {"material": "urea", "kg": 10}],
        },
        raw_materials=[],
    )
    assert result["mass_balance"]["charged_mass_kg"] == 60
    assert result["readiness"] == "BLOCKED"
    assert any("mass" in error.lower() for error in result["errors"])


def test_unknown_raw_material_blocks_liquid_assessment():
    result = assess_liquid_formulation(
        {
            "product_name": "Unknown material regression test",
            "batch_kg": 100,
            "density_g_ml": 1.2,
            "materials": [{"material": "MadeUpSalt", "kg": 20}],
        },
        raw_materials=[],
    )
    assert result["readiness"] == "BLOCKED"
    assert result["errors"]
    assert any("MadeUpSalt" in error for error in result["errors"])


def test_non_finite_density_is_rejected():
    import math
    try:
        assess_liquid_formulation(
            {"batch_kg": 10, "density_g_ml": math.nan,
             "materials": [{"material": "water", "kg": 10}]},
            raw_materials=[],
        )
    except ValueError as exc:
        assert "density" in str(exc).lower()
    else:
        raise AssertionError("NaN density must be rejected")


def test_non_finite_material_mass_is_rejected():
    import math
    try:
        assess_liquid_formulation(
            {"batch_kg": 10, "density_g_ml": 1,
             "materials": [{"material": "water", "kg": math.inf}]},
            raw_materials=[],
        )
    except ValueError as exc:
        assert "positive kg" in str(exc).lower()
    else:
        raise AssertionError("Infinite ingredient mass must be rejected")


def test_target_volume_mismatch_is_flagged_and_material_volume_pct_is_not_fabricated():
    result = assess_liquid_formulation(
        {
            "product_name": "Volume consistency regression test",
            "batch_kg": 100,
            "density_g_ml": 1.2,
            "target_volume_l": 100,
            "materials": [{"material": "water", "kg": 100}],
        },
        raw_materials=[],
    )
    assert abs(result["estimated_volume_l"] - (100 / 1.2)) < 1e-9
    assert any("Volume check" in warning for warning in result["warnings"])
    assert all("wv_pct" not in material for material in result["materials"])
