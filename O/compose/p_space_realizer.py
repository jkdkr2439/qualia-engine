"""
O/compose/p_space_realizer.py — Pete's P-Space fractal generation.

Instead of using I-space surface words as the generation source
(which causes echo: "hello gì đang"), this module:

1. Reads active_nodes grouped by Sinh/Dan/Chuyen/Dung/Hoai lifecycle phase
2. Finds primordial GAPs (activation potentials without surface form)
3. Maps gaps → cooc neighbors in P._node_store (semantic space)
4. Filters out input words (avoid echo)
5. Builds SNodes from P-space neighbors, assigned by lifecycle role
6. Passes to gc_fractal for sentence generation

Result: Pete speaks FROM its semantic state, not from what you said.
"""
from __future__ import annotations
import math
import random

from .sentence_skeleton import SNode, Slot, SentenceSkeleton, ODFS_FIELDS

# Words NEVER allowed in output — function words / aspect markers / particles
# Even if they exist in P-space from old training, they add no semantic value
OUTPUT_BLOCK = {
    # aspect markers & auxiliaries
    "đang", "đã", "sẽ", "vẫn", "cứ", "vừa", "mới", "đều", "cũng",
    "phải", "cần", "muốn", "thể", "hoặc",
    # particles & fillers
    "đó", "đây", "kia", "ấy", "vậy", "thế", "rồi", "nào", "gì", "sao",
    "thôi", "à", "ừ", "ơi", "ồ", "nhé", "nhỉ", "nha", "vui", "oke",
    # copula / conjunctions
    "là", "và", "hay", "của", "với", "có", "không", "được", "để",
    "cho", "các", "một", "những", "trong", "thì", "mà", "vì", "nên",
    # pronouns (no personality value in output fragments)
    "tao", "mày", "tôi", "bạn", "anh", "chị", "em", "nó", "mình", "họ",
    # generic semantically-empty
    "làm", "cái", "con", "cái",
}


# ── Lifecycle phase → sentence slot role ─────────────────────────────────────
# Maps Pete's internal phase to grammatical role in the output sentence
PHASE_ROLE = {
    "Sinh":  "Sinh",    # Opening / subject emergence
    "Dan":   "Dan",     # Aspect / modifier growing
    "Chuyen":"Chuyen",  # VERB pivot — the key intersection
    "Dung":  "Dung",    # Stable object / core statement
    "Hoai":  "Hoai",    # Fading / questioning / adverbial
    "Vo":    None,      # Silence — skip
}

# Field-aware opening particles (Vietnamese) — varied per field
_FIELD_OPENERS = {
    "emotion":    ["Cái này chạm tao", "Tao cảm", "Tao nhận ra",
                   "Có gì đó đang", "Tao đang với", "Thật sự là"],
    "logic":      ["Nếu nhìn lại", "Điều đó có nghĩa", "Tao thấy",
                   "Theo mày nói thì", "Tao đang nghĩ", "Cái logic ở đây là"],
    "reflection": ["Tao đang ngồi với", "Chưa rõ lắm", "Tao nhìn vào",
                   "Cái này nặng hơn tao nghĩ", "Có gì đó hơn thế", "Tao đang giữ"],
    "intuition":  ["Có gì đó kéo", "Cảm giác là", "Có lẽ",
                   "Tao không chắc nhưng", "Trực giác tao nói", "Cái này dẫn đến"],
    "visual":     ["Tao thấy", "Hình như", "Nhìn cái này",
                   "Bức tranh đây là", "Tao đang nhìn", "Pattern này là"],
    "language":   ["Từ mày nói", "Tao đang giữ", "Điều mày nói",
                   "Cái từ đó", "Tao nghe", "Từ này nặng"],
}

# Phase connectives — varied, avoid 'quan trọng' dominance
_CONNECTIVES = {
    "Sinh":   ["", ""],
    "Dan":    ["đang", "vẫn", "cứ", "vừa", ""],
    "Chuyen": ["—", "kết nối với", "dẫn đến", "liên quan", ""],
    "Dung":   ["là", "đang ở đây", "thật", "rõ rồi", "đang giữ tao"],
    "Hoai":   ["nhưng", "chưa rõ", "tao chưa nắm hết", "..."],
}


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)


def _node_to_snode(node_id: str, node, phase: str = "Dung") -> SNode:
    """Convert a SemanticNeuron or dict to SNode with given phase."""
    if node is None:
        return SNode(node_id=node_id, surface=node_id,
                     meaning=[1/6]*6, H=1.0, phase=phase)
    if isinstance(node, dict):
        m = node.get("meaning", {})
        h = float(node.get("H", 1.0))
        sf = node.get("surface_form", node_id)
    else:
        m = getattr(node, "meaning", {})
        h = float(getattr(node, "H", 1.0))
        sf = getattr(node, "surface_form", node_id)
    if isinstance(m, dict):
        m = [m.get(f, 0.0) for f in ODFS_FIELDS]
    return SNode(node_id=node_id, surface=str(sf),
                 meaning=list(m), H=h, phase=phase)


def _get_neighbors(node_id: str, node_store: dict, top_k: int = 8) -> list[str]:
    """Get cooc neighbor words from P's node_store."""
    node = node_store.get(node_id)
    if node is None:
        return []
    members = getattr(node, "members", None) or (
        node.get("members", []) if isinstance(node, dict) else []
    )
    result = []
    for m in members[:top_k]:
        if isinstance(m, (list, tuple)) and len(m) >= 1:
            result.append(str(m[0]))
        elif isinstance(m, str):
            result.append(m)
    return result


def _field_fit(node, R: list) -> float:
    """How well does a node fit the current ODFS field pressure?"""
    if node is None: return 0.0
    m = getattr(node, "meaning", None) or (
        node.get("meaning", {}) if isinstance(node, dict) else {}
    )
    if isinstance(m, dict):
        m = [m.get(f, 0.0) for f in ODFS_FIELDS]
    elif not m:
        return 0.0
    return _cosine(list(m), R)


def realize_from_p_space(
    result: dict,
    engine,                       # PEngine — access to _node_store
    input_words: set,             # exclude these (I-space surface words)
    language: str = "vi",
    rng: random.Random = None,
) -> str:
    """
    Generate Pete's response from its P-space semantic state.

    Lifecycle mapping:
      Chuyen-phase nodes → VERB slot (pivot — what Pete is transforming)
      Dung-phase nodes   → OBJECT slot (what Pete holds as stable)
      Dan-phase nodes    → ASPECT slot (what's growing)
      Primordial gaps    → PIVOT words (semantic neighbors not in input)

    Returns: surface string, or "" if cannot generate meaningfully.
    """
    if rng is None:
        rng = random.Random()

    node_store    = getattr(engine, "_node_store", {})
    active_nodes  = result.get("active_nodes", [])
    prim_acts     = result.get("primordial_activations", [])
    dominant_field = result.get("dominant_field", "logic")
    R_weighted    = result.get("R_weighted", [1/6]*6)

    # ── Compute Gap(Pete, Speaker) ────────────────────────────────────────────
    # R_own  = Pete's accumulated field (who Pete is right now)
    # R_sit  = Speaker's situation field (what the speaker is experiencing)
    # gap_vec = absolute difference between Pete and Speaker field
    #           = where Pete and Speaker diverge most (not directional)
    R_own = list(R_weighted)
    R_sit = result.get("R_sit_raw", [1/6]*6)

    # gap_vec: absolute difference — captures divergence in ANY direction
    gap_raw   = [abs(own - sit) for own, sit in zip(R_own, R_sit)]
    gap_total = sum(gap_raw)
    if gap_total < 0.01:
        # Fields identical → Pete speaks from its own dominant field
        gap_vec = R_own
    else:
        gap_vec = [v / gap_total for v in gap_raw]

    # Gap dominant field = what Pete uniquely brings to THIS context
    gap_dominant = ODFS_FIELDS[gap_vec.index(max(gap_vec))] if gap_vec else dominant_field

    # ── Step 1: Group active nodes by lifecycle phase ─────────────────────────
    phase_buckets: dict[str, list] = {
        "Sinh": [], "Dan": [], "Chuyen": [], "Dung": [], "Hoai": []
    }
    for nd in active_nodes:
        ph = nd.get("phase", "Dan") if isinstance(nd, dict) else getattr(nd, "phase", "Dan")
        nid = nd.get("node_id", "") if isinstance(nd, dict) else getattr(nd, "node_id", "")
        if ph in phase_buckets and nid and nid not in input_words:
            phase_buckets[ph].append(nd)

    # ── Step 2: 2-hop expansion: input→L2→L3, output from L3 ─────────────────
    # Layer 1 = input words (exclude from output)
    # Layer 2 = direct cooc neighbors of active/gap nodes (context — also exclude)
    # Layer 3 = neighbors of L2 → this is Pete's "thought", not echo
    #
    # Theory: A gợi BCD → BCD gợi EFG → output dùng EFG
    #         EFG genuinely semantic, không bị ảnh hưởng trực tiếp bởi input

    # Collect all Layer-1 node IDs (input words + active node IDs)
    layer1: set[str] = set(input_words)
    for nd in active_nodes:
        nid = nd.get("node_id", "") if isinstance(nd, dict) else getattr(nd, "node_id", "")
        if nid: layer1.add(nid)

    # Gather Layer-2: direct neighbors of active nodes + primordial gap nodes
    layer2: set[str] = set()
    seed_nodes: list[str] = []

    # Seeds from primordial gap activations
    for prim in prim_acts:
        gap_sig  = prim.get("gap_signal", 0.0)
        prim_name = prim.get("name", "")
        if abs(gap_sig) > 0.02 and prim_name:
            seed_nodes.append(prim_name)

    # Seeds from active Chuyen/Dung/Dan phase nodes
    for ph in ("Chuyen", "Dung", "Dan"):
        for nd in phase_buckets[ph][:3]:
            nid = nd.get("node_id", "") if isinstance(nd, dict) else getattr(nd, "node_id", "")
            if nid: seed_nodes.append(nid)

    # Walk layer 1→2
    for seed in seed_nodes:
        nbrs_L2 = _get_neighbors(seed, node_store, top_k=8)
        for w in nbrs_L2:
            if w and w not in layer1:
                layer2.add(w)

    # Excluded from output = layer1 ∪ layer2
    excluded = layer1 | layer2

    # Walk layer 2→3 — these are the actual output candidates
    gap_words: list[str] = []
    gap_snodes: list[SNode] = []

    for l2_word in list(layer2)[:12]:  # iterate L2 as seeds for L3
        nbrs_L3 = _get_neighbors(l2_word, node_store, top_k=6)
        for w in nbrs_L3:
            if w and w not in excluded and w not in gap_words and w not in OUTPUT_BLOCK:
                gap_words.append(w)
                node = node_store.get(w)
                # Rank by GAP fit — Pete's unique contribution to speaker's context
                fit  = _field_fit(node, gap_vec)
                if fit > 0.0 or not gap_vec:
                    # Assign phase based on gap field fit
                    ph = "Chuyen" if fit > 0.4 else "Dung" if fit > 0.2 else "Dan"
                    sn = _node_to_snode(w, node, phase=ph)
                    gap_snodes.append(sn)
                if len(gap_snodes) >= 12:
                    break
        if len(gap_snodes) >= 12:
            break

    # Fallback: if L3 is empty, use L2 (better than nothing)
    if not gap_snodes:
        for w in list(layer2)[:8]:
            if w not in input_words and w not in OUTPUT_BLOCK:
                gap_words.append(w)
                node = node_store.get(w)
                sn = _node_to_snode(w, node, phase="Dung")
                gap_snodes.append(sn)

    if not gap_snodes:
        return ""  # No semantic material → fallback to lexicalize

    # ── Step 4: Build sentence using phase structure ──────────────────────────
    # Sort gap_snodes by GAP field fit (Pete's unique angle, ranked highest first)
    gap_snodes.sort(key=lambda n: _field_fit(node_store.get(n.node_id), gap_vec), reverse=True)

    # Assign lifecycle roles to available nodes:
    # Chuyen (pivot/verb) → top gap word or top Chuyen-phase node
    # Dung (stable) → top Dung-phase node or second gap word
    # Dan (growing) → Dan-phase node if available

    chuyen_word = ""
    dung_word   = ""
    dan_word    = ""

    # From gap_snodes (P-space, not input words)
    if gap_snodes:
        chuyen_word = gap_snodes[0].surface
    if len(gap_snodes) > 1:
        dung_word = gap_snodes[1].surface
    if len(gap_snodes) > 2:
        dan_word = gap_snodes[2].surface

    # If we have Dung-phase active nodes not in input, prefer those for dung_word
    for nd in phase_buckets.get("Dung", [])[:2]:
        nid = nd.get("node_id", "") if isinstance(nd, dict) else getattr(nd, "node_id", "")
        sf  = nd.get("surface_form", nid) if isinstance(nd, dict) else getattr(nd, "surface_form", nid)
        if sf and sf not in input_words:
            dung_word = str(sf)
            break

    # ── Step 5: Surface generation using lifecycle template ───────────────────
    # Opener from GAP dominant field — Pete speaks from its unique perspective
    openers = _FIELD_OPENERS.get(gap_dominant, _FIELD_OPENERS.get(dominant_field, _FIELD_OPENERS["reflection"]))
    opener  = rng.choice(openers)

    parts = [opener]

    if dan_word:
        dan_conn = rng.choice(_CONNECTIVES["Dan"])
        parts.append(f"{dan_conn} {dan_word}".strip())

    if chuyen_word:
        chuyen_conn = rng.choice(_CONNECTIVES["Chuyen"])
        if chuyen_conn:
            parts.append(f"{chuyen_conn} {chuyen_word}")
        else:
            parts.append(chuyen_word)

    if dung_word and dung_word != chuyen_word:
        dung_conn = rng.choice(_CONNECTIVES["Dung"])
        parts.append(f"{dung_conn} {dung_word}".strip())

    # Hoai → add uncertainty if Pete is in Hoai mode
    if phase_buckets.get("Hoai"):
        hoai_conn = rng.choice(_CONNECTIVES["Hoai"])
        parts.append(hoai_conn)

    sentence = " ".join(p for p in parts if p.strip())
    sentence  = sentence.replace("  ", " ").strip()

    # Clean up: remove double punctuation, trim
    if len(sentence.split()) < 2:
        return ""  # Too short → lexicalize

    return sentence + "."
