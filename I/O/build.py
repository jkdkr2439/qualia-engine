"""I/O/build.py — Symbol verification + LearningEvent construction.
Implements full L(n) formula for symbol worthiness.

L(n) = freq^0.5 × CF^1.0 × D^0.8 × (1+Surp)^0.3 × source_weight
Verify: L(n) > theta_L=1.5 AND coherence > theta_coh=0.1
"""
from __future__ import annotations
import math
from collections import Counter

THETA_L   = 1.5   # minimum symbol learning score
THETA_COH = 0.1   # minimum coherence threshold


def _freq_score(token: str, freq_map: dict[str, int]) -> float:
    """Observed frequency of token in corpus so far."""
    return freq_map.get(token, 1)


def _context_frequency(token: str, context_pairs: list[tuple]) -> float:
    """CF = number of unique context clusters this token appears in."""
    contexts = set(c for c, n in context_pairs if n == token)
    contexts |= set(n for c, n in context_pairs if c == token)
    return max(1.0, len(contexts))


def _diversity(token: str, context_pairs: list[tuple]) -> float:
    """D = 1 - (max_context_freq / total_context_freq)."""
    all_ctxs = [c for c, n in context_pairs if n == token]
    all_ctxs += [n for c, n in context_pairs if c == token]
    if not all_ctxs:
        return 0.5
    counts = Counter(all_ctxs)
    total  = sum(counts.values())
    max_f  = max(counts.values())
    return 1.0 - (max_f / total)


def _surprise(token: str, freq_map: dict[str, int], total_tokens: int) -> float:
    """Surp = -log P(token) where P = freq/total."""
    freq  = freq_map.get(token, 1)
    p     = freq / max(total_tokens, 1)
    return -math.log(max(p, 1e-9))


def _coherence(token: str, context_pairs: list[tuple]) -> float:
    """
    Coherence = how consistently this token appears with others.
    Simple: ratio of bidirectional context pairs.
    """
    forward  = [(c, n) for c, n in context_pairs if c == token]
    backward = [(c, n) for c, n in context_pairs if n == token]
    if not (forward or backward):
        return 0.0
    total_ctx = len(forward) + len(backward)
    return min(1.0, total_ctx / 5.0)   # saturates at 5 pairs


def compute_L(
    token:         str,
    freq_map:      dict[str, int],
    context_pairs: list[tuple],
    total_tokens:  int,
    source_weight: float = 1.0,
) -> tuple[float, dict]:
    """
    Compute full L(n) score for a token.
    Returns (score, components_dict).
    """
    freq = _freq_score(token, freq_map)
    CF   = _context_frequency(token, context_pairs)
    D    = _diversity(token, context_pairs)
    Surp = _surprise(token, freq_map, total_tokens)
    coh  = _coherence(token, context_pairs)

    score = (
        math.pow(freq, 0.5) *
        math.pow(CF,   1.0) *
        math.pow(max(D, 0.01), 0.8) *
        math.pow(1 + Surp, 0.3) *
        source_weight
    )

    return score, {
        "freq": freq, "CF": CF, "D": round(D, 4),
        "Surp": round(Surp, 4), "coherence": round(coh, 4),
        "score": round(score, 4),
    }


def verify_symbol(
    token:         str,
    freq_map:      dict[str, int],
    context_pairs: list[tuple],
    total_tokens:  int,
    source_weight: float = 1.0,
) -> tuple[bool, float, dict]:
    """
    Check if symbol passes L(n) > theta_L AND coherence > theta_coh.
    Returns (passes, score, components).
    """
    score, comps = compute_L(token, freq_map, context_pairs, total_tokens, source_weight)
    passes = score > THETA_L and comps["coherence"] > THETA_COH
    return passes, score, comps


def build_verified_symbols(
    tokens:        list[str],
    context_pairs: list[tuple],
    total_tokens:  int,
    source_weight: float = 1.0,
) -> list[str]:
    """
    From a list of candidate tokens, return only those passing verification.
    Updates internal freq_map as it processes.
    """
    freq_map = Counter(tokens)
    verified = []
    for tok in tokens:
        passes, score, _ = verify_symbol(
            tok, freq_map, context_pairs, total_tokens, source_weight
        )
        if passes:
            verified.append(tok)
    # If nothing verified (fresh Pete with no history), return all non-empty
    return verified if verified else [t for t in tokens if t]
