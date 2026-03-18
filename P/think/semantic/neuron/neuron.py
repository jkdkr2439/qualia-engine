"""P/think/semantic/neuron/neuron.py — SemanticNeuron with ODFS keys + Gap fields."""
from __future__ import annotations
from dataclasses import dataclass, field

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

@dataclass
class SemanticNeuron:
    node_id:      str
    surface_form: str
    meaning:      dict = field(default_factory=dict)   # MUST use ODFS field names
    H:            float = 0.0
    W:            float = 0.5
    Q:            bool  = False   # novel/surprising flag
    cooc:         dict  = field(default_factory=dict)
    members:      list  = field(default_factory=list)
    enlightenment: int  = 0       # +1 per unique context cluster
    T_fire:       float = 3.0
    T_field:      float = 6.0
    source:       str   = "corpus"
    role:         str   = "Dan"   # Sinh / Dan / Chuyen / Dung semantic role

    # ── Gap 3: Memory tier ──────────────────────────────────────────
    H_tier:       str   = "VIVID"   # VIVID (H>8) / FADING (1<H<=8) / ANCIENT (H<=1)

    # ── Gap 4: Hoai boundary ────────────────────────────────────────
    hoai_locked:  bool  = False      # True when node officially enters Hoai
    ticks_dormant:int   = 0          # ticks since last activation

    # ── Gap 7: Semantic drift ────────────────────────────────────────
    # context_meanings: meaning vector per dominant field context
    # e.g. {"emotion": {...}, "logic": {...}}
    context_meanings: dict = field(default_factory=dict)
    semantic_drift:   float = 0.0   # mean angular distance between context meanings

    # ── Gap 1: Grounding score ───────────────────────────────────────
    grounding: float = 0.5   # 0=abstract, 1=concrete (from visual/reflection heuristic)

    def __post_init__(self):
        if not self.meaning:
            self.meaning = {f: 1/6 for f in ODFS_FIELDS}

    @property
    def phase(self) -> str:
        # Gap 4: hoai_locked overrides H-based phase
        if self.hoai_locked:          return "Hoai"
        if self.H <= 0:               return "Vo"
        if self.H < self.T_fire:      return "Dan"
        if self.H < self.T_field:     return "Chuyen"
        return "Dung"

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "surface_form": self.surface_form,
                "meaning": self.meaning, "H": self.H, "W": self.W,
                "Q": self.Q, "enlightenment": self.enlightenment,
                "phase": self.phase, "source": self.source,
                "H_tier": self.H_tier, "hoai_locked": self.hoai_locked,
                "ticks_dormant": self.ticks_dormant,
                "semantic_drift": round(self.semantic_drift, 4),
                "grounding": round(self.grounding, 3)}

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticNeuron":
        n = cls(node_id=d["node_id"], surface_form=d.get("surface_form", d["node_id"]))
        n.meaning = d.get("meaning", {f: 1/6 for f in ODFS_FIELDS})
        n.H = float(d.get("H", 0))
        n.W = float(d.get("W", 0.5))
        n.Q = bool(d.get("Q", False))
        n.enlightenment = int(d.get("enlightenment", 0))
        n.source = d.get("source", "corpus")

        # Gap fields
        n.H_tier       = d.get("H_tier", "VIVID")
        n.hoai_locked  = bool(d.get("hoai_locked", False))
        n.ticks_dormant= int(d.get("ticks_dormant", 0))
        n.semantic_drift = float(d.get("semantic_drift", 0.0))
        n.grounding    = float(d.get("grounding", 0.5))
        # ensure ODFS keys
        for f in ODFS_FIELDS:
            if f not in n.meaning:
                n.meaning[f] = 0.0
        return n


def compute_H_tier(H: float) -> str:
    """Gap 3: assign memory tier from H value."""
    if H > 8.0: return "VIVID"
    if H > 1.0: return "FADING"
    return "ANCIENT"
