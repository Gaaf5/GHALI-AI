MASS_TO_KG = {
    "kg": 1.0,
    "g": 0.001,
    "mg": 0.000001,
    "t": 1000.0,
}

VOLUME_TO_L = {
    "l": 1.0,
    "ml": 0.001,
    "m3": 1000.0,
}


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    source = from_unit.lower().strip()
    target = to_unit.lower().strip()
    if source not in MASS_TO_KG or target not in MASS_TO_KG:
        raise ValueError("Unsupported mass unit")
    return value * MASS_TO_KG[source] / MASS_TO_KG[target]


def convert_volume(value: float, from_unit: str, to_unit: str) -> float:
    source = from_unit.lower().strip()
    target = to_unit.lower().strip()
    if source not in VOLUME_TO_L or target not in VOLUME_TO_L:
        raise ValueError("Unsupported volume unit")
    return value * VOLUME_TO_L[source] / VOLUME_TO_L[target]
