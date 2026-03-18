"""P/think/chakra/chakra_sequential.py — Approach C: Root→Crown sequential refinement."""
from __future__ import annotations
import math
from .chakra_definitions import CHAKRAS, chakra_weights_as_list, ODFS_FIELDS

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)

def _normalize(v: list) -> list:
    total = sum(v) or 1.0
    return [x/total for x in v]

def chakra_sequential(R_sit: list, passes: int = 3) -> list[float]:
    """
    Approach C: Signal refined passing Root→Crown multiple times.
    Heavy input (fear/survival) → concentrated at Root/Sacral.
    Deep input (why exist?) → rises to Crown.
    Invariant: MEDITATION mode uses chakra_resonance, GAP.TRAVERSE uses this.
    """
    signal = list(R_sit)
    for _ in range(passes):
        for chakra in CHAKRAS:  # Root → Crown
            weights = chakra_weights_as_list(chakra)
            fit = _cosine(signal, weights)
            if fit > 0.3:  # resonance gate — only pass if chakra activates
                # blend signal with chakra field weights scaled by fit
                blended = [0.7*s + 0.3*(w*fit) for s, w in zip(signal, weights)]
                signal  = blended
    return _normalize(signal)
