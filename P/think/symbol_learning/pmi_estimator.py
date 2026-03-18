"""P/think/symbol_learning/pmi_estimator.py — PPMI matrix."""
from __future__ import annotations
import math
from collections import defaultdict

class PPMIEstimator:
    """
    Point-wise Mutual Information (positive only).
    PPMI(a,b) = max(0, log P(a,b) / P(a)P(b))
    denom = total_tokens * window_size * 2  (invariant)
    """
    def __init__(self, window: int = 3):
        self.window   = window
        self._cooc:   dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._freq:   dict[str, int] = defaultdict(int)
        self._total:  int = 0

    def update(self, center: str, neighbor: str, count: int = 1) -> None:
        self._cooc[center][neighbor] += count
        self._cooc[neighbor][center] += count
        self._freq[center]   += count
        self._freq[neighbor] += count
        self._total          += count

    def ppmi(self, a: str, b: str) -> float:
        if self._total == 0: return 0.0
        c_ab = self._cooc.get(a, {}).get(b, 0)
        if c_ab == 0: return 0.0
        denom = self._total * self.window * 2
        p_ab  = c_ab / denom
        p_a   = self._freq.get(a, 0) / denom
        p_b   = self._freq.get(b, 0) / denom
        if p_a <= 0 or p_b <= 0: return 0.0
        return max(0.0, math.log(p_ab / (p_a * p_b) + 1e-12))

    def top_neighbors(self, node_id: str, k: int = 5) -> list[tuple[str, float]]:
        neighbors = self._cooc.get(node_id, {})
        scored = [(n, self.ppmi(node_id, n)) for n in neighbors]
        scored.sort(key=lambda x: -x[1])
        return scored[:k]

    def load_cooc(self, cooc: dict) -> None:
        for c, neighbors in cooc.items():
            for n, cnt in neighbors.items():
                self._cooc[c][n] = cnt
                self._freq[c]   += cnt
                self._total     += cnt

    def to_cooc_dict(self) -> dict:
        return {c: dict(nb) for c, nb in self._cooc.items()}
