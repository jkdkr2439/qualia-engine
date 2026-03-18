"""
P/think/subconscious.py — Pete's Tiềm Thức (Subconscious) Layer

Role in P layer:
  After ODFS computes gap_vec (what Pete is missing relative to balanced field),
  the subconscious queries subconscious.db co-occurrence graph using chakra seed
  words as anchors, returning background semantic neighbors that Pete "feels"
  without consciously focusing on them.

  This is distinct from I layer's void expansion (which expands INPUT context).
  This expands Pete's INTERNAL OUTPUT CANDIDATE POOL from Pete's deep memory.

Architecture:
  I layer  → void.db        → expands what Pete *receives* from user
  P layer  → subconscious.db → expands what Pete *emits* from its own depth

Usage (called from p_engine during response preparation):
  from P.think.subconscious import SubconsciousLayer
  sub = SubconsciousLayer()
  words = sub.surface_from_gap(gap_vec, top_k=8)
"""
from __future__ import annotations
import sqlite3, math
from pathlib import Path

SUBCON_DB = Path(__file__).parent.parent / "HardMemory" / "subconscious.db"

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# Chakra seed words (Vietnamese) — anchors in subconscious.db
# Each chakra maps to ODFS field dominance
CHAKRA_SEEDS: dict[str, list[str]] = {
    "root":      ["đất", "sống", "sợ", "an", "thân", "ổn", "gốc", "sinh", "nền"],
    "sacral":    ["cảm", "xúc", "sáng", "tạo", "nước", "vui", "đam", "mê", "chảy"],
    "solar":     ["ý", "chí", "sức", "mạnh", "tự", "tin", "lửa", "hành", "động"],
    "heart":     ["yêu", "đồng", "tha", "gió", "kết", "nối", "tình", "thương", "mở"],
    "throat":    ["nói", "nghe", "thật", "biểu", "đạt", "ngôn", "ngữ", "lời", "tiếng"],
    "thirdeye":  ["trực", "giác", "hiểu", "nhìn", "nghĩa", "tưởng", "trí", "sáng", "suốt"],
    "crown":     ["thức", "toàn", "im", "lặng", "vũ", "trụ", "ngộ", "vô", "tịch"],
}

# Which ODFS fields each chakra is strong in (for gap matching)
CHAKRA_FIELDS: dict[str, dict[str, float]] = {
    "root":      {"emotion": 0.5, "logic": 0.6, "visual": 0.7},
    "sacral":    {"emotion": 0.9, "intuition": 0.7, "visual": 0.5},
    "solar":     {"logic": 0.8, "reflection": 0.7, "emotion": 0.4},
    "heart":     {"emotion": 0.8, "language": 0.7, "intuition": 0.6},
    "throat":    {"language": 0.9, "reflection": 0.6, "logic": 0.4},
    "thirdeye":  {"intuition": 0.9, "reflection": 0.8, "logic": 0.5},
    "crown":     {"reflection": 0.7, "intuition": 0.8, "emotion": 0.4},
}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a)) + 1e-9
    nb  = math.sqrt(sum(y * y for y in b)) + 1e-9
    return dot / (na * nb)


def _field_vec(chakra_name: str) -> list[float]:
    d = CHAKRA_FIELDS.get(chakra_name, {})
    return [d.get(f, 0.0) for f in ODFS_FIELDS]


class SubconsciousLayer:
    """
    Pete's P-layer subconscious: queries subconscious.db via chakra seeds
    to surface background semantic associations matching the gap vector.
    """

    def __init__(self):
        self._conn: sqlite3.Connection | None = None
        self._vocab: dict[str, int] = {}
        self._ready = False
        self._try_connect()

    def _try_connect(self):
        if not SUBCON_DB.exists():
            return
        try:
            self._conn = sqlite3.connect(str(SUBCON_DB), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA query_only=ON")
            # Cache vocab
            rows = self._conn.execute("SELECT word, id FROM vocab").fetchall()
            self._vocab = {r[0]: r[1] for r in rows}
            self._ready = True
        except Exception:
            self._conn = None

    @property
    def available(self) -> bool:
        return self._ready

    def neighbors_of(self, word: str, top_k: int = 8) -> list[str]:
        """Top-K co-occurrence neighbors of a word in subconscious."""
        if not self._ready:
            return []
        wid = self._vocab.get(word.lower())
        if wid is None:
            return []
        try:
            rows = self._conn.execute("""
                SELECT v.word FROM edges e
                JOIN vocab v ON v.id = e.dst
                WHERE e.src = ?
                ORDER BY e.weight DESC LIMIT ?
            """, (wid, top_k)).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    def best_chakra_for_gap(self, gap_vec: list[float]) -> str:
        """Find which chakra resonates most with this gap vector."""
        best, best_name = -1.0, "heart"
        for cname in CHAKRA_SEEDS:
            score = _cosine(gap_vec, _field_vec(cname))
            if score > best:
                best, best_name = score, cname
        return best_name

    def surface_from_gap(self, gap_vec: list[float],
                         top_chakras: int = 3,
                         seeds_per_chakra: int = 3,
                         neighbors_per_seed: int = 5) -> dict[str, list[str]]:
        """
        Core method: given a gap vector, find top chakras matching the gap,
        then expand each chakra's seed words via subconscious co-occurrence.

        Returns {chakra_name: [neighbor_words]}
        """
        if not self._ready:
            return {}

        # Rank all chakras by gap fit
        ranked = sorted(
            CHAKRA_SEEDS.keys(),
            key=lambda c: _cosine(gap_vec, _field_vec(c)),
            reverse=True
        )

        result = {}
        for chakra in ranked[:top_chakras]:
            seeds   = CHAKRA_SEEDS[chakra][:seeds_per_chakra]
            all_nb  = []
            seen    = set(seeds)
            for seed in seeds:
                for nb in self.neighbors_of(seed, top_k=neighbors_per_seed):
                    if nb not in seen:
                        all_nb.append(nb)
                        seen.add(nb)
            result[chakra] = all_nb

        return result

    def surface_report(self, gap_user: list[float],
                       gap_pete: list[float]) -> dict:
        """
        Full dual-gap surface report for debug/response generation.
        Returns all surfaced words tagged by which gap they came from.
        """
        user_words = self.surface_from_gap(gap_user)
        pete_words = self.surface_from_gap(gap_pete)

        all_u = [w for ws in user_words.values() for w in ws]
        all_p = [w for ws in pete_words.values() for w in ws]

        return {
            "gap_user": user_words,
            "gap_pete": pete_words,
            "pool_user": all_u,
            "pool_pete": all_p,
            "intersection": list(set(all_u) & set(all_p)),
        }
