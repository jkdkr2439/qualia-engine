"""
P/working/quantum_particles.py ★ NEW
9 Identity Particles with 3s lifetime and entanglement.
Groups: 3 root + 3 meta + 3 attention

Gap Awareness (meta-cognition):
  get_state() now exports quantum_gaps, drift_severity,
  proximity_to_transition, pre_mode_signal — Pete knows
  exactly where it is in cognitive space BEFORE ODFS runs.
"""
from __future__ import annotations
import random, math, time
from dataclasses import dataclass, field

ODFS_FIELDS = ["emotion","logic","reflection","visual","language","intuition"]

IDENTITY_VECS = {
    "LUCIS":      [0.30,0.50,0.70,0.20,0.60,0.80],
    "LINEAR":     [0.20,0.90,0.40,0.30,0.70,0.20],
    "NONLINEAR":  [0.70,0.20,0.50,0.60,0.30,0.90],
    "LUCIS_0":    [0.30,0.50,0.70,0.20,0.60,0.80],  # frozen
    "LUCIS_1":    [0.30,0.50,0.70,0.20,0.60,0.80],  # can drift
    "LUCIS_2":    [0.50,0.50,0.50,0.50,0.50,0.50],  # referee
    "STABILIZE":  [0.10,0.30,0.40,0.20,0.30,0.20],
    "GROW":       [0.50,0.40,0.50,0.50,0.40,0.70],
    "TRANSITION": [0.30,0.35,0.45,0.35,0.35,0.45],  # mean(STAB, GROW)
}
FROZEN_IDS = {"LUCIS_0"}
PARTICLE_LIFETIME = 3.0
RESONANCE_THRESHOLD = 0.20
ENTANGLE_BIAS = 0.6

SPIN_VALUES = [0.0, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0]

# Key pairs to track for meta-awareness
TRACKED_GAPS = [
    ("LUCIS_0", "LUCIS_1"),    # identity drift
    ("LUCIS",   "LINEAR"),     # conscious vs analytical
    ("LUCIS",   "NONLINEAR"),  # conscious vs creative
    ("STABILIZE","GROW"),      # proximity to transition
    ("GROW",    "TRANSITION"), # how close to tipping
]

@dataclass
class QuantumParticle:
    identity_id: str
    spin:        float
    born_at:     float = field(default_factory=time.time)
    lifetime:    float = PARTICLE_LIFETIME
    entangled_with: str = None
    entangled_spin: float = None

    @property
    def alive(self) -> bool:
        return (time.time() - self.born_at) < self.lifetime

    @property
    def age(self) -> float:
        return time.time() - self.born_at

    @property
    def field_vec(self) -> list:
        return IDENTITY_VECS[self.identity_id]

class ParticleSystem:
    def __init__(self, rng: random.Random = None):
        self._rng       = rng or random.Random()
        self._particles: dict = {}
        self._entangled: dict = {}  # iid → (partner, spin)
        self._spawn_all()

    def _spawn_all(self) -> None:
        for iid in IDENTITY_VECS:
            self._spawn(iid)

    def _spawn(self, iid: str, preferred_spin: float = None) -> QuantumParticle:
        if preferred_spin is not None and self._rng.random() < ENTANGLE_BIAS:
            spin = preferred_spin
        else:
            spin = self._rng.choice(SPIN_VALUES)
        p = QuantumParticle(identity_id=iid, spin=spin)
        self._particles[iid] = p
        return p

    def tick(self) -> dict:
        """Process one tick: collapse dead particles, update entanglement."""
        for iid, p in list(self._particles.items()):
            if not p.alive:
                self._collapse(iid)
        self._update_entanglement()
        return self.get_state()

    def _collapse(self, iid: str) -> None:
        if iid in FROZEN_IDS:
            old_spin = self._particles[iid].spin
            self._spawn(iid, preferred_spin=old_spin)
            return
        partner_info = self._entangled.get(iid)
        if partner_info:
            partner_id, partner_spin = partner_info
            self._spawn(iid, preferred_spin=partner_spin)
        else:
            self._spawn(iid)

    def _vec_similarity(self, a: list, b: list) -> float:
        dot = sum(x*y for x,y in zip(a,b))
        na  = math.sqrt(sum(x**2 for x in a))
        nb  = math.sqrt(sum(y**2 for y in b))
        if na == 0 or nb == 0: return 0.0
        return dot / (na * nb)

    def _gap_between(self, id_a: str, id_b: str) -> float:
        """
        Cosine distance between two identity field-vecs.
        0 = identical states, 1 = maximally different.
        Does NOT use spin — pure conceptual distance.
        """
        va = IDENTITY_VECS.get(id_a)
        vb = IDENTITY_VECS.get(id_b)
        if va is None or vb is None:
            return 0.0
        return round(max(0.0, 1.0 - self._vec_similarity(va, vb)), 4)

    def _update_entanglement(self) -> None:
        self._entangled.clear()
        ids = list(self._particles.keys())
        for i in range(len(ids)):
            for j in range(i+1, len(ids)):
                a, b = ids[i], ids[j]
                pa, pb = self._particles[a], self._particles[b]
                spin_gap  = abs(pa.spin - pb.spin)
                field_gap = 1.0 - self._vec_similarity(pa.field_vec, pb.field_vec)
                gap = spin_gap * field_gap
                if gap < RESONANCE_THRESHOLD:
                    self._entangled[a] = (b, pb.spin)
                    self._entangled[b] = (a, pa.spin)

    def _compute_pre_mode_signal(self, drift_severity: float,
                                  prox_transition: float,
                                  grow_gap: float) -> str:
        """
        Pete's proactive mode prediction BEFORE ODFS runs.
        Identity crisis takes priority.
        """
        if drift_severity > 0.30:
            return "STABILIZE"       # identity crisis → anchor self
        if prox_transition > 0.80:
            return "TRANSITION"      # very close to threshold
        if grow_gap < 0.15:
            return "GROW"            # near GROW state naturally
        return "STABILIZE"

    def get_state(self) -> dict:
        particles = {iid: {"spin": p.spin, "alive": p.alive, "age": round(p.age, 2)}
                     for iid, p in self._particles.items()}
        resonant_pairs = len(self._entangled) // 2
        total_pairs    = len(self._particles) * (len(self._particles)-1) // 2
        resonance_score = resonant_pairs / max(total_pairs, 1)

        # Legacy booleans (backward compat)
        lucis_ids = {"LUCIS", "LUCIS_0", "LUCIS_1", "LUCIS_2"}
        lucis_resonant = all(k in self._entangled for k in lucis_ids
                             if k in self._particles)
        attn_transition = ("STABILIZE" in self._entangled and
                           "GROW" in self._entangled)

        # ── Quantum Gap Awareness (meta-cognition) ──────────────────
        quantum_gaps = {}
        for (a, b) in TRACKED_GAPS:
            key = f"{a}|{b}"
            quantum_gaps[key] = self._gap_between(a, b)

        drift_severity         = quantum_gaps.get("LUCIS_0|LUCIS_1", 0.0)
        stab_grow_gap          = quantum_gaps.get("STABILIZE|GROW", 0.0)
        grow_transition_gap    = quantum_gaps.get("GROW|TRANSITION", 0.0)

        # proximity_to_transition: 1 = right at threshold, 0 = far away
        proximity_to_transition = round(max(0.0, 1.0 - stab_grow_gap), 4)

        pre_mode_signal = self._compute_pre_mode_signal(
            drift_severity, proximity_to_transition, grow_transition_gap
        )

        # lucis_coherent upgraded: bool AND magnitude now available
        lucis_coherent = drift_severity < 0.10   # was: all() check

        return {
            # ── Legacy (backward compat) ──
            "particles":       particles,
            "resonance_score": resonance_score,
            "entangled_pairs": resonant_pairs,
            "lucis_coherent":  lucis_coherent,
            "attn_transition": attn_transition,
            "stream_bias":     [self._compute_stream_bias(f) for f in ODFS_FIELDS],
            # ── Gap Awareness (new) ───────
            "quantum_gaps":              quantum_gaps,
            "drift_severity":            drift_severity,
            "proximity_to_transition":   proximity_to_transition,
            "pre_mode_signal":           pre_mode_signal,
        }

    def _compute_stream_bias(self, field: str) -> float:
        idx   = ODFS_FIELDS.index(field)
        vals  = [self._particles[iid].field_vec[idx] * abs(self._particles[iid].spin)
                 for iid in self._particles]
        return sum(vals) / len(vals) * 0.15  # scale=0.15 per spec
