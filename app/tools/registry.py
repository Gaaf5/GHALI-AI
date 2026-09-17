from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    function: Callable[..., Any]


TOOLS: dict[str, ToolSpec] = {}


def register_tool(name: str, description: str, function: Callable[..., Any]) -> ToolSpec:
    name = name.strip()
    if not name:
        raise ValueError("Tool name cannot be empty")
    spec = ToolSpec(name, description.strip(), function)
    TOOLS[name] = spec
    return spec


def list_tools() -> tuple[ToolSpec, ...]:
    return tuple(TOOLS.values())


def get_tool(name: str) -> ToolSpec | None:
    return TOOLS.get(name.strip())


def run_tool(name: str, **kwargs: Any) -> Any:
    spec = get_tool(name)
    if spec is None:
        raise KeyError(f"Unknown tool: {name}")
    return spec.function(**kwargs)


def load_defaults() -> tuple[ToolSpec, ...]:
    from .chemistry import mass_percent, mass_to_moles, molar_mass, moles_to_mass
    from .mass_balance import mixed_composition
    from .formulation import solve_named_formulation
    from .npk import npk_grade_from_compounds
    from .solutions import dilution_c1v1_to_v2, mass_fraction, molarity
    from .units import convert_mass, convert_volume

    specs = [
        ("molar_mass", "Calculate formula molar mass.", molar_mass),
        ("mass_to_moles", "Convert mass to moles.", mass_to_moles),
        ("moles_to_mass", "Convert moles to mass.", moles_to_mass),
        ("mass_percent", "Calculate mass percent.", mass_percent),
        ("formulation_solver", "Solve exact N-P2O5-K2O fertilizer formulations from selected raw materials.", solve_named_formulation),
        ("npk_grade_from_compounds", "Calculate N-P2O5-K2O grade.", npk_grade_from_compounds),
        ("molarity", "Calculate molarity.", molarity),
        ("dilution_c1v1_to_v2", "Calculate dilution concentration.", dilution_c1v1_to_v2),
        ("mass_fraction", "Calculate solution mass fraction.", mass_fraction),
        ("convert_mass", "Convert mass units.", convert_mass),
        ("convert_volume", "Convert volume units.", convert_volume),
        ("mixed_composition", "Calculate mixed stream composition.", mixed_composition),
    ]
    return tuple(register_tool(*item) for item in specs)
