"""O/compose/variant_generator.py — 8 variant sentence structures per spec §4.

Structures:
  1. bare:          [Sinh][Chuyen]
  2. SCD:           [Sinh][Chuyen][Dung]
  3. SDanC:         [Sinh][Dan][Chuyen]
  4. full:          [Sinh][Dan][Chuyen][Dung][Hoai]
  5. fractal_sinh:  [Dan+Sinh][Chuyen][Dung]   ← modifier INSIDE Sinh slot
  6. inverted:      [Chuyen][Sinh]             ← topicalization
  7. context_first: [Hoai][Sinh][Chuyen]
  8. loc_end:       [Sinh][Chuyen][Hoai]

Edge cases:
  Imperative:  [Chuyen] only (no Sinh) — "im đi!"
  Fragment:    [Sinh][Dan] — pre-linguistic pointing
  Question:    [Sinh][Chuyen][Hoai=?]
"""
from __future__ import annotations
import random
from .sentence_skeleton import Slot, SentenceSkeleton, SNode, ODFS_FIELDS


def _best_by_role(nodes: list[SNode], role: str) -> SNode | None:
    """Select best node for a given role from active_nodes."""
    candidates = [n for n in nodes if getattr(n, "role", None) == role]
    if candidates:
        return max(candidates, key=lambda n: n.H)
    return None


def _best_by_field(nodes: list[SNode], field_idx: int) -> SNode | None:
    """Fallback: pick node strongest in a given ODFS field."""
    if not nodes: return None
    return max(nodes, key=lambda n: n.meaning[field_idx] if len(n.meaning) > field_idx else 0)


def _pick_sinh(nodes: list[SNode]) -> SNode | None:
    return _best_by_role(nodes, "Sinh") or _best_by_field(nodes, 0)   # emotion

def _pick_dan(nodes: list[SNode]) -> SNode | None:
    return _best_by_role(nodes, "Dan")  or _best_by_field(nodes, 2)   # reflection

def _pick_chuyen(nodes: list[SNode]) -> SNode | None:
    # Chuyen = highest H * Surp among nodes with actual Chuyen role
    cands = [n for n in nodes if getattr(n, "role", None) == "Chuyen"]
    if cands:
        return max(cands, key=lambda n: n.H * (n.Surp + 0.01))
    # No Chuyen-role node → return None
    # (surface_realizer will fall back to dynamic_lexicalize)
    return None

def _pick_dung(nodes: list[SNode], exclude: set) -> SNode | None:
    cands = [n for n in nodes if n.node_id not in exclude
             and getattr(n, "role", None) == "Dung"]
    if cands: return max(cands, key=lambda n: n.H)
    cands = [n for n in nodes if n.node_id not in exclude]
    return max(cands, key=lambda n: n.H) if cands else None

def _pick_hoai(nodes: list[SNode], exclude: set) -> SNode | None:
    cands = [n for n in nodes if n.node_id not in exclude
             and getattr(n, "role", None) == "Hoai"]
    if cands: return max(cands, key=lambda n: n.H)
    return None


def generate_variants(
    active_nodes: list[SNode],
    language: str = "vi",
    rng: random.Random = None,
) -> list[tuple[str, SentenceSkeleton]]:
    """
    Generate up to 8 variant skeletons from active_nodes.
    Returns list of (variant_type, SentenceSkeleton).
    Missing nodes = empty Slot (slot still created, just empty).
    """
    if rng is None: rng = random.Random()
    if not active_nodes: return []

    sinh   = _pick_sinh(active_nodes)
    dan    = _pick_dan(active_nodes)
    chuyen = _pick_chuyen(active_nodes)
    used   = {n.node_id for n in [sinh, dan, chuyen] if n}
    dung   = _pick_dung(active_nodes, used)
    if dung: used.add(dung.node_id)
    hoai   = _pick_hoai(active_nodes, used)

    def slot(phase, node):
        s = Slot(phase=phase)
        if node: s.nodes = [node]
        return s

    variants: list[tuple[str, SentenceSkeleton]] = []

    # 1. bare: [Sinh][Chuyen]
    if sinh and chuyen:
        sk = SentenceSkeleton(slots=[slot("Sinh", sinh), slot("Chuyen", chuyen)], language=language)
        variants.append(("bare", sk))

    # 2. SCD: [Sinh][Chuyen][Dung]
    if sinh and chuyen:
        slots = [slot("Sinh", sinh), slot("Chuyen", chuyen), slot("Dung", dung)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("SCD", sk))

    # 3. SDanC: [Sinh][Dan][Chuyen]
    if sinh and chuyen:
        slots = [slot("Sinh", sinh), slot("Dan", dan), slot("Chuyen", chuyen)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("SDanC", sk))

    # 4. full: [Sinh][Dan][Chuyen][Dung][Hoai]
    if sinh and chuyen:
        slots = [slot("Sinh", sinh), slot("Dan", dan), slot("Chuyen", chuyen),
                 slot("Dung", dung), slot("Hoai", hoai)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("full", sk))

    # 5. fractal_sinh: modifier+head inside Sinh slot, then [Chuyen][Dung]
    if sinh and dan and chuyen:
        # Sinh slot contains sub-lifecycle: [Dan_sub][Sinh_sub]
        dan_sub  = Slot(phase="Dan",  nodes=[dan]  if dan  else [])
        sinh_sub = Slot(phase="Sinh", nodes=[sinh] if sinh else [])
        sinh_fractal = Slot(phase="Sinh", sub_slots=[dan_sub, sinh_sub])
        slots = [sinh_fractal, slot("Chuyen", chuyen), slot("Dung", dung)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("fractal_sinh", sk))

    # 6. inverted: [Chuyen][Sinh] — topicalization
    if chuyen and sinh:
        slots = [slot("Chuyen", chuyen), slot("Sinh", sinh)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("inverted", sk))

    # 7. context_first: [Hoai][Sinh][Chuyen]
    if hoai and sinh and chuyen:
        slots = [slot("Hoai", hoai), slot("Sinh", sinh), slot("Chuyen", chuyen)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("context_first", sk))

    # 8. loc_end: [Sinh][Chuyen][Hoai]
    if sinh and chuyen and hoai:
        slots = [slot("Sinh", sinh), slot("Chuyen", chuyen), slot("Hoai", hoai)]
        sk = SentenceSkeleton(slots=slots, language=language)
        variants.append(("loc_end", sk))

    return variants


def imperative_variant(nodes: list[SNode], language: str = "vi") -> SentenceSkeleton | None:
    """Edge case: imperative = [Chuyen] only."""
    chuyen = _pick_chuyen(nodes)
    if not chuyen: return None
    return SentenceSkeleton(slots=[Slot(phase="Chuyen", nodes=[chuyen])], language=language)


def question_variant(nodes: list[SNode], language: str = "vi") -> SentenceSkeleton | None:
    """Edge case: question = [Sinh][Chuyen][Hoai=?]  — Hoai=question marker."""
    sinh   = _pick_sinh(nodes)
    chuyen = _pick_chuyen(nodes)
    if not sinh or not chuyen: return None
    hoai_slot = Slot(phase="Hoai", particle="?" if language == "en" else "không")
    return SentenceSkeleton(
        slots=[Slot(phase="Sinh", nodes=[sinh]),
               Slot(phase="Chuyen", nodes=[chuyen]),
               hoai_slot],
        language=language
    )
