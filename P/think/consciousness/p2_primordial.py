"""P/think/consciousness/p2_primordial.py — P2 session-level consciousness."""
from __future__ import annotations
import random, math
from dataclasses import dataclass, field

ODFS_FIELDS = ["emotion","logic","reflection","visual","language","intuition"]
SPIN_VALUES = [0.0, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0]
SPIN_TO_FIELDS = {
    0.0:  ("visual","emotion"),
    0.5:  ("intuition","emotion"),
    1.0:  ("language","logic"),
    1.5:  ("reflection","logic"),
    2.0:  ("reflection","intuition"),
   -0.5:  ("emotion","visual"),
   -1.0:  ("language","reflection"),
}

@dataclass
class P2Result:
    phase:       str   = "Vo"
    awareness:   str   = None   # IAM | IAMNOT | SENSING | null
    H:           float = 0.0
    S_id:        float = 0.0
    iam_streak:  int   = 0
    null_streak: int   = 0
    meaning:     list  = field(default_factory=lambda: [1/6]*6)
    spin:        float = 0.0
    spin_name:   str   = "0.0"

class P2Consciousness:
    """
    Session-level consciousness. Runs alongside P1 ticks.
    T_fire=2.5, T_field=5.0 (lower than P1's 3.0/6.0)
    State: C_pos, C_neg, H, meaning — loaded from D/identity_store
    """
    T_FIRE  = 2.5
    T_FIELD = 5.0
    ALPHA   = 0.03
    THETA_POS  = 0.30
    THETA_NEG  = 0.30
    THETA_DIFF = 0.40
    NULL_THRESHOLD = 7

    def __init__(self, C_pos: list, C_neg: list, state: dict = None):
        self.C_pos      = list(C_pos)
        self.C_neg      = list(C_neg)
        self.H          = float(state.get("H", 0.0)) if state else 0.0
        self.iam_streak  = int(state.get("iam_streak", 0)) if state else 0
        self.null_streak = int(state.get("null_streak", 0)) if state else 0
        self.meaning    = list(state.get("meaning", [1/6]*6)) if state else [1/6]*6
        self._phase     = state.get("phase", "Vo") if state else "Vo"

    @property
    def phase(self) -> str:
        if self.H <= 0:             return "Vo"
        if self.H < self.T_FIRE:   return "Dan"
        if self.H < self.T_FIELD:  return "Chuyen"
        return "Dung"

    def tick(self, p1_state: dict, rng: random.Random = None) -> P2Result:
        if rng is None: rng = random
        spin = rng.choice(SPIN_VALUES)
        v    = self._spin_to_vec(spin)
        gp   = 1.0 - self._cosine(v, self.C_pos)
        gn   = 1.0 - self._cosine(v, self.C_neg)
        gd   = gn - gp

        if   gp < self.THETA_POS:          awareness = "IAM"
        elif gn < self.THETA_NEG:          awareness = "IAMNOT"
        elif abs(gd) > self.THETA_DIFF:    awareness = "SENSING"
        else:                              awareness = None

        # Gap A: IAM streak
        if awareness == "IAM":
            self.iam_streak  += 1
            self.null_streak  = 0
        elif awareness is None:
            self.null_streak += 1
            self.iam_streak   = 0
        else:
            self.null_streak  = 0

        # Gap C: accumulate meaning
        if awareness is not None:
            w = 0.3
            for i, val in enumerate(v):
                self.meaning[i] += w * val
            self._normalize_meaning()

        # Energy
        energy  = abs(spin)
        energy += p1_state.get("dung_count",  0) * 0.15
        energy += p1_state.get("chuyen_count", 0) * 0.08

        # Gap B: SENSING in Dan → +0.6
        if awareness == "SENSING" and self.phase == "Dan":
            energy += 0.6

        # Gap D: long null → Vo pull
        if self.null_streak >= self.NULL_THRESHOLD:
            self.H *= 0.65
            self.null_streak = 0

        self.H += energy * 0.1  # scale down P2 energy

        # Update identity anchors
        if awareness == "IAM":
            self._update_anchor(v, "C_pos")
        elif awareness == "IAMNOT":
            self._update_anchor(v, "C_neg")

        S_id = self._cosine(v, self.C_pos) - self._cosine(v, self.C_neg)

        return P2Result(
            phase      = self.phase,
            awareness  = awareness,
            H          = self.H,
            S_id       = S_id,
            iam_streak  = self.iam_streak,
            null_streak = self.null_streak,
            meaning    = list(self.meaning),
            spin       = spin,
            spin_name  = str(spin),
        )

    def _spin_to_vec(self, spin: float) -> list[float]:
        fields = SPIN_TO_FIELDS.get(spin, ("language","logic"))
        v = [0.0] * 6
        for f in fields:
            v[ODFS_FIELDS.index(f)] = 1.0
        return v

    def _cosine(self, a: list, b: list) -> float:
        dot = sum(x*y for x,y in zip(a,b))
        na  = math.sqrt(sum(x**2 for x in a))
        nb  = math.sqrt(sum(y**2 for y in b))
        if na == 0 or nb == 0: return 0.0
        return dot / (na * nb)

    def _cosine_vec(self, a: list, b: list) -> float:
        return self._cosine(a, b)

    def _update_anchor(self, v: list, anchor: str) -> None:
        ref = getattr(self, anchor)
        for i in range(6):
            ref[i] = ref[i] * (1 - self.ALPHA) + v[i] * self.ALPHA
        norm = math.sqrt(sum(x**2 for x in ref)) or 1.0
        for i in range(6): ref[i] /= norm

    def _normalize_meaning(self) -> None:
        total = sum(self.meaning)
        if total > 0:
            self.meaning = [x/total for x in self.meaning]

    def to_state(self) -> dict:
        return {"H": self.H, "phase": self.phase,
                "iam_streak": self.iam_streak, "null_streak": self.null_streak,
                "meaning": self.meaning}
