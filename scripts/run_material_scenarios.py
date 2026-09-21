from __future__ import annotations

import json
from pathlib import Path

from app.tools.lab import MATERIALS, simulate

OUT = Path("data/lab_scenarios/material_scenarios.jsonl")
SCENARIOS_PER_MATERIAL = 100


def make_case(material: str, i: int) -> dict:
    temps = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
    rpms = [100, 200, 300, 450, 600, 750, 900, 1100, 1400, 1800]
    times = [5, 10, 20, 30, 60, 120, 300, 600, 1200, 2400]
    volumes = [1, 2, 5, 10, 20, 50, 100, 250, 500, 1000]
    masses = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500]
    row, col = divmod(i, 10)
    return {
        "name": f"AUTO-{material}-{i+1:03d}",
        "working_volume_l": volumes[row],
        "temperature_c": temps[col],
        "rpm": rpms[(row * 3 + col) % 10],
        "duration_s": times[(row + 2 * col) % 10],
        "additions": [{"material": material, "mass_g": masses[(2 * row + col) % 10], "addition_time_s": 0}],
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    status_counts: dict[str, int] = {}
    material_counts: dict[str, int] = {}
    with OUT.open("w", encoding="utf-8") as fh:
        for material in MATERIALS:
            material_counts[material] = 0
            for i in range(SCENARIOS_PER_MATERIAL):
                case = make_case(material, i)
                result = simulate(case)
                fh.write(json.dumps({"input": case, "result": result}, ensure_ascii=False, separators=(",", ":")) + "\n")
                total += 1
                material_counts[material] += 1
                key = str(result.get("status", "OK"))
                status_counts[key] = status_counts.get(key, 0) + 1
    summary = {
        "materials": len(MATERIALS),
        "scenarios_per_material": SCENARIOS_PER_MATERIAL,
        "total_scenarios": total,
        "status_counts": status_counts,
        "material_counts": material_counts,
        "output": str(OUT),
        "note": "Synthetic screening scenarios; not experimental validation or production truth.",
    }
    Path("data/lab_scenarios/material_scenarios_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
