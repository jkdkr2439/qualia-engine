"""P/working/sync.py — P1↔P2 coordinator."""
from __future__ import annotations
import math
from ..think.semantic.neuron.meaning import cosine_meaning

# ── Helpers: handle both DictNode objects AND plain dicts (HardMemory nodes) ──

def _get(node, key, default=None):
    """Get attribute from either a DictNode object or a plain dict."""
    if isinstance(node, dict):
        return node.get(key, default)
    return getattr(node, key, default)

def _set(node, key, value):
    """Set attribute on either a DictNode object or a plain dict."""
    if isinstance(node, dict):
        node[key] = value
    else:
        setattr(node, key, value)

def _get_meaning(node) -> dict:
    """Get meaning dict from either a DictNode or a plain dict node."""
    if isinstance(node, dict):
        m = node.get("meaning", {})
        if not m:
            # Build meaning from ODFS fields stored directly
            fields = ["emotion","logic","reflection","visual","language","intuition"]
            m = {f: node.get(f, 1/6) for f in fields}
        return m
    return getattr(node, "meaning", {})

# ── Core sync functions ───────────────────────────────────────────────────────

def sync_p1_to_p2(node_store: dict) -> dict:
    """Compute P1 state snapshot for P2 tick input."""
    dung = [n for n in node_store.values() if _get(n, "phase") == "Dung"]
    chuy = [n for n in node_store.values() if _get(n, "phase") == "Chuyen"]
    return {"dung_count": len(dung), "chuyen_count": len(chuy)}

def sync_p2_to_p1(p2_result: dict, node_store: dict) -> None:
    """
    P2 state modulates P1 nodes.
    - same phase → resonance boost
    - iam_streak>=3 + Dung → identity grounds nodes
    - p2 Vo → nodes rest slightly
    - Dung nodes → meaning pulled toward p2.meaning
    HardMemory nodes (plain dicts) are handled safely via _get/_set.
    """
    p2_phase   = p2_result.get("phase", "Vo")
    iam_streak = p2_result.get("iam_streak", 0)
    p2_meaning = p2_result.get("meaning", [1/6]*6)
    p2_m_dict  = dict(zip(
        ["emotion","logic","reflection","visual","language","intuition"],
        p2_meaning
    ))

    for node in node_store.values():
        n_phase  = _get(node, "phase", "Vo")
        n_H      = _get(node, "H", 0.0)
        n_Tfield = _get(node, "T_field", 18.0)

        # Resonance boost if P1 and P2 share phase
        if p2_phase in ("Chuyen", "Dung") and n_phase in ("Chuyen", "Dung"):
            boost = 1.15 if n_phase == p2_phase else 1.10
            _set(node, "H", min(n_H * boost, n_Tfield * 3))

        # Identity grounds nodes when P2 is confident
        if iam_streak >= 3 and p2_phase == "Dung":
            _set(node, "H", min(_get(node,"H",0.0) * 1.02, n_Tfield * 3))

        # P2 Vo → light rest
        if p2_phase == "Vo":
            _set(node, "H", _get(node,"H",0.0) * 0.98)

        # Dung nodes: meaning 0.5% pull toward p2.meaning
        if n_phase == "Dung":
            meaning = _get_meaning(node)
            for f, v in p2_m_dict.items():
                meaning[f] = meaning.get(f, 0.0) * 0.995 + v * 0.005
            _normalize_in_place(meaning)
            if isinstance(node, dict):
                node["meaning"] = meaning
            else:
                node.meaning = meaning

def _normalize_in_place(d: dict) -> None:
    fields = ["emotion","logic","reflection","visual","language","intuition"]
    total  = sum(d.get(f, 0) for f in fields)
    if total > 0:
        for f in fields:
            d[f] = d.get(f, 0) / total

def compute_identity_coherence(p2_meaning: list, node_store: dict) -> float:
    """cosine_avg(p2.meaning, P1_Dung_meanings) — NOT stored, always fresh."""
    fields  = ["emotion","logic","reflection","visual","language","intuition"]
    p2_dict = dict(zip(fields, p2_meaning))
    dung    = [n for n in node_store.values() if _get(n, "phase") == "Dung"]
    if not dung:
        return 0.0
    scores = []
    for n in dung:
        m = _get_meaning(n)
        if m:
            scores.append(cosine_meaning(p2_dict, m))
    return sum(scores) / len(scores) if scores else 0.0
