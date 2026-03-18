"""P/think/memory/memory_consolidator.py — export_grammar_to_O() after Dream Cycle Stage 5.
Exports learned grammar patterns (high-H node pairs) to O/grammar/ for template enrichment.
"""
from __future__ import annotations
import json
from pathlib import Path

GRAMMAR_PATH = Path(__file__).parent.parent.parent.parent / "D" / "long_term" / "grammar"
O_GRAMMAR_PATH = Path(__file__).parent.parent.parent.parent / "O" / "grammar_cache.json"

ODFS_FIELDS = ["emotion", "logic", "reflection", "visual", "language", "intuition"]
MIN_H_FOR_GRAMMAR = 5.0    # only export well-established nodes


def export_grammar_to_O(node_store: dict, field_store: dict) -> dict:
    """
    Stage 5 of Dream Cycle: export grammar to O layer.
    Scans Dung/Hoai nodes → creates grammar patterns (dominant_field → node labels).
    Returns summary dict of exported patterns.
    """
    GRAMMAR_PATH.mkdir(parents=True, exist_ok=True)

    grammar: dict[str, list[str]] = {f: [] for f in ODFS_FIELDS}

    for node_id, node in node_store.items():
        if node.H < MIN_H_FOR_GRAMMAR:
            continue
        if node.phase not in ("Dung", "Hoai"):
            continue
        dom = max(node.meaning, key=lambda k: node.meaning.get(k, 0))
        sf  = getattr(node, "surface_form", node_id)
        grammar[dom].append(sf)

    # Write to O-accessible cache
    try:
        O_GRAMMAR_PATH.parent.mkdir(parents=True, exist_ok=True)
        O_GRAMMAR_PATH.write_text(
            json.dumps(grammar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[MemoryConsolidator] write error: {e}")

    # Also persist to D/long_term/grammar/
    try:
        (GRAMMAR_PATH / "grammar.json").write_text(
            json.dumps(grammar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[MemoryConsolidator] D write error: {e}")

    counts = {f: len(v) for f, v in grammar.items()}
    total  = sum(counts.values())
    print(f"[MemoryConsolidator] Exported {total} grammar tokens to O layer")
    return {"counts": counts, "total": total}


def load_grammar() -> dict[str, list[str]]:
    """Load grammar cache for O layer enrichment."""
    if O_GRAMMAR_PATH.exists():
        try:
            return json.loads(O_GRAMMAR_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {f: [] for f in ODFS_FIELDS}
