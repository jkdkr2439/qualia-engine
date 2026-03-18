"""O/compose/sentence_skeleton.py — Slot + SentenceSkeleton with fractal sub-lifecycle.

Câu = Primordial lifecycle:
  Sinh   = context opens     (subject/entity)
  Dan    = meaning accumulates (modifier/aspect)
  Chuyen = meaning FIRES     (VERB — intersection of 2 streams)
  Dung   = meaning integrates (object/complement)
  Hoai   = meaning dissolves  (adverbial/time/location)
  Vo     = silence after sentence
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
PHASES = ["Sinh", "Dan", "Chuyen", "Dung", "Hoai", "Vo"]


@dataclass
class SNode:
    """Lightweight surface node for sentence construction."""
    node_id:      str
    surface:      str           # display form
    meaning:      list[float]   # [6] ODFS vector
    H:            float = 0.0
    Surp:         float = 0.0
    role:         str   = None  # Sinh/Dan/Chuyen/Dung/Hoai (learned)
    phase:        str   = "Vo"  # primordial phase state

    @classmethod
    def from_node(cls, node) -> "SNode":
        """Build SNode from a SemanticNeuron or dict."""
        if isinstance(node, dict):
            nid = node.get("node_id", "?")
            sf  = node.get("surface_form", nid)
            m   = node.get("meaning", {})
            H   = node.get("H", 0.0)
            ph  = node.get("phase", "Vo")
        else:
            nid = getattr(node, "node_id", "?")
            sf  = getattr(node, "surface_form", nid)
            m   = getattr(node, "meaning", {})
            H   = getattr(node, "H", 0.0)
            ph  = getattr(node, "phase", "Vo")
        if isinstance(m, dict):
            m = [m.get(f, 0.0) for f in ODFS_FIELDS]
        return cls(node_id=nid, surface=str(sf), meaning=list(m), H=H, phase=ph)


@dataclass
class Slot:
    """One slot in the sentence lifecycle."""
    phase:     str           # Sinh/Dan/Chuyen/Dung/Hoai
    nodes:     list[SNode]   = field(default_factory=list)
    sub_slots: list["Slot"]  = field(default_factory=list)
    particle:  str           = ""   # aspect/modal/determiner particle

    @property
    def surface(self) -> str:
        """Render slot to surface string (fractal recursive)."""
        if self.sub_slots:
            parts = [s.surface for s in self.sub_slots if s.surface]
        else:
            parts = [n.surface for n in self.nodes if n.surface]
        out = " ".join(parts)
        if self.particle:
            # Particle position: aspect before verb (Dan), else after phrase
            if self.phase == "Dan":
                out = self.particle + " " + out
            else:
                out = out + " " + self.particle
        return out.strip()

    @property
    def meaning(self) -> list[float]:
        """Mean meaning vector across all nodes in this slot."""
        all_nodes = self.nodes.copy()
        for ss in self.sub_slots:
            all_nodes.extend(ss.nodes)
        if not all_nodes:
            return [1/6] * 6
        total = [0.0] * 6
        for n in all_nodes:
            for i, v in enumerate(n.meaning):
                total[i] += v
        return [x / len(all_nodes) for x in total]

    @property
    def H(self) -> float:
        """Mean H of nodes in slot."""
        ns = self.nodes + [n for ss in self.sub_slots for n in ss.nodes]
        if not ns: return 0.0
        return sum(n.H for n in ns) / len(ns)

    def empty(self) -> bool:
        return not self.nodes and not self.sub_slots


@dataclass
class SentenceSkeleton:
    """Ordered list of Slots forming a complete Primordial lifecycle sentence."""
    slots:    list[Slot]
    language: str = "vi"     # "vi" | "en" | "zh"

    @property
    def surface(self) -> str:
        """Full rendered sentence."""
        parts = [s.surface for s in self.slots if not s.empty()]
        return " ".join(parts).strip()

    @property
    def has_chuyen(self) -> bool:
        return any(s.phase == "Chuyen" and not s.empty() for s in self.slots)

    @property
    def sinh_slot(self) -> Slot | None:
        for s in self.slots:
            if s.phase == "Sinh": return s
        return None

    @property
    def chuyen_slot(self) -> Slot | None:
        for s in self.slots:
            if s.phase == "Chuyen": return s
        return None

    @property
    def slot_order(self) -> list[str]:
        return [s.phase for s in self.slots]


def cosine_slot(a: Slot, b: Slot) -> float:
    """Cosine similarity between two slot meanings."""
    return _cosine(a.meaning, b.meaning)


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)
