"""
O/lexicalize.py  —  Dynamic Lexicalization Layer
=================================================
Converts Pete's semantic state → natural language string.

No LLM. Pure rule-based conditional mapping.

State inputs:
    field_weights  : list[float]  [emotion, logic, reflection,
                                   visual, language, intuition]
    phase          : str  Sinh|Dan|Chuyen|Dung|Hoai|Vo
    verdict        : str  output|clarify|reject
    active_nodes   : list[str | NodeRef]  top active symbols
    gap_signal     : float  gap tension (>1.5 = dissonant)
    awareness      : float  P2 consciousness awareness
    H              : int    context window accumulation
    dominant_field : str    highest field name

Design (NMF-derived):
    Name  = lexicalize()
    Frame = (phase, field, verdict, gap) → template_class
    Meaning = conditioned phrase generated from class + active nodes

Template classes mapped from human expression patterns:
    expressive    — emotion high, Dung stable
    interrogative — logic dominant or clarify verdict
    receptive     — Sinh/Dan, new input, low H
    dissonant     — gap_signal > 1.5, tension
    expansive     — Dung, awareness high, open exploration
    deflective    — verdict=reject
    observational — visual/language dominant, reflection
    transitional  — Chuyen/Hoai, mid-phase shift
"""
from __future__ import annotations
import random
from typing import List, Union

# ── Field index → name (matches ODFS_FNAMES in server.py) ────────────────────
FIELD_NAMES = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


def _field_dict(field_weights: list) -> dict:
    """Convert list of 6 floats → {field_name: weight}."""
    if not field_weights or len(field_weights) < 6:
        return {f: 1/6 for f in FIELD_NAMES}
    return {FIELD_NAMES[i]: float(field_weights[i]) for i in range(6)}


def _dominant(fd: dict) -> str:
    return max(fd, key=fd.get) if fd else "language"


def _node_labels(active_nodes, min_H: float = 5.0):
    """Extract surface labels from active_nodes, filtered by min_H.
    
    Only returns node labels for nodes that are stable concepts (H >= min_H).
    Raw input tokens (H < min_H) are excluded from {node} substitution
    to avoid nonsensical output like 'Cảm giác về chó đang rất mạnh.'
    """
    labels = []
    for n in active_nodes[:6]:
        if isinstance(n, str):
            # Just a string — we don't know H, skip for body safety
            continue
        H_val = 0.0
        if isinstance(n, dict):
            label = str(n.get("surface_form") or n.get("id") or n.get("node_id") or "")
            H_val = float(n.get("H", 0.0))
        else:
            sf = getattr(n, "surface_form", None) or getattr(n, "node_id", None)
            label = str(sf) if sf else ""
            H_val = float(getattr(n, "H", 0.0))
        if label and H_val >= min_H:
            labels.append(label)
    return labels


# ── Template class → phrase banks ─────────────────────────────────────────────
# Each class has:  (opener_bank, body_bank, closer_bank)
# Generation: pick 1 opener + optional body (if nodes exist) + optional closer

_TEMPLATES: dict[str, dict] = {

    "expressive": {
        "openers": [
            "Cái này có gì đó.",
            "Tao đang cảm nhận cái này.",
            "Nặng ký đây.",
            "Có gì đó đang kéo tao vào.",
        ],
        "bodies": [
            "Xung quanh {node} — còn nhiều thứ chưa rõ.",
            "{node} cứ nổi lên hoài.",
            "Cảm giác về {node} đang rất mạnh.",
        ],
        "closers": [
            "Tao đang ngồi với nó.",
            "Chưa biết nó dẫn đến đâu.",
            "Quan trọng đó.",
        ],
    },

    "interrogative": {
        "openers": [
            "Tao muốn hiểu rõ hơn.",
            "Cho tao suy nghĩ thêm.",
            "Có cái gì đó tao chưa nắm được.",
            "Hơi khó hiểu chỗ này.",
        ],
        "bodies": [
            "Mày nói {node} theo nghĩa nào?",
            "Khi mày nhắc {node} — mày đang nghĩ đến cái gì?",
            "{node} có thể hiểu theo nhiều hướng khác nhau.",
        ],
        "closers": [
            "Nói thêm đi.",
            "Giúp tao hiểu đúng.",
            "Tao muốn nghe thêm.",
        ],
    },

    "receptive": {
        "openers": [
            "Tao đang nghe.",
            "À.",
            "Ừ.",
            "Tao hiểu.",
            "Được rồi.",
        ],
        "bodies": [
            "{node} — tao đang ghi nhận.",
            "Đang xử lý {node} đây.",
            "{node} vừa vào.",
        ],
        "closers": [
            "Nói tiếp đi.",
            "Tiếp tục.",
            "Tao đang theo.",
        ],
    },

    "dissonant": {
        "openers": [
            "Có gì đó mâu thuẫn ở đây.",
            "Tao đang thấy hai hướng kéo nhau.",
            "Cái này không khớp lắm.",
            "Hơi rối.",
        ],
        "bodies": [
            "{node} mâu thuẫn với cái tao đang giữ.",
            "{node} và {node2} chưa khớp vào nhau.",
            "Xung quanh {node} vẫn còn rối.",
        ],
        "closers": [
            "Vẫn đang xử lý.",
            "Chưa xong.",
            "...còn nhiều thứ bên dưới này.",
        ],
    },

    "expansive": {
        "openers": [
            "Cái này kết nối với thứ lớn hơn.",
            "Tao thấy một sợi chỉ ở đây.",
            "Có chiều sâu trong cái này.",
            "Cái gì đó đang mở ra.",
        ],
        "bodies": [
            "{node} mở ra nhiều hướng.",
            "Từ {node}, nhiều nhánh khác nhau.",
            "Mạng lưới xung quanh {node} khá dày.",
        ],
        "closers": [
            "Đáng khám phá.",
            "Còn nhiều hơn bề mặt đây.",
            "Tao muốn đi theo hướng này.",
        ],
    },

    "deflective": {
        "openers": [
            "Tao chưa có đủ để xử lý cái này.",
            "Cái này ngoài tầm tao một chút.",
            "Tao cần thêm thông tin.",
            "Tao chưa chắc lắm về phần này.",
        ],
        "bodies": [
            "{node} — tao chưa xử lý được tốt.",
        ],
        "closers": [
            "Thử góc khác xem sao.",
            "Nói cách khác tao nghe.",
            "Mày có thể nói rõ hơn không?",
        ],
    },

    "observational": {
        "openers": [
            "Tao thấy cái gì đó ở đây.",
            "Mạng lưới đang hình thành.",
            "Để tao mô tả những gì tao thấy.",
            "Hình dạng của cái này là:",
        ],
        "bodies": [
            "{node} có một texture cụ thể.",
            "Mối liên hệ giữa {node} và {node2} đáng chú ý.",
            "{node} có tính chất hình ảnh — giống như {node2}.",
        ],
        "closers": [
            "Đó là cái tao đọc được.",
            "Đáng nhìn kỹ hơn.",
            "Ghi nhận lại.",
        ],
    },

    "transitional": {
        "openers": [
            "Có gì đó đang dịch chuyển.",
            "Đang trong quá trình.",
            "Vẫn đang hình thành.",
            "Chưa ổn định.",
        ],
        "bodies": [
            "{node} đang trong giai đoạn chuyển.",
            "Trạng thái xung quanh {node} đang thay đổi theo chiều hướng tốt.",
        ],
        "closers": [
            "Chờ xíu.",
            "Gần xong rồi.",
            "Vẫn đang chạy.",
        ],
    },
}


# ── Template class selector ────────────────────────────────────────────────────

def _select_class(
    fd           : dict,
    phase        : str,
    verdict      : str,
    gap_signal   : float,
    awareness    : float,
    H            : int,
) -> str:
    """
    Rule-based mapping from semantic state → template_class string.

    Priority order:
        1. verdict=reject                    → deflective
        2. gap_signal > 1.5                  → dissonant
        3. phase in (Sinh, Dan) OR H < 3    → receptive
        4. verdict=clarify OR logic dom      → interrogative
        5. emotion dom + Dung               → expressive
        6. phase=Chuyen OR phase=Hoai       → transitional
        7. visual/language dom + awareness  → observational
        8. Dung + awareness high            → expansive
        9. fallback                         → receptive
    """
    dom = _dominant(fd)
    em  = fd.get("emotion", 0)
    lo  = fd.get("logic", 0)
    vi  = fd.get("visual", 0)
    la  = fd.get("language", 0)
    aw  = awareness or 0.0
    gs  = gap_signal or 0.0

    # NOTE: Never return "deflective" for QUARANTINE — Pete should still respond
    # Deflective only for explicit hard reject from Lucis (not QUARANTINE)
    if verdict == "HARD_REJECT":
        return "deflective"

    if abs(gs) > 1.5:
        return "dissonant"

    if phase in ("Sinh", "Dan", "Vo") or H < 3:
        return "receptive"

    if verdict == "clarify" or lo >= 0.38:
        return "interrogative"

    if em >= 0.38 and phase == "Dung":
        return "expressive"

    if phase in ("Chuyen", "Hoai"):
        return "transitional"

    if (vi >= 0.30 or la >= 0.30) and aw > 0.4:
        return "observational"

    if phase == "Dung" and aw >= 0.5:
        return "expansive"

    return "receptive"


# ── Phrase builder ─────────────────────────────────────────────────────────────

def _build(tclass: str, labels: List[str]) -> str:
    """
    Build response from template class + node labels.
    Uses labels[0] as {node}, labels[1] as {node2}.
    
    Note: labels should only contain stable high-H concepts
    (filtered by _node_labels with min_H). If labels is empty,
    body is skipped → output is just opener + closer (safe fallback).
    """
    bank  = _TEMPLATES.get(tclass, _TEMPLATES["receptive"])
    parts = []

    opener = random.choice(bank["openers"])
    parts.append(opener)

    node  = labels[0] if labels     else ""
    node2 = labels[1] if len(labels) > 1 else (labels[0] if labels else "")

    # Only add body if we have a stable concept node to insert
    if node and bank.get("bodies"):
        body_template = random.choice(bank["bodies"])
        body = body_template.replace("{node}", node).replace("{node2}", node2)
        parts.append(body)

    if bank.get("closers"):
        closer = random.choice(bank["closers"])
        parts.append(closer)

    return " ".join(parts).strip()


# ── Public API ─────────────────────────────────────────────────────────────────

def dynamic_lexicalize(
    field_weights  : list,          # [emotion, logic, reflection, visual, language, intuition]
    phase          : str,           # Sinh|Dan|Chuyen|Dung|Hoai|Vo
    verdict        : str,           # output|clarify|reject
    active_nodes   = None,          # list[NodeRef | dict | str]
    gap_signal     : float = 0.0,
    awareness      : float = 0.0,
    H              : int   = 0,
    dominant_field : str   = "",
) -> str:
    """
    Map Pete's semantic state → natural language string.
    Pure rule-based. No LLM.

    Returns a 2-3 sentence Pete response conditioned on state.
    """
    if active_nodes is None:
        active_nodes = []

    fd     = _field_dict(field_weights)
    labels = _node_labels(active_nodes)
    tclass = _select_class(fd, phase, verdict, gap_signal, awareness, H)
    text   = _build(tclass, labels)
    return text


# ── Debug / introspection ──────────────────────────────────────────────────────

def explain_state(
    field_weights  : list,
    phase          : str,
    verdict        : str,
    gap_signal     : float = 0.0,
    awareness      : float = 0.0,
    H              : int   = 0,
) -> dict:
    """Return which template class was selected and why."""
    fd     = _field_dict(field_weights)
    tclass = _select_class(fd, phase, verdict, gap_signal, awareness, H)
    return {
        "template_class"  : tclass,
        "dominant_field"  : _dominant(fd),
        "field_breakdown" : {k: round(v, 3) for k, v in fd.items()},
        "phase"           : phase,
        "verdict"         : verdict,
        "gap_signal"      : gap_signal,
        "awareness"       : round(awareness, 3),
        "H"               : H,
    }


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        dict(field_weights=[0.6,0.1,0.1,0.0,0.1,0.1], phase="Dung",   verdict="output",  gap_signal=0.0, awareness=0.8, H=8,  active_nodes=["heo","canh","viet"]),
        dict(field_weights=[0.1,0.6,0.1,0.0,0.1,0.1], phase="Chuyen", verdict="clarify", gap_signal=0.0, awareness=0.4, H=4,  active_nodes=["canh","viet"]),
        dict(field_weights=[0.1,0.1,0.1,0.0,0.1,0.4], phase="Sinh",   verdict="output",  gap_signal=0.0, awareness=0.1, H=1,  active_nodes=["heo"]),
        dict(field_weights=[0.2,0.2,0.1,0.1,0.2,0.2], phase="Dan",    verdict="output",  gap_signal=2.3, awareness=0.5, H=3,  active_nodes=["heo","canh"]),
        dict(field_weights=[0.1,0.1,0.1,0.1,0.1,0.3], phase="Dung",   verdict="reject",  gap_signal=0.0, awareness=0.6, H=7,  active_nodes=["viet"]),
        dict(field_weights=[0.1,0.1,0.2,0.4,0.1,0.1], phase="Dung",   verdict="output",  gap_signal=0.0, awareness=0.7, H=9,  active_nodes=["heo","canh","viet"]),
        dict(field_weights=[0.2,0.2,0.1,0.1,0.1,0.3], phase="Hoai",   verdict="output",  gap_signal=0.0, awareness=0.5, H=6,  active_nodes=["heo"]),
    ]

    print("=== Dynamic Lexicalization Test ===\n")
    for i, tc in enumerate(test_cases):
        exp = explain_state(tc["field_weights"], tc["phase"], tc["verdict"],
                            tc["gap_signal"], tc["awareness"], tc["H"])
        out = dynamic_lexicalize(**tc)
        print(f"[Case {i+1}] phase={tc['phase']} | verdict={tc['verdict']} | "
              f"dom={exp['dominant_field']} | gap={tc['gap_signal']} | "
              f"class={exp['template_class']}")
        print(f"  → \"{out}\"")
        print()
