"""P/think/lucis/lucis_2.py — L2 REFEREE: checks L1 drift vs L0, every N_L2=50 ticks.
NEVER modifies L1 — report only.
"""
from __future__ import annotations
import math
from .lucis_0 import LUCIS_0_VEC

N_L2 = 50                       # tick interval
L2_DRIFT_THRESHOLD  = 0.9       # below this → DRIFT_DETECTED
L2_CRITICAL_THRESHOLD = 0.3     # below this → CRITICAL


class Lucis2:
    """
    Referee — runs every N_L2 ticks.
    Compares L1.field_vec against frozen L0 vec.
    Result: status + alignment score (does NOT modify L1).
    """
    def __init__(self):
        self._tick = 0
        self._last_report: dict = {"status": "OK", "alignment": 1.0}

    def maybe_audit(self, l1_field_vec: list, tick_n: int) -> dict | None:
        """
        Run audit if tick_n divisible by N_L2. Otherwise return None.
        Returns dict: {status, alignment, field_gaps}
        """
        if tick_n % N_L2 != 0:
            return None
        return self._audit(l1_field_vec)

    def force_audit(self, l1_field_vec: list) -> dict:
        """Force audit regardless of tick count."""
        return self._audit(l1_field_vec)

    def _audit(self, l1_field_vec: list) -> dict:
        alignment = self._cosine(l1_field_vec, LUCIS_0_VEC)
        field_gaps = [abs(a - b) for a, b in zip(l1_field_vec, LUCIS_0_VEC)]

        if alignment < L2_CRITICAL_THRESHOLD:
            status = "CRITICAL"
        elif alignment < L2_DRIFT_THRESHOLD:
            status = "DRIFT_DETECTED"
        else:
            status = "OK"

        report = {
            "status":        status,
            "alignment":     round(alignment, 4),
            "field_gaps":    [round(g, 4) for g in field_gaps],
            "l2_threshold":  L2_DRIFT_THRESHOLD,
        }
        self._last_report = report
        return report

    def last_report(self) -> dict:
        return self._last_report

    @staticmethod
    def _cosine(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na  = math.sqrt(sum(x ** 2 for x in a))
        nb  = math.sqrt(sum(y ** 2 for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
