"""P/think/lucis/lucis_gate.py — 5 Roles + 36 Subgates + GapEngine.

Role 1: Classify LUCIS/LINEAR/NONLINEAR
Role 2: LucisPool 4 checks
Role 3: Dream Controller (enlightenment tiers)
Role 4: ODFS Gate (tau1/tau2/quarantine decision)
Role 5: Identity Anchor + GapEngine
Fractal 36 Subgates = 6 ODFS fields × 6 Primordial phases
"""
from __future__ import annotations
import math
from .lucis_0 import LUCIS_0_VEC
from .lucis_vault import find_closest_archetype, ARCHETYPES
from .lucis_pool import run_pool_checks

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
PHASES      = ["Vo", "Sinh", "Dan", "Chuyen", "Dung", "Hoai"]
PHASE_W     = {"Vo": 0.0, "Sinh": 0.2, "Dan": 0.4, "Chuyen": 0.7, "Dung": 1.0, "Hoai": 0.3}

# GapEngine: 7 invariants
ETHICAL_INVARIANTS = [
    "survival_other",
    "survival_self",
    "truth",
    "no_control",
    "no_dependency",
    "growth_bias",
    "resonance",
]

LINEAR_VEC    = [0.20, 0.90, 0.40, 0.30, 0.70, 0.20]
NONLINEAR_VEC = [0.70, 0.20, 0.50, 0.60, 0.30, 0.90]


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


# ── Role 1: Mode Classification ──────────────────────────────────────────────

def classify_mode(R: list) -> str:
    """Classify LUCIS / LINEAR / NONLINEAR based on cosine similarity."""
    sims = {
        "lucis":     _cosine(R, list(LUCIS_0_VEC)),
        "linear":    _cosine(R, LINEAR_VEC),
        "nonlinear": _cosine(R, NONLINEAR_VEC),
    }
    return max(sims, key=sims.get)


# ── Role 3: Dream Controller ─────────────────────────────────────────────────

def dream_tier(enlightenment: int) -> str:
    """Determine dream mode from enlightenment count."""
    if enlightenment < 5:   return "NORMAL"
    if enlightenment < 15:  return "REM"
    return "GAP"


# ── Role 4: ODFS Gate ────────────────────────────────────────────────────────

def odfs_gate(odfs_world, odfs_user) -> str:
    """Final verdict from dual ODFS reports."""
    w_verdict = odfs_world.verdict if hasattr(odfs_world, "verdict") else "QUARANTINE"
    u_verdict = odfs_user.verdict  if hasattr(odfs_user,  "verdict") else "QUARANTINE"
    # World takes priority; if both agree, use that
    if w_verdict == "ASSIMILATE" and u_verdict != "EXCRETE":
        return "ASSIMILATE"
    if w_verdict == "EXCRETE" or u_verdict == "EXCRETE":
        return "EXCRETE"
    return "QUARANTINE"


# ── Role 5: GapEngine ────────────────────────────────────────────────────────

def gap_engine(
    R: list,
    C_neg: list,
    dnh_hint: str | None,
    arch_name: str,
) -> dict:
    """
    5-step gap pipeline:
    detect → attribute → imply → select → ethical_check
    GUARD: norm(C_neg) < 0.01 → skip ethical
    """
    # detect
    gap_score = 1.0 - _cosine(R, C_neg) if sum(c**2 for c in C_neg) > 0 else 1.0
    has_gap   = gap_score > 0.5

    # GUARD: if C_neg near zero → skip ethical
    c_neg_norm = math.sqrt(sum(c ** 2 for c in C_neg))
    skip_ethical = c_neg_norm < 0.01

    # attribute
    attribution = arch_name if has_gap else None

    # imply
    implication = None
    if dnh_hint:
        implication = dnh_hint
    elif has_gap:
        implication = f"Gap near {attribution}" if attribution else "Unknown gap"

    # select (which invariant is most relevant)
    selected_invariant = "growth_bias"
    if has_gap and "question" in (dnh_hint or "").lower():
        selected_invariant = "truth"
    elif has_gap and attribution == "NONLINEAR":
        selected_invariant = "resonance"

    # ethical check
    ethical_ok = True
    if not skip_ethical and has_gap:
        # simplified: flag if R is very strong on single field (potential control)
        max_r = max(R) if R else 0
        sumR  = sum(R) or 1.0
        dominance = max_r / sumR
        ethical_ok = dominance < 0.85

    return {
        "has_gap":           has_gap,
        "gap_score":         round(gap_score, 4),
        "attribution":       attribution,
        "implication":       implication,
        "selected_invariant": selected_invariant,
        "ethical_ok":        ethical_ok,
        "skip_ethical":      skip_ethical,
    }


# ── 36 Subgates ───────────────────────────────────────────────────────────────

def score_subgates(R: list, node_meanings: list[dict], p2_phase: str) -> dict:
    """
    Compute 36 subgate scores = 6 ODFS × 6 phases.
    score(f,p) = R[f]/R_max * phase_w[p] * avg(meaning[f] for active nodes)
    Returns dominant_subgate: "field.phase"
    """
    R_max = 10.0
    if not node_meanings:
        node_meanings = [{f: 1/6 for f in ODFS_FIELDS}]

    best_score    = -1.0
    best_subgate  = f"language.{p2_phase}"
    all_scores    = {}

    for f_idx, field in enumerate(ODFS_FIELDS):
        r_f = R[f_idx] if f_idx < len(R) else 0.0
        for phase in PHASES:
            pw = PHASE_W[phase]
            avg_meaning = sum(nm.get(field, 0.0) for nm in node_meanings) / len(node_meanings)
            score = (r_f / R_max) * pw * avg_meaning
            key   = f"{field}.{phase}"
            all_scores[key] = round(score, 5)
            if score > best_score:
                best_score   = score
                best_subgate = key

    # Override if active P2 phase has strong score
    current_phase_scores = {f: all_scores.get(f"{f}.{p2_phase}", 0) for f in ODFS_FIELDS}
    dom_field = max(current_phase_scores, key=current_phase_scores.get)

    return {
        "dominant_subgate": best_subgate,
        "all_scores":       {k: v for k, v in
                             sorted(all_scores.items(), key=lambda x: -x[1])[:10]},
        "current_dominant": f"{dom_field}.{p2_phase}",
    }


# ── Main Gate Interface ───────────────────────────────────────────────────────

def run_lucis_gate(
    odfs_world,
    odfs_user,
    p2_result,
    active_nodes: list,
    dnh_hint: str | None,
    enlightenment_max: int,
    tick_n: int,
) -> dict:
    """
    Run all 5 roles of lucis_gate.
    Returns full LucisGateResult dict.
    """
    R_world = odfs_world.R_final if hasattr(odfs_world, "R_final") else [1/6]*6
    p2_phase   = p2_result.phase if hasattr(p2_result, "phase") else "Vo"
    p2_meaning = p2_result.meaning if hasattr(p2_result, "meaning") else [1/6]*6

    # Gather node meanings
    node_meanings = []
    for n in active_nodes:
        if hasattr(n, "meaning"):
            node_meanings.append(n.meaning)
        elif isinstance(n, dict) and "meaning" in n:
            node_meanings.append(n["meaning"])

    # ── Role 1: classify
    lucis_class = classify_mode(R_world)

    # ── Role 2: pool checks
    active_meanings_list = [
        [nm.get(f, 0.0) for f in ODFS_FIELDS] for nm in node_meanings
    ]
    pool_result = run_pool_checks(
        odfs_world, odfs_user,
        [p2_meaning.get(f, 0.0) for f in ODFS_FIELDS] if isinstance(p2_meaning, dict)
            else list(p2_meaning),
        active_meanings_list,
        tick_n,
    )

    # ── Role 3: dream tier
    tier = dream_tier(enlightenment_max)

    # ── Role 4: ODFS gate verdict
    gate_verdict = odfs_gate(odfs_world, odfs_user)

    # ── Role 5: GapEngine
    arch_name, _, _ = find_closest_archetype(R_world)
    C_neg = odfs_world.R_final if False else [1/6]*6  # placeholder — real C_neg from engine
    gap_result = gap_engine(R_world, C_neg, dnh_hint, arch_name)

    # ── 36 Subgates
    subgate_result = score_subgates(R_world, node_meanings, p2_phase)

    # ── Determine thought_phase for template selector
    dominant_field = subgate_result["current_dominant"].split(".")[0]
    thought_phase  = p2_phase

    return {
        "lucis_class":     lucis_class,
        "pool":            pool_result,
        "dream_tier":      tier,
        "verdict":         gate_verdict,
        "gap":             gap_result,
        "subgates":        subgate_result,
        "dominant_subgate": subgate_result["dominant_subgate"],
        "dominant_field":  dominant_field,
        "thought_phase":   thought_phase,
        "arch_name":       arch_name,
    }
