"""
D/db_gateway.py
═══════════════════════════════════════════════════════════════════════════════
Pete's Central Database Gateway — D Layer

Vị trí: D layer (long-term memory store)
Vai trò: Entry point duy nhất cho mọi database của Pete.
         Không component nào nên mở sqlite3 trực tiếp — luôn dùng gateway này.

Databases được quản lý:
  pete.db          — P-space nodes (SemanticNeuron), cooc table, identity anchors
  subconscious.db  — 70k word co-occurrence graph (void / tiềm thức)
  memory.db        — 800 words từ câu chuyện của Pete (episodic memory)
  pete_context.db  — Context expansions từ ODFS ingestion
  pete_framework.db— Core framework concepts (frameworks, models)
  pete_seeds.db    — Chakra seed words
  symbols.db       — Symbol/graph layer (concepts, relations)

Usage:
    from D.db_gateway import gateway

    # Node lookup
    node = gateway.get_node("chó")
    # Search across ALL databases
    results = gateway.search("yêu", top_k=10)
    # Neighbors từ subconscious
    neighbors = gateway.get_neighbors("chó", db="subconscious", top_k=8)
    # Raw SQL nếu cần
    rows = gateway.query("pete", "SELECT * FROM nodes WHERE H > 10 LIMIT 5")

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import sqlite3
import json
import math
import threading
from pathlib import Path
from typing import Any

# ── Database paths ────────────────────────────────────────────────────────────
_HERE  = Path(__file__).parent
_PETE4 = _HERE.parent

DATABASES: dict[str, Path] = {
    # D layer
    "pete":          _HERE / "long_term" / "pete.db",
    "symbols":       _HERE / "long_term" / "graph" / "symbols.db",
    # P/HardMemory  (linked from D layer gateway)
    "subconscious":  _PETE4 / "P" / "HardMemory" / "subconscious.db",
    "memory":        _PETE4 / "P" / "HardMemory" / "memory.db",
    "pete_context":  _PETE4 / "P" / "HardMemory" / "pete_context.db",
    "pete_framework":_PETE4 / "P" / "HardMemory" / "pete_framework.db",
    "pete_seeds":    _PETE4 / "P" / "HardMemory" / "pete_seeds.db",
}

# ── Thread-local connections (one per thread, auto-open) ─────────────────────
_local = threading.local()


class DBGateway:
    """
    Central access point for all Pete databases.
    Each method is explicit about which DB it touches.
    """

    # ── Connection management ─────────────────────────────────────────────────

    def _conn(self, db_name: str) -> sqlite3.Connection:
        """Get (or create) a thread-local connection to the given DB."""
        connections = getattr(_local, "connections", None)
        if not connections:
            _local.connections = {}
            connections = _local.connections

        if db_name not in connections:
            path = DATABASES.get(db_name)
            if path is None:
                raise ValueError(f"Unknown database: '{db_name}'. Known: {list(DATABASES)}")
            if not path.exists():
                raise FileNotFoundError(f"DB not found: {path}")
            conn = sqlite3.connect(str(path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            connections[db_name] = conn

        return connections[db_name]

    def close_all(self):
        """Close all connections on current thread."""
        conns = getattr(_local, "connections", {})
        for conn in conns.values():
            try: conn.close()
            except Exception: pass
        _local.connections = {}

    def available_dbs(self) -> dict[str, dict]:
        """Return info about all registered databases."""
        result = {}
        for name, path in DATABASES.items():
            result[name] = {
                "path":   str(path),
                "exists": path.exists(),
                "size_mb": round(path.stat().st_size / 1_048_576, 2) if path.exists() else 0,
            }
        return result

    # ── Raw query ─────────────────────────────────────────────────────────────

    def query(self, db: str, sql: str, params: tuple = ()) -> list[dict]:
        """
        Run arbitrary SELECT on any DB.
        Returns list of dicts.

        Example:
            gateway.query("pete", "SELECT word, H FROM nodes WHERE H > 10 LIMIT 20")
        """
        conn = self._conn(db)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def execute(self, db: str, sql: str, params: tuple = ()) -> int:
        """
        Run INSERT/UPDATE/DELETE on any DB.
        Returns rowcount.
        """
        conn = self._conn(db)
        cur  = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount

    # ── pete.db — P-space nodes ───────────────────────────────────────────────

    def get_node(self, word: str) -> dict | None:
        """
        Get a node from pete.db by node_id.
        Returns dict with ODFS fields: emotion, logic, reflection, visual, language, intuition
        Plus: H, W, Q, enlighten, role, phase.
        """
        rows = self.query(
            "pete",
            "SELECT node_id, surface, emotion, logic, reflection, visual, language, intuition, "
            "H, W, Q, enlighten, role, phase FROM nodes WHERE node_id = ?",
            (word,)
        )
        if not rows:
            return None
        nd = dict(rows[0])
        # Build meaning dict for convenience
        nd["meaning"] = {
            "emotion":    nd["emotion"],
            "logic":      nd["logic"],
            "reflection": nd["reflection"],
            "visual":     nd["visual"],
            "language":   nd["language"],
            "intuition":  nd["intuition"],
        }
        return nd

    def search_nodes(self, q: str, top_k: int = 10) -> list[dict]:
        """
        Search pete.db nodes by prefix/substring match on node_id.
        Sorted by H (activation) descending.
        """
        return self.query(
            "pete",
            "SELECT node_id, surface, H, W, role, phase FROM nodes "
            "WHERE node_id LIKE ? ORDER BY H DESC LIMIT ?",
            (f"%{q}%", top_k)
        )

    def get_top_nodes(self, top_k: int = 20, min_H: float = 0.0) -> list[dict]:
        """Get highest-activation nodes from pete.db."""
        return self.query(
            "pete",
            "SELECT node_id, surface, H, W, role, phase FROM nodes "
            "WHERE H >= ? ORDER BY H DESC LIMIT ?",
            (min_H, top_k)
        )

    def upsert_node(self, word: str, H: float, W: float = 0.5,
                    meaning: dict | None = None) -> None:
        """
        Insert or update a node in pete.db.
        meaning = dict with keys: emotion, logic, reflection, visual, language, intuition
        """
        m = meaning or {}
        self.execute(
            "pete",
            """INSERT INTO nodes
               (node_id, surface, emotion, logic, reflection, visual, language, intuition, H, W)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(node_id) DO UPDATE SET
                   H = MAX(H, excluded.H),
                   W = excluded.W""",
            (word, word,
             m.get("emotion",0.167), m.get("logic",0.167),
             m.get("reflection",0.167), m.get("visual",0.167),
             m.get("language",0.167), m.get("intuition",0.167),
             H, W)
        )

    def get_cooc_neighbors(self, word: str, top_k: int = 10,
                           min_ppmi: float = 0.3) -> list[dict]:
        """
        Get co-occurrence neighbors from pete.db cooc table.
        Returns: [{neighbor, ppmi}, ...]
        """
        return self.query(
            "pete",
            """SELECT symbol_b as neighbor, ppmi
               FROM cooc WHERE symbol_a = ? AND ppmi >= ?
               ORDER BY ppmi DESC LIMIT ?""",
            (word, min_ppmi, top_k)
        )

    def get_patterns(self, language: str = "vi", top_k: int = 10) -> list[dict]:
        """Get learned sentence patterns from pete.db."""
        return self.query(
            "pete",
            "SELECT name, slot_order, context_gate, rhythm, gap_level, avg_score "
            "FROM patterns WHERE language = ? ORDER BY avg_score DESC LIMIT ?",
            (language, top_k)
        )

    def get_identity(self) -> dict:
        """Get Pete's identity anchors (C_pos, C_neg) as ODFS vectors."""
        rows = self.query("pete",
            "SELECT anchor_id, emotion, logic, reflection, visual, language, intuition "
            "FROM identity")
        return {r["anchor_id"]: dict(r) for r in rows}

    def node_count(self, db: str = "pete") -> int:
        """Count total nodes/vocab in a DB."""
        col_map = {
            "pete": "nodes", "symbols": "nodes",
            "subconscious": "vocab", "memory": "vocab",
            "pete_context": "vocab", "pete_framework": "vocab", "pete_seeds": "vocab",
        }
        table = col_map.get(db, "vocab")
        rows  = self.query(db, f"SELECT COUNT(*) as cnt FROM {table}")
        return rows[0]["cnt"] if rows else 0

    # ── subconscious.db / memory.db — vocab + edges ───────────────────────────

    def get_vocab_id(self, db: str, word: str) -> int | None:
        """Get vocab id for a word in subconscious/memory DB."""
        rows = self.query(db, "SELECT id FROM vocab WHERE word = ?", (word,))
        return rows[0]["id"] if rows else None

    def get_neighbors(self, word: str, db: str = "subconscious",
                      top_k: int = 10, min_weight: float = 0.05) -> list[dict]:
        """
        Get co-occurrence neighbors of a word from subconscious or memory DB.
        Returns: [{word, weight}, ...]
        """
        wid = self.get_vocab_id(db, word)
        if wid is None:
            return []
        rows = self.query(
            db,
            """SELECT v.word, e.weight
               FROM edges e
               JOIN vocab v ON v.id = e.dst
               WHERE e.src = ? AND e.weight >= ?
               ORDER BY e.weight DESC LIMIT ?""",
            (wid, min_weight, top_k)
        )
        return [dict(r) for r in rows]

    def search_vocab(self, db: str, q: str, top_k: int = 10) -> list[dict]:
        """Search vocab table by substring match."""
        return self.query(
            db,
            "SELECT id, word FROM vocab WHERE word LIKE ? LIMIT ?",
            (f"%{q}%", top_k)
        )

    # ── Cross-database lookup ─────────────────────────────────────────────────

    def search(self, q: str, top_k: int = 10) -> dict[str, list]:
        """
        Search across ALL Pete databases simultaneously.
        Returns results grouped by database.
        """
        results = {}
        # pete.db — nodes table (uses node_id column)
        try:
            results["pete"] = self.search_nodes(q, top_k)
        except Exception as e:
            results["pete"] = [{"error": str(e)}]

        # vocab-based databases
        for db in ("subconscious", "memory", "pete_context", "pete_framework", "pete_seeds"):
            try:
                results[db] = self.search_vocab(db, q, top_k)
            except Exception as e:
                results[db] = [{"error": str(e)}]

        return results

    def word_profile(self, word: str) -> dict:
        """
        Full profile of a word across all Pete's databases.
        P-space state, subconscious neighbors, episodic memory, chakra seeds.
        This is Pete's 'what do I know about X?' method.
        """
        profile: dict[str, Any] = {"word": word}

        # P-space state
        profile["p_space"] = self.get_node(word)
        # Cooc neighbors from pete.db itself
        profile["cooc_neighbors"] = self.get_cooc_neighbors(word, top_k=5)

        # Subconscious neighbors
        profile["subconscious_neighbors"] = self.get_neighbors(
            word, "subconscious", top_k=8)

        # Episodic memory
        mem_id = self.get_vocab_id("memory", word)
        profile["in_memory"]  = mem_id is not None
        if mem_id:
            profile["memory_neighbors"] = self.get_neighbors(
                word, "memory", top_k=5)

        # Chakra seeds
        profile["in_context"]   = self.get_vocab_id("pete_context", word) is not None
        profile["in_seeds"]     = self.get_vocab_id("pete_seeds", word) is not None
        profile["in_framework"] = self.get_vocab_id("pete_framework", word) is not None

        return profile

    # ── Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """
        Return health stats for all Pete databases.
        Call this to quickly check Pete's memory state.
        """
        s = {}
        col_map = {
            "pete":          ("nodes",  "word"),
            "symbols":       ("nodes",  "name"),   # guess — might differ
            "subconscious":  ("vocab",  "word"),
            "memory":        ("vocab",  "word"),
            "pete_context":  ("vocab",  "word"),
            "pete_framework":("vocab",  "word"),
            "pete_seeds":    ("vocab",  "word"),
        }
        for db_name, path in DATABASES.items():
            if not path.exists():
                s[db_name] = {"status": "missing", "path": str(path)}
                continue
            try:
                table, col = col_map.get(db_name, ("vocab", "word"))
                rows = self.query(db_name,
                    f"SELECT COUNT(*) as cnt FROM {table}")
                cnt = rows[0]["cnt"] if rows else "?"
                s[db_name] = {
                    "status":  "ok",
                    "records": cnt,
                    "size_mb": round(path.stat().st_size / 1_048_576, 2),
                    "path":    str(path),
                }
            except Exception as e:
                s[db_name] = {"status": "error", "error": str(e), "path": str(path)}
        return s

    # ── Dump for Pete's self-awareness ────────────────────────────────────────

    def snapshot(self, top_k: int = 50) -> dict:
        """
        Compact snapshot of Pete's current memory state.
        Used by P-layer for self-reflection / identity anchoring.
        """
        top    = self.get_top_nodes(top_k=top_k, min_H=5.0)
        totals = {}
        for db in ("pete", "subconscious", "memory"):
            totals[db] = self.node_count(db)
        identity = self.get_identity()
        return {
            "top_active_nodes": top,
            "totals":           totals,
            "identity":         identity,
            "summary": (
                f"Pete has {totals['pete']:,} active concepts. "
                f"Subconscious: {totals['subconscious']:,} words. "
                f"Episodic memory: {totals['memory']:,} words."
            ),
        }

    def __repr__(self) -> str:
        dbs = [n for n, p in DATABASES.items() if p.exists()]
        return f"<DBGateway: {len(dbs)} databases online>"


# ── Module-level singleton — import trực tiếp ────────────────────────────────
#
#   from D.db_gateway import gateway
#
#   gateway.get_node("love")
#   gateway.search("chó")
#   gateway.stats()
#   gateway.word_profile("fear")
#
gateway = DBGateway()
