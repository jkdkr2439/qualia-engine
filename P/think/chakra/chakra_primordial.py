"""P/think/chakra/chakra_primordial.py — ChakraPrimordial with full lifecycle.
Each chakra has its own Primordial energy state (Vo/Sinh/Dan/Chuyen/Dung).
Heavy inputs stay at Root/Sacral; deep inputs rise to Crown.

Key design: each chakra has its OWN Omega_user kernel.
When user input arrives (R_sit), each chakra:
  1. Filters R_sit through its field_weights (only attends to relevant dimensions)
  2. Writes the filtered signal into its own Omega_user
This gives each primordial a separate, evolving model of the user.
"""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
import json, math
from pathlib import Path

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
N = len(ODFS_FIELDS)

D_IDENTITIES = Path(__file__).parent.parent.parent.parent.parent / "D" / "identities"

T_FIRE  = 2.0   # chakra fire threshold (lower than P1)
T_FIELD = 4.0   # chakra field threshold

# Default ODFS coupling matrix (identity ~ balanced)
_OMEGA_DEFAULT = [
    [0.00, 0.25, 0.25, 0.25, 0.25, 0.75],  # emotion    → intuition
    [0.25, 0.00, 0.75, 0.25, 0.25, 0.25],  # logic      → reflection
    [0.25, 0.75, 0.00, 0.25, 0.25, 0.25],  # reflection → logic
    [0.25, 0.25, 0.25, 0.00, 0.65, 0.25],  # visual     → language
    [0.25, 0.25, 0.25, 0.65, 0.00, 0.25],  # language   → visual
    [0.75, 0.25, 0.25, 0.25, 0.25, 0.00],  # intuition  → emotion
]

# Chakra definitions (same as chakra_definitions.py for self-containment)
CHAKRA_DEFS: dict[str, dict] = {
    "root":     {"field_weights": {"visual": 0.7, "logic": 0.6, "emotion": 0.5}},
    "sacral":   {"field_weights": {"emotion": 0.9, "intuition": 0.7, "visual": 0.5}},
    "solar":    {"field_weights": {"logic": 0.8, "reflection": 0.7, "emotion": 0.4}},
    "heart":    {"field_weights": {"emotion": 0.8, "language": 0.7, "intuition": 0.6}},
    "throat":   {"field_weights": {"language": 0.9, "reflection": 0.6, "logic": 0.4}},
    "thirdeye": {"field_weights": {"intuition": 0.9, "reflection": 0.8, "logic": 0.5}},
    "crown":    {"field_weights": {"reflection": 0.7, "intuition": 0.8, "emotion": 0.4}},
}


@dataclass
class ChakraPrimordial:
    """
    A chakra with its own energy state, primordial lifecycle,
    and independent Omega_user kernel.

    Omega_user: 6×6 ODFS coupling matrix learned from user signals,
    filtered through this chakra's field_weights (selective attention).
    Stored in D/identities/{name}/omega_user.json
    """
    name:          str
    field_weights: dict[str, float]   # from CHAKRA_DEFS
    H:             float = 0.0
    meaning:       dict  = dc_field(default_factory=lambda: {f: 1/6 for f in ODFS_FIELDS})
    phase:         str   = "Vo"
    # Per-chakra user model — clone of OMEGA_DEFAULT, updated per user signal
    omega_user:    list  = dc_field(default_factory=lambda: [row[:] for row in _OMEGA_DEFAULT])

    @property
    def current_phase(self) -> str:
        if self.H <= 0:           return "Vo"
        if self.H < T_FIRE:       return "Sinh"
        if self.H < T_FIELD:      return "Dan"
        return "Chuyen"

    def tick(self, R_sit: list, scale: float = 1.0) -> float:
        """
        Energy intake from R_sit.
        Affinity = cosine(R_sit, this chakra's field_weights_vec).
        Energy added = affinity * |R_sit| * scale.
        """
        fw_vec  = [self.field_weights.get(f, 0.0) for f in ODFS_FIELDS]
        r_norm  = math.sqrt(sum(x ** 2 for x in R_sit))
        affinity = _cosine_list(R_sit, fw_vec)
        energy   = affinity * r_norm * scale

        self.H += energy * 0.1   # scale down
        self.H  = max(0.0, self.H)
        self.phase = self.current_phase

        # Dung: update meaning pull toward this chakra's profile
        if self.phase == "Chuyen":
            for f in ODFS_FIELDS:
                w = self.field_weights.get(f, 0.0)
                self.meaning[f] = self.meaning.get(f, 0.0) * 0.98 + w * 0.02
            _normalize_meaning(self.meaning)

        return affinity

    def signal(self) -> list[float]:
        """Return field signal weighted by H activation level."""
        fw_vec = [self.field_weights.get(f, 0.0) for f in ODFS_FIELDS]
        scale  = min(self.H / T_FIELD, 1.0)
        return [x * scale for x in fw_vec]

    def absorb_user_signal(self, R_sit: list[float], lr: float = 0.05) -> None:
        """
        Write user signal into this chakra's own Omega_user.
        Each chakra only 'listens' to the dimensions its field_weights are strong on.
        The stronger a field weight, the more that dimension updates Omega_user.

        This gives each primordial a distinct, evolving model of the user
        based on its own selective attention.
        """
        fw = [self.field_weights.get(f, 0.0) for f in ODFS_FIELDS]
        fw_max = max(fw) or 1.0
        fw_norm = [w / fw_max for w in fw]  # normalize so max attention = 1.0

        for i in range(N):
            attn_i = fw_norm[i]           # how much does this chakra attend to dim i?
            if attn_i < 0.1:              # below threshold → ignore
                continue
            for j in range(N):
                if i == j:
                    continue
                # Update: Omega[i][j] ← Omega[i][j] + lr * attn_i * R_sit[j]
                # R_sit[j] signals how strongly dimension j is active in user input
                delta = lr * attn_i * R_sit[j]
                self.omega_user[i][j] = (
                    (1 - lr) * self.omega_user[i][j] + delta
                )
                # Clamp to [0, 1]
                self.omega_user[i][j] = max(0.0, min(1.0, self.omega_user[i][j]))

    def save_omega_user(self) -> None:
        """Persist this chakra's omega_user to D/identities/{name}/omega_user.json"""
        path = D_IDENTITIES / self.name
        path.mkdir(parents=True, exist_ok=True)
        (path / "omega_user.json").write_text(
            json.dumps(self.omega_user, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_omega_user(self) -> None:
        """Load this chakra's omega_user from D/identities/{name}/omega_user.json"""
        f = D_IDENTITIES / self.name / "omega_user.json"
        if f.exists():
            try:
                loaded = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(loaded, list) and len(loaded) == N:
                    self.omega_user = loaded
            except Exception:
                pass  # corrupt → keep default




def build_chakra_primordials() -> dict[str, ChakraPrimordial]:
    """Build all 7 chakra primordials from definitions."""
    return {
        name: ChakraPrimordial(
            name=name, field_weights=defn["field_weights"]
        )
        for name, defn in CHAKRA_DEFS.items()
    }


def _cosine_list(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x ** 2 for x in a))
    nb  = math.sqrt(sum(y ** 2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


def _normalize_meaning(d: dict) -> None:
    total = sum(d.get(f, 0) for f in ODFS_FIELDS)
    if total > 0:
        for f in ODFS_FIELDS:
            d[f] = d.get(f, 0) / total
