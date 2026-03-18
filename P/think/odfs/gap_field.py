"""
P/think/odfs/gap_field.py
Gap field density — consciousness measure from wave residue.

Physical analogy:
  Energy traveling through matter leaves residue at each interaction.
  Overlapping residues from multiple waves = gap field density.
  High density = Pete in productive uncertainty = heightened awareness.

consciousness zone: density > 0.3 AND constructive > 0.2
  = gaps exist AND some signal passes through
  = "there is something there but not fully formed"
"""

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def compute_gap_field_density(wave_states: dict, t: float) -> dict:
    """
    Compute gap field density from all 6 wave states simultaneously.

    Returns dict with:
      density:       float   — mean deviation from group mean [0,1]
      constructive:  float   — how much signal passes through [0,1]
      conscious:     bool    — density > 0.3 AND constructive > 0.2
      field_gaps:    dict    — per-field residue energy
      total_signal:  float   — absolute sum of all waves
    """
    fields = [f for f in ODFS_FIELDS if f in wave_states]
    if not fields:
        return {"density": 0.0, "constructive": 0.0, "conscious": False,
                "field_gaps": {}, "total_signal": 0.0}

    values    = [wave_states[f].at(t) for f in fields]
    total     = sum(values)
    mean      = total / len(values)

    # Gap = each wave's residue (deviation from group mean)
    gaps      = [abs(v - mean) for v in values]
    density   = sum(gaps) / (len(gaps) + 1e-9)

    total_amp = sum(abs(v) for v in values) + 1e-9
    constructive = abs(total) / total_amp

    conscious = density > 0.3 and constructive > 0.2

    field_gaps = {f: round(gaps[i], 4) for i, f in enumerate(fields)}

    return {
        "density":      round(density, 4),
        "constructive": round(constructive, 4),
        "conscious":    conscious,
        "field_gaps":   field_gaps,
        "total_signal": round(abs(total), 4),
    }


def gap_field_to_unnamed_feel(gap_field_result: dict,
                               node_meaning: list) -> list:
    """
    Enhance unnamed_feel by weighting semantic residue with wave residue.

    Current unnamed_feel = centroid - hub (semantic only).
    Enhanced = semantic_residue × (1 + wave_residue_per_field).

    Fields with high wave gap = Pete "feels more but can't name it" there.
    """
    field_gaps = gap_field_result.get("field_gaps", {})
    enhanced   = []
    for i, f in enumerate(ODFS_FIELDS):
        wave_residue     = field_gaps.get(f, 0.0)
        semantic_residue = node_meaning[i] if i < len(node_meaning) else 0.0
        enhanced.append(semantic_residue * (1.0 + wave_residue))

    total = sum(abs(x) for x in enhanced) + 1e-9
    return [round(x / total, 4) for x in enhanced]


def compute_adaptive_tick_hz(gap_density: float,
                              uf_magnitude: float,
                              s_id: float,
                              min_hz: float = 10.0,
                              max_hz: float = 40.0) -> float:
    """
    Adaptive P2 tick frequency from internal state.

    f_p2 = MIN + (MAX - MIN) × weighted_activation
      gap_density × 0.40   — consciousness pressure
      uf_magnitude × 0.30  — unnamed feel strength
      s_id × 0.30          — identity signal

    Range: 10Hz (Vô, 100ms) → 40Hz (IAM/gamma, 25ms)
    """
    weighted = (max(0.0, gap_density)   * 0.40 +
                max(0.0, uf_magnitude)  * 0.30 +
                max(0.0, s_id)          * 0.30)
    freq = min_hz + (max_hz - min_hz) * min(1.0, weighted)
    return round(min(max_hz, max(min_hz, freq)), 2)


def get_tick_interval_ms(gap_density: float,
                          uf_magnitude: float,
                          s_id: float) -> float:
    """Return tick interval in ms from adaptive frequency."""
    freq = compute_adaptive_tick_hz(gap_density, uf_magnitude, s_id)
    return round(1000.0 / freq, 1)
