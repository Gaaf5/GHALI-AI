import re

ATOMIC_WEIGHTS = {
    "H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "K": 39.098, "Ca": 40.078,
    "Fe": 55.845, "Cu": 63.546, "Zn": 65.38, "Mo": 95.95,
}


def _parse_formula(formula):
    formula = formula.replace(" ", "")
    if not formula:
        raise ValueError("Formula cannot be empty")
    tokens = re.findall(r"([A-Z][a-z]?|\(|\)|\d+(?:\.\d+)?)", formula)
    if "".join(tokens) != formula:
        raise ValueError(f"Invalid formula: {formula}")
    stack = [{}]
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "(":
            stack.append({})
        elif tok == ")":
            if len(stack) == 1:
                raise ValueError(f"Invalid formula: {formula}")
            group = stack.pop()
            mult = 1.0
            if i + 1 < len(tokens) and re.fullmatch(r"\d+(?:\.\d+)?", tokens[i + 1]):
                mult = float(tokens[i + 1]); i += 1
            for e, n in group.items():
                stack[-1][e] = stack[-1].get(e, 0.0) + n * mult
        elif re.fullmatch(r"\d+(?:\.\d+)?", tok):
            raise ValueError(f"Invalid formula: {formula}")
        else:
            count = 1.0
            if i + 1 < len(tokens) and re.fullmatch(r"\d+(?:\.\d+)?", tokens[i + 1]):
                count = float(tokens[i + 1]); i += 1
            stack[-1][tok] = stack[-1].get(tok, 0.0) + count
        i += 1
    if len(stack) != 1:
        raise ValueError(f"Invalid formula: {formula}")
    return list(stack[0].items())


def atomic_weight(symbol):
    try:
        return ATOMIC_WEIGHTS[symbol]
    except KeyError as exc:
        raise ValueError(f"Unsupported element: {symbol}") from exc


def molar_mass(formula):
    return sum(atomic_weight(e) * n for e, n in _parse_formula(formula))


def element_mass_fraction(formula, element):
    total = molar_mass(formula)
    count = sum(n for e, n in _parse_formula(formula) if e == element)
    if count == 0:
        return 0.0
    return atomic_weight(element) * count / total


def element_mass_percent(formula, element):
    return element_mass_fraction(formula, element) * 100.0


def mass_to_moles(mass_g, formula):
    if mass_g < 0:
        raise ValueError("Mass cannot be negative")
    return mass_g / molar_mass(formula)


def moles_to_mass(moles, formula):
    if moles < 0:
        raise ValueError("Moles cannot be negative")
    return moles * molar_mass(formula)


def mass_percent(part_mass, total_mass):
    if part_mass < 0 or total_mass <= 0 or part_mass > total_mass:
        raise ValueError("Masses must be non-negative and part cannot exceed total")
    return (part_mass / total_mass) * 100.0


def solution_molarity(moles, volume_l):
    if moles < 0 or volume_l <= 0:
        raise ValueError("Moles must be non-negative and volume positive")
    return moles / volume_l


def dilution_volume(c1, v1, c2):
    if c1 <= 0 or v1 < 0 or c2 <= 0 or c2 > c1:
        raise ValueError("Require c1>0, v1>=0, 0<c2<=c1")
    return (c1 * v1) / c2


def molarity(moles, volume_l):
    return solution_molarity(moles, volume_l)
