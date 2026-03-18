"""
P/think/odfs/wave_state.py
Wave interference layer for Pete v4.

Each ODFS field oscillates at an EEG-aligned frequency.
Interference between fields produces:
  - Primordial phase (Sinh/Dan/Chuyen/Dung/Hoai) via phase_diff
  - Gap field density (consciousness measure) via residue energy
  - Dynamic Omega matrix (field coupling from beat frequency)

ADDITIVE to existing architecture — does not replace anything.
"""
import math
import random
from dataclasses import dataclass, field


# EEG-aligned base frequencies per ODFS field
DEFAULT_WAVE_FREQS: dict[str, float] = {
    "emotion":    6.0,   # θ theta  — deep feeling
    "logic":      18.0,  # β beta   — analytical
    "reflection": 35.0,  # γ gamma  — meta-awareness
    "visual":     10.0,  # α alpha  — perceptual
    "language":   22.0,  # β beta   — structured expression
    "intuition":  5.0,   # θ theta  — pre-linguistic
}

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


@dataclass
class WaveState:
    """Oscillation state for one ODFS field."""
    field_name: str
    freq:       float    # Hz
    phase:      float    # radians, current
    amp:        float    # amplitude ≈ field activation [0,1]

    def at(self, t: float) -> float:
        """Signal value at time t (seconds)."""
        return self.amp * math.sin(2.0 * math.pi * self.freq * t + self.phase)

    def advance(self, dt: float) -> None:
        """Advance phase by dt seconds (call each P2 tick)."""
        self.phase = (self.phase + 2.0 * math.pi * self.freq * dt) % (2.0 * math.pi)


@dataclass
class WaveInterferenceResult:
    beat_freq:        float   # |f_A - f_B| Hz
    constructive:     float   # 0-1 how constructive
    phase_diff:       float   # radians [0, π]
    prime:            str     # Dung / Dan / Chuyen / Hoai
    gap_contribution: float   # residue energy (gap signal)


def interfere(A: WaveState, B: WaveState, t: float) -> WaveInterferenceResult:
    """
    Compute wave interference between two ODFS fields at time t.
    Returns lifecycle prime classification and gap contribution.
    """
    beat  = abs(A.freq - B.freq)
    val_a = A.at(t)
    val_b = B.at(t)
    combined     = val_a + val_b
    max_possible = A.amp + B.amp + 1e-9

    constructive = abs(combined) / max_possible
    phase_diff   = abs(A.phase - B.phase) % (2.0 * math.pi)
    if phase_diff > math.pi:
        phase_diff = 2.0 * math.pi - phase_diff

    # Lifecycle phase emerges from wave physics
    if constructive > 0.7 and beat < 2.0:
        prime = "Dung"
    elif constructive > 0.4 and beat < 5.0:
        prime = "Chuyen"
    elif constructive < 0.2 or (beat > 20 and phase_diff > math.pi * 0.7):
        prime = "Hoai"
    elif 0.3 < constructive < 0.7 or beat < 10.0:
        prime = "Dan"
    else:
        prime = "Sinh"

    # Gap = residue energy (each field's contribution that doesn't cancel)
    gap = abs(val_a - val_b) / max_possible

    return WaveInterferenceResult(
        beat_freq        = round(beat, 3),
        constructive     = round(constructive, 4),
        phase_diff       = round(phase_diff, 4),
        prime            = prime,
        gap_contribution = round(gap, 4),
    )


def init_wave_states(odfs_R: list) -> dict:
    """
    Initialize wave states from current ODFS R vector.
    amp = R[i] / max(R) normalized.
    phase = random (fields start uncorrelated).
    """
    r_list = list(odfs_R)
    max_r  = max(r_list) if r_list else 1.0
    states = {}
    for i, fname in enumerate(ODFS_FIELDS):
        amp = r_list[i] / (max_r + 1e-9) if i < len(r_list) else 0.1
        states[fname] = WaveState(
            field_name = fname,
            freq       = DEFAULT_WAVE_FREQS[fname],
            phase      = random.uniform(0, 2.0 * math.pi),
            amp        = max(0.05, amp),
        )
    return states
