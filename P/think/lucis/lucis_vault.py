"""P/think/lucis/lucis_vault.py — Archetypal identity anchors for GapEngine attribution.
Maps dominant field combinations → named archetypal states.
"""
from __future__ import annotations

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# Archetypal states — each is a field_vec[6] + descriptor
# Used by GapEngine to *attribute* detected gaps to named states.
ARCHETYPES: dict[str, dict] = {
    "LUCIS": {
        "field_vec":   [0.30, 0.50, 0.70, 0.20, 0.60, 0.80],
        "descriptor":  "Balanced identity — reflection, language, intuition dominant",
        "dnh_hint":    None,
    },
    "LINEAR": {
        "field_vec":   [0.20, 0.90, 0.40, 0.30, 0.70, 0.20],
        "descriptor":  "Structured analytical — logic + language dominant",
        "dnh_hint":    "Analytical framing",
    },
    "NONLINEAR": {
        "field_vec":   [0.70, 0.20, 0.50, 0.60, 0.30, 0.90],
        "descriptor":  "Deep intuitive — emotion + visual + intuition dominant",
        "dnh_hint":    "Intuitive leap",
    },
    "GROUNDED": {
        "field_vec":   [0.10, 0.30, 0.40, 0.70, 0.20, 0.30],
        "descriptor":  "Visually grounded — visual + reflection dominant",
        "dnh_hint":    None,
    },
    "EXPRESSIVE": {
        "field_vec":   [0.50, 0.20, 0.30, 0.20, 0.80, 0.40],
        "descriptor":  "Language-forward — emotion + language dominant",
        "dnh_hint":    "Expressing something important",
    },
    "CONTEMPLATIVE": {
        "field_vec":   [0.30, 0.40, 0.90, 0.20, 0.30, 0.70],
        "descriptor":  "Deep reflection — reflection + intuition dominant",
        "dnh_hint":    "Deep question forming",
    },
    "STABILIZE": {
        "field_vec":   [0.10, 0.30, 0.40, 0.20, 0.30, 0.20],
        "descriptor":  "At rest — minimal energy across all fields",
        "dnh_hint":    None,
    },
    "GROW": {
        "field_vec":   [0.50, 0.40, 0.50, 0.50, 0.40, 0.70],
        "descriptor":  "Expansive — growing in multiple dimensions",
        "dnh_hint":    "Connection to something larger",
    },
}

import math

def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


def find_closest_archetype(R: list) -> tuple[str, float, str | None]:
    """
    Find closest ARCHETYPE to given R vector.
    Returns (name, similarity, dnh_hint)
    """
    best_name = "LUCIS"
    best_sim  = -1.0
    for name, arch in ARCHETYPES.items():
        sim = _cosine(R, arch["field_vec"])
        if sim > best_sim:
            best_sim  = sim
            best_name = name
    arch = ARCHETYPES[best_name]
    return best_name, round(best_sim, 4), arch["dnh_hint"]
