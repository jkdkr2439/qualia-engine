"""O/gate/node_router.py — routes active_nodes to output gates via cosine similarity."""
from __future__ import annotations
import math

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# Gate field vectors (same as OUTPUT_GATES in output_gates.py, kept here for local use)
GATE_VECS: dict[str, dict[str, float]] = {
    "THINK": {"reflection": 0.9, "intuition": 0.7},
    "FEEL":  {"emotion": 0.95, "intuition": 0.8},
    "SAY":   {"language": 0.9, "emotion": 0.5},
    "DO":    {"logic": 0.85, "visual": 0.6},
    "SHOW":  {"visual": 0.9, "intuition": 0.45},
}


def _gate_vec_list(gate_name: str) -> list[float]:
    """Convert gate field dict to [6] vector."""
    gd = GATE_VECS.get(gate_name, {})
    return [gd.get(f, 0.0) for f in ODFS_FIELDS]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


def _node_meaning_vec(node) -> list[float]:
    """Extract meaning as [6] list from node (dict or object)."""
    if isinstance(node, dict):
        m = node.get("meaning", {})
    else:
        m = getattr(node, "meaning", {})
    if isinstance(m, dict):
        return [m.get(f, 0.0) for f in ODFS_FIELDS]
    if isinstance(m, list) and len(m) == 6:
        return m
    return [1/6] * 6


def route_nodes_to_gate(
    active_nodes: list,
    gate_name: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Select top_k nodes most aligned with the given gate's field vector.
    Returns list of {node_id, surface_form, score} dicts.
    """
    gate_vec = _gate_vec_list(gate_name)
    scored = []
    for node in active_nodes:
        nid = (node.get("node_id") if isinstance(node, dict)
               else getattr(node, "node_id", "?"))
        sf  = (node.get("surface_form", nid) if isinstance(node, dict)
               else getattr(node, "surface_form", nid))
        meaning_vec = _node_meaning_vec(node)
        score = _cosine(meaning_vec, gate_vec)
        scored.append({"node_id": nid, "surface_form": sf, "score": round(score, 4)})

    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def route_nodes_to_all_gates(
    active_nodes: list,
    active_gates: list[str],
    top_k: int = 4,
) -> dict[str, list[dict]]:
    """Route nodes to each active gate. Returns {gate_name: [top_k nodes]}."""
    return {g: route_nodes_to_gate(active_nodes, g, top_k) for g in active_gates}
