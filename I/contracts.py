"""
I/contracts.py — Data contracts for the Input layer.
All contracts flow I→P (LearningEvent) and O→I (FeedbackEvent).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ODFS field names — canonical order
ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# ─── SituationSignal ★ NEW ─────────────────────────────────────────────────────
@dataclass
class SituationSignal:
    """
    Extracted BEFORE tokenization from raw text.
    Controls how Pete 'feels' the situation, independent of token content.
    Result: R_sit[6] — situation-derived field pressure.
    """
    emotional_intensity: float = 0.0   # caps, !, repetition → 0-1
    valence:             float = 0.0   # pos/neg keywords → -1..+1
    urgency:             float = 0.0   # !, short, help → 0-1
    question_pressure:   float = 0.0   # ?, gì/sao/why → 0-1
    assertion_pressure:  float = 0.0   # vì/nên/because → 0-1
    social_pressure:     float = 0.0   # tao/mày/you/we → 0-1

    def to_R0(self) -> list[float]:
        """
        situation_to_R0: convert signal → R_sit[6] (ODFS order)
        [emotion, logic, reflection, visual, language, intuition]
        """
        emotion    = self.emotional_intensity * 8.0 * (1.2 if self.valence < 0 else 1.0)
        logic      = self.assertion_pressure * 7.0
        reflection = self.question_pressure  * 6.0
        visual     = 1.0   # baseline always present
        language   = self.social_pressure * 5.0 + 2.0
        intuition  = self.urgency * 6.0
        return [emotion, logic, reflection, visual, language, intuition]

    @classmethod
    def neutral(cls) -> "SituationSignal":
        return cls(emotional_intensity=0.0, valence=0.0, urgency=0.0,
                   question_pressure=0.0, assertion_pressure=0.0, social_pressure=0.3)


# ─── LearningEvent ─────────────────────────────────────────────────────────────
@dataclass
class LearningEvent:
    """
    Main contract from I → P.
    Carries tokenized symbols, context pairs, and situation for one input.
    """
    normalized_symbol_ids: list[str]
    context_pairs:         list[tuple[str, str]]   # (center, neighbor)
    source_weight:         float = 1.0             # user=1.0, pete=0.5, corpus=0.8
    language_boost:        dict  = field(default_factory=dict)  # {odfs_field: boost}
    modality:              str   = "chat"          # chat|voice|action|visual
    situation_signal:      Optional[SituationSignal] = None     # ★ NEW
    raw_text:              str   = ""              # original input, for dual-route filter

    def __post_init__(self):
        if self.situation_signal is None:
            self.situation_signal = SituationSignal.neutral()


# ─── FeedbackEvent ────────────────────────────────────────────────────────────
@dataclass
class FeedbackEvent:
    """O→I: Pete's output fed back as training signal."""
    text:          str
    source:        str   = "pete_output"
    source_weight: float = 0.5    # Pete's own output weighted less than user
