"""P/think/semantic/prelinguistic/build.py — Build PreLinguisticPrimordial."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from ..neuron.neuron import ODFS_FIELDS

@dataclass
class PreLinguisticPrimordial:
    name:         str          # = hub_id (hub IS the name)
    hub_id:       str
    satellite_ids: list
    hub_vec:      list         # hub.meaning as list[6]
    centroid:     list         # weighted centroid of hub+sats
    gap:          float        # 1 - cosine(centroid, hub)
    unnamed_feel: list         # centroid - hub.meaning
    weight:       float        # mean(W_i)

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)

def build_prelinguistic(hub_id: str, sat_ids: list,
                        node_store: dict) -> PreLinguisticPrimordial | None:
    """
    Build from hub + min 3 satellites = 4 nodes total. (Invariant 17)
    hub IS the name — no new name invented. (Invariant 18)
    """
    hub = node_store.get(hub_id)
    if hub is None: return None
    sats = [node_store[s] for s in sat_ids if s in node_store]
    if len(sats) < 1: return None   # need at least hub+1

    all_nodes  = [hub] + sats
    total_H    = sum(n.H for n in all_nodes) or 1.0

    centroid   = [0.0] * 6
    for n in all_nodes:
        w = n.H / total_H
        for i, f in enumerate(ODFS_FIELDS):
            centroid[i] += w * n.meaning.get(f, 0.0)

    hub_vec      = [hub.meaning.get(f, 0.0) for f in ODFS_FIELDS]
    gap          = 1.0 - _cosine(centroid, hub_vec)
    unnamed_feel = [centroid[i] - hub_vec[i] for i in range(6)]
    weight       = sum(n.W for n in all_nodes) / len(all_nodes)

    return PreLinguisticPrimordial(
        name          = hub_id,
        hub_id        = hub_id,
        satellite_ids = sat_ids,
        hub_vec       = hub_vec,
        centroid      = centroid,
        gap           = gap,
        unnamed_feel  = unnamed_feel,
        weight        = weight,
    )
