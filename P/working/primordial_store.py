"""P/working/primordial_store.py — Persistent pre-linguistic primordial cache.
Wraps the in-memory list of PreLinguisticPrimordials with save/load to D/short_term/.
"""
from __future__ import annotations
import json
from pathlib import Path

D_PATH = Path(__file__).parent.parent.parent / "D" / "short_term" / "primordials"


class PrimordialStore:
    """
    Storage and retrieval for pre-linguistic primordial structures.
    Backed by D/short_term/primordials/ (JSON).
    """
    def __init__(self):
        self._store: list[dict] = []
        D_PATH.mkdir(parents=True, exist_ok=True)
        self._load()

    def add(self, prim: dict) -> None:
        """Add a new primordial (dict or object-as-dict)."""
        if hasattr(prim, "to_dict"):
            prim = prim.to_dict()
        self._store.append(prim)

    def all(self) -> list[dict]:
        return list(self._store)

    def count(self) -> int:
        return len(self._store)

    def prune(self, min_weight: float = 0.03) -> int:
        """Remove primordials below weight threshold. Returns count removed."""
        before = len(self._store)
        self._store = [p for p in self._store if p.get("weight", 0) >= min_weight]
        return before - len(self._store)

    def save(self) -> None:
        out = D_PATH / "primordials.json"
        try:
            out.write_text(json.dumps(self._store, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        except Exception as e:
            print(f"[PrimordialStore] save error: {e}")

    def _load(self) -> None:
        f = D_PATH / "primordials.json"
        if f.exists():
            try:
                self._store = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                self._store = []
