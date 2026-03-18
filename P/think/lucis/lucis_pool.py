"""P/think/lucis/lucis_pool.py — LucisPool: 4 knowledge checks (Role 2 of lucis_gate).
Checks ODFS report for: consistency, identity coherence, archetype alignment, novelty.
"""
from __future__ import annotations
import math
from .lucis_vault import find_closest_archetype

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def run_pool_checks(
    odfs_world,          # ODFSReport
    odfs_user,           # ODFSReport
    p2_meaning: list,    # P2.meaning[6]
    active_node_meanings: list[list],  # list of meaning vectors from active nodes
    tick_n: int,
) -> dict:
    """
    4 knowledge checks.
    Returns dict: {check_1..4, overall_pass, pool_score}
    """
    R_world = odfs_world.R_final if hasattr(odfs_world, "R_final") else [1/6]*6
    R_user  = odfs_user.R_final  if hasattr(odfs_user,  "R_final") else [1/6]*6

    # ── Check 1: ODFS consistency (world vs user S_combined close) ────────────
    sw = odfs_world.S_combined if hasattr(odfs_world, "S_combined") else 0.5
    su = odfs_user.S_combined  if hasattr(odfs_user,  "S_combined") else 0.5
    consistency_delta = abs(sw - su)
    check_1 = consistency_delta < 0.4  # world/user not too divergent
    check_1_score = max(0.0, 1.0 - consistency_delta / 0.4)

    # ── Check 2: Identity coherence (P2 meaning vs active nodes) ─────────────
    if active_node_meanings:
        coherence = sum(
            _cosine(p2_meaning, nm) for nm in active_node_meanings
        ) / len(active_node_meanings)
    else:
        coherence = 0.5
    check_2 = coherence > 0.1
    check_2_score = coherence

    # ── Check 3: Archetype alignment (R_world fits a known archetype) ─────────
    arch_name, arch_sim, _ = find_closest_archetype(R_world)
    check_3 = arch_sim > 0.3
    check_3_score = arch_sim

    # ── Check 4: Novelty vs base (not pure baseline [1/6]*6) ──────────────────
    baseline = [1/6] * 6
    novelty = 1.0 - _cosine(R_world, baseline)
    check_4 = novelty > 0.05
    check_4_score = min(novelty * 2, 1.0)

    pool_score = (check_1_score + check_2_score + check_3_score + check_4_score) / 4.0
    overall_pass = sum([check_1, check_2, check_3, check_4]) >= 2

    return {
        "check_consistency":  check_1,
        "check_coherence":    check_2,
        "check_archetype":    check_3,
        "check_novelty":      check_4,
        "overall_pass":       overall_pass,
        "pool_score":         round(pool_score, 4),
        "closest_archetype":  arch_name,
        "coherence":          round(coherence, 4),
    }


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)
