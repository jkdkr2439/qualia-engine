"""P/working/active_nodes_cache.py — LRU cache for active working nodes."""
from __future__ import annotations
from collections import OrderedDict
import time

MAX_SIZE    = 200    # max nodes to keep in active cache
DECAY_RATE  = 0.99   # energy decay per tick for cached nodes
MIN_ENERGY  = 0.05   # below this → evict from cache


class ActiveNodesCache:
    """
    LRU cache for active semantic nodes.
    Nodes enter cache when activated; decay over time.
    Evicted when energy < MIN_ENERGY or cache full.
    """
    def __init__(self, max_size: int = MAX_SIZE):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max  = max_size

    def activate(self, node_id: str, node, energy: float = 1.0) -> None:
        """Add or refresh a node in the active cache."""
        if node_id in self._cache:
            self._cache.move_to_end(node_id)
            self._cache[node_id]["energy"] = min(self._cache[node_id]["energy"] + energy, 5.0)
        else:
            self._cache[node_id] = {
                "node_id":     node_id,
                "node":        node,
                "energy":      energy,
                "last_active": time.time(),
            }
            self._cache.move_to_end(node_id)

        # Evict if full
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)

    def decay_all(self) -> None:
        """Apply decay to all cached nodes. Evict dead ones."""
        dead = []
        for nid, entry in self._cache.items():
            entry["energy"] *= DECAY_RATE
            if entry["energy"] < MIN_ENERGY:
                dead.append(nid)
        for nid in dead:
            del self._cache[nid]

    def top(self, k: int = 20) -> list:
        """Return top k nodes by energy."""
        sorted_entries = sorted(
            self._cache.values(), key=lambda e: -e["energy"]
        )
        return [e["node"] for e in sorted_entries[:k]]

    def all_ids(self) -> list[str]:
        return list(self._cache.keys())

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
