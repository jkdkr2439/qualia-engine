"""P/think/lucis/lucis_1.py — L1 GUARDIAN: drifts, guards ODFS output, corrects via L0."""
from __future__ import annotations
import math
from .lucis_0 import Lucis0, LUCIS_0_VEC

THETA_SOFT = 0.3
THETA_HARD = 0.15
CORRECTION_RATE = 0.1

class Lucis1:
    """
    Guardian — can drift from L0 but self-corrects.
    Modulates tau thresholds based on P2 awareness.
    """
    def __init__(self):
        self.field_vec = list(LUCIS_0_VEC)
        self._l0       = Lucis0()
        self.drift_history: list[float] = []

    def guard(self, odfs_world, odfs_user, p2_result,
              attn_mode = "STABILIZE") -> dict:
        """
        Lucis1 verdict — synthesizes world + user ODFS.
        Returns LucisVerdict as dict.

        Gap 6: attn_mode can be str OR dict[str,float] (soft mode_weights).
        Gap 8: adds identity_gap_score = distance from Lucis0 anchor.
        """
        # Bug 1 fix: read p2.awareness (IAM/IAMNOT/SENSING/null), NOT p2.phase
        awareness  = (getattr(p2_result, "awareness",  None)
                      or (p2_result.get("awareness",  None) if isinstance(p2_result, dict) else None))
        iam_streak = (getattr(p2_result, "iam_streak", 0)
                      if hasattr(p2_result, "iam_streak") else p2_result.get("iam_streak", 0))

        # Modulate thresholds based on P2 awareness
        tau_hard = THETA_HARD * (0.8 if awareness == "IAM" else 1.0)
        tau_soft = THETA_SOFT * (1.2 if awareness == "IAMNOT" else 1.0)

        # Gap 6: accept str or dict
        from ...modes.attention_controller import AttentionController
        attn_tau1 = AttentionController.tau1(attn_mode)  # handles both str and dict

        # Classify response mode
        S_world = odfs_world.S_combined if hasattr(odfs_world, "S_combined") else odfs_world.get("S_combined", 0.5)
        S_user  = odfs_user.S_combined  if hasattr(odfs_user,  "S_combined") else odfs_user.get("S_combined", 0.5)
        R_world = odfs_world.R_final    if hasattr(odfs_world, "R_final")    else odfs_world.get("R_final", [1/6]*6)

        lucis_class = self._classify_mode(R_world)

        # Occasionally self-compare vs L0
        alignment = self._l0.alignment(self.field_vec)
        if alignment < 0.9:
            self._correct_drift()

        # Gap 8: identity_gap_score = how far current processing is from anchor
        identity_gap_score = max(0.0, min(1.0, 1.0 - alignment))

        return {
            "verdict":              odfs_world.verdict if hasattr(odfs_world, "verdict") else "QUARANTINE",
            "S_combined_world":     S_world,
            "S_combined_user":      S_user,
            "lucis_class":          lucis_class,
            "alignment_L0":         alignment,
            "theta_soft":           tau_soft,
            "theta_hard":           tau_hard,
            "iam_streak":           iam_streak,
            "identity_gap_score":   identity_gap_score,   # Gap 8
        }


    def _classify_mode(self, R: list) -> str:
        LUCIS_VEC    = LUCIS_0_VEC
        LINEAR_VEC   = [0.20,0.90,0.40,0.30,0.70,0.20]
        NONLINEAR_VEC= [0.70,0.20,0.50,0.60,0.30,0.90]
        sims = {
            "lucis":     self._cos(R, LUCIS_VEC),
            "linear":    self._cos(R, LINEAR_VEC),
            "nonlinear": self._cos(R, NONLINEAR_VEC),
        }
        return max(sims, key=sims.get)

    def _cos(self, a: list, b: list) -> float:
        dot = sum(x*y for x,y in zip(a,b))
        na  = math.sqrt(sum(x**2 for x in a))
        nb  = math.sqrt(sum(y**2 for y in b))
        if na==0 or nb==0: return 0.0
        return dot/(na*nb)

    def _correct_drift(self) -> None:
        for i in range(6):
            self.field_vec[i] += CORRECTION_RATE * (LUCIS_0_VEC[i] - self.field_vec[i])
        norm = math.sqrt(sum(x**2 for x in self.field_vec)) or 1.0
        self.field_vec = [x/norm for x in self.field_vec]
