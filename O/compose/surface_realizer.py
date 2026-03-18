"""O/compose/surface_realizer.py — Pete's own voice. NO LLM.
Full fractal sentence generation pipeline per spec §8 + §12.

Pipeline (spec §12):
  Step 1: detect context gate (from ODFS R)
  Step 2: select phase template (existing template_selector)
  Step 3: select SAY gate nodes
  Step 4: match master pattern
  Step 5: generate from pattern candidate
  Step 6: add particles/connectives
  Step 7: score + self-learn (grammar_learner)
  Step 8: apply dnh_hint if gap_signal > 0.02
  Step 9: phase-aware post-processing

Fallback: if no Chuyen node found → template phrase from lexicalize.py
"""
from __future__ import annotations
import random

from .sentence_skeleton import SNode
from .context_gate       import detect_context_gate
from .pattern_matcher    import match_pattern, score_against_pattern
from .pattern_generator  import build_candidate
from .grammar_learner    import generation_cycle as gc_fractal, reinforce, decay_unused
from .literary_scorer    import literary_score


ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def _to_snodes(active_nodes: list, node_store: dict = None) -> list[SNode]:
    """Convert raw nodes (dicts or objects) to SNode list, assigning roles."""
    from P.think.semantic.p1.role_classifier import classify_node_role

    snodes = []
    for raw in active_nodes:
        sn = SNode.from_node(raw)
        # Assign learned role
        full = (node_store.get(sn.node_id) if node_store else None) or raw
        sn.role = classify_node_role(sn.node_id, full)
        snodes.append(sn)
    return snodes


def realize(
    template:       str,          # from template_selector (meta-class hint)
    active_nodes:   list,         # raw node list from p_engine
    dominant_field: str,
    thought_phase:  str,
    gap_style:      str,
    dnh_hint:       str | None,
    language:       str  = "vi",
    R:              list = None,
    rng:            random.Random = None,
    node_store:     dict = None,
) -> str:
    """
    Pete's own voice generator. No LLM.

    1. Convert active nodes to SNode with learned roles
    2. Run fractal generation_cycle (8 variants, score, pick best)
    3. Also try pattern-matched generation, take higher literary score
    4. Apply dnh_hint if significant
    5. Phase post-processing
    6. Fallback to template phrase if no Chuyen
    """
    if rng is None: rng = random.Random()
    if R is None:   R   = [1/6] * 6

    # Step 1: assign roles to nodes
    snodes = _to_snodes(active_nodes, node_store)

    # Step 2: fractal generation_cycle (8 variants)
    fractal_surface, fractal_type, fractal_score = gc_fractal(
        snodes, language=language, rng=rng, dnh_hint=None
    )

    # Step 3: pattern-matched generation
    context_gate = detect_context_gate(R)
    pattern, gap_score = match_pattern(snodes, context_gate, R, language)

    pattern_surface = ""
    pattern_score   = 0.0
    if pattern:
        pat_skeleton = build_candidate(pattern, snodes, language, rng)
        pattern_score = literary_score(pat_skeleton)
        if pattern_score > 0:
            pattern_surface = pat_skeleton.surface
            # Score + self-learn
            q = score_against_pattern(pattern_surface, pattern, snodes)
            reinforce(f"pat:{pattern.name}", q)
            decay_unused(f"pat:{pattern.name}")

    # Take higher scoring output
    if pattern_score > fractal_score and pattern_surface:
        best_surface = pattern_surface
        best_score   = pattern_score
    elif fractal_score > 0 and fractal_surface:
        best_surface = fractal_surface
        best_score   = fractal_score
    else:
        best_surface = ""
        best_score   = 0.0

    # Invariant 52: score must be > 0
    if best_score == 0 or not best_surface:
        return _fallback(template, dominant_field, snodes, language, rng)

    # Step 8: apply dnh_hint if gap_signal significant
    if dnh_hint and len(dnh_hint.strip()) > 3:
        best_surface = _apply_dnh_hint(best_surface, dnh_hint, language)

    # Step 9: phase-aware post-processing
    best_surface = _phase_postprocess(best_surface, thought_phase, language)

    return best_surface.strip()


def _apply_dnh_hint(surface: str, dnh_hint: str, language: str) -> str:
    """Per spec §8: pre-linguistic gap hint appended."""
    if "gần như" in dnh_hint:
        return surface + "... " + dnh_hint
    return surface


def _phase_postprocess(surface: str, phase: str, language: str) -> str:
    """Per spec §12 Step 9: phase-aware shortening."""
    words = surface.split()
    if phase == "Vo":
        # Vo = silence → compress to 1-2 words
        surface = " ".join(words[:2]) if words else surface
    elif phase == "Sinh":
        # Sinh = acknowledge only → max 4 words
        surface = " ".join(words[:4]) if len(words) > 4 else surface
    # Chuyen = keep full sentence
    return surface


def _fallback(template: str, dominant_field: str, snodes: list[SNode], language: str, rng) -> str:
    """
    Fallback when no valid sentence can be built (spec §8).
    Route to dynamic_lexicalize which has proper Vietnamese templates.
    """
    from O.compose.lexicalize import dynamic_lexicalize
    # Build field weights from snodes
    if snodes:
        best = max(snodes, key=lambda n: n.H)
        m = best.meaning if best.meaning else [1/6]*6
    else:
        m = [1/6]*6
    fw_max = max(m) or 1.0
    fw_norm = [x / fw_max for x in m]
    return dynamic_lexicalize(
        field_weights = fw_norm,
        phase         = "Dung",
        verdict       = "clarify",
        active_nodes  = snodes,
        gap_signal    = 0.0,
    )
