import math

from app.tools import (
    mass_percent,
    mass_to_moles,
    moles_to_mass,
    molar_mass,
    npk_grade_from_compounds,
)


def test_formula_and_moles():
    assert math.isclose(molar_mass("H2O"), 18.015, rel_tol=1e-9)
    assert math.isclose(molar_mass("CO(NH2)2"), 60.056, rel_tol=1e-9)
    assert math.isclose(mass_to_moles(60.056, "CO(NH2)2"), 1.0, rel_tol=1e-6)
    assert math.isclose(moles_to_mass(1.0, "CO(NH2)2"), 60.056, rel_tol=1e-9)


def test_mass_percent_validation():
    assert mass_percent(25, 100) == 25.0

    try:
        mass_percent(101, 100)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected validation error")


def test_urea_nitrogen_grade():
    grade = npk_grade_from_compounds([("CO(NH2)2", 100.0)])
    assert math.isclose(grade["N"], 46.64646, rel_tol=1e-5)
    assert grade["P2O5"] == 0.0
    assert grade["K2O"] == 0.0
