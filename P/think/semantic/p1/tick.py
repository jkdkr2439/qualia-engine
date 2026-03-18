"""
P/think/semantic/p1/tick.py — Primordial lifecycle tick per node.
Sinh → Dan → Chuyen → Dung → Hoai → Vo
"""
from __future__ import annotations
from ..neuron.neuron import SemanticNeuron, ODFS_FIELDS, compute_H_tier
from ..neuron.meaning import normalize_meaning
from ..gravity.field_gravity import update_meaning

LR_FIELD = 0.2       # base learning rate for meaning update
DECAY_MEANING = 0.02  # Hoai phase decay per tick

# Gap 4 constants
T_HOAI    = 0.5    # H below this → Hoai candidate
T_DORMANT = 300    # ticks unused before Hoai trigger
SURPRISE_REVIVE = 2.0  # surprise score to revive Hoai node
H_PASSIVE_DECAY = 0.05  # H decay per tick when not active

def _nset(node, attr: str, value):
    """Set attribute on node, handling both SemanticNeuron objects and dict-wrappers."""
    try:
        setattr(node, attr, value)
    except AttributeError:
        try:
            node.__dict__[attr] = value
        except (AttributeError, TypeError):
            pass  # frozen namedtuple or _DictNode — skip

def _nget(node, attr: str, default=0):
    """Get attribute from node, handling both objects and dict-wrappers."""
    try:
        return getattr(node, attr, default)
    except Exception:
        return default


def _tick_dormancy(node: SemanticNeuron, in_active: bool, surprise: float = 0.0) -> None:
    """Gap 3+4: update H_tier, ticks_dormant, and trigger/revive Hoai."""
    dormant = _nget(node, 'ticks_dormant', 0)
    if in_active:
        _nset(node, 'ticks_dormant', 0)
    else:
        _nset(node, 'ticks_dormant', dormant + 1)
        # passive H decay when not activated
        new_H = max(0.0, node.H - H_PASSIVE_DECAY)
        _nset(node, 'H', new_H)

    # Gap 3: update tier
    _nset(node, 'H_tier', compute_H_tier(node.H))

    # Gap 4: Hoai trigger
    hoai_locked = _nget(node, 'hoai_locked', False)
    ticks_d = _nget(node, 'ticks_dormant', 0)
    if (not hoai_locked
            and node.H < T_HOAI
            and ticks_d > T_DORMANT):
        _nset(node, 'hoai_locked', True)

    # Revival: surprise can wake Hoai node
    if _nget(node, 'hoai_locked', False) and surprise >= SURPRISE_REVIVE:
        _nset(node, 'hoai_locked', False)
        _nset(node, 'ticks_dormant', 0)
        _nset(node, 'H', T_HOAI + 0.5)


def primordial_tick(
    symbol:         str,
    neighbors:      list[str],
    node_store:     dict,
    field_store:    dict,
    source_weight:  float = 1.0,
    language_boost: dict  = None,
    p2_iam_streak:  int   = 0,
    p2_awareness:   str   = None,
    p2_phase:       str   = "Vo",
    R_sit:          list  = None,
    surprise:       float = 0.0,    # Gap 4: for Hoai revival
    in_active_set:  bool  = True,   # Gap 4: was this node in active set?
) -> SemanticNeuron:
    """
    Run one primordial tick for a symbol.
    Returns (possibly new) node from node_store.
    """
    if language_boost is None:
        language_boost = {}

    # ── Sinh: create if absent ─────────────────────────────────────────
    if symbol not in node_store:
        node = SemanticNeuron(node_id=symbol, surface_form=symbol)
        node_store[symbol] = node
        node.H = source_weight * 0.5
        node.H_tier = compute_H_tier(node.H)
        return node

    node: SemanticNeuron = node_store[symbol]

    # Gap 3+4: dormancy tick (always runs)
    _tick_dormancy(node, in_active=in_active_set, surprise=surprise)

    if node.phase == "Vo":
        node.H = source_weight * 0.5
        node.H_tier = compute_H_tier(node.H)
        return node

    # Skip further updates if Hoai-locked
    if node.hoai_locked:
        # Hoai: decay meaning
        for f in ODFS_FIELDS:
            node.meaning[f] = max(0.0, node.meaning.get(f, 0.0) - DECAY_MEANING)
        normalize_meaning(node.meaning)
        return node

    # ── Dan: accumulate H ─────────────────────────────────────────────
    if node.phase == "Dan":
        node.H += source_weight
        node.H_tier = compute_H_tier(node.H)
        cluster = hash(frozenset(neighbors))
        if not hasattr(node, "_seen_clusters"):
            node._seen_clusters: set = set()
        if cluster not in node._seen_clusters:
            node._seen_clusters.add(cluster)
            node.enlightenment += 1

    # ── Chuyen: fire ──────────────────────────────────────────────────
    elif node.phase == "Chuyen":
        if neighbors:
            node.members = list(set(node.members) | set(neighbors))
            if p2_awareness == "SENSING":
                node.H += 0.6 * source_weight

    # ── Dung: update meaning via field gravity ─────────────────────────
    elif node.phase == "Dung":
        if field_store:
            dung_boost  = 1 + p2_iam_streak * 0.02
            lr_eff      = LR_FIELD * source_weight * dung_boost
            update_meaning(node, field_store, lr_eff, source_weight, language_boost)
        node.Q = (node.enlightenment > 5)

    # ── Vo reset ────────────────────────────────────────────────────
    if node.H < 0.1 and node.phase not in ("Sinh", "Dan"):
        node.H = 0.0

    return node
