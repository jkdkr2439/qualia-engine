"""I/P/boundary.py — Language detection + source_weight boost.
Detects language (Vietnamese vs English), computes boost for language field.
"""
from __future__ import annotations
import re
import unicodedata

# Vietnamese-specific diacritics range
_VI_CHARS = set("àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắặẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỷỹỵ"
                "ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯẠẢẤẦẨẪẬẮẶẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỶỸỴ")

# Simple English word patterns
_EN_WORDS = re.compile(r'\b[a-zA-Z]{3,}\b')

def detect_language(text: str) -> str:
    """
    Returns 'vi' or 'en' based on text character analysis.
    Vietnamese has distinct diacritics; English has plain Latin letters.
    """
    vi_count = sum(1 for c in text if c in _VI_CHARS)
    en_count = len(_EN_WORDS.findall(text))
    total    = max(len(text), 1)

    vi_ratio = vi_count / total
    if vi_ratio > 0.05:
        return "vi"
    # fallback — if has plain latin words and no vi → english
    if en_count > 0:
        return "en"
    return "vi"  # default Pete operates in Vietnamese


def language_boost(lang: str) -> dict:
    """
    Returns boost dict for language field based on detected language.
    Vietnamese → language field gets +0.3 boost.
    English → language field +0.1 (less native).
    """
    if lang == "vi":
        return {"language": 0.3}
    if lang == "en":
        return {"language": 0.1}
    return {}


def source_weight(source: str) -> float:
    """
    Source weighting per spec:
        user       → 1.0
        pete_output → 0.5
        corpus     → 0.8
    """
    return {
        "user":        1.0,
        "pete_output": 0.5,
        "corpus":      0.8,
    }.get(source, 1.0)


def process_boundary(text: str, source: str = "user") -> dict:
    """
    Full boundary processing.
    Returns: {lang, language_boost, source_weight, has_vi}
    """
    lang  = detect_language(text)
    boost = language_boost(lang)
    sw    = source_weight(source)
    return {
        "lang":           lang,
        "language_boost": boost,
        "source_weight":  sw,
        "has_vi":         lang == "vi",
    }
