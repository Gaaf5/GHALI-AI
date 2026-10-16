from app.tools.formulation import solve_formulation, solve_named_formulation


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
    result = solve_named_formulation("20-30-10", 1000, ["Urea", "MAP", "SOP", "Ammonium Nitrate"], 0.0)
    assert result["status"] == "FEASIBLE"
    assert abs(sum(result["materials"].values()) - 1000) < 1e-6
    for nutrient in ("N", "P2O5", "K2O"):
        assert abs(result["achieved"][nutrient] - result["target"][nutrient]) < 1e-6


def test_simultaneous_max_and_min_objectives():
    result = solve_named_formulation("20-20-20", 1000, ["Urea", "MAP", "MKP", "SOP"], 0.2, {}, {"maximize": ["Urea"], "minimize": ["MAP"]})
    assert result["status"] == "FEASIBLE"
    assert result["objective"]["maximize"] == ["urea"]
    assert result["objective"]["minimize"] == ["map"]
    assert abs(sum(result["materials"].values()) - 1000) < 1e-6


def _assert_raises_value_error(expected_text, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        assert expected_text in str(exc), f"Expected {expected_text!r} in {str(exc)!r}"
    else:
        raise AssertionError(f"Expected ValueError containing {expected_text!r}")


def test_solver_rejects_non_finite_batch_tolerance_and_material_analysis():
    materials = {"urea": {"N": 46, "P2O5": 0, "K2O": 0}}
    _assert_raises_value_error("finite positive", solve_formulation, 10, 0, 0, float("nan"), materials)
    _assert_raises_value_error("finite non-negative", solve_formulation, 10, 0, 0, 100, materials, tolerance=float("inf"))
    _assert_raises_value_error("finite values", solve_formulation, float("nan"), 0, 0, 100, materials)
    _assert_raises_value_error("Nutrient analysis", solve_formulation, 10, 0, 0, 100, {"urea": {"N": float("inf")}})


def test_solver_rejects_negative_and_over_100_target_grades():
    materials = {"urea": {"N": 46, "P2O5": 0, "K2O": 0}}
    _assert_raises_value_error("between 0 and 100", solve_formulation, -1, 0, 0, 100, materials)
    _assert_raises_value_error("between 0 and 100", solve_formulation, 101, 0, 0, 100, materials)



def test_solver_rejects_invalid_fixed_quantities_and_limits():
    materials = {"urea": {"N": 46, "P2O5": 0, "K2O": 0}}
    _assert_raises_value_error(
        "quantity must be finite", solve_formulation, 46, 0, 0, 100, materials,
        fixed_kg={"urea": float("nan")}
    )
    _assert_raises_value_error(
        "quantity must be finite", solve_formulation, 46, 0, 0, 100, materials,
        fixed_kg={"urea": float("inf")}
    )
    _assert_raises_value_error(
        "within batch mass", solve_formulation, 46, 0, 0, 100, materials,
        limits={"urea": {"min_kg": 101}}
    )
