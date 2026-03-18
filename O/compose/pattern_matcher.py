"""O/compose/pattern_matcher.py — Match best MasterPattern to nodes + compute gap score.
Per spec §12 Step 4: match by field_profile cosine + context_gate filter.
"""
from __future__ import annotations
import math
from .pattern_registry import MasterPattern, get_patterns, ODFS_FIELDS
from .sentence_skeleton import SNode


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


def _node_centroid(nodes: list[SNode]) -> list[float]:
    """Mean ODFS meaning across active nodes."""
    if not nodes: return [1/6]*6
    total = [0.0]*6
    for n in nodes:
        for i, v in enumerate(n.meaning[:6]):
            total[i] += v
    return [x/len(nodes) for x in total]


def match_pattern(
    nodes:        list[SNode],
    context_gate: str,
    R:            list[float],
    language:     str,
) -> tuple[MasterPattern | None, float]:
    """
    Select best MasterPattern from pool filtered by gate + language.
    Score = cosine(pattern.field_profile, node_centroid) * gate_match_bonus.
    Returns (best_pattern, gap_score).
    gap_score = 1 - cosine(node_centroid, pattern.field_profile).
    """
    pool = get_patterns(language, context_gate)
    if not pool:
        return None, 0.0

    centroid = _node_centroid(nodes)

    best_pattern = None
    best_score   = -1.0

    for pat in pool:
        # Field profile match
        profile_sim = _cosine(centroid, pat.field_profile)
        # Bonus if R also matches pattern field profile
        r_sim = _cosine(R, pat.field_profile) if R else 0.0
        combined = profile_sim * 0.6 + r_sim * 0.4
        if combined > best_score:
            best_score   = combined
            best_pattern = pat

    if best_pattern is None:
        return None, 0.0

    gap_score = max(0.0, 1.0 - _cosine(centroid, best_pattern.field_profile))
    return best_pattern, gap_score


def score_against_pattern(
    surface: str,
    pattern: MasterPattern,
    nodes:   list[SNode],
) -> float:
    """
    Judge quality of generated surface vs pattern expectations.
    Simple: cosine(node_centroid, pattern.field_profile) × length_factor.
    """
    if not surface or not pattern: return 0.0
    centroid = _node_centroid(nodes)
    sim = _cosine(centroid, pattern.field_profile)
    # Length factor: reward concise outputs (sparse rhythm wants shorter)
    words = len(surface.split())
    if pattern.rhythm == "sparse":
        length_bonus = 1.0 if words <= 4 else max(0.5, 1.0 - (words-4)*0.05)
    elif pattern.rhythm == "medium":
        length_bonus = 1.0 if 2 <= words <= 8 else 0.8
    else:  # dense
        length_bonus = 1.0 if words >= 4 else 0.8
    return round(sim * length_bonus, 4)
