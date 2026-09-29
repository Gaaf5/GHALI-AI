"""Structured thermodynamic/product evidence records for GHALI-TDB.

This is intentionally metadata-first. A value is not considered solver-ready
unless its units, temperature basis, phase/species, source and confidence are
known. Product-grade fertilizer data remain distinct from pure compounds.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class PropertyEvidence:
    material_id: str
    property: str
    value: Any
    units: str
    temperature_c: float | None
    basis: str
    phase: str
    source_id: str
    source_url: str
    confidence: str
    notes: str = ""

@dataclass(frozen=True)
class SpeciesRecord:
    species_id: str
    formula: str
    charge: int
    element_moles: dict[str, float]
    source_id: str
    confidence: str
    notes: str = ""

@dataclass(frozen=True)
class EquilibriumPhase:
    phase_id: str
    formula: str
    log_k_25c: float | None
    reaction: str
    source_id: str
    confidence: str
    notes: str = ""

class GHALITDB:
    def __init__(self):
        self.properties: list[PropertyEvidence] = []
        self.species: dict[str, SpeciesRecord] = {}
        self.phases: dict[str, EquilibriumPhase] = {}

    def add_property(self, record: PropertyEvidence):
        self.properties.append(record)

    def add_species(self, record: SpeciesRecord):
        self.species[record.species_id] = record

    def add_phase(self, record: EquilibriumPhase):
        self.phases[record.phase_id] = record

    def audit(self) -> dict[str, Any]:
        missing=[]
        for p in self.properties:
            if not p.source_id or not p.confidence or not p.units or not p.basis:
                missing.append(asdict(p))
        return {
            "properties": len(self.properties),
            "species": len(self.species),
            "phases": len(self.phases),
            "missing_provenance": missing,
            "ready": not missing,
            "policy": "No solver-critical numeric value enters the TDB without provenance.",
        }


def seed_identity_records(tdb: GHALITDB):
    """Load identity/species records only; no unsupported equilibrium constants."""
    from app.knowledge.chemical_mapping import MAPPINGS
    for material in MAPPINGS.values():
        for comp in material.components:
            tdb.add_species(SpeciesRecord(
                species_id=comp.species,
                formula=comp.species,
                charge=comp.charge,
                element_moles=dict(comp.elements),
                source_id=material.source_id,
                confidence=material.confidence,
                notes=f"Mapped from product material {material.material_id}; identity layer only.",
            ))
    return tdb


def build_seed_tdb() -> GHALITDB:
    db=GHALITDB()
    return seed_identity_records(db)

__all__=["PropertyEvidence","SpeciesRecord","EquilibriumPhase","GHALITDB",
         "seed_identity_records","build_seed_tdb"]
