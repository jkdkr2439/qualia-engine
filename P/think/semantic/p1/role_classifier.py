"""P/think/semantic/p1/role_classifier.py — Role learning backed by SQLite.
Classifies Sinh/Dan/Chuyen/Dung/Hoai from corpus positional statistics.
Persists to D/long_term/pete.db > role_positions + nodes.role.
"""
from __future__ import annotations
import sys
from pathlib import Path

_PETE_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(_PETE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PETE_ROOT))

ROLES       = ["Sinh", "Dan", "Chuyen", "Dung", "Hoai"]
T_PRE_VERB  = 0.5
T_MID       = 0.4
T_POST_VERB = 0.5
T_END       = 0.4
T_FIELD     = 3.0
T_SURP      = 0.4

# In-memory caches
_ASSIGNMENTS: dict[str, str] = {}   # node_id → role (hot cache)
_POSITIONS:   dict[str, dict] = {}  # node_id → positional counters (write buffer)
_DB = None
_LOADED = False


def _db():
    global _DB, _LOADED
    if _DB is None:
        from D.db import get_db
        _DB = get_db()
    if not _LOADED:
        _ASSIGNMENTS.update(_DB.load_all_role_assignments())
        _LOADED = True
    return _DB


def record_position(node_id: str, position: str) -> None:
    """Record a positional observation from corpus."""
    _db()
    if node_id not in _POSITIONS:
        _POSITIONS[node_id] = {"pre_verb":0, "post_verb":0, "mid":0, "end":0, "verb":0, "total":0}
    _POSITIONS[node_id][position] = _POSITIONS[node_id].get(position, 0) + 1
    _POSITIONS[node_id]["total"]  = _POSITIONS[node_id].get("total", 0) + 1
    # Write to DB immediately (batched via WAL)
    _db().increment_position(node_id, position)
    # Invalidate cached assignment
    _ASSIGNMENTS.pop(node_id, None)


def classify_node_role(node_id: str, node=None) -> str:
    """Classify node's syntactic role from positional stats → hot cache → DB."""
    # 1. Hot cache
    if node_id in _ASSIGNMENTS:
        return _ASSIGNMENTS[node_id]

    # 2. Load from DB
    db   = _db()
    pos  = db.get_role_positions(node_id)
    total = max(pos.get("total", 0), 1)

    p_pre   = pos.get("pre_verb",  0) / total
    p_mid   = pos.get("mid",       0) / total
    p_post  = pos.get("post_verb", 0) / total
    p_end   = pos.get("end_pos",   0) / total

    if   p_pre  > T_PRE_VERB:  role = "Sinh"
    elif p_mid  > T_MID:       role = "Dan"
    elif p_post > T_POST_VERB: role = "Dung"
    elif p_end  > T_END:       role = "Hoai"
    else:
        H    = getattr(node, "H",    0.0) if node else 0.0
        Surp = getattr(node, "Surp", 0.0) if node else 0.0
        role = "Chuyen" if H >= T_FIELD and Surp > T_SURP else "Sinh"

    # Write back to cache + DB
    _ASSIGNMENTS[node_id] = role
    db.set_node_role(node_id, role)
    return role


def record_sentence(tokens: list[str], verb_indices: list[int]) -> None:
    """Record positional stats from a tokenized sentence."""
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if i in verb_indices:
            record_position(tok, "verb")
            continue
        if verb_indices and i < min(verb_indices):
            if len(verb_indices) > 1 and min(verb_indices) < i < max(verb_indices):
                record_position(tok, "mid")
            else:
                record_position(tok, "pre_verb")
        elif verb_indices and i > max(verb_indices):
            record_position(tok, "end" if i == n - 1 else "post_verb")


def assign_roles_to_nodes(nodes: list, node_store: dict = None) -> None:
    """Assign roles in-place to a list of node objects or dicts."""
    for node in nodes:
        nid = (getattr(node, "node_id", None)
               or (node.get("node_id") if isinstance(node, dict) else None))
        if not nid: continue
        full = (node_store.get(nid) if node_store else None) or node
        role = classify_node_role(nid, full)
        if hasattr(node, "role"):
            node.role = role
        elif isinstance(node, dict):
            node["role"] = role


def save_roles() -> None:
    """Explicit commit (Dream Cycle Stage 5)."""
    if _DB:
        _DB.commit()


def get_store_summary() -> dict:
    from collections import Counter
    return {
        "total_nodes_classified": len(_ASSIGNMENTS),
        "role_distribution": dict(Counter(_ASSIGNMENTS.values())),
        "tracked_positions":  len(_POSITIONS),
    }
