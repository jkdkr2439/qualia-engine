"""D/db.py — Central SQLite database for Pete v4.
Single file: D/long_term/pete.db
Replaces all scattered JSON/pkl files in long_term/.

Tables:
  nodes           — SemanticNeuron store (node_store)
  cooc            — PPMI co-occurrence pairs (graph)
  grammar_scores  — GRAMMAR_STORE per structure type
  role_positions  — positional stats for role_classifier
  identity        — C_pos / C_neg anchor vectors
  patterns        — learned MasterPatterns from Dream Cycle

Usage:
  from D.db import PeteDB
  db = PeteDB()            # auto-creates / migrates
  db.upsert_node(node)
  db.load_nodes() → dict
"""
from __future__ import annotations
import sqlite3
import json
import time
from pathlib import Path
from contextlib import contextmanager

DB_PATH  = Path(__file__).parent / "long_term" / "pete.db"
ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# ── DDL ───────────────────────────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS nodes (
    node_id     TEXT PRIMARY KEY,
    surface     TEXT NOT NULL,
    emotion     REAL DEFAULT 0.0,
    logic       REAL DEFAULT 0.0,
    reflection  REAL DEFAULT 0.0,
    visual      REAL DEFAULT 0.0,
    language    REAL DEFAULT 0.0,
    intuition   REAL DEFAULT 0.0,
    H           REAL DEFAULT 0.0,
    W           REAL DEFAULT 0.5,
    Q           INTEGER DEFAULT 0,
    enlighten   INTEGER DEFAULT 0,
    role        TEXT DEFAULT NULL,
    phase       TEXT DEFAULT 'Vo',
    updated_at  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cooc (
    symbol_a    TEXT NOT NULL,
    symbol_b    TEXT NOT NULL,
    ppmi        REAL DEFAULT 0.0,
    updated_at  INTEGER DEFAULT 0,
    PRIMARY KEY (symbol_a, symbol_b)
);

CREATE TABLE IF NOT EXISTS grammar_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    structure   TEXT NOT NULL,
    score       REAL NOT NULL,
    tick        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_grammar ON grammar_scores(structure);

CREATE TABLE IF NOT EXISTS role_positions (
    node_id     TEXT PRIMARY KEY,
    pre_verb    INTEGER DEFAULT 0,
    post_verb   INTEGER DEFAULT 0,
    mid         INTEGER DEFAULT 0,
    end_pos     INTEGER DEFAULT 0,
    verb        INTEGER DEFAULT 0,
    total       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS identity (
    anchor_id   TEXT PRIMARY KEY,
    emotion     REAL DEFAULT 0.0,
    logic       REAL DEFAULT 0.0,
    reflection  REAL DEFAULT 0.0,
    visual      REAL DEFAULT 0.0,
    language    REAL DEFAULT 0.0,
    intuition   REAL DEFAULT 0.0,
    updated_at  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS patterns (
    name        TEXT PRIMARY KEY,
    language    TEXT NOT NULL,
    slot_order  TEXT NOT NULL,
    field_profile TEXT NOT NULL,
    context_gate TEXT NOT NULL,
    rhythm      TEXT DEFAULT 'medium',
    gap_level   TEXT DEFAULT 'mid',
    avg_score   REAL DEFAULT 0.0,
    use_count   INTEGER DEFAULT 0,
    updated_at  INTEGER DEFAULT 0
);
"""


class PeteDB:
    """Thin SQLite wrapper. One connection per instance. Thread-safe with WAL."""

    def __init__(self, path: str | Path = None):
        self._path = Path(path) if path else DB_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    @contextmanager
    def _tx(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self):
        self._conn.close()

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def upsert_node(self, node) -> None:
        """Insert or update a SemanticNeuron (object or dict)."""
        if isinstance(node, dict):
            nid = node.get("node_id") or node.get("id", "?")
            sf  = node.get("surface_form", nid)
            m   = node.get("meaning", {})
            H   = node.get("H", 0.0)
            W   = node.get("W", 0.5)
            Q   = int(node.get("Q", False))
            en  = node.get("enlightenment", 0)
            role= node.get("role")
            phase = node.get("phase", "Vo")
        else:
            nid = getattr(node, "node_id", "?")
            sf  = getattr(node, "surface_form", nid)
            m   = getattr(node, "meaning", {})
            H   = getattr(node, "H", 0.0)
            W   = getattr(node, "W", 0.5)
            Q   = int(getattr(node, "Q", False))
            en  = getattr(node, "enlightenment", 0)
            role= getattr(node, "role", None)
            phase = getattr(node, "phase", "Vo")

        if isinstance(m, dict):
            vals = [m.get(f, 0.0) for f in ODFS_FIELDS]
        else:
            vals = list(m) + [0.0] * (6 - len(m))

        self._conn.execute("""
            INSERT INTO nodes (node_id, surface, emotion, logic, reflection,
                               visual, language, intuition, H, W, Q,
                               enlighten, role, phase, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(node_id) DO UPDATE SET
              emotion=excluded.emotion, logic=excluded.logic,
              reflection=excluded.reflection, visual=excluded.visual,
              language=excluded.language, intuition=excluded.intuition,
              H=excluded.H, W=excluded.W, Q=excluded.Q,
              enlighten=excluded.enlighten, role=excluded.role,
              phase=excluded.phase, updated_at=excluded.updated_at
        """, [nid, sf] + vals + [H, W, Q, en, role, phase, int(time.time())])

    def bulk_upsert_nodes(self, nodes: list) -> None:
        with self._tx():
            for n in nodes:
                self.upsert_node(n)

    def load_nodes(self) -> dict:
        """Load all nodes as dict {node_id: dict}."""
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        result = {}
        for r in rows:
            r = dict(r)
            nid = r["node_id"]
            result[nid] = {
                "node_id":      nid,
                "surface_form": r["surface"],
                "meaning": {f: r[f] for f in ODFS_FIELDS},
                "H":            r["H"],
                "W":            r["W"],
                "Q":            bool(r["Q"]),
                "enlightenment":r["enlighten"],
                "role":         r["role"],
                "phase":        r["phase"],
            }
        return result

    def load_nodes_above_H(self, min_H: float = 1.0) -> dict:
        """Load only active nodes (H above threshold) — faster startup."""
        rows = self._conn.execute(
            "SELECT * FROM nodes WHERE H >= ?", [min_H]
        ).fetchall()
        result = {}
        for r in rows:
            r = dict(r)
            nid = r["node_id"]
            result[nid] = {
                "node_id":      nid,
                "surface_form": r["surface"],
                "meaning": {f: r[f] for f in ODFS_FIELDS},
                "H":            r["H"],
                "W":            r["W"],
                "Q":            bool(r["Q"]),
                "enlightenment":r["enlighten"],
                "role":         r["role"],
                "phase":        r["phase"],
            }
        return result

    def count_nodes(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    # ── PPMI Co-occurrence ────────────────────────────────────────────────────

    def upsert_cooc(self, a: str, b: str, ppmi: float) -> None:
        self._conn.execute("""
            INSERT INTO cooc (symbol_a, symbol_b, ppmi, updated_at)
            VALUES (?,?,?,?)
            ON CONFLICT(symbol_a,symbol_b) DO UPDATE SET
              ppmi=excluded.ppmi, updated_at=excluded.updated_at
        """, [a, b, ppmi, int(time.time())])

    def get_top_cooc(self, symbol: str, top_k: int = 10) -> list[tuple]:
        rows = self._conn.execute("""
            SELECT symbol_b, ppmi FROM cooc
            WHERE symbol_a=? ORDER BY ppmi DESC LIMIT ?
        """, [symbol, top_k]).fetchall()
        return [(r["symbol_b"], r["ppmi"]) for r in rows]

    def load_cooc_neighbors(self, node_id: str, min_ppmi: float = 0.5) -> set:
        """Return the set of neighbor node_ids for a given node (from cooc table).
        Used to populate node.members at startup so field_gravity works correctly.
        """
        rows = self._conn.execute("""
            SELECT symbol_b FROM cooc
            WHERE symbol_a=? AND ppmi >= ?
        """, [node_id, min_ppmi]).fetchall()
        return {r["symbol_b"] for r in rows}

    def load_all_cooc_neighbors(self, min_ppmi: float = 0.5) -> dict:
        """Return {node_id: set(neighbors)} for ALL nodes in one query.
        More efficient than calling load_cooc_neighbors() per node at startup.
        Filters to neighbors that also exist in the nodes table.
        """
        rows = self._conn.execute("""
            SELECT c.symbol_a, c.symbol_b
            FROM cooc c
            WHERE c.ppmi >= ?
        """, [min_ppmi]).fetchall()
        result: dict[str, set] = {}
        for r in rows:
            result.setdefault(r["symbol_a"], set()).add(r["symbol_b"])
        return result

    # ── Grammar Scores ────────────────────────────────────────────────────────

    def add_grammar_score(self, structure: str, score: float, tick: int = 0) -> None:
        self._conn.execute(
            "INSERT INTO grammar_scores (structure, score, tick) VALUES (?,?,?)",
            [structure, score, tick]
        )

    def get_grammar_scores(self) -> dict[str, list[float]]:
        """Return {structure: [scores]} matching grammar_learner._GRAMMAR_STORE."""
        rows = self._conn.execute(
            "SELECT structure, score FROM grammar_scores ORDER BY id"
        ).fetchall()
        result: dict[str, list] = {}
        for r in rows:
            result.setdefault(r["structure"], []).append(r["score"])
        return result

    def get_grammar_avg(self, structure: str) -> float:
        row = self._conn.execute(
            "SELECT AVG(score) as avg FROM grammar_scores WHERE structure=?",
            [structure]
        ).fetchone()
        return row["avg"] or 0.0

    def prune_grammar_scores(self, keep_last: int = 50) -> None:
        """Keep only last N scores per structure (avoid unbounded growth)."""
        structures = self._conn.execute(
            "SELECT DISTINCT structure FROM grammar_scores"
        ).fetchall()
        for row in structures:
            s = row["structure"]
            self._conn.execute("""
                DELETE FROM grammar_scores WHERE structure=? AND id NOT IN (
                  SELECT id FROM grammar_scores WHERE structure=?
                  ORDER BY id DESC LIMIT ?
                )
            """, [s, s, keep_last])

    # ── Role Positions ────────────────────────────────────────────────────────

    def increment_position(self, node_id: str, position: str) -> None:
        """Atomically increment a positional counter for a node."""
        col_map = {
            "pre_verb":  "pre_verb",
            "post_verb": "post_verb",
            "mid":       "mid",
            "end":       "end_pos",
            "verb":      "verb",
        }
        col = col_map.get(position, "total")
        self._conn.execute(f"""
            INSERT INTO role_positions (node_id, {col}, total)
            VALUES (?, 1, 1)
            ON CONFLICT(node_id) DO UPDATE SET
              {col} = {col} + 1, total = total + 1
        """, [node_id])

    def get_role_positions(self, node_id: str) -> dict:
        row = self._conn.execute(
            "SELECT * FROM role_positions WHERE node_id=?", [node_id]
        ).fetchone()
        if row:
            return dict(row)
        return {"pre_verb":0,"post_verb":0,"mid":0,"end_pos":0,"verb":0,"total":0}

    def load_all_role_assignments(self) -> dict[str, str]:
        """Load pre-computed role assignments from nodes table."""
        rows = self._conn.execute(
            "SELECT node_id, role FROM nodes WHERE role IS NOT NULL"
        ).fetchall()
        return {r["node_id"]: r["role"] for r in rows}

    def set_node_role(self, node_id: str, role: str) -> None:
        self._conn.execute(
            "UPDATE nodes SET role=? WHERE node_id=?", [role, node_id]
        )

    # ── Identity anchors ──────────────────────────────────────────────────────

    def save_identity(self, anchor_id: str, vec: list[float]) -> None:
        vals = list(vec) + [0.0] * (6 - len(vec))
        self._conn.execute("""
            INSERT INTO identity (anchor_id, emotion, logic, reflection,
                                  visual, language, intuition, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(anchor_id) DO UPDATE SET
              emotion=excluded.emotion, logic=excluded.logic,
              reflection=excluded.reflection, visual=excluded.visual,
              language=excluded.language, intuition=excluded.intuition,
              updated_at=excluded.updated_at
        """, [anchor_id] + vals[:6] + [int(time.time())])
        self._conn.commit()

    def load_identity(self, anchor_id: str) -> list[float] | None:
        row = self._conn.execute(
            "SELECT * FROM identity WHERE anchor_id=?", [anchor_id]
        ).fetchone()
        if not row: return None
        return [row[f] for f in ODFS_FIELDS]

    # ── Patterns ──────────────────────────────────────────────────────────────

    def upsert_pattern(self, name: str, language: str, slot_order: list,
                       field_profile: list, context_gate: str,
                       rhythm: str, gap_level: str,
                       avg_score: float = 0.0) -> None:
        self._conn.execute("""
            INSERT INTO patterns (name, language, slot_order, field_profile,
                                  context_gate, rhythm, gap_level, avg_score,
                                  use_count, updated_at)
            VALUES (?,?,?,?,?,?,?,?,0,?)
            ON CONFLICT(name) DO UPDATE SET
              avg_score=excluded.avg_score,
              use_count=use_count+1, updated_at=excluded.updated_at
        """, [name, language, json.dumps(slot_order), json.dumps(field_profile),
              context_gate, rhythm, gap_level, avg_score, int(time.time())])

    # ── Bulk commit helper ────────────────────────────────────────────────────

    def commit(self):
        self._conn.commit()

    def stats(self) -> dict:
        return {
            "nodes":          self.count_nodes(),
            "cooc_pairs":     self._conn.execute("SELECT COUNT(*) FROM cooc").fetchone()[0],
            "grammar_scores": self._conn.execute("SELECT COUNT(*) FROM grammar_scores").fetchone()[0],
            "role_positions": self._conn.execute("SELECT COUNT(*) FROM role_positions").fetchone()[0],
            "db_path":        str(self._path),
            "db_size_kb":     self._path.stat().st_size // 1024 if self._path.exists() else 0,
        }

    def __repr__(self):
        return f"PeteDB({self._path}, nodes={self.count_nodes()})"


# ── Global singleton ──────────────────────────────────────────────────────────
_INSTANCE: PeteDB | None = None

def get_db(path: str | Path = None) -> PeteDB:
    """Get global PeteDB singleton."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PeteDB(path)
    return _INSTANCE
