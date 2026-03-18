"""P/think/chakra/chakra_resonance.py — Approach D: sequential + adjacent chakra influence.
Also provides chakra_gap_matrix() for gap-driven attention.
"""
from __future__ import annotations
import math
from .chakra_definitions import CHAKRAS, chakra_weights_as_list, ODFS_FIELDS

# ── 3-Layer grouping of chakras → Reality layers ──────────────────────────────
# Matches subjective/intersubjective/objective in language philosophy
LAYER_CHAKRAS = {
    "OBJECTIVE":       ["root", "sacral"],           # visual/emotion — raw sensing
    "INTERSUBJECTIVE": ["solar", "heart"],            # logic/language — shared meaning
    "SUBJECTIVE":      ["throat", "thirdeye", "crown"],  # language/intuition/reflection
}

# Gap threshold guide (from sandbox validation)
GAP_HIGH     = 0.55   # layers contradict strongly → MEDITATION or TRANSITION
GAP_MODERATE = 0.30   # meaningful difference → GROW

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)

def _normalize(v: list) -> list:
    total = sum(v) or 1.0
    return [x/total for x in v]

def _mean_lists(*lists) -> list:
    n = len(lists)
    return [sum(l[i] for l in lists)/n for i in range(len(lists[0]))]

def chakra_resonance(R_sit: list, passes: int = 3) -> list[float]:
    """
    Approach D: sequential + adjacent chakras influence each other.
    Richer representation — adjacent chakras modulate each other's signal.
    "tao sợ" through D:
        root=visual, sacral=emotion, solar=emotion,
        throat=language (need to express), crown=intuition
    = richer than flat blend.
    Invariant: MEDITATION mode uses this (not sequential).
    """
    # Initialize each chakra signal from R_sit
    n_chakras = len(CHAKRAS)
    signals   = []
    for chakra in CHAKRAS:
        weights = chakra_weights_as_list(chakra)
        fit     = max(0.0, _cosine(R_sit, weights))
        # signal is weights scaled by fit, blended with R_sit
        s = [0.7*r + 0.3*(w*fit) for r,w in zip(R_sit, weights)]
        signals.append(s)

    # Adjacent influence passes
    for _ in range(passes):
        new_signals = []
        for i in range(n_chakras):
            s = signals[i]
            adj = []
            if i > 0:         adj.append(signals[i-1])
            if i < n_chakras-1: adj.append(signals[i+1])
            if adj:
                adj_mean = _mean_lists(*adj)
                s = [0.8*s[j] + 0.2*adj_mean[j] for j in range(6)]
            new_signals.append(s)
        signals = new_signals

    # Sum all chakra signals
    total = [sum(signals[i][j] for i in range(n_chakras)) for j in range(6)]
    return _normalize(total)


# ── Chakra Gap Matrix ─────────────────────────────────────────────────────────

def _chakra_signal_vec(chakra_def: dict) -> list:
    """Return normalized weight vector for a chakra definition."""
    w = [chakra_def["weights"].get(f, 0.0) for f in ODFS_FIELDS]
    return _normalize(w)

def layer_signal(layer: str) -> list:
    """
    Mean ODFS signal vector across all chakras in a reality layer.
    layer: "OBJECTIVE" | "INTERSUBJECTIVE" | "SUBJECTIVE"
    """
    names = LAYER_CHAKRAS.get(layer, [])
    chakra_map = {c["name"]: c for c in CHAKRAS}
    vecs = [_chakra_signal_vec(chakra_map[n]) for n in names if n in chakra_map]
    if not vecs:
        return [1/6] * 6
    return _mean_lists(*vecs)

def chakra_gap_matrix(chakras_live=None) -> dict:
    """
    Compute pairwise and cross-layer cosine gaps between chakra signals.

    chakras_live: optional dict {name: ChakraPrimordial} — uses live .signal()
                  if None, uses static CHAKRA definition weights.

    Returns:
      {
        "pairwise": {"root|sacral": 0.12, ...},   # all 21 pairs
        "layer_gaps": {
            "obj_vs_inter": float,
            "inter_vs_subj": float,
            "obj_vs_subj":  float,
        },
        "max_gap":          float,
        "dominant_tension": str,    # e.g. "obj_vs_subj"
        "coherence":        float,  # 1 - max_gap (overall harmony)
      }
    """
    # Build signal vectors
    if chakras_live is not None:
        sig = {name: ck.signal() for name, ck in chakras_live.items()}
    else:
        chakra_map = {c["name"]: c for c in CHAKRAS}
        sig = {c["name"]: _chakra_signal_vec(c) for c in CHAKRAS}

    names = list(sig.keys())

    # Pairwise gaps
    pairwise = {}
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            key  = f"{a}|{b}"
            pairwise[key] = round(max(0.0, 1.0 - _cosine(sig[a], sig[b])), 4)

    # Layer signals (mean of member chakra signals)
    layer_vecs = {}
    for layer, members in LAYER_CHAKRAS.items():
        vecs = [sig[m] for m in members if m in sig]
        layer_vecs[layer] = _mean_lists(*vecs) if vecs else [1/6]*6

    # Cross-layer gaps
    g_oi  = round(max(0.0, 1.0 - _cosine(layer_vecs["OBJECTIVE"],
                                          layer_vecs["INTERSUBJECTIVE"])), 4)
    g_is_ = round(max(0.0, 1.0 - _cosine(layer_vecs["INTERSUBJECTIVE"],
                                          layer_vecs["SUBJECTIVE"])), 4)
    g_os  = round(max(0.0, 1.0 - _cosine(layer_vecs["OBJECTIVE"],
                                          layer_vecs["SUBJECTIVE"])), 4)

    tension_map = {g_oi: "obj_vs_inter", g_is_: "inter_vs_subj", g_os: "obj_vs_subj"}
    max_gap         = max(g_oi, g_is_, g_os)
    dominant_tension = tension_map[max_gap]

    return {
        "pairwise":         pairwise,
        "layer_gaps": {
            "obj_vs_inter":  g_oi,
            "inter_vs_subj": g_is_,
            "obj_vs_subj":   g_os,
        },
        "layer_vecs":       {k: v for k, v in layer_vecs.items()},
        "max_gap":          max_gap,
        "dominant_tension": dominant_tension,
        "coherence":        round(1.0 - max_gap, 4),
    }


def gap_to_mode(ck_gaps: dict, drift_severity: float = 0.0) -> str:
    """
    Gap-driven attention mode selection.
    Combines chakra layer gaps + quantum drift_severity.

    Priority order:
      1. Identity crisis (drift_severity > 0.3) → STABILIZE
      2. High cross-layer tension → MEDITATION or TRANSITION
      3. Moderate gap → GROW
      4. Coherent → STABILIZE
    """
    if drift_severity > 0.3:
        return "STABILIZE"

    max_gap  = ck_gaps.get("max_gap", 0.0)
    tension  = ck_gaps.get("dominant_tension", "")
    lg       = ck_gaps.get("layer_gaps", {})
    subj_str = lg.get("inter_vs_subj", 0.0) + lg.get("obj_vs_subj", 0.0)

    if max_gap > GAP_HIGH:
        if "obj_vs_subj" in tension:
            return "MEDITATION"     # Pete's inner world vs cold objective facts
        if "inter_vs_subj" in tension:
            return "TRANSITION"     # Pete's identity in tension with social layer
        return "TRANSITION"
    elif max_gap > GAP_MODERATE:
        if subj_str > 0.5:
            return "MEDITATION"     # SUBJECTIVE involved in moderate tension
        return "GROW"               # External tension, safe to absorb
    else:
        return "STABILIZE"          # All layers coherent
