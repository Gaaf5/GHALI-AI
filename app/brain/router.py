from dataclasses import dataclass
import re

from app.tools.registry import get_tool, list_tools


@dataclass(frozen=True)
class Route:
    kind: str
    tool_name: str | None = None


_PATTERNS = {
    "molar_mass": (r"molar mass", r"molecular weight", r"molecular mass"),
    "mass_to_moles": (r"mass.*moles", r"grams?.*moles?"),
    "moles_to_mass": (r"moles?.*mass", r"mass.*from.*moles?"),
    "mass_percent": (r"mass percent", r"wt ?%", r"weight percent", r"calculate.*percent", r"percent.*mass", r"%"),
    "molarity": (r"molarity", r"moles?.*liter", r"mol/L"),
    "formulation_solver": (r"formulat", r"formulation", r"[0-9]+-[0-9]+-[0-9]+", r"target.*npk", r"fertilizer.*grade", r"تركيبة", r"تركيبه", r"سماد", r"بدون زيادة", r"بدون نقصان", r"خلطة"),
    "npk_grade_from_compounds": (r"\bnpk\b", r"p2o5", r"k2o"),
    "convert_mass": (r"convert.*(?:kg|g|mg|ton|t)" ,),
    "convert_volume": (r"convert.*(?:l|ml|m3)" ,),
    "dilution_c1v1_to_v2": (r"dilution", r"dilute", r"c1.*v1.*v2"),
    "mass_fraction": (r"mass fraction", r"mass percent.*solution"),
    "mixed_composition": (r"mass balance", r"mixed composition", r"blend.*composition"),
}


def classify(text: str) -> Route:
    lowered = text.lower()
    best = None
    best_score = 0
    for tool, patterns in _PATTERNS.items():
        hits = sum(bool(re.search(pattern, lowered)) for pattern in patterns)
        if hits > best_score and get_tool(tool):
            best, best_score = tool, hits
    return Route("tool", best) if best else Route("chat")


def tool_help() -> str:
    return "\n".join(f"{spec.name}: {spec.description}" for spec in list_tools())
