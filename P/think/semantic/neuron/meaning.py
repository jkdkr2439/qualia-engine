"""P/think/semantic/neuron/meaning.py — Helper: normalize meaning dict."""
from __future__ import annotations
from .neuron import ODFS_FIELDS

def normalize_meaning(meaning: dict) -> dict:
    """Ensure sum(meaning.values()) == 1.0, all ODFS keys present."""
    for f in ODFS_FIELDS:
        meaning.setdefault(f, 0.0)
    total = sum(meaning[f] for f in ODFS_FIELDS)
    if total > 0:
        for f in ODFS_FIELDS:
            meaning[f] /= total
    else:
        for f in ODFS_FIELDS:
            meaning[f] = 1/6
    return meaning

def init_meaning() -> dict:
    return {f: 1/6 for f in ODFS_FIELDS}

def cosine_meaning(a: dict, b: dict) -> float:
    import math
    dot = sum(a.get(f,0)*b.get(f,0) for f in ODFS_FIELDS)
    na  = math.sqrt(sum(a.get(f,0)**2 for f in ODFS_FIELDS))
    nb  = math.sqrt(sum(b.get(f,0)**2 for f in ODFS_FIELDS))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)
