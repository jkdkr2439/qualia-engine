"""O/compose/slot_filler.py — Fill {node} template slots with actual node surface forms."""
from __future__ import annotations
import re
import random

SLOT_PATTERN = re.compile(r'\{(\w+)\}')


def fill_slots(template_str: str, nodes: list, fallback: str = "this") -> str:
    """
    Replace {node}, {node2}, {action}, etc. in template_str with surface forms.

    nodes: list of dicts or objects with 'surface_form' or 'node_id' field.
    """
    surfaces = _extract_surfaces(nodes)

    def replacer(match):
        key = match.group(1)
        if key == "node":
            return surfaces[0] if surfaces else fallback
        if key == "node2":
            return surfaces[1] if len(surfaces) > 1 else (surfaces[0] if surfaces else fallback)
        if key == "action":
            return surfaces[0] if surfaces else "act"
        # For any other slot, pick from remaining surfaces
        idx = int(re.sub(r'\D', '', key) or 0) if key != "node" else 0
        return surfaces[idx] if idx < len(surfaces) else fallback
    return SLOT_PATTERN.sub(replacer, template_str)


def _extract_surfaces(nodes: list) -> list[str]:
    """Extract readable surface labels from heterogeneous node list."""
    result = []
    for n in nodes:
        if isinstance(n, str):
            result.append(n)
        elif isinstance(n, dict):
            sf = n.get("surface_form") or n.get("node_id") or ""
            if sf:
                result.append(str(sf))
        else:
            sf = getattr(n, "surface_form", None) or getattr(n, "node_id", None)
            if sf:
                result.append(str(sf))
    return result


def enrich_phrase(phrase: str, nodes: list, dnh_hint: str | None = None) -> str:
    """
    Fully enrich a phrase:
    1. fill_slots with node surfaces
    2. append dnh_hint as pre-linguistic suffix if significant
    """
    text = fill_slots(phrase, nodes)
    if dnh_hint and abs(len(dnh_hint)) > 3:
        text += f" — {dnh_hint}"
    return text.strip()
