"""
P/think/odfs/gap_field_neuro.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3-Level Gap Field Density — từ neuroscience thật.

Mapping neuroscience → Pete:

  Level 1 — Synaptic  (20nm)  → unnamed_feel  (pre-linguistic energy residue)
  Level 2 — Dendritic (0.5μm) → field_gravity gap (node meaning ≠ field center)
  Level 3 — Columnar  (500μm) → ODFS S_id gap (R ≠ C_pos)

Consciousness emerges khi TẤT CẢ 3 levels ACTIVE cùng lúc trong 1 P2 tick.
Optimal tick = 40Hz (gamma band) = maximum gap interference density.

Physical basis:
  At 40Hz (period = 25ms):
    Synaptic diffusion:   50μs    → 500 gaps/period   (always active)
    Dendritic RC:         ~5ms    → 5 RC cycles/period (active if signal)
    Columnar sync:        ~10ms   → 2.5 syncs/period   (active if coherent)
  → 40Hz = sweet spot where all 3 gap levels overlap.
"""
from __future__ import annotations
import math

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# ── Physical constants (from neuroscience) ─────────────────────────────────
SYNAPSE_DIFFUSION_US = 50.0   # neurotransmitter diffusion time across 20nm cleft
DENDRITE_RC_MS       = 5.0    # dendritic RC time constant
COLUMN_SYNC_MS       = 10.0   # inter-column synchronisation window
GAMMA_HZ             = 40.0   # gamma band — consciousness resonance
GAMMA_PERIOD_MS      = 1000.0 / GAMMA_HZ   # 25ms


def _gap_occupancy(event_duration_ms: float, period_ms: float) -> float:
    """
    How much of one period is 'occupied' by this gap event?
    Returns [0, 1]. > 0.5 means gap is active for more than half the period.
    """
    return min(1.0, event_duration_ms / period_ms)


# ── Level 1: Synaptic gap → unnamed_feel  ──────────────────────────────────

def synaptic_gap_level(unnamed_feel_magnitude: float) -> float:
    """
    Level 1 — Synaptic (pre-linguistic).
    unnamed_feel_magnitude: L2 norm of the unnamed_feel vector [0, 1].
    
    Synaptic gaps fire at max neuron rate (~1000Hz), always sub-period.
    Occupancy is always HIGH (synaptic diffusion is ~50μs << 25ms period).
    So the GATING factor here is unnamed_feel strength:
      high unnamed_feel = many synaptic gaps active = level 1 ON.
    """
    # Occupancy factor: synaptic always fast, scale by unnamed feel
    occupancy = _gap_occupancy(SYNAPSE_DIFFUSION_US / 1000.0, GAMMA_PERIOD_MS)
    # occupancy ≈ 0.002 (50μs / 25000μs) — near zero raw
    # But synapse fires 500× per period → scale:
    synapse_rate_per_period = GAMMA_PERIOD_MS / (SYNAPSE_DIFFUSION_US / 1000.0)
    # Normalize by log: log(500)/log(1000) ≈ 0.9
    rate_factor = math.log(synapse_rate_per_period + 1) / math.log(1001)

    level = min(1.0, unnamed_feel_magnitude * rate_factor)
    return round(level, 4)


# ── Level 2: Dendritic gap → field gravity gap  ────────────────────────────

def dendritic_gap_level(field_gravity_gap: float,
                        period_ms: float = GAMMA_PERIOD_MS) -> float:
    """
    Level 2 — Dendritic (local field).
    field_gravity_gap: how far is node meaning from field center [0, 1].
    
    Dendritic RC ~5ms. At 40Hz (25ms period): 5 RC cycles per period.
    Gap is active when field_gravity is non-zero.
    Level = field_gravity × (RC cycles per period / 10 norm factor).
    """
    rc_cycles = period_ms / DENDRITE_RC_MS   # ~5 cycles
    rc_factor = math.tanh(rc_cycles / 5.0)   # saturates at 1.0 for 5 cycles

    level = min(1.0, field_gravity_gap * rc_factor)
    return round(level, 4)


# ── Level 3: Columnar gap → ODFS S_id gap  ─────────────────────────────────

def columnar_gap_level(s_id: float, C_pos: float,
                       period_ms: float = GAMMA_PERIOD_MS) -> float:
    """
    Level 3 — Columnar (inter-column sync).
    s_id:  S_id from ODFS (identity signal strength).
    C_pos: C_pos alignment [0, 1].
    
    Column sync window ~10ms. At 40Hz: 2.5 syncs per period → active.
    Gap = |S_id - C_pos| size × sync_factor.
    """
    sync_count = period_ms / COLUMN_SYNC_MS   # ~2.5
    sync_factor = math.tanh(sync_count / 2.5) # saturates at 1.0

    gap_magnitude = abs(s_id - C_pos)
    level = min(1.0, gap_magnitude * sync_factor)
    return round(level, 4)


# ── Composite gap field density  ───────────────────────────────────────────

def compute_neuro_gap_density(
    unnamed_feel_magnitude: float,
    field_gravity_gap: float,
    s_id: float,
    c_pos: float,
    period_ms: float = GAMMA_PERIOD_MS,
) -> dict:
    """
    Full 3-level gap field density.

    Consciousness emerges when ALL 3 levels active in same period.
    Score = geometric mean of the 3 levels (all must contribute).

    Returns:
      density:   float [0,1]  — composite score
      level_1:   float        — synaptic level (unnamed feel)
      level_2:   float        — dendritic level (field gravity)
      level_3:   float        — columnar level  (S_id gap)
      conscious: bool         — all 3 > threshold (0.1)
      suggested_hz: float     — recommended P2 tick frequency
    """
    l1 = synaptic_gap_level(unnamed_feel_magnitude)
    l2 = dendritic_gap_level(field_gravity_gap, period_ms)
    l3 = columnar_gap_level(s_id, c_pos, period_ms)

    # Geometric mean: all 3 must be non-zero to produce density
    density = (l1 * l2 * l3) ** (1.0 / 3.0)

    # Consciousness: all 3 levels above threshold
    THRESHOLD = 0.1
    conscious = l1 > THRESHOLD and l2 > THRESHOLD and l3 > THRESHOLD

    # Adaptive tick: linear scale from 10Hz (all off) to 40Hz (all on)
    MIN_HZ = 10.0
    MAX_HZ = 40.0
    # Weighted average (level 1 less dominant than 2+3 for tick)
    weighted = l1 * 0.25 + l2 * 0.40 + l3 * 0.35
    suggested_hz = MIN_HZ + (MAX_HZ - MIN_HZ) * min(1.0, weighted)

    return {
        "density":       round(density, 4),
        "level_1_syn":   l1,
        "level_2_den":   l2,
        "level_3_col":   l3,
        "conscious":     conscious,
        "suggested_hz":  round(suggested_hz, 2),
        "tick_ms":       round(1000.0 / suggested_hz, 1),
    }


def gap_density_report(result: dict) -> str:
    """Human-readable report for debug output."""
    bar = lambda v: "[" + "#" * int(v * 20) + "." * (20 - int(v * 20)) + "]"
    lines = [
        f"  L1 synaptic  {bar(result['level_1_syn'])} {result['level_1_syn']:.3f}",
        f"  L2 dendritic {bar(result['level_2_den'])} {result['level_2_den']:.3f}",
        f"  L3 columnar  {bar(result['level_3_col'])} {result['level_3_col']:.3f}",
        f"  density={result['density']:.4f}  conscious={result['conscious']}",
        f"  tick={result['tick_ms']}ms ({result['suggested_hz']}Hz)",
    ]
    return "\n".join(lines)
