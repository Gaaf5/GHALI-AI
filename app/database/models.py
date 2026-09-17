from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RawMaterial:
    name: str
    n_pct: float = 0.0
    p2o5_pct: float = 0.0
    k2o_pct: float = 0.0
    moisture_pct: Optional[float] = None
    assay_pct: Optional[float] = None
    source: str = "project"
    active: bool = True

    def composition(self) -> dict[str, float]:
        factor = 1.0 if self.assay_pct is None else self.assay_pct / 100.0
        return {
            "N": self.n_pct * factor,
            "P2O5": self.p2o5_pct * factor,
            "K2O": self.k2o_pct * factor,
        }


@dataclass(frozen=True)
class ProductionOrder:
    order_no: str
    product_grade: str
    batch_kg: float
    status: str = "draft"


@dataclass(frozen=True)
class LabResult:
    order_no: str
    n_pct: float
    p2o5_pct: float
    k2o_pct: float
    sample_id: str = ""
