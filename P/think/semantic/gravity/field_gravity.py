"""
P/think/semantic/gravity/field_gravity.py
Updates node.meaning via gravitational pull from field connections.
CRITICAL: node.meaning keys MUST be ODFS field names, NOT field_ids.
"""
from __future__ import annotations
import math
from ..neuron.meaning import normalize_meaning

# Mapping: field_id prefix → ODFS field
# field_id like "field_hello_0" → dominant ODFS field from hub node's meaning
ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
CONTEXT_CAP  = 6   # max entries in context_meanings dict

def _field_id_to_odfs(field_id: str, field_store: dict) -> str:
    """Map a field_id to its dominant ODFS field name."""
    fc = field_store.get(field_id)
    if fc is None: return "language"
    return getattr(fc, "odfs_field", "language")

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    return dot/(na*nb) if na and nb else 0.0

def update_meaning(node, field_store: dict, lr: float,
                   source_weight: float = 1.0,
                   language_boost: dict = None) -> None:
    """
    Gravity pull: each field the node is near adds weight to its ODFS field.

    gravity = |neighbors ∩ field.members| / |node.members|
    node.meaning[odfs_field] += lr * source_weight * (gravity + boost)
    then normalize.
    """
    if language_boost is None:
        language_boost = {}

    node_members = set(node.members) if node.members else set()
    if not node_members:
        return

    for field_id, fc in field_store.items():
        field_members = set(getattr(fc, "members", []))
        if not field_members:
            continue
        shared  = len(node_members & field_members)
        gravity = shared / len(node_members)
        if gravity < 0.01:
            continue
        odfs_field = getattr(fc, "odfs_field", "language")
        if odfs_field not in ODFS_FIELDS:
            odfs_field = "language"
        boost = language_boost.get(odfs_field, 0.0)
        node.meaning[odfs_field] = node.meaning.get(odfs_field, 0.0) \
                                   + lr * source_weight * (gravity + boost)

    normalize_meaning(node.meaning)


# ─── Gap 7: Semantic drift ───────────────────────────────────────────────────

def update_context_meaning(node, dominant_field: str, lr: float = 0.05) -> None:
    """
    Gap 7: Update meaning vector for the current dominant field context.
    Computes semantic_drift = avg angular distance between context pairs.

    node.context_meanings: {field_name → {odfs_f → value}}
    """
    if not hasattr(node, "context_meanings") or node.context_meanings is None:
        node.context_meanings = {}

    curr = node.context_meanings.get(
        dominant_field,
        {f: node.meaning.get(f, 1/6) for f in ODFS_FIELDS}
    )
    updated = {
        f: (1 - lr) * curr.get(f, 0.0) + lr * node.meaning.get(f, 0.0)
        for f in ODFS_FIELDS
    }
    node.context_meanings[dominant_field] = updated

    # Cap at CONTEXT_CAP (drop oldest entry by insertion order)
    if len(node.context_meanings) > CONTEXT_CAP:
        oldest_key = next(iter(node.context_meanings))
        del node.context_meanings[oldest_key]

    # Compute semantic_drift = mean pairwise (1 - cosine)
    vecs = [[v.get(f, 0.0) for f in ODFS_FIELDS]
            for v in node.context_meanings.values()]
    if len(vecs) >= 2:
        pairs = [(vecs[i], vecs[j])
                 for i in range(len(vecs)) for j in range(i+1, len(vecs))]
        dists  = [max(0.0, 1.0 - _cosine(a, b)) for a, b in pairs]
        drift  = sum(dists) / len(dists)
    else:
        drift = 0.0
    node.semantic_drift = min(1.0, drift)  # clamp to [0,1]


# ─── Gap 1: Grounding score ──────────────────────────────────────────────────

def estimate_grounding(node) -> float:
    """
    Gap 1: Heuristic grounding score from node's ODFS meaning.
    0 = abstract/languistic, 1 = concrete/physical.

    High visual + low reflection + low language → concrete.
    """
    v = node.meaning.get("visual", 0.0)
    r = node.meaning.get("reflection", 0.0)
    l = node.meaning.get("language", 0.0)
    g = v * 0.6 + (1.0 - r) * 0.25 + (1.0 - l) * 0.15
    return max(0.0, min(1.0, g))
