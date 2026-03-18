"""P/modes/attention_controller.py — STABILIZE | TRANSITION | GROW decision.
Gap 6: replaced hard mode string with soft mode_weights dict.
"""
from __future__ import annotations
import math

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))

class AttentionController:
    """
    Decides attention mode each tick.
    Mode affects lr scaling and tau1 threshold.

    Gap 6: decide_weights() returns soft dict instead of hard string,
           allowing blend states (e.g. 70% STABILIZE + 30% MEDITATION).
    """
    N_CYCLE = 15   # default alternation period

    def __init__(self):
        self._tick = 0
        self._last_mode = "STABILIZE"

    def decide_weights(self, odfs_prev: dict, iam_streak: int,
                       quantum_state: dict = None,
                       hoai_ratio: float = 0.0,
                       pre_mode_bias: str = "STABILIZE",
                       drift_severity: float = 0.0,
                       chakra_gaps: dict = None) -> dict:
        """
        Gap 6 — Soft mode weights: returns {mode: weight} dict summing to 1.0.

        hoai_ratio:    fraction of active nodes in Hoai phase.
        pre_mode_bias: proactive signal from quantum gap (before ODFS).
        drift_severity: LUCIS_0↔LUCIS_1 gap — identity crisis indicator.
        chakra_gaps:   output of chakra_gap_matrix() — cross-layer tension.
        """
        self._tick += 1
        rho   = odfs_prev.get("rho_U", 0.5)
        S_id  = odfs_prev.get("S_id", 0.0)
        Gamma = odfs_prev.get("Gamma", 0.0)
        q     = quantum_state or {}

        # Soft weights via sigmoid
        w_stabilize  = _sigmoid(0.4 - rho) * 2.0 + _sigmoid(Gamma - 3.0)
        w_grow       = _sigmoid(rho - 0.65) * _sigmoid(S_id - 0.5)
        w_meditate   = _sigmoid(hoai_ratio - 0.3) * 1.5  # Gap 6: hoai→meditate
        w_transition = 1.0 if (q.get("attn_transition") and rho > 0.5 and S_id > 0.4) else 0.0

        raw = {
            "STABILIZE":  max(0.0, w_stabilize),
            "GROW":       max(0.0, w_grow),
            "MEDITATION": max(0.0, w_meditate),
            "TRANSITION": max(0.0, w_transition),
        }

        # ── Quantum pre-mode bias ──────────────────────────────────────────────
        if drift_severity > 0.30:
            raw["STABILIZE"] *= 2.0
        PRE_BOOST = {"STABILIZE": 0.25, "TRANSITION": 0.35, "GROW": 0.20, "MEDITATION": 0.15}
        boost = PRE_BOOST.get(pre_mode_bias, 0.0)
        if pre_mode_bias in raw:
            raw[pre_mode_bias] += boost

        # ── Chakra gap bias (3-layer reality tension) ──────────────────────────
        cg = chakra_gaps or {}
        max_ck = cg.get("max_gap", 0.0)
        tension = cg.get("dominant_tension", "")
        lg = cg.get("layer_gaps", {})
        if max_ck > 0.55:
            if "obj_vs_subj" in tension:
                raw["MEDITATION"] += 0.50   # Pete vs cold reality → go deep
            elif "inter_vs_subj" in tension:
                raw["TRANSITION"] += 0.45   # Pete vs social norm → at threshold
            else:
                raw["TRANSITION"] += 0.30
        elif max_ck > 0.30:
            subj_tension = lg.get("inter_vs_subj", 0) + lg.get("obj_vs_subj", 0)
            if subj_tension > 0.5:
                raw["MEDITATION"] += 0.20
            else:
                raw["GROW"] += 0.25         # moderate external gap → absorb

        total = sum(raw.values()) or 1.0
        weights = {k: v/total for k,v in raw.items()}
        self._last_mode = max(weights, key=weights.get)
        return weights

    def decide(self, odfs_prev: dict, iam_streak: int,
               quantum_state: dict = None) -> str:
        """Legacy API — returns dominant mode string. Uses decide_weights internally."""
        weights = self.decide_weights(odfs_prev, iam_streak, quantum_state)
        return self._last_mode

    @staticmethod
    def lr_scale(mode_or_weights) -> float:
        """Accept either str or dict[str,float]."""
        if isinstance(mode_or_weights, dict):
            # Weighted average of lr_scales
            scales = {"STABILIZE": 0.5, "TRANSITION": 1.0, "GROW": 1.5, "MEDITATION": 0.7}
            return sum(mode_or_weights.get(m, 0) * s for m, s in scales.items())
        return {"STABILIZE": 0.5, "TRANSITION": 1.0, "GROW": 1.5}.get(mode_or_weights, 1.0)

    @staticmethod
    def tau1(mode_or_weights) -> float:
        """Accept either str or dict[str,float]."""
        if isinstance(mode_or_weights, dict):
            taus = {"STABILIZE": 0.6, "TRANSITION": 0.55, "GROW": 0.5, "MEDITATION": 0.65}
            return sum(mode_or_weights.get(m, 0) * t for m, t in taus.items())
        return {"STABILIZE": 0.6, "TRANSITION": 0.55, "GROW": 0.5}.get(mode_or_weights, 0.6)
