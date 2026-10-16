from app.tools.formulation import _nutrient_breakdown


def test_te_mix_percent_to_ppm_conversion_uses_10000_factor():
    # 0.080% B in the TE-MIX material is 800 ppm in that material.
    properties = {
        "TE-MIX": {
            "trace_elements": {
                "B": 0.080,
                "Cu-EDTA": 0.260,
                "Fe-EDTA": 0.510,
                "Mn-EDTA": 0.260,
                "Zn-EDTA": 0.260,
                "Mo": 0.005,
            }
        }
    }
    result = _nutrient_breakdown({"TE-MIX": 1.0}, properties, 1.0)
    assert result["te_mix_trace_elements_ppm"] == {
        "B": 800.0,
        "Cu-EDTA": 2600.0,
        "Fe-EDTA": 5100.0,
        "Mn-EDTA": 2600.0,
        "Zn-EDTA": 2600.0,
        "Mo": 50.0,
    }


def test_nutrient_breakdown_uses_only_charged_material_masses():
    properties = {
        "urea": {"N": 46.0, "n_urea_pct": 46.0},
        "ammonium nitrate": {"N": 34.0, "n_nitrate_pct": 17.0, "n_ammoniacal_pct": 17.0},
        "unused": {"N": 99.0, "n_urea_pct": 99.0},
    }
    result = _nutrient_breakdown({"urea": 10.0, "ammonium nitrate": 5.0}, properties, 15.0)
    assert abs(result["total_N_kg"] - 6.3) < 1e-9
    assert abs(result["nitrogen_forms_kg"]["urea_N"] - 4.6) < 1e-9
    assert abs(result["nitrogen_forms_kg"]["nitrate_N"] - 0.85) < 1e-9
    assert abs(result["nitrogen_forms_kg"]["ammoniacal_N"] - 0.85) < 1e-9


def test_trace_element_product_percentage_scales_with_batch_mass():
    properties = {"TE-MIX": {"trace_elements": {"B": 0.080}}}
    result = _nutrient_breakdown({"TE-MIX": 2.0}, properties, 100.0)
    assert abs(result["trace_elements_kg"]["B"] - 0.0016) < 1e-12
    assert abs(result["trace_elements_pct_of_product"]["B"] - 0.0016) < 1e-12
    assert result["te_mix_trace_elements_ppm"]["B"] == 800.0
