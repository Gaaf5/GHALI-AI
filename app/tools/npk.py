from .chemistry import molar_mass, element_mass_fraction

N_TO_N = 1.0
P_TO_P2O5 = 2.29138
K_TO_K2O = 1.20459


def element_fraction(formula, element):
    return element_mass_fraction(formula, element)


def npk_grade_from_compounds(compounds):
    """Calculate N-P2O5-K2O mass percentages from (formula, mass) pairs."""
    total_mass = sum(mass for _, mass in compounds)
    if total_mass <= 0:
        raise ValueError("Total recipe mass must be positive")

    nitrogen = 0.0
    phosphorus = 0.0
    potassium = 0.0
    for formula, mass in compounds:
        if mass < 0:
            raise ValueError("Component mass cannot be negative")
        nitrogen += mass * element_mass_fraction(formula, "N")
        phosphorus += mass * element_mass_fraction(formula, "P") * P_TO_P2O5
        potassium += mass * element_mass_fraction(formula, "K") * K_TO_K2O

    return {
        "N": nitrogen / total_mass * 100.0,
        "P2O5": phosphorus / total_mass * 100.0,
        "K2O": potassium / total_mass * 100.0,
    }
