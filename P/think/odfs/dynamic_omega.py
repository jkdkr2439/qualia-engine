"""
P/think/odfs/dynamic_omega.py
Dynamic Omega matrix — coupling strength between ODFS fields.

Unlike the hardcoded OMEGA in odfs_kernel.py, this computes Omega
from two components:
  1. beat_coupling: physical ← 1 / (1 + |f_A - f_B|)
  2. functional_affinity: cognitive similarity between fields

Omega[a,b] = alpha × beat_coupling + (1-alpha) × functional_affinity

Rebuild only at: session start, Field Connect, Dream Cycle.
NOT every tick.
"""

# How cognitively similar two fields are (manually defined, stable)
FUNCTIONAL_AFFINITY: dict[tuple, float] = {
    ("emotion",    "intuition"):   0.90,  # both feeling-based
    ("logic",      "reflection"):  0.80,  # both analytical
    ("visual",     "language"):    0.70,  # both representational
    ("emotion",    "language"):    0.50,  # social emotion
    ("reflection", "intuition"):   0.60,  # meta-awareness
    ("logic",      "language"):    0.55,  # structured expression
    ("emotion",    "reflection"):  0.45,
    ("visual",     "intuition"):   0.40,
    ("logic",      "visual"):      0.35,
    ("language",   "intuition"):   0.55,
    # default: 0.20
}

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def beat_coupling(freq_a: float, freq_b: float) -> float:
    """
    Coupling from beat frequency. Near-resonant → high coupling.
    beat_coupling = 1 / (1 + |f_a - f_b|)
    """
    return 1.0 / (1.0 + abs(freq_a - freq_b))


def get_functional_affinity(field_a: str, field_b: str) -> float:
    """Look up functional affinity (symmetric)."""
    key = (field_a, field_b)
    if key in FUNCTIONAL_AFFINITY:
        return FUNCTIONAL_AFFINITY[key]
    key_rev = (field_b, field_a)
    if key_rev in FUNCTIONAL_AFFINITY:
        return FUNCTIONAL_AFFINITY[key_rev]
    return 0.20  # default


def compute_omega_entry(field_a: str, field_b: str,
                         wave_states: dict,
                         alpha: float = 0.5) -> float:
    """
    Omega[a,b] = alpha × beat_coupling + (1-alpha) × functional_affinity
    alpha = 0.5: balanced physics + function
    """
    wa = wave_states.get(field_a)
    wb = wave_states.get(field_b)
    if wa is None or wb is None:
        return 0.25

    bc = beat_coupling(wa.freq, wb.freq)
    fa = get_functional_affinity(field_a, field_b)
    return round(alpha * bc + (1.0 - alpha) * fa, 4)


def rebuild_omega(wave_states: dict, alpha: float = 0.5) -> list:
    """
    Rebuild 6×6 Omega matrix from current wave states.
    Returns list of lists (6×6).
    """
    N     = len(ODFS_FIELDS)
    omega = [[0.0] * N for _ in range(N)]

    for i, fa in enumerate(ODFS_FIELDS):
        for j, fb in enumerate(ODFS_FIELDS):
            if i == j:
                omega[i][j] = 1.0
            else:
                omega[i][j] = compute_omega_entry(fa, fb, wave_states, alpha)

    return omega


def flat_omega(omega_matrix: list) -> dict:
    """Convert 6×6 list to {(field_a, field_b): value} dict for odfs_kernel."""
    result = {}
    for i, fa in enumerate(ODFS_FIELDS):
        for j, fb in enumerate(ODFS_FIELDS):
            if i != j:
                result[(fa, fb)] = omega_matrix[i][j]
    return result
