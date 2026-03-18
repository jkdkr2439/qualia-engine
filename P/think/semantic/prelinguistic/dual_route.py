"""
P/think/semantic/prelinguistic/dual_route.py
============================================
Dual-Route Syntactic Channel.

Two tiers of tokens:
  FUNCTION_WORDS   → syntactic channel (suppressed during comprehension, 0× weight)
  LOGIC_CONNECTIVES → partial logic signal (0.4× weight, still carry meaning)
  CONTENT_WORDS    → full ODFS field matching

Usage:
  from P.think.semantic.prelinguistic.dual_route import apply_dual_route
  R_sit, meta = apply_dual_route(R_sit_raw, input_text)
  # meta: {"syntactic_ratio": float, "content_density": float, "logic_boost": float}

Design:
  - R_sit_raw already has field activations from situation_signal
  - apply_dual_route rescales the language field downward by syntactic_ratio
    (because many language activations came from function words)
  - Other fields are boosted proportionally to preserve normalization
  - meta["syntactic_ratio"] is a useful feature for gap computation

Note about EXPRESSION vs COMPREHENSION:
  During comprehension (reading): function words suppressed → syntactic_ratio penalizes language field
  During expression (generating): use raw field weights → function words needed for grammar
"""
from __future__ import annotations
import re
from typing import Tuple

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
LANG_IDX    = ODFS_FIELDS.index("language")
LOGIC_IDX   = ODFS_FIELDS.index("logic")

# ── Tier 1: Pure function words (suppress completely during comprehension) ────
FUNCTION_WORDS: set = {
    # Vietnamese hư từ
    "là","còn","và","thì","mà","của","cho","với","đến","từ","khi","đã","sẽ",
    "đang","rồi","nhưng","hay","hoặc","cũng","đều","lại","đó","này","thôi",
    "bị","được","ra","vào","lên","xuống","theo","trên","dưới","trong","ngoài",
    "sau","trước","cùng","như","hơn","nhất","không","có","một","chúng","nó",
    "ta","người","về","tới","qua","ấy","cái","kẻ","đây","đây","kia",
    # English
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","that","this","it","be","been","have","has","had","do","did",
    "not","no","so","yet","as","is","are","we","he","she","they","you","i",
}

# ── Tier 2: Logic connectives (partial credit: 0.4× → logic field) ────────────
LOGIC_CONNECTIVES: set = {
    "nếu","do đó","vậy","bởi vì","cho nên","vì vậy","vì","do","bởi","nên",
    "therefore","if","then","thus","hence","because","since","so","whereas",
}
LOGIC_CONNECTIVE_WEIGHT = 0.4   # how much they boost logic field

def _tokenize(text: str):
    return re.findall(r"[\w\u00c0-\u024f\u1e00-\u1eff]{2,}", text.lower())

def compute_syntactic_meta(text: str) -> dict:
    """
    Analyse token composition of input text.
    Returns:
      syntactic_ratio:   fraction of tokens that are function words
      logic_boost:       fraction of tokens that are logic connectives
      content_density:   1 - syntactic_ratio - logic_boost
    """
    tokens = _tokenize(text)
    if not tokens:
        return {"syntactic_ratio": 0.0, "logic_boost": 0.0, "content_density": 1.0}

    syn_ct   = sum(1 for t in tokens if t in FUNCTION_WORDS)
    logic_ct = sum(1 for t in tokens if t in LOGIC_CONNECTIVES and t not in FUNCTION_WORDS)
    total    = len(tokens)

    syn_ratio   = syn_ct / total
    logic_ratio = logic_ct / total
    content     = max(0.0, 1.0 - syn_ratio - logic_ratio)

    return {
        "syntactic_ratio": round(syn_ratio, 4),
        "logic_boost":     round(logic_ratio, 4),
        "content_density": round(content, 4),
        "n_tokens":        total,
        "n_function":      syn_ct,
        "n_logic_conn":    logic_ct,
    }

def apply_dual_route(R_sit: list, text: str) -> Tuple[list, dict]:
    """
    Apply dual-route suppression to an existing R_sit vector.

    Effect:
      - language field is scaled DOWN by syntactic_ratio
        (function words inflate language; we correct for that)
      - logic field is boosted UP by logic_boost × LOGIC_CONNECTIVE_WEIGHT
      - remaining fields scaled proportionally so vector sums to 1.0

    Returns:
      (R_corrected, meta_dict)
    """
    meta = compute_syntactic_meta(text)
    syn_ratio   = meta["syntactic_ratio"]
    logic_ratio = meta["logic_boost"]

    R = list(R_sit)  # copy

    # Step 1: suppress language field
    lang_penalty = syn_ratio * 0.8   # 80% of syntactic ratio suppresses language
    R[LANG_IDX] = max(0.0, R[LANG_IDX] * (1.0 - lang_penalty))

    # Step 2: boost logic field from connectives
    logic_gain = logic_ratio * LOGIC_CONNECTIVE_WEIGHT
    R[LOGIC_IDX] = min(1.0, R[LOGIC_IDX] + logic_gain)

    # Step 3: renormalize to sum = 1.0
    total = sum(R) or 1.0
    R_corrected = [x / total for x in R]

    meta["lang_penalty_applied"]  = round(lang_penalty, 4)
    meta["logic_gain_applied"]    = round(logic_gain, 4)
    meta["R_raw_lang"]            = round(R_sit[LANG_IDX], 4)
    meta["R_corrected_lang"]      = round(R_corrected[LANG_IDX], 4)

    return R_corrected, meta
