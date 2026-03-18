"""O/compose/context_gate.py — ODFS → dominant context gate + language detection.
Per spec §11: gate = dominant ODFS field. Language from LearningEvent.language_hint.
"""
from __future__ import annotations
import math

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]

# Context gate = dominant ODFS field (1:1 mapping)
FIELD_TO_GATE: dict[str, str] = {f: f for f in ODFS_FIELDS}

# Field profile → gate threshold
GATE_THRESHOLD = 0.20   # gate fires if dominant field > this ratio


def detect_context_gate(R: list[float]) -> str:
    """
    ODFS R_0 vector → dominant context gate.
    Returns field name of the highest R value if above threshold.
    """
    if not R or len(R) != 6:
        return "language"
    total = sum(R) or 1.0
    ratios = [r / total for r in R]
    max_idx = ratios.index(max(ratios))
    if ratios[max_idx] >= GATE_THRESHOLD:
        return ODFS_FIELDS[max_idx]
    return "language"  # default gate


def detect_language(event) -> str:
    """
    Language from LearningEvent or dict.
    Priority:
      1. event.language_hint ("vi"|"en"|"zh")
      2. language_boost — if language field boost > 0.2 → "vi"
      3. default: "en"
    """
    if hasattr(event, "language_hint") and event.language_hint:
        return event.language_hint
    if isinstance(event, dict):
        hint = event.get("language_hint")
        if hint: return hint

    # Check language_boost
    boost = (getattr(event, "language_boost", {})
             or (event.get("language_boost", {}) if isinstance(event, dict) else {}))
    if isinstance(boost, dict) and boost.get("language", 0) > 0.2:
        return "vi"
    return "en"


def language_from_boundary(boundary_result: dict) -> str:
    """Extract language string from boundary.process_boundary() result."""
    return boundary_result.get("lang", "en")


def route_gate(R: list[float], language: str) -> tuple[str, str]:
    """
    Full routing: returns (context_gate, language).
    context_gate = dominant ODFS field.
    """
    gate = detect_context_gate(R)
    return gate, language
