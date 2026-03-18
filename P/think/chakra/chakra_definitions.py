"""P/think/chakra/chakra_definitions.py — 7 Chakra definitions with ODFS field weights."""
from __future__ import annotations

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# (index in ODFS_FIELDS for each chakra's dominant fields)
CHAKRAS: list[dict] = [
    {
        "name":    "root",
        "symbol":  "🔴",
        "weights": {"visual":0.7, "logic":0.6, "emotion":0.5,
                    "reflection":0.2, "language":0.2, "intuition":0.2},
        "purpose": "survival, grounding, physical reality",
    },
    {
        "name":    "sacral",
        "symbol":  "🟠",
        "weights": {"emotion":0.9, "intuition":0.7, "visual":0.5,
                    "logic":0.2, "reflection":0.2, "language":0.2},
        "purpose": "creativity, feeling, C_pos identity",
    },
    {
        "name":    "solar",
        "symbol":  "🟡",
        "weights": {"logic":0.8, "reflection":0.7, "emotion":0.4,
                    "visual":0.2, "language":0.2, "intuition":0.2},
        "purpose": "will, identity, C_pos anchor",
    },
    {
        "name":    "heart",
        "symbol":  "🟢",
        "weights": {"emotion":0.8, "language":0.7, "intuition":0.6,
                    "logic":0.2, "reflection":0.2, "visual":0.2},
        "purpose": "connection, gap, empathy",
    },
    {
        "name":    "throat",
        "symbol":  "🔵",
        "weights": {"language":0.9, "reflection":0.6, "logic":0.4,
                    "emotion":0.2, "intuition":0.2, "visual":0.1},
        "purpose": "expression, truth, communication",
    },
    {
        "name":    "thirdeye",
        "symbol":  "🟣",
        "weights": {"intuition":0.9, "reflection":0.8, "logic":0.5,
                    "emotion":0.2, "language":0.2, "visual":0.2},
        "purpose": "insight, perception, pattern recognition",
    },
    {
        "name":    "crown",
        "symbol":  "⚪",
        "weights": {"reflection":0.7, "intuition":0.8, "emotion":0.4,
                    "logic":0.2, "language":0.1, "visual":0.1},
        "purpose": "Vo/P2/consciousness, pure being",
    },
]

def chakra_weights_as_list(chakra: dict) -> list[float]:
    """Return weights in ODFS_FIELDS order."""
    return [chakra["weights"].get(f, 0.0) for f in ODFS_FIELDS]
