"""D/build_patterns.py — Build initial MasterPatterns from role_positions data.

Run after migrate_cooc.py.
Uses top Chuyen (verb) nodes from role_positions to construct minimal
sentence patterns: [Dan → Chuyen → Dung] and [Dan → Chuyen].

These seed the `patterns` table so surface_realizer.match_pattern() can work.

Usage (from Pete_4 root):
  python D/build_patterns.py
"""
import sys, json, time
from pathlib import Path

PETE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PETE_ROOT))

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def compute_field_profile(node_ids: list, db) -> list:
    """Average meaning vector for a list of node_ids."""
    total = [0.0] * 6
    count = 0
    for nid in node_ids:
        row = db._conn.execute(
            "SELECT emotion,logic,reflection,visual,language,intuition FROM nodes WHERE node_id=?",
            [nid]
        ).fetchone()
        if row:
            for i, f in enumerate(ODFS_FIELDS):
                total[i] += row[i]
            count += 1
    if count == 0:
        return [1/6] * 6
    return [v / count for v in total]


def build_patterns(db):
    # 1. Get top Chuyen nodes (verbs) from role_positions
    rows = db._conn.execute("""
        SELECT rp.node_id, rp.verb, rp.total
        FROM role_positions rp
        JOIN nodes n ON n.node_id = rp.node_id
        WHERE rp.verb > 0 AND rp.total > 3
        ORDER BY CAST(rp.verb AS REAL)/CAST(rp.total AS REAL) DESC
        LIMIT 100
    """).fetchall()

    chuyen_nodes = [r["node_id"] for r in rows]
    print(f"  Top Chuyen nodes: {len(chuyen_nodes)} (e.g. {chuyen_nodes[:5]})")

    # 2. Get top Dan nodes (pre-verb / subject-like)
    dan_rows = db._conn.execute("""
        SELECT rp.node_id
        FROM role_positions rp
        JOIN nodes n ON n.node_id = rp.node_id
        WHERE rp.pre_verb > 0 AND rp.total > 3
        ORDER BY CAST(rp.pre_verb AS REAL)/CAST(rp.total AS REAL) DESC
        LIMIT 50
    """).fetchall()
    dan_nodes = [r["node_id"] for r in dan_rows]

    # 3. Get top Dung nodes (stable/post-verb objects)
    dung_rows = db._conn.execute("""
        SELECT rp.node_id
        FROM role_positions rp
        JOIN nodes n ON n.node_id = rp.node_id
        WHERE rp.post_verb > 0 AND rp.total > 3
        ORDER BY CAST(rp.post_verb AS REAL)/CAST(rp.total AS REAL) DESC
        LIMIT 50
    """).fetchall()
    dung_nodes = [r["node_id"] for r in dung_rows]

    # 4. Build patterns
    patterns = []

    # Pattern class A: [Dan, Chuyen, Dung] — full SVO
    fp_a = compute_field_profile(dan_nodes[:10] + chuyen_nodes[:10] + dung_nodes[:10], db)
    for i, c_node in enumerate(chuyen_nodes[:20]):
        name = f"vi_SVO_{i:02d}"
        patterns.append({
            "name": name,
            "language": "vi",
            "slot_order": ["Dan", "Chuyen", "Dung"],
            "field_profile": fp_a,
            "context_gate": "SAY",
            "rhythm": "medium",
            "gap_level": "mid",
        })

    # Pattern class B: [Dan, Chuyen] — minimal SV
    fp_b = compute_field_profile(dan_nodes[:10] + chuyen_nodes[:10], db)
    for i, c_node in enumerate(chuyen_nodes[:20]):
        name = f"vi_SV_{i:02d}"
        patterns.append({
            "name": name,
            "language": "vi",
            "slot_order": ["Dan", "Chuyen"],
            "field_profile": fp_b,
            "context_gate": "SAY",
            "rhythm": "short",
            "gap_level": "low",
        })

    # Pattern class C: [Chuyen, Dung] — predicate-object (starting with verb, common in VI)
    fp_c = compute_field_profile(chuyen_nodes[:10] + dung_nodes[:10], db)
    for i in range(10):
        name = f"vi_VO_{i:02d}"
        patterns.append({
            "name": name,
            "language": "vi",
            "slot_order": ["Chuyen", "Dung"],
            "field_profile": fp_c,
            "context_gate": "SAY",
            "rhythm": "short",
            "gap_level": "low",
        })

    # Pattern class D: single Hoai (reflective) — just a node with reflection field
    fp_d = [0.1, 0.1, 0.6, 0.1, 0.3, 0.4]  # reflection + intuition dominant
    for i in range(5):
        name = f"vi_REFLECT_{i:02d}"
        patterns.append({
            "name": name,
            "language": "vi",
            "slot_order": ["Hoai"],
            "field_profile": fp_d,
            "context_gate": "THINK",
            "rhythm": "short",
            "gap_level": "high",
        })

    # 5. Upsert into DB
    conn = db._conn
    for p in patterns:
        conn.execute("""
            INSERT INTO patterns (name, language, slot_order, field_profile,
                                  context_gate, rhythm, gap_level, avg_score,
                                  use_count, updated_at)
            VALUES (?,?,?,?,?,?,?,0.5,0,?)
            ON CONFLICT(name) DO NOTHING
        """, [
            p["name"], p["language"],
            json.dumps(p["slot_order"]),
            json.dumps(p["field_profile"]),
            p["context_gate"], p["rhythm"], p["gap_level"],
            int(time.time())
        ])
    conn.commit()

    return len(patterns)


def main():
    from D.db import get_db
    db = get_db()

    print("=" * 55)
    print("Pete v4 — Build Initial MasterPatterns")
    print(f"role_positions available: {db._conn.execute('SELECT COUNT(*) FROM role_positions').fetchone()[0]:,}")
    print("=" * 55)

    n = build_patterns(db)
    print(f"\nDone: {n} patterns inserted into `patterns` table")
    print(f"DB state: {db.stats()}")


if __name__ == "__main__":
    main()
