from app.tools.formulation import solve_named_formulation


def test_exact_three_material_solution_rejects_mass_mismatch():
    result = solve_named_formulation("20-30-10", 1000, ["Urea", "MAP", "SOP"], 0.0)
    assert result["status"] == "NOT_FEASIBLE"


def test_known_formulation_uses_exact_npk_and_mass_with_filler():
    result = solve_named_formulation("20-30-10", 1000, ["Urea", "MAP", "SOP", "Bentonite"], 0.0)
    assert result["status"] == "FEASIBLE"
    assert abs(sum(result["materials"].values()) - 1000) < 1e-6
    for nutrient in ("N", "P2O5", "K2O"):
        assert abs(result["achieved"][nutrient] - result["target"][nutrient]) < 1e-6


def test_four_nutrient_materials_are_supported():
    result = solve_named_formulation("20-30-10", 1000, ["Urea", "MAP", "SOP", "Ammonium Nitrate"], 0.0, {}, {"material":"Ammonium Nitrate","direction":"max"})
    assert result["status"] == "FEASIBLE"
    assert abs(sum(result["materials"].values()) - 1000) < 1e-6
    for nutrient in ("N", "P2O5", "K2O"):
        assert abs(result["achieved"][nutrient] - result["target"][nutrient]) < 1e-6


def test_impossible_grade_is_rejected():
    result = solve_named_formulation("60-60-60", 1000, ["Urea", "MAP", "SOP", "Bentonite"])
    assert result["status"] == "NOT_FEASIBLE"


def test_arabic_material_aliases():
    result = solve_named_formulation("20-30-10", 1000, ["اليوريا", "ماب", "كبريتات البوتاسيوم", "بنتونيت"])
    assert result["status"] == "FEASIBLE"


def test_zero_target_and_inert_only_case():
    result = solve_named_formulation("0-0-0", 1000, ["Bentonite"])
    assert result["status"] == "FEASIBLE"
    assert abs(result["materials"]["bentonite"] - 1000) < 1e-6


def test_four_material_solution_is_not_forced_to_use_filler():
    result = solve_named_formulation(
        "20-30-10", 1000,
        ["Urea", "MAP", "SOP", "Ammonium Nitrate"], 0.0,
    )
    assert result["status"] == "FEASIBLE"
    assert abs(sum(result["materials"].values()) - 1000) < 1e-6
    for nutrient in ("N", "P2O5", "K2O"):
        assert abs(result["achieved"][nutrient] - result["target"][nutrient]) < 1e-6
