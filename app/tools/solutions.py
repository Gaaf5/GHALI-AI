def molarity(moles: float, volume_l: float) -> float:
    if moles < 0 or volume_l <= 0:
        raise ValueError("Moles must be non-negative and volume must be positive")
    return moles / volume_l


def dilution_c1v1_to_v2(c1: float, v1: float, v2: float) -> float:
    if c1 < 0 or v1 < 0 or v2 <= 0:
        raise ValueError("Invalid concentration or volume")
    return c1 * v1 / v2


def mass_fraction(solute_mass: float, solution_mass: float) -> float:
    if solute_mass < 0 or solution_mass <= 0:
        raise ValueError("Invalid masses")
    if solute_mass > solution_mass:
        raise ValueError("Solute mass cannot exceed solution mass")
    return solute_mass / solution_mass * 100.0
