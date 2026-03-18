"""I/P/segment.py — Symbol segmentation + syntax filter.
Segments normalized tokens into valid symbols, filters junk.
"""
from __future__ import annotations
import re

MIN_LENGTH = 2          # spec: min_symbol_length=2
MAX_LENGTH = 60         # reject very long strings
_JUNK_PATTERN = re.compile(r'^[^a-zA-ZÀ-ỵ\d]+$')   # pure punctuation/symbols → junk
_NUMERIC_ONLY = re.compile(r'^\d+$')                  # pure numbers — keep short ones

# Common stop tokens to reduce noise
STOP_TOKENS = {
    # English
    "the","a","an","is","are","was","were","be","been","being",
    "this","that","these","those","it","its",
    # Vietnamese — copula & conjunctions
    "và","hay","của","với","là","có","không","được","để","cho",
    "các","một","những","trong","ngoài","vì","nên","thì","mà",
    # Vietnamese — aspect markers & auxiliaries (high-freq, low-meaning)
    "đang","đã","sẽ","vẫn","cứ","vừa","mới","đã","đều","cũng",
    "phải","cần","nên","muốn","thể","hay","hoặc",
    # Vietnamese — demonstratives & particles
    "đó","đây","kia","ấy","vậy","thế","rồi","nào","gì","sao",
    "thôi","à","ừ","ơ","ô","ồ","ừ","nhé","nhỉ","nha",
    # Vietnamese — pronouns (high-freq, low-semantic)
    "tao","mày","tôi","bạn","anh","chị","em","nó","mình","họ",
}


def segment(tokens: list[str]) -> list[str]:
    """
    Filter and validate tokenized symbols.
    Returns only meaningful symbol tokens suitable for node creation.

    Rules (per spec):
      - min_symbol_length = 2
      - reject pure punctuation
      - reject numeric-only if too short
      - reject stop tokens
      - deduplicate while preserving order
    """
    seen    = set()
    result  = []
    for tok in tokens:
        # length check
        if len(tok) < MIN_LENGTH or len(tok) > MAX_LENGTH:
            continue
        # junk (pure non-alpha)
        if _JUNK_PATTERN.match(tok):
            continue
        # stop tokens
        if tok.lower() in STOP_TOKENS:
            continue
        # numeric only: allow if 2-4 digits (years etc.)
        if _NUMERIC_ONLY.match(tok):
            if not (2 <= len(tok) <= 4):
                continue
        # dedup
        if tok not in seen:
            seen.add(tok)
            result.append(tok)

    return result


def syntax_filter(tokens: list[str]) -> list[str]:
    """
    Syntax-level coherence filter.
    Removes tokens that pass segment() but still look incoherent.
    Currently: rejects tokens with >3 consecutive repeated chars.
    """
    filtered = []
    for tok in tokens:
        # reject 'haaaaaah', 'lolllll'
        if re.search(r'(.)\1{3,}', tok):
            continue
        filtered.append(tok)
    return filtered


def process_segment(tokens: list[str]) -> list[str]:
    """Full pipeline: segment → syntax_filter."""
    return syntax_filter(segment(tokens))
