"""O/compose/pattern_generator.py — Generate candidate sentence from MasterPattern.
Per spec §12 Steps 5-6: generate from pattern + add particles/connectives.
"""
from __future__ import annotations
import random
from .pattern_registry import MasterPattern, PARTICLES, SLOT_ORDER_BY_LANGUAGE
from .sentence_skeleton import Slot, SentenceSkeleton, SNode
from .variant_generator import (
    _pick_sinh, _pick_dan, _pick_chuyen, _pick_dung, _pick_hoai
)


def generate_from_pattern(
    pattern:     MasterPattern,
    nodes:       list[SNode],
    language:    str,
    rng:         random.Random = None,
) -> SentenceSkeleton:
    """
    Build a SentenceSkeleton matching the pattern's slot_order.
    Nodes assigned by role first, fallback by ODFS field dominance.
    """
    if rng is None: rng = random.Random()

    def slot(phase, node):
        s = Slot(phase=phase)
        if node: s.nodes = [node]
        return s

    # Pick nodes for each phase
    sinh   = _pick_sinh(nodes)
    dan    = _pick_dan(nodes)
    chuyen = _pick_chuyen(nodes)
    used   = {n.node_id for n in [sinh, dan, chuyen] if n}
    dung   = _pick_dung(nodes, used)
    if dung: used.add(dung.node_id)
    hoai   = _pick_hoai(nodes, used)

    phase_map = {
        "Sinh":   sinh,
        "Dan":    dan,
        "Chuyen": chuyen,
        "Dung":   dung,
        "Hoai":   hoai,
    }

    slots = [slot(phase, phase_map.get(phase)) for phase in pattern.slot_order]
    return SentenceSkeleton(slots=slots, language=language)


def add_particles(
    skeleton: SentenceSkeleton,
    pattern:  MasterPattern,
    language: str,
    rng:      random.Random = None,
) -> SentenceSkeleton:
    """
    Add particles/connectives to the skeleton.
    Per spec: particles added AFTER pattern generation (not part of SDCHDV slots).
    - Aspect particle added to Dan slot (if present)
    - Sentence-final particle for vi
    - Determiner for en Dan slot
    """
    if rng is None: rng = random.Random()
    lang_particles = PARTICLES.get(language, {})
    aspects = lang_particles.get("aspect", [])
    particles = lang_particles.get("particle", [])
    determiners = lang_particles.get("determiner", {})

    for slot in skeleton.slots:
        # Dan slot: add aspect particle sometimes (30% chance for naturalness)
        if slot.phase == "Dan" and not slot.empty():
            if aspects and rng.random() < 0.30:
                chosen = rng.choice(aspects)
                slot.particle = chosen

        # Sinh slot in EN: add determiner ("the") before noun
        if slot.phase == "Sinh" and language == "en" and not slot.empty():
            if "definite" in determiners and rng.random() < 0.50:
                slot.particle = determiners["definite"]

        # Hoai slot: for vi question pattern, add question particle
        if slot.phase == "Hoai" and language == "vi" and pattern.gap_level == "mid":
            if particles and rng.random() < 0.20:
                slot.particle = rng.choice(particles)

    return skeleton


def build_candidate(
    pattern:  MasterPattern,
    nodes:    list[SNode],
    language: str,
    rng:      random.Random = None,
) -> SentenceSkeleton:
    """Full pipeline: generate from pattern → add particles."""
    if rng is None: rng = random.Random()
    skeleton = generate_from_pattern(pattern, nodes, language, rng)
    skeleton = add_particles(skeleton, pattern, language, rng)
    return skeleton
