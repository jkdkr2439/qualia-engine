"""
P/think/semantic/p1/wave_lifecycle.py
Maps wave interference results → primordial lifecycle signals.

This is ADDITIVE — does not replace H/T_fire/T_field lifecycle.
Wave provides an ADDITIONAL energy boost signal based on physics.

Usage:
  ir = interfere(field_wave_emotion, field_wave_intuition, t)
  phase = phase_to_primordial_phase(ir.phase_diff)
  boost = ir.constructive * 0.2   ← small additive to H
"""
import math


def phase_to_primordial_phase(phase_diff: float) -> str:
    """
    Map phase difference (radians [0,π]) → primordial lifecycle phase.
    Emerges from wave physics — no manual definition needed.

      0      → Dung   (perfect constructive, resonant)
      0-π/4  → Dung   (in-phase)
      π/4-π/2→ Chuyen (near-resonant, firing, active)
      π/2-3π/4→ Dan   (probing, uncertain)
      3π/4-π → Hoai   (destructive, dissolving)
    """
    if phase_diff < math.pi / 4:
        return "Dung"
    elif phase_diff < math.pi / 2:
        return "Chuyen"
    elif phase_diff < 3 * math.pi / 4:
        return "Dan"
    else:
        return "Hoai"


def wave_energy_to_H_boost(amp: float, constructive: float,
                             T_field: int = 6,
                             boost_scale: float = 0.15) -> float:
    """
    Convert wave amplitude × constructive → additive H energy boost.

    boost = amp × constructive × T_field × boost_scale
    Keeps boost small (≤ 0.15×T_field) so it doesn't override P1 lifecycle.
    """
    return round(amp * constructive * T_field * boost_scale, 4)


def dominant_interference(wave_states: dict, t: float) -> dict:
    """
    Find the pair of ODFS fields with highest constructive interference at t.
    Returns: {"fields": (a, b), "prime": str, "constructive": float, "boost": float}
    """
    from P.think.odfs.wave_state import interfere, ODFS_FIELDS

    best_c    = -1.0
    best_pair = ("logic", "emotion")
    best_ir   = None

    fields = [f for f in ODFS_FIELDS if f in wave_states]
    for i in range(len(fields)):
        for j in range(i + 1, len(fields)):
            fa, fb = fields[i], fields[j]
            ir = interfere(wave_states[fa], wave_states[fb], t)
            if ir.constructive > best_c:
                best_c    = ir.constructive
                best_pair = (fa, fb)
                best_ir   = ir

    if best_ir is None:
        return {"fields": best_pair, "prime": "Dan",
                "constructive": 0.0, "boost": 0.0}

    boost = wave_energy_to_H_boost(
        amp=sum(wave_states[f].amp for f in best_pair) / 2,
        constructive=best_ir.constructive,
    )
    return {
        "fields":       best_pair,
        "prime":        best_ir.prime,
        "constructive": best_ir.constructive,
        "boost":        boost,
        "gap":          best_ir.gap_contribution,
    }
