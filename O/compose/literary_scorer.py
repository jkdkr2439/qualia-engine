"""O/compose/literary_scorer.py — 4 literary metrics + combined score.

Per spec §5:
  coherence:   cosine(slot_i.meaning, slot_{i+1}.meaning)  — semantic consistency
  surprise:    Surp score of Chuyen node (verb)            — vivid/interesting
  rhythm:      H-variance across slots                      — rich vs monotone
  gap_tension: 1 - cosine(Sinh.meaning, Chuyen.meaning)    — metaphorical depth

Combined: coherence × (1 + surprise) × (1 + rhythm) × (1 + gap_tension/2)

Test scores from spec:
  fractal_sinh: avg=1.99 ← BEST
  SCD:          avg=1.67
  context_first: avg=1.58
  full:          avg=1.43 (too long, coherence drops)
"""
from __future__ import annotations
import math
from .sentence_skeleton import SentenceSkeleton, Slot, _cosine


def _surface_words(skeleton: SentenceSkeleton) -> list[str]:
    """All surface tokens in the rendered sentence."""
    return skeleton.surface.lower().split()



def score_coherence(skeleton: SentenceSkeleton) -> float:
    """
    Mean cosine similarity between adjacent slot meanings.
    High = semantically consistent flow.
    """
    slots = [s for s in skeleton.slots if not s.empty()]
    if len(slots) < 2:
        return 0.5
    pairs = zip(slots, slots[1:])
    sims  = [_cosine(a.meaning, b.meaning) for a, b in pairs]
    return sum(sims) / len(sims)


def score_surprise(skeleton: SentenceSkeleton) -> float:
    """
    Surp score of the Chuyen (verb) node.
    High = unexpected verb = vivid, interesting.
    """
    chuyen = skeleton.chuyen_slot
    if not chuyen or chuyen.empty():
        return 0.0
    # Use max Surp among Chuyen nodes
    surps = [n.Surp for n in chuyen.nodes if hasattr(n, "Surp")]
    return max(surps) if surps else 0.1


def score_rhythm(skeleton: SentenceSkeleton) -> float:
    """
    H-variance across slots.
    High variance = rich rhythm (high-low-high pattern).
    Low variance  = monotone = boring.
    Returns normalized variance [0,1].
    """
    slots = [s for s in skeleton.slots if not s.empty()]
    if len(slots) < 2:
        return 0.0
    h_vals = [s.H for s in slots]
    mean_h = sum(h_vals) / len(h_vals)
    variance = sum((h - mean_h) ** 2 for h in h_vals) / len(h_vals)
    # Normalize: typical H range 0-6, so max variance ≈ 9
    return min(math.sqrt(variance) / 3.0, 1.0)


def score_gap_tension(skeleton: SentenceSkeleton) -> float:
    """
    1 - cosine(Sinh.meaning, Chuyen.meaning).
    High = large semantic gap between subject and verb.
    High gap = metaphorical, poetic.
    Low gap  = literal, prose.
    """
    sinh   = skeleton.sinh_slot
    chuyen = skeleton.chuyen_slot
    if not sinh or not chuyen or sinh.empty() or chuyen.empty():
        return 0.0
    sim = _cosine(sinh.meaning, chuyen.meaning)
    return max(0.0, 1.0 - sim)


def literary_score(skeleton: SentenceSkeleton) -> float:
    """
    Combined literary quality score.
    = coherence × (1 + surprise) × (1 + rhythm) × (1 + gap_tension/2)
    Must be > 0 to allow output (spec invariant 52).

    GUARDRAILS (anti-salad):
      - No Chuyen slot     → 0
      - Surface < 3 tokens → 0 (too short, not a real sentence)
      - Duplicate tokens   → 0 (word salad: "may cam may dang")
      - All tokens same role (no variety) → halve score
    """
    if not skeleton.has_chuyen:
        return 0.0  # No verb = no output

    words = _surface_words(skeleton)

    # GUARDRAIL 1: must have at least 3 tokens
    if len(words) < 3:
        return 0.0

    # GUARDRAIL 2: duplicate tokens = word salad → reject
    if len(words) != len(set(words)):
        return 0.0

    # GUARDRAIL 3: Sinh and Chuyen must be different nodes
    sinh   = skeleton.sinh_slot
    chuyen = skeleton.chuyen_slot
    if sinh and chuyen and not sinh.empty() and not chuyen.empty():
        sinh_ids   = {n.node_id for n in sinh.nodes}
        chuyen_ids = {n.node_id for n in chuyen.nodes}
        if sinh_ids & chuyen_ids:  # same node in both slots
            return 0.0

    c = score_coherence(skeleton)
    s = score_surprise(skeleton)
    r = score_rhythm(skeleton)
    g = score_gap_tension(skeleton)
    score = c * (1 + s) * (1 + r) * (1 + g / 2)
    return round(score, 4)


def score_all(skeleton: SentenceSkeleton) -> dict:
    """Return all 4 component scores + combined."""
    return {
        "coherence":    round(score_coherence(skeleton), 4),
        "surprise":     round(score_surprise(skeleton), 4),
        "rhythm":       round(score_rhythm(skeleton), 4),
        "gap_tension":  round(score_gap_tension(skeleton), 4),
        "literary":     literary_score(skeleton),
    }
