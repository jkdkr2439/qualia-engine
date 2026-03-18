"""O/gate/output_gates.py — FIXED gate definitions. NEVER learned, NEVER drift."""
from __future__ import annotations
import math

ODFS_FIELDS = ["emotion","logic","reflection","visual","language","intuition"]

OUTPUT_GATES = {
    # INNER GATES (always fire)
    "THINK": {"emotion":0.0,  "logic":0.0,  "reflection":0.9, "visual":0.0, "language":0.0, "intuition":0.7},
    "FEEL":  {"emotion":0.95, "logic":0.0,  "reflection":0.0, "visual":0.0, "language":0.0, "intuition":0.8},
    # OUTER GATES (conditional)
    "SAY":   {"emotion":0.5,  "logic":0.0,  "reflection":0.0, "visual":0.0, "language":0.9, "intuition":0.0},
    "DO":    {"emotion":0.0,  "logic":0.85, "reflection":0.0, "visual":0.6, "language":0.0, "intuition":0.0},
    "SHOW":  {"emotion":0.0,  "logic":0.0,  "reflection":0.0, "visual":0.9, "language":0.0, "intuition":0.45},
}

MODALITY_TO_OUTER = {
    "chat":   ["SAY"],
    "voice":  ["SAY"],
    "action": ["DO", "SAY"],
    "visual": ["SHOW", "SAY"],
}

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a)) or 1.0
    nb  = math.sqrt(sum(y**2 for y in b)) or 1.0
    return dot/(na*nb)

def select_active_gates(modality: str = "chat") -> list[str]:
    """THINK + FEEL always. Outer based on modality."""
    outer = MODALITY_TO_OUTER.get(modality, ["SAY"])
    return ["THINK", "FEEL"] + outer

def route_nodes_to_gates(active_nodes: list, active_gates: list) -> dict:
    """
    Same nodes → different subset per gate.
    cosine(node.meaning, gate_vec) → top-5 per gate.
    """
    routed = {}
    for gate_name in active_gates:
        g_vec = [OUTPUT_GATES[gate_name].get(f,0) for f in ODFS_FIELDS]
        scored = [(n, _cosine([n.meaning.get(f,0) for f in ODFS_FIELDS], g_vec))
                  for n in active_nodes]
        scored.sort(key=lambda x: -x[1])
        routed[gate_name] = [n for n, _ in scored[:5]]
    return routed
