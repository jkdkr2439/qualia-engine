"""O/compose/pattern_registry.py — MasterPattern dataclass + patterns VI + EN.
13 bootstrap patterns (7 VI + 6 EN) sufficient for minimal quality output.
Learned patterns added by grammar_learner from Dream Cycle Stage 5.
"""
from __future__ import annotations
from dataclasses import dataclass, field

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]


@dataclass
class MasterPattern:
    name:          str
    slot_order:    list[str]          # ordered lifecycle phases
    field_profile: list[float]        # [6] dominant field vector
    context_gate:  str                # "emotion"|"logic"|"reflection"|"visual"|"language"|"intuition"
    language:      str                # "vi"|"en"
    examples:      list[str]          = field(default_factory=list)
    rhythm:        str                = "medium"  # "sparse"|"medium"|"dense"
    gap_level:     str                = "mid"     # "low"|"mid"|"high"


# ── Vietnamese Patterns (7) ───────────────────────────────────────────────────

PATTERNS_VI: list[MasterPattern] = [
    MasterPattern(
        name         = "Tối giản trữ tình",
        slot_order   = ["Sinh", "Chuyen"],
        field_profile= [0.4, 0.1, 0.6, 0.5, 0.2, 0.7],
        context_gate = "reflection",
        language     = "vi",
        examples     = ["ánh nắng rọi", "con chó sủa", "tao nhớ", "mưa rơi"],
        rhythm       = "sparse",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Trữ tình mở rộng",
        slot_order   = ["Dan", "Sinh", "Chuyen", "Hoai"],
        field_profile= [0.5, 0.1, 0.7, 0.6, 0.2, 0.8],
        context_gate = "reflection",
        language     = "vi",
        examples     = [
            "lặng lẽ ánh nắng rọi mãi mãi",
            "dịu dàng gió thổi ngoài sân",
            "nhẹ nhàng mưa rơi trong đêm",
        ],
        rhythm       = "medium",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Cảm xúc trực tiếp",
        slot_order   = ["Sinh", "Chuyen", "Dung"],
        field_profile= [0.9, 0.1, 0.3, 0.2, 0.5, 0.6],
        context_gate = "emotion",
        language     = "vi",
        examples     = ["tao nhớ mày", "tao yêu mày", "tao thấy đau"],
        rhythm       = "sparse",
        gap_level    = "low",
    ),
    MasterPattern(
        name         = "Phân tích logic",
        slot_order   = ["Sinh", "Dan", "Chuyen", "Dung"],
        field_profile= [0.2, 0.9, 0.5, 0.2, 0.7, 0.3],
        context_gate = "logic",
        language     = "vi",
        examples     = [
            "cách này rõ ràng giải quyết vấn đề",
            "kết quả này chắc chắn chứng minh giả thuyết",
        ],
        rhythm       = "dense",
        gap_level    = "low",
    ),
    MasterPattern(
        name         = "Mô tả thị giác",
        slot_order   = ["Dan", "Sinh", "Chuyen", "Dung", "Hoai"],
        field_profile= [0.3, 0.2, 0.3, 0.9, 0.4, 0.5],
        context_gate = "visual",
        language     = "vi",
        examples     = [
            "vàng ánh nắng rọi ký ức mãi mãi",
            "xanh lá rung trong gió nhẹ",
        ],
        rhythm       = "dense",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Câu hỏi suy ngẫm",
        slot_order   = ["Sinh", "Chuyen", "Dung", "Hoai"],
        field_profile= [0.3, 0.4, 0.9, 0.2, 0.5, 0.7],
        context_gate = "reflection",
        language     = "vi",
        examples     = [
            "tại sao mọi thứ cứ thay đổi mãi",
            "điều này có ý nghĩa gì không",
        ],
        rhythm       = "medium",
        gap_level    = "mid",
    ),
    MasterPattern(
        name         = "Bối cảnh trước",
        slot_order   = ["Hoai", "Sinh", "Chuyen"],
        field_profile= [0.4, 0.2, 0.5, 0.5, 0.3, 0.6],
        context_gate = "intuition",
        language     = "vi",
        examples     = [
            "trong lòng tao vẫn nhớ",
            "mãi mãi ký ức này sống",
            "ngoài kia mưa vẫn rơi",
        ],
        rhythm       = "medium",
        gap_level    = "mid",
    ),
]


# ── English Patterns (6) ──────────────────────────────────────────────────────

PATTERNS_EN: list[MasterPattern] = [
    MasterPattern(
        name         = "Lyric minimal EN",
        slot_order   = ["Sinh", "Chuyen"],
        field_profile= [0.4, 0.1, 0.6, 0.5, 0.2, 0.7],
        context_gate = "reflection",
        language     = "en",
        examples     = ["light fades", "wind blows", "rain falls", "heart breaks"],
        rhythm       = "sparse",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Lyric extended EN",
        slot_order   = ["Dan", "Sinh", "Chuyen", "Hoai"],
        field_profile= [0.5, 0.1, 0.7, 0.6, 0.2, 0.8],
        context_gate = "reflection",
        language     = "en",
        examples     = [
            "silently the light fades into night",
            "gently the wind moves through the leaves",
            "softly rain falls on memory",
        ],
        rhythm       = "medium",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Emotional direct EN",
        slot_order   = ["Sinh", "Chuyen", "Dung"],
        field_profile= [0.8, 0.1, 0.4, 0.3, 0.5, 0.6],
        context_gate = "emotion",
        language     = "en",
        examples     = ["I miss you", "I love you", "this hurts"],
        rhythm       = "sparse",
        gap_level    = "low",
    ),
    MasterPattern(
        name         = "Logical assertion EN",
        slot_order   = ["Sinh", "Dan", "Chuyen", "Dung"],
        field_profile= [0.2, 0.9, 0.5, 0.2, 0.7, 0.3],
        context_gate = "logic",
        language     = "en",
        examples     = [
            "the system works correctly",
            "this approach clearly solves the problem",
        ],
        rhythm       = "dense",
        gap_level    = "low",
    ),
    MasterPattern(
        name         = "Visual descriptive EN",
        slot_order   = ["Dan", "Sinh", "Chuyen", "Dung", "Hoai"],
        field_profile= [0.3, 0.2, 0.3, 0.9, 0.4, 0.5],
        context_gate = "visual",
        language     = "en",
        examples     = [
            "golden light spreads across the field",
            "pale shadows dissolve into dusk",
        ],
        rhythm       = "dense",
        gap_level    = "high",
    ),
    MasterPattern(
        name         = "Reflective question EN",
        slot_order   = ["Sinh", "Chuyen", "Dung", "Hoai"],
        field_profile= [0.3, 0.4, 0.9, 0.2, 0.5, 0.7],
        context_gate = "reflection",
        language     = "en",
        examples     = [
            "why does everything keep changing",
            "what does any of this mean",
            "where does memory go when it fades",
        ],
        rhythm       = "medium",
        gap_level    = "mid",
    ),
]


# ── Word order by language (spec §11) ────────────────────────────────────────

SLOT_ORDER_BY_LANGUAGE: dict[str, dict] = {
    "vi": {
        "default":       ["Sinh", "Dan", "Chuyen", "Dung", "Hoai"],
        "lyric":         ["Dan", "Sinh", "Chuyen", "Hoai"],
        "context_first": ["Hoai", "Sinh", "Chuyen"],
        "classifier":    "con",
    },
    "en": {
        "default":       ["Dan", "Sinh", "Chuyen", "Dung", "Hoai"],
        "lyric":         ["Dan", "Sinh", "Chuyen", "Hoai"],
        "context_first": ["Hoai", "Sinh", "Chuyen"],
        "determiner":    "the",
    },
    "zh": {
        "default":       ["Sinh", "Dan", "Chuyen", "Dung", "Hoai"],
        "topic_first":   ["Hoai", "Sinh", "Chuyen"],
    },
}

PARTICLES: dict[str, dict] = {
    "vi": {
        "aspect":     ["đang", "đã", "sẽ", "vừa", "mới"],
        "modal":      ["có thể", "nên", "phải", "muốn"],
        "connective": ["và", "nhưng", "mà", "vì", "nên", "thì"],
        "particle":   ["à", "nhỉ", "nhé", "ơi", "thôi"],
        "classifier": {"animate": "con", "inanimate": "cái", "abstract": "nỗi"},
    },
    "en": {
        "aspect":     ["is", "was", "has been", "will be"],
        "modal":      ["can", "should", "must", "want to"],
        "connective": ["and", "but", "because", "so", "yet"],
        "particle":   [],
        "determiner": {"definite": "the", "indefinite": "a"},
    },
}


def get_patterns(language: str, context_gate: str) -> list[MasterPattern]:
    """Filter pattern library by language + context_gate."""
    pool = PATTERNS_VI if language == "vi" else PATTERNS_EN
    matched = [p for p in pool if p.context_gate == context_gate]
    return matched if matched else pool  # fallback: all patterns of that language
