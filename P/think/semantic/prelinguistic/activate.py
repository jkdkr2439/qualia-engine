"""P/think/semantic/prelinguistic/activate.py — Activate primordials against R_weighted."""
from __future__ import annotations
import math
from .build import PreLinguisticPrimordial

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na, nb = math.sqrt(sum(x**2 for x in a)), math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot/(na*nb)

def activate_primordials(R_weighted: list,
                         primordial_store: list,
                         threshold: float = 0.3) -> list[dict]:
    """
    Score all primordials against R_weighted.
    Returns sorted list (centroid_sim DESC) with dnh_hints.
    Feeling match (centroid_sim) prioritized over exact hub match.
    """
    results = []
    for prim in primordial_store:
        if not isinstance(prim, PreLinguisticPrimordial):
            continue
        hub_sim      = _cosine(R_weighted, prim.hub_vec)
        centroid_sim = _cosine(R_weighted, prim.centroid)
        gap_signal   = centroid_sim - hub_sim

        dnh_hint = None
        if gap_signal > 0.02:
            dnh_hint = f"gần như '{prim.name}' nhưng..."
        elif gap_signal < -0.02:
            dnh_hint = f"'{prim.name}' nhưng chưa đầy đủ"

        if centroid_sim >= threshold or hub_sim >= threshold:
            results.append({
                "name":         prim.name,
                "hub_sim":      hub_sim,
                "centroid_sim": centroid_sim,
                "gap_signal":   gap_signal,
                "dnh_hint":     dnh_hint,
                "weight":       prim.weight,
            })

    results.sort(key=lambda x: -x["centroid_sim"])
    return results
