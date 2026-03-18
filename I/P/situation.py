"""
I/P/situation.py ★ NEW — SituationSignal extraction.
Called BEFORE tokenization so Pete 'feels' HOW before parsing WHAT.
"""
from __future__ import annotations
import re
from ..contracts import SituationSignal

# ─── Keyword lists ─────────────────────────────────────────────────────────────
_POS_KW = {"good","great","love","happy","yes","yep","tốt","đúng","hay","thích","yêu","vui"}
_NEG_KW = {"bad","hate","no","sad","wrong","sợ","buồn","tệ","ghét","không","mất","đau"}
_HELP_KW = {"help","cần","urgent","please","giúp","khẩn"}
_Q_KW   = {"gì","sao","tại","why","how","what","where","who","when","huh","hả","à"}
_ASSERT = {"vì","nên","bởi","because","therefore","so","hence","clearly","obviously"}
_SOCIAL = {"tao","mày","tôi","bạn","you","we","us","mình","họ","chúng"}

def _cap_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters: return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)

def _clamp(v: float, lo=0.0, hi=1.0) -> float:
    return max(lo, min(hi, v))


def extract_situation(raw: str) -> SituationSignal:
    """
    Extract SituationSignal from raw text BEFORE tokenization.

    Invariant: called first in I/core.py, before normalize/segment.
    Same tokens can produce completely different signals:
      "tao yêu mày"    → social dominant
      "TAO YÊU MÀY!!!" → emotion dominant
    """
    if not raw or not raw.strip():
        return SituationSignal.neutral()

    tokens_raw = raw.split()
    n = max(len(tokens_raw), 1)
    lower = raw.lower()
    words = set(re.findall(r'\b\w+\b', lower))

    # ── emotional_intensity ─────────────────────────────────────────────
    excl   = raw.count("!") / n
    caps   = _cap_ratio(raw)
    repeat = sum(1 for i in range(1, len(tokens_raw))
                 if tokens_raw[i].lower() == tokens_raw[i-1].lower()) / n
    emotional_intensity = _clamp(excl*0.4 + caps*0.4 + repeat*0.2)

    # ── valence ──────────────────────────────────────────────────────────
    pos = len(words & _POS_KW)
    neg = len(words & _NEG_KW)
    total_sentiment = pos + neg
    valence = (pos - neg) / total_sentiment if total_sentiment > 0 else 0.0

    # ── urgency ──────────────────────────────────────────────────────────
    excl_score = _clamp(raw.count("!") / n * 2)
    short_score = 1.0 if n <= 5 else 0.0
    help_score  = _clamp(len(words & _HELP_KW) / n * 4)
    urgency = _clamp(excl_score*0.4 + short_score*0.3 + help_score*0.3)

    # ── question_pressure ────────────────────────────────────────────────
    q_marks  = raw.count("?") / n
    q_words  = len(words & _Q_KW) / n
    question_pressure = _clamp(q_marks*0.6 + q_words*0.4)

    # ── assertion_pressure ───────────────────────────────────────────────
    a_words  = len(words & _ASSERT) / n
    assertion_pressure = _clamp(a_words * 3)

    # ── social_pressure ──────────────────────────────────────────────────
    s_words  = len(words & _SOCIAL) / n
    social_pressure = _clamp(s_words * 3)

    return SituationSignal(
        emotional_intensity = emotional_intensity,
        valence             = valence,
        urgency             = urgency,
        question_pressure   = question_pressure,
        assertion_pressure  = assertion_pressure,
        social_pressure     = social_pressure,
    )
