"""
P/HardMemory/hard_memory_loader.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Loads subconscious.db and memory.db into P-space node_store format.

Both DBs use the same schema:
  vocab(id INTEGER PK, word TEXT UNIQUE)
  edges(src INTEGER, dst INTEGER, weight REAL, last_sent INTEGER)

Strategy:
  - Each word → one node_store entry (SemanticNeuron-compatible dict)
  - ODFS meaning vector = computed from edge connectivity pattern:
      • emotion     ← neighbors with high weight variance (emotional signal = uncertainty)
      • logic       ← neighbors with consistent weight (stable semantic relations)
      • reflection  ← words co-occurring with abstract/introspective words
      • visual      ← words with many unique neighbors (rich sensory cloud)
      • language    ← high overall degree (grammatical/functional)
      • intuition   ← rare edge weight distribution (outlier connectivity)
  - H (activation) = log(degree) / log(max_degree) — more connected = higher H
  - members = set of neighbor word strings (for field_gravity, 2-hop expansion)

Design:
  subconscious.db → load ALL 70k words (for lookup/neighbor access)
  memory.db       → load ALL 805 words (Pete's story vocabulary)
  Both merged into node_store, memory.db words get a MEMORY tag (higher "intuition")
  
  Nodes from HardMemory will NOT overwrite existing pete.db nodes (coexist).
  HardMemory nodes get H=0 initially (not activated in P-space until touched).
  This prevents the 3k function-word nodes from dominating — HardMemory nodes
  start silent and only activate when semantically relevant.
"""
from __future__ import annotations
import sqlite3
import math
from pathlib import Path

HARD_MEM_DIR = Path(__file__).parent
SUBCON_DB    = HARD_MEM_DIR / "subconscious.db"
MEMORY_DB    = HARD_MEM_DIR / "memory.db"

ODFS_FIELDS  = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# Stop words — never create nodes for these
STOP_WORDS = {
    "the","a","an","is","are","was","were","be","been","being",
    "this","that","these","those","it","its","and","or","but","not",
    "to","of","in","on","at","for","with","by","from",
    "và","hay","của","với","là","có","không","được","để","cho",
    "các","một","những","trong","ngoài","vì","nên","thì","mà",
    "đang","đã","sẽ","vẫn","cứ","vừa","mới","đều","cũng",
    "phải","cần","muốn","thể","hoặc","đó","đây","kia","ấy",
    "vậy","thế","rồi","nào","gì","sao","thôi","à","ừ","ơi","ồ",
    "nhé","nhỉ","nha","làm","cái","con",
    # pronouns
    "tao","mày","tôi","bạn","anh","chị","em","nó","mình","họ",
}


def _compute_meaning(
    word_id: int,
    all_edges: dict[int, list[tuple[int, float]]],
    max_degree: int,
    is_memory: bool = False,
) -> dict:
    """
    Compute ODFS meaning vector from edge connectivity.
    Returns dict {field: float} summing to 1.0.
    """
    edges_out = all_edges.get(word_id, [])
    degree    = len(edges_out)
    
    if degree == 0:
        # Isolated word: uniform distribution
        return {f: 1/6 for f in ODFS_FIELDS}
    
    weights = [w for _, w in edges_out]
    mean_w  = sum(weights) / degree
    
    # Variance of edge weights → maps to emotion (unpredictability)
    var_w   = sum((w - mean_w)**2 for w in weights) / degree
    
    # Range of weights → visual richness
    max_w   = max(weights)
    min_w   = min(weights)
    range_w = max_w - min_w
    
    # Degree (connectivity) → language (high degree = functional word)
    norm_degree = math.log(degree + 1) / math.log(max_degree + 1)
    
    # Mean weight → logic (stable, strong connections = logical anchoring)
    norm_mean = min(1.0, mean_w * 2)
    
    # Outlier score: max_w / (mean_w + 1e-9) → intuition (spike = intuitive leap)
    outlier = min(1.0, (max_w - mean_w) / (mean_w + 1e-9))
    
    # reflection = inverse degree (low connectivity = introspective/rare word)
    reflection = 1.0 - norm_degree
    
    # memory override: boost intuition and reflection
    if is_memory:
        outlier    = min(1.0, outlier * 1.5)
        reflection = min(1.0, reflection * 1.3)
    
    raw = {
        "emotion":    var_w,
        "logic":      norm_mean,
        "reflection": reflection,
        "visual":     range_w,
        "language":   norm_degree,
        "intuition":  outlier,
    }
    
    total = sum(raw.values()) + 1e-9
    return {f: raw[f] / total for f in ODFS_FIELDS}


def _load_single_db(
    db_path: Path,
    is_memory: bool = False,
    max_vocab: int = 70_000,
) -> dict[str, dict]:
    """
    Load vocab + edges from one HardMemory DB.
    Returns: {word: node_dict} compatible with P-space node_store.
    """
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Load vocab
    rows  = conn.execute("SELECT id, word FROM vocab LIMIT ?", [max_vocab]).fetchall()
    id2w  = {r["id"]: r["word"] for r in rows}
    w2id  = {r["word"]: r["id"] for r in rows}

    # Load all edges
    all_edges: dict[int, list[tuple[int, float]]] = {}
    edge_rows = conn.execute(
        "SELECT src, dst, weight FROM edges WHERE weight > 0.05"
    ).fetchall()
    for er in edge_rows:
        all_edges.setdefault(er["src"], []).append((er["dst"], er["weight"]))

    conn.close()

    max_degree = max((len(v) for v in all_edges.values()), default=1)

    result = {}
    for wid, word in id2w.items():
        if not word or len(word) < 2 or word.lower() in STOP_WORDS:
            continue
        if len(word) > 40:
            continue

        meaning = _compute_meaning(wid, all_edges, max_degree, is_memory)

        # Collect neighbor words (string set for members)
        neighbor_ids = [dst for dst, _ in all_edges.get(wid, [])[:20]]
        members      = {id2w[nid] for nid in neighbor_ids if nid in id2w}

        # H = logarithmic activation scaled to degree
        degree = len(all_edges.get(wid, []))
        H      = round(math.log(degree + 1) / math.log(max_degree + 1) * 8.0, 3)
        # Memory words slightly higher H (more salient in Pete's mind)
        if is_memory:
            H = min(12.0, H * 1.5)

        result[word] = {
            "node_id":       word,
            "surface_form":  word,
            "meaning":       meaning,
            "H":             H,
            "W":             0.5,
            "Q":             False,
            "enlightenment": 0,
            "role":          None,
            "phase":         "Vo",
            "members":       members,
            "_source":       "memory" if is_memory else "subconscious",
        }

    return result


class HardMemoryLoader:
    """
    Loads subconscious.db + memory.db into P-space _node_store.
    
    Usage:
        loader = HardMemoryLoader()
        loader.load_into(engine._node_store)
    """

    def __init__(self):
        self._sub_nodes: dict | None = None
        self._mem_nodes: dict | None = None

    def load_all(self, force: bool = False) -> tuple[dict, dict]:
        """Load both DBs. Cached after first load."""
        if self._sub_nodes is None or force:
            print("[HardMemory] Loading subconscious.db ...")
            self._sub_nodes = _load_single_db(SUBCON_DB, is_memory=False)
            print(f"[HardMemory]   -> {len(self._sub_nodes):,} words from subconscious.db")

        if self._mem_nodes is None or force:
            print("[HardMemory] Loading memory.db ...")
            self._mem_nodes = _load_single_db(MEMORY_DB, is_memory=True)
            print(f"[HardMemory]   -> {len(self._mem_nodes):,} words from memory.db")

        return self._sub_nodes, self._mem_nodes

    def load_into(self, node_store: dict, overwrite: bool = False) -> int:
        """
        Merge HardMemory nodes into existing node_store.
        
        Priority: pete.db nodes (already in store) > memory.db > subconscious.db
        Unless overwrite=True.
        
        All nodes are wrapped as SemanticNeuron objects so p_engine can access
        .meaning / .phase / .H / .T_field attributes without AttributeError.
        
        Returns: number of new nodes added.
        """
        from ..think.semantic.neuron.neuron import SemanticNeuron

        sub_nodes, mem_nodes = self.load_all()

        added = 0

        # Add subconscious first (lower priority)
        for word, nd in sub_nodes.items():
            if word not in node_store or overwrite:
                node_store[word] = SemanticNeuron.from_dict(nd)
                added += 1

        # Add memory nodes (higher priority — may overwrite subconscious)
        for word, nd in mem_nodes.items():
            if word not in node_store or overwrite:
                node_store[word] = SemanticNeuron.from_dict(nd)
                added += 1
            else:
                # Boost H of existing node if it's in memory (Pete knows this word deeply)
                existing = node_store[word]
                if isinstance(existing, dict):
                    existing["H"] = min(15.0, existing.get("H", 0) + 2.0)
                else:
                    try:
                        existing.H = min(15.0, getattr(existing, "H", 0) + 2.0)
                    except Exception:
                        pass

        return added

    def get_neighbors(self, word: str, top_k: int = 10) -> list[str]:
        """
        Get co-occurrence neighbors of a word from HardMemory.
        Tries subconscious first, then memory.
        """
        sub_nodes, mem_nodes = self.load_all()
        
        nd = mem_nodes.get(word) or sub_nodes.get(word)
        if nd is None:
            return []
        
        members = nd.get("members", set())
        return list(members)[:top_k]


# ── Module-level singleton ────────────────────────────────────────────────────
_LOADER: HardMemoryLoader | None = None

def get_loader() -> HardMemoryLoader:
    global _LOADER
    if _LOADER is None:
        _LOADER = HardMemoryLoader()
    return _LOADER
