"""
I/I_unconscious.py — Void context expansion (I layer).

Role: RECEIVE side only.
  Queries subconscious.db (= void co-occurrence graph) to expand
  LearningEvent context_pairs with background semantic neighbors.
  This expands what Pete *receives* from the user's input.

  ⚠️  NOT for output word surfacing — that is P layer's SubconsciousLayer role.
  ⚠️  NOT Pete's internal state — P/think/subconscious.py handles that.

Weight: SUB_WEIGHT = 0.15 → void contributions are 15% of attention.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

SUBCON_DB   = Path(__file__).parent.parent / "P" / "HardMemory" / "subconscious.db"
SUB_WEIGHT  = 0.15   # tiềm thức ít attention hơn
TOP_K       = 5      # top-5 neighbors per input word

_CONN: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        if not SUBCON_DB.exists():
            return None
        _CONN = sqlite3.connect(str(SUBCON_DB), check_same_thread=False)
        _CONN.execute("PRAGMA journal_mode=WAL")
    return _CONN


def query_neighbors(word: str, top_k: int = TOP_K) -> list[str]:
    """
    Query subconscious.db for top-k semantic neighbors of `word`.
    Returns list of neighbor words (empty if word not in map).
    """
    conn = _get_conn()
    if conn is None:
        return []
    try:
        # Get word id
        row = conn.execute(
            "SELECT id FROM vocab WHERE word=?", (word,)
        ).fetchone()
        if not row:
            return []
        wid = row[0]
        # Get top-k neighbors by edge weight
        rows = conn.execute("""
            SELECT v.word FROM edges e
            JOIN vocab v ON v.id = e.dst
            WHERE e.src=?
            ORDER BY e.weight DESC LIMIT ?
        """, (wid, top_k)).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def expand_context(
    symbols: list[str],
    existing_pairs: list[tuple[str,str]],
    top_k: int = TOP_K,
) -> list[tuple[str,str]]:
    """
    Expand context_pairs with subconscious neighbors.
    Only adds pairs NOT already in existing_pairs.
    Returns ADDITIONAL pairs (not duplicating existing).

    These should be tagged at lower weight by p_engine.
    """
    existing_set = set(existing_pairs)
    new_pairs = []
    for sym in symbols:
        neighbors = query_neighbors(sym, top_k)
        for nb in neighbors:
            pair = (sym, nb)
            if pair not in existing_set:
                new_pairs.append(pair)
                existing_set.add(pair)
    return new_pairs


def get_subconscious_field_signal(symbols: list[str]) -> list[float]:
    """
    Compute a 6D ODFS field signal from subconscious neighbors.
    Used in p_engine to blend R_weighted with tiềm thức signal.

    Strategy: get all neighbors → look up their meaning in subconscious
    (uses edge weights as proxy for field presence).
    Returns [6] normalized vector or [1/6]*6 if unavailable.
    """
    conn = _get_conn()
    if conn is None:
        return [1/6] * 6

    # Aggregate edge weights per neighbor cluster
    # Simple proxy: neighbor count weighted by edge weight
    # We return uniform — actual field gravity is done in p_engine
    # from node.meaning, not from subconscious directly.
    # This is intentionally minimal: subconscious expands *context*,
    # not meaning vectors.
    return [1/6] * 6


def is_available() -> bool:
    """Check if subconscious.db is accessible."""
    return SUBCON_DB.exists() and _get_conn() is not None
