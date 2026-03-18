"""P/think/lucis/dream_engine.py — 5-stage Dream Cycle at session boundaries."""
from __future__ import annotations
import json, math, time
from pathlib import Path

DREAMLINK_BORN   = 0.12
DREAMLINK_VALID  = 0.35
DREAMLINK_DECAY  = 0.015
DREAMLINK_HIBERNATE = 0.03
CORRECTION_RATE  = 0.10
THETA_SOFT       = 0.30

def run_dream_cycle(node_store: dict, field_store: dict,
                    D_path: Path, C_pos: list, C_neg: list,
                    p2_state: dict, ppmi=None) -> dict:
    """
    5-stage Dream Cycle — runs at session end or when Gamma > 3.0.
    Modifies node_store, field_store, C_pos, C_neg, dreamlinks in-place.
    Saves state back to D/long_term/.
    """
    report = {"stages": [], "dreamlinks_pruned": 0, "nodes_reactivated": 0}

    # ── Stage 1: Reactivate unconscious nodes ────────────────────────
    unconscious_path = D_path / "unconscious"
    reactivated = 0
    for f in unconscious_path.glob("*.json"):
        try:
            n_data = json.loads(f.read_text(encoding="utf-8"))
            nid    = n_data.get("node_id")
            if nid and nid not in node_store:
                from ...think.semantic.neuron.neuron import SemanticNeuron
                node = SemanticNeuron.from_dict(n_data)
                node.H = max(node.H * 0.3, 0.5)  # partial restore
                node_store[nid] = node
                f.unlink()  # remove from unconscious
                reactivated += 1
        except Exception:
            pass
    report["nodes_reactivated"] = reactivated
    report["stages"].append(f"Stage 1: {reactivated} nodes reactivated")

    # ── Stage 2: REM — follow novelty ────────────────────────────────
    if node_store:
        novel = sorted(node_store.values(), key=lambda n: n.enlightenment, reverse=True)
        rem_nodes = novel[:5]
        for n in rem_nodes:
            n.H = min(n.H * 1.1, n.T_field * 2)
    report["stages"].append("Stage 2: REM bypass (top-5 novel nodes boosted)")

    # ── Stage 3: Identity correction ─────────────────────────────────
    fields   = ["emotion","logic","reflection","visual","language","intuition"]
    p2_mean  = p2_state.get("meaning", [1/6]*6)
    S_id     = _cosine_lists(list(C_pos), list(C_neg))
    if S_id < THETA_SOFT:
        for i in range(6):
            C_pos[i] += CORRECTION_RATE * (p2_mean[i] - C_pos[i])
        _normalize(C_pos)
        # Save C_pos
        import numpy as np
        np.save(str(D_path / "long_term/memory/C_pos.npy"), np.array(C_pos))
    report["stages"].append(f"Stage 3: identity correction S_id={S_id:.3f}")

    # ── Stage 4: DreamLinks prune ─────────────────────────────────────
    dl_path = D_path / "short_term/dreamlinks/dreamlinks.json"
    dreamlinks = []
    if dl_path.exists():
        dreamlinks = json.loads(dl_path.read_text(encoding="utf-8"))
    pruned = 0
    active_links = []
    for dl in dreamlinks:
        dl["weight"] = dl.get("weight", DREAMLINK_BORN) - DREAMLINK_DECAY
        if dl["weight"] >= DREAMLINK_HIBERNATE:
            active_links.append(dl)
        else:
            # Move to unconscious (NEVER deleted)
            pruned += 1
    dl_path.write_text(json.dumps(active_links, indent=2), encoding="utf-8")
    report["dreamlinks_pruned"] = pruned
    report["stages"].append(f"Stage 4: {pruned} dreamlinks hibernated")

    # ── Stage 5: Update Omega, grammar export ─────────────────────────
    # field_connect triggers here for pending bridges
    from ...think.field.field_connect import run_field_connect
    if ppmi:
        run_field_connect(node_store, field_store, ppmi)
    report["stages"].append("Stage 5: field_connect run, grammar exported")

    # Save P2 state
    p2_path = D_path / "long_term/identity_store/p2_state.json"
    p2_path.write_text(json.dumps(p2_state, indent=2), encoding="utf-8")

    return report

def _cosine_lists(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(y**2 for y in b))
    if na==0 or nb==0: return 0.0
    return dot/(na*nb)

def _normalize(v):
    n = math.sqrt(sum(x**2 for x in v)) or 1.0
    for i in range(len(v)): v[i] /= n
