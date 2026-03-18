"""P/think/semantic/p1/promote.py — Promote node to field when H >= T_field."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from ..neuron.neuron import ODFS_FIELDS

T_FIELD = 6.0

@dataclass
class FieldCenter:
    field_id:   str
    core_node:  str
    members:    list
    odfs_field: str = "language"   # dominant ODFS field
    stability:  float = 0.5
    center:     list  = dc_field(default_factory=lambda: [1/6]*6)

def promote_to_field(node_id: str, node_store: dict,
                     ppmi_estimator, field_store: dict) -> tuple[FieldCenter, dict] | None:
    """
    Promote node to FieldCenter if H >= T_field.
    Returns (FieldCenter, prelinguistic_primordial) or None.
    """
    node = node_store.get(node_id)
    if node is None or node.H < T_FIELD:
        return None

    # top-3 PPMI neighbors as satellites
    neighbors = ppmi_estimator.top_neighbors(node_id, k=3)
    sat_ids   = [n for n, _ in neighbors if n in node_store]
    if len(sat_ids) < 1:
        sat_ids = list(node.members)[:3]

    field_id  = f"field_{node_id}"
    odfs_field = max(node.meaning, key=node.meaning.get, default="language")

    # build FieldCenter
    fc = FieldCenter(
        field_id   = field_id,
        core_node  = node_id,
        members    = sat_ids,
        odfs_field = odfs_field,
        stability  = min(1.0, node.H / (T_FIELD * 2)),
        center     = [node.meaning.get(f, 0.0) for f in ODFS_FIELDS],
    )
    field_store[field_id] = fc

    # build prelinguistic primordial (min 4 nodes required by invariant)
    from ..prelinguistic.build import build_prelinguistic
    all_ids = [node_id] + sat_ids
    if len(all_ids) >= 4:
        prim = build_prelinguistic(node_id, sat_ids[:3], node_store)
    else:
        prim = None

    return fc, prim
