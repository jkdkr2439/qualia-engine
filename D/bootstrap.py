"""
D/bootstrap.py — Initialize D layer data files if missing.
Run once before starting Pete for the first time.
"""
import json, numpy as np
from pathlib import Path

BASE = Path(__file__).parent

def bootstrap():
    # ── C_pos / C_neg ─────────────────────────────────────────────────────
    mem = BASE / "long_term/memory"
    cp  = mem / "C_pos.npy"
    cn  = mem / "C_neg.npy"
    if not cp.exists():
        # Pete's positive identity anchor: balanced across all fields
        np.save(str(cp), np.array([0.30, 0.50, 0.70, 0.20, 0.60, 0.80], dtype=np.float32))
        print("[bootstrap] C_pos created")
    if not cn.exists():
        # NOT-Pete anchor: LINEAR (high logic, reflection, low emotion)
        # INVARIANT: C_neg != [0]*6
        np.save(str(cn), np.array([0.10, 0.80, 0.05, 0.70, 0.15, 0.05], dtype=np.float32))
        print("[bootstrap] C_neg created (LINEAR baseline)")

    # ── OMEGA matrices ─────────────────────────────────────────────────────
    odfs = BASE / "long_term/odfs_state"
    ow   = odfs / "omega_world.npy"
    ou   = odfs / "omega_user.npy"
    if not ow.exists() or not ou.exists():
        # 6 ODFS fields: emotion, logic, reflection, visual, language, intuition
        # Cluster A: emotion(0)↔intuition(5)=0.75
        # Cluster B: logic(1)↔reflection(2)=0.75
        # Cluster C: visual(3)↔language(4)=0.65
        O = np.full((6, 6), 0.25, dtype=np.float32)
        np.fill_diagonal(O, 0.0)
        O[0, 5] = O[5, 0] = 0.75
        O[1, 2] = O[2, 1] = 0.75
        O[3, 4] = O[4, 3] = 0.65
        np.save(str(ow), O)
        np.save(str(ou), O.copy())
        print("[bootstrap] OMEGA_WORLD + OMEGA_USER created")

    # ── node_store ────────────────────────────────────────────────────────
    ns = BASE / "long_term/node_store/node_store.json"
    if not ns.exists():
        ns.write_text("{}", encoding="utf-8")
        print("[bootstrap] node_store.json created (empty)")

    # ── plane_store ───────────────────────────────────────────────────────
    ps = BASE / "long_term/plane_store/planes.json"
    if not ps.exists():
        ps.write_text("[]", encoding="utf-8")
        print("[bootstrap] planes.json created (empty)")

    # ── cooc_graph ────────────────────────────────────────────────────────
    cg = BASE / "long_term/graph/cooc_graph.json"
    if not cg.exists():
        cg.write_text("{}", encoding="utf-8")
        print("[bootstrap] cooc_graph.json created (empty)")

    # ── identity_store / P2 ───────────────────────────────────────────────
    idf = BASE / "long_term/identity_store/p2_state.json"
    if not idf.exists():
        state = {"H": 0.0, "phase": "Vo", "iam_streak": 0, "null_streak": 0,
                 "meaning": [1/6]*6}
        idf.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print("[bootstrap] p2_state.json created")

    # ── dreamlinks ────────────────────────────────────────────────────────
    dl = BASE / "short_term/dreamlinks/dreamlinks.json"
    if not dl.exists():
        dl.write_text("[]", encoding="utf-8")
        print("[bootstrap] dreamlinks.json created")

    print("[bootstrap] D layer ready.")

if __name__ == "__main__":
    bootstrap()
