from __future__ import annotations
import itertools
from typing import Any, Iterable
from .lab import MATERIALS, resolve, simulate

def combination_count(n: int, levels: Iterable[int], ordered: bool = True, repeats: bool = True) -> int:
    total = 0
    for r in levels:
        if r < 1:
            continue
        if ordered and repeats:
            total += n ** r
        elif ordered:
            total += 0 if r > n else __import__("math").factorial(n) // __import__("math").factorial(n-r)
        elif repeats:
            total += __import__("math").comb(n+r-1, r)
        else:
            total += 0 if r > n else __import__("math").comb(n, r)
    return total

def _iter_level(ids, r, ordered, repeats):
    if ordered and repeats:
        return itertools.product(ids, repeat=r)
    if ordered:
        return itertools.permutations(ids, r)
    if repeats:
        return itertools.combinations_with_replacement(ids, r)
    return itertools.combinations(ids, r)

def iter_combinations(ids: list[str], start: int = 0, levels: Iterable[int] | None = None,
                      ordered: bool = True, repeats: bool = True):
    ids=[resolve(x) for x in ids]
    if not ids or any(x not in MATERIALS for x in ids):
        raise ValueError("All combination materials must exist in the lab catalog.")
    levels=list(levels or range(1,len(ids)+1))
    index=0
    for r in levels:
        for combo in _iter_level(ids,r,ordered,repeats):
            if index >= start:
                yield index, combo
            index += 1

def run_combination_batch(material_ids: list[str], base: dict[str,Any] | None = None,
                          levels: list[int] | None = None, start: int = 0, limit: int = 1000,
                          ordered: bool = True, repeats: bool = True, dose_g: float = 100.0,
                          spacing_s: float = 10.0) -> dict[str,Any]:
    if limit < 1 or limit > 10000:
        raise ValueError("Combination batch limit must be 1..10000.")
    ids=[resolve(x) for x in material_ids]
    if len(ids) < 1 or len(ids) > 24:
        raise ValueError("Select between 1 and 24 candidate materials.")
    if dose_g <= 0 or spacing_s < 0:
        raise ValueError("Dose must be positive and spacing cannot be negative.")
    levels=list(levels or range(1,len(ids)+1))
    total=combination_count(len(ids),levels,ordered,repeats)
    base=dict(base or {})
    base.setdefault("vessel",{"working_volume_l":10})
    base.setdefault("temperature_c",20)
    base.setdefault("rpm",300)
    base.setdefault("duration_s",1200)
    results=[]; next_index=start
    for idx,combo in itertools.islice(iter_combinations(ids,start,levels,ordered,repeats),limit):
        additions=[]
        t=0.0
        if "water" not in combo and resolve(base.get("base_solvent","water")) in MATERIALS:
            solvent=resolve(base.get("base_solvent","water"))
            additions.append({"order":1,"material":solvent,"mass_g":float(base.get("base_solvent_mass_g",1000)),"time_s":0})
            t=spacing_s
        for pos,mid in enumerate(combo,1):
            additions.append({"order":len(additions)+1,"material":mid,"mass_g":float(dose_g),"time_s":t})
            t += spacing_s
        exp={k:v for k,v in base.items() if k not in {"base_solvent","base_solvent_mass_g"}}
        exp["additions"]=additions
        exp["duration_s"]=max(float(exp.get("duration_s",1200)), t)
        try:
            r=simulate(exp)
            results.append({"index":idx,"combination":list(combo),"status":"SIMULATED",
                            "undissolved_g":r["mass_balance"]["undissolved_solids_g"],
                            "dissolved_g":r["mass_balance"]["dissolved_solids_g"],
                            "warnings":len(r["warnings"])})
        except Exception as exc:
            results.append({"index":idx,"combination":list(combo),"status":"ERROR","error":str(exc)})
        next_index=idx+1
    return {"total":total,"start":start,"completed":len(results),"next_start":next_index,
            "remaining":max(0,total-next_index),"ordered":ordered,"repeats":repeats,
            "levels":levels,"results":results}

__all__=["combination_count","iter_combinations","run_combination_batch"]