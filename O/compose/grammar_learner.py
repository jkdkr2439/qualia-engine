"""O/compose/grammar_learner.py — GRAMMAR_STORE backed by SQLite (pete.db).
Per spec §6: reinforce winning structure, decay unused, persist via D/db.py.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Ensure Pete root on path for D.db import
_PETE_ROOT = Path(__file__).parent.parent.parent
if str(_PETE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PETE_ROOT))

DECAY_RATE   = 0.99
MAX_HISTORY  = 50

# In-memory cache on top of DB (avoid DB hit per tick)
_CACHE: dict[str, list[float]] = {}
_DIRTY = False
_DB = None

def _db():
    global _DB
    if _DB is None:
        from D.db import get_db
        _DB = get_db()
        # Bootstrap cache from DB
        _CACHE.update(_DB.get_grammar_scores())
    return _DB


def reinforce(structure_type: str, score: float) -> None:
    """Add score to winning structure."""
    global _DIRTY
    _db()
    if structure_type not in _CACHE:
        _CACHE[structure_type] = []
    _CACHE[structure_type].append(score)
    if len(_CACHE[structure_type]) > MAX_HISTORY:
        _CACHE[structure_type] = _CACHE[structure_type][-MAX_HISTORY:]
    # Write to DB
    _db().add_grammar_score(structure_type, score)
    _DIRTY = True


def decay_unused(winner: str) -> None:
    """Decay scores for all structures except winner."""
    global _DIRTY
    for stype in list(_CACHE.keys()):
        if stype != winner:
            _CACHE[stype] = [s * DECAY_RATE for s in _CACHE[stype]]
            _CACHE[stype] = [s for s in _CACHE[stype] if s > 0.01]
    _DIRTY = True


def avg_score(structure_type: str) -> float:
    _db()
    scores = _CACHE.get(structure_type, [])
    if not scores: return 0.0
    return sum(scores) / len(scores)


def bias_score(base_score: float, structure_type: str) -> float:
    avg = avg_score(structure_type)
    return base_score * (1 + avg * 0.1)


def generation_cycle(
    active_snodes: list,
    language: str,
    rng,
    dnh_hint: str | None = None,
    auto_save_every: int = 20,
) -> tuple[str, str, float]:
    """
    Full generation cycle (spec §6).
    Returns (surface_text, structure_type, literary_score).
    """
    _db()
    from .variant_generator import generate_variants
    from .literary_scorer   import literary_score as score_fn

    variants = generate_variants(active_snodes, language=language, rng=rng)
    if not variants:
        return "", "none", 0.0

    scored = []
    for stype, skeleton in variants:
        base   = score_fn(skeleton)
        biased = bias_score(base, stype)
        scored.append((biased, base, stype, skeleton))

    scored.sort(key=lambda x: -x[0])

    # Invariant 52: literary_score > 0
    valid = [(bi, ba, st, sk) for bi, ba, st, sk in scored if ba > 0]
    if not valid:
        return "", "none", 0.0

    best_biased, best_base, best_type, best_sk = valid[0]

    reinforce(best_type, best_base)
    decay_unused(best_type)

    # Auto-save to DB every N reinforcements
    total = sum(len(v) for v in _CACHE.values())
    if total % auto_save_every == 0:
        save_store()

    surface = best_sk.surface
    if dnh_hint and len(dnh_hint) > 3:
        surface = surface + "... " + dnh_hint

    return surface.strip(), best_type, best_base


def save_store() -> None:
    """Flush to DB + prune old scores."""
    global _DIRTY
    db = _db()
    db.prune_grammar_scores(keep_last=MAX_HISTORY)
    db.commit()
    _DIRTY = False


def get_store_summary() -> dict:
    _db()
    return {
        stype: {
            "count": len(scores),
            "avg":   round(sum(scores)/len(scores), 4) if scores else 0.0,
            "best":  round(max(scores), 4) if scores else 0.0,
        }
        for stype, scores in _CACHE.items()
    }
