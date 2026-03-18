"""O/modality/chat_output.py — format_chat_response() for chat modality.
Post-processes lexicalize output, injects active node surface forms via slot_filler,
and optionally enriches with grammar cache.
"""
from __future__ import annotations
from pathlib import Path
import json

from O.compose.slot_filler import enrich_phrase, _extract_surfaces

GRAMMAR_CACHE = Path(__file__).parent.parent.parent / "O" / "grammar_cache.json"


def format_chat_response(
    raw_text:     str,
    active_nodes: list,
    dominant_field: str,
    thought_phase:  str,
    dnh_hint:       str | None = None,
    dialect:        str = "en",   # "en" | "vi"
) -> str:
    """
    Full chat output formatting pipeline:
    1. Slot-fill {node}/{node2} in raw_text
    2. Enrich with grammar vocabulary if nodes are sparse
    3. Append dnh_hint pre-linguistic suffix when significant
    4. Clean up whitespace + punctuation
    """
    # Step 1: slot fill
    text = enrich_phrase(raw_text, active_nodes, dnh_hint=None)

    # Step 2: grammar enrichment (if output still generic / no node slots used)
    surfaces = _extract_surfaces(active_nodes)
    if not surfaces:
        grammar = _load_grammar()
        vocab = grammar.get(dominant_field, [])
        if vocab:
            surfaces = vocab[:2]

    # Step 3: add node context in Chuyen/Dung phases
    if surfaces and thought_phase in ("Chuyen", "Dung"):
        ctx = ", ".join(surfaces[:2])
        if ctx and f"[{ctx}]" not in text:
            text = text.rstrip(".")  + f" [{ctx}]"

    # Step 4: dnh_hint suffix
    if dnh_hint and len(dnh_hint) > 3 and dnh_hint not in text:
        text += f" — {dnh_hint}"

    # Clean
    text = text.strip()
    if text and not text[-1] in ".!?":
        text += "."

    return text


def _load_grammar() -> dict:
    if GRAMMAR_CACHE.exists():
        try:
            return json.loads(GRAMMAR_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
