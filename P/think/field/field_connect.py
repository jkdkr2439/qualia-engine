"""P/think/field/field_connect.py — Connect FieldCenters based on 4 conditions."""
from __future__ import annotations
import math

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    if na==0 or nb==0: return 0.0
    return dot/(na*nb)

def should_connect(A, B, ppmi, node_store) -> tuple[bool, float]:
    """
    4 conditions for field connection:
    1. PPMI(A.core, B.core) > 0.5
    2. 0.15 < cosine(A.center, B.center) < 0.85
    3. shared_nodes >= 3
    4. A.stability >= 0.3 AND B.stability >= 0.3
    strength = ppmi * (1-sim) * min(shared/10, 1.0)
    """
    ppmi_score = ppmi.ppmi(A.core_node, B.core_node) if hasattr(ppmi, "ppmi") else 0.0
    if ppmi_score < 0.5: return False, 0.0

    sim = _cosine(A.center, B.center)
    if not (0.15 < sim < 0.85): return False, 0.0

    shared = len(set(A.members) & set(B.members))
    if shared < 3: return False, 0.0

    if getattr(A, "stability", 0) < 0.3 or getattr(B, "stability", 0) < 0.3:
        return False, 0.0

    strength = ppmi_score * (1 - sim) * min(shared/10, 1.0)
    return True, strength

def run_field_connect(node_store: dict, field_store: dict, ppmi) -> list[dict]:
    """
    Run field connection for all field pairs.
    Returns connection report for UI.
    Trigger: explicit call OR Dream Cycle Stage 5 ONLY.
    """
    connections = []
    ids = list(field_store.keys())
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            A = field_store[ids[i]]
            B = field_store[ids[j]]
            ok, strength = should_connect(A, B, ppmi, node_store)
            if ok:
                connections.append({
                    "A": ids[i], "B": ids[j],
                    "strength": round(strength, 4)
                })
    return connections
