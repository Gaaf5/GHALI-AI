"""Equilibrium-engine adapter for GHALI Chemical Intelligence Laboratory.

The lab must never silently pretend that its heuristic model is a full
thermodynamic solver. This adapter makes the engine provenance explicit and
provides a stable seam for IPhreeqc/PHREEQC integration.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import importlib.util

@dataclass(frozen=True)
class EngineCapabilities:
    engine: str
    available: bool
    speciation: bool
    activity_model: str
    saturation_indices: bool
    mineral_equilibrium: bool
    kinetics: bool
    multicomponent: bool
    source: str

class EquilibriumEngine:
    name = "screening_shared_solution"

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            engine=self.name, available=True, speciation=True,
            activity_model="charge-balance + low-I screening; no high-I Davies",
            saturation_indices=True, mineral_equilibrium=False,
            kinetics=True, multicomponent=True,
            source="GHALI engineering screening model",
        )

    def solve(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "fallback",
            "engine": self.name,
            "capabilities": asdict(self.capabilities()),
            "reason": "Advanced PHREEQC/IPhreeqc adapter is not installed; caller must use the existing deterministic screening engine.",
        }


def detect_phreeqc() -> dict[str, Any]:
    """Detect optional Python bindings without importing or requiring them."""
    candidates = ["phreeqpy", "phreeqc"]
    found = [name for name in candidates if importlib.util.find_spec(name) is not None]
    return {
        "available": bool(found),
        "bindings": found,
        "recommended_backend": "IPhreeqc/PHREEQC v3" if found else None,
        "source": "https://www.usgs.gov/software/phreeqc-version-3",
    }


def engine_status() -> dict[str, Any]:
    e = EquilibriumEngine()
    return {"active": asdict(e.capabilities()), "phreeqc": detect_phreeqc()}
