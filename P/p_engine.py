"""
P/p_engine.py — PEngine orchestrator: 13-step tick.
This is the central processing unit of Pete v4.
"""
from __future__ import annotations
import json, random, math, time
from pathlib import Path

ODFS_FIELDS = ["emotion","logic","reflection","visual","language","intuition"]
D_PATH = Path(__file__).parent.parent / "D"


class _DictNode:
    """Wraps a dict (from SQLite) as attribute-accessible node for p_engine compatibility."""
    __slots__ = ("node_id","surface_form","meaning","H","W","Q","enlightenment",
                 "role","phase","T_fire","T_field","Surp","members","_seen_clusters")
    def __init__(self, d: dict):
        self.node_id      = d.get("node_id", "?")
        self.surface_form = d.get("surface_form", self.node_id)
        self.meaning      = d.get("meaning", {f: 1/6 for f in ODFS_FIELDS})
        self.H            = d.get("H", 0.0)
        self.W            = d.get("W", 0.5)
        self.Q            = d.get("Q", False)
        self.enlightenment= d.get("enlightenment", 0)
        self.role         = d.get("role")
        self.phase        = d.get("phase", "Vo")
        self.T_fire       = 3
        self.T_field      = 6
        self.Surp         = 0.0  # computed dynamically during ticks
        self.members      = set()  # co-occurrence neighbors (built live during chat)
        self._seen_clusters = set()  # chakra cluster tracking

    def to_dict(self) -> dict:
        return {
            "node_id":       self.node_id,
            "surface_form":  self.surface_form,
            "meaning":       self.meaning,
            "H":             self.H,
            "W":             self.W,
            "Q":             self.Q,
            "enlightenment": self.enlightenment,
            "role":          self.role,
            "phase":         self.phase,
        }

class PEngine:

    def __init__(self):
        self._rng    = random.Random()
        self._tick_n = 0
        self._Gamma  = 0.0   # accumulated noise/chaos metric
        self._loading = True   # True while background load in progress
        self._load_progress = "starting"

        # Load D layer data
        self._node_store:   dict = {}
        self._field_store:  dict = {}
        self._primordials:  list = []
        self._C_pos = [0.30,0.50,0.70,0.20,0.60,0.80]
        self._C_neg = [0.10,0.80,0.05,0.70,0.15,0.05]
        self._Omega_world = None
        self._Omega_user  = None
        self._p2_state    = {}

        self._load_D()

        # Init modules
        from .think.consciousness.p2_primordial import P2Consciousness
        from .think.odfs.odfs_kernel import OMEGA_DEFAULT
        from .modes.attention_controller import AttentionController
        from .think.symbol_learning.pmi_estimator import PPMIEstimator
        from .working.quantum_particles import ParticleSystem
        from .think.lucis.lucis_1 import Lucis1
        from .think.lucis.lucis_2 import Lucis2
        from .working.session_state import SessionState
        from .working.active_nodes_cache import ActiveNodesCache

        self._p2      = P2Consciousness(self._C_pos, self._C_neg, self._p2_state)
        self._attn    = AttentionController()
        self._ppmi    = PPMIEstimator(window=3)
        self._quantum = ParticleSystem(self._rng)
        self._lucis1  = Lucis1()
        self._lucis2  = Lucis2()           # referee every 50 ticks
        self._session = SessionState()     # Gamma_acc, mode tracking
        self._active_cache = ActiveNodesCache()
        self._Omega_world = self._Omega_world or OMEGA_DEFAULT
        self._Omega_user  = self._Omega_user  or OMEGA_DEFAULT
        self._odfs_prev   = {"rho_U":0.5, "S_id":0.0, "Gamma":0.0}

        # Per-primordial chakra system — each has its own omega_user kernel
        from .think.chakra.chakra_primordial import build_chakra_primordials
        self._chakras: dict = build_chakra_primordials()  # 7 chakras

        # Gap 2: multi-instance identity anchors
        # Each identity has a C_pos-like 6D anchor.
        # Gap metric: cosine distance between pairs = how different are they?
        self.identity_anchors: dict = {
            "pete":   list(self._C_pos) if hasattr(self, "_C_pos") else [1/6]*6,
            "shadow": None,   # lazy: inverted C_pos
            "tung":   None,   # loaded from D/identities/tung/ if available
        }
        self.identity_gap_matrix: dict = {}
        self._mode_weights: dict = {"STABILIZE":1.0,"GROW":0.0,"MEDITATION":0.0,"TRANSITION":0.0}

        self._load_cooc()

        # Load per-chakra omega_user from D/identities/
        for ck in self._chakras.values():
            ck.load_omega_user()

        # Gap 2: load external identity anchors
        self._load_identity_anchors()

        # Wave interference layer — additive, does not replace anything
        try:
            from .think.odfs.wave_state import init_wave_states
            self._wave_states: dict = init_wave_states([1/6]*6)
            self._wave_t: float     = 0.0   # monotonic clock (seconds)
        except Exception:
            self._wave_states = {}
            self._wave_t      = 0.0

        # Tiềm thức (Subconscious) — P layer only, queries subconscious.db via chakra seeds
        try:
            from .think.subconscious import SubconsciousLayer
            self._subcon = SubconsciousLayer()
            if self._subcon.available:
                print(f"[PEngine] Tiềm thức ready: {len(self._subcon._vocab):,} words")
        except Exception:
            self._subcon = None

        print(f"[PEngine] Ready: {len(self._node_store):,} nodes, {len(self._field_store):,} fields")



    # ── D loading — SQLite first, .npy fallback ────────────────────────────────
    def _load_D(self):
        import numpy as np

        # Try SQLite first (primary DB)
        try:
            from D.db import get_db
            db = get_db()
            # Load identity anchors from DB
            c_pos_db = db.load_identity("C_pos")
            c_neg_db = db.load_identity("C_neg")
            if c_pos_db: self._C_pos = c_pos_db
            if c_neg_db: self._C_neg = c_neg_db

            # Load active nodes (H >= 1.0) from DB — faster than full JSON
            db_nodes = db.load_nodes_above_H(min_H=1.0)
            if db_nodes:
                from P.think.semantic.neuron.neuron import SemanticNeuron as _SN
                for nid, nd in db_nodes.items():
                    if nid not in self._node_store:
                        self._node_store[nid] = _SN.from_dict(nd)
                print(f"[PEngine] Loaded {len(db_nodes):,} nodes from pete.db")

                # Populate node.members from cooc table (one bulk query)
                # Required for field_gravity.update_meaning() to work
                try:
                    cooc_map = db.load_all_cooc_neighbors(min_ppmi=0.3)
                    populated = 0
                    for nid, neighbors in cooc_map.items():
                        if nid in self._node_store:
                            self._node_store[nid].members = neighbors
                            populated += 1
                    if cooc_map:
                        print(f"[PEngine] members populated: {populated:,} nodes from cooc table")
                except Exception as e:
                    pass  # cooc table empty — will be populated after migrate_cooc.py

        except Exception as e:
            print(f"[PEngine] SQLite load skipped: {e}")

        # ── HardMemory: subconscious.db + memory.db → node_store ─────────────
        # These extend P-space with 70k+ words from the void/imagination layer.
        # Pete.db nodes (H>1) are NOT overwritten — they retain their learned state.
        # HardMemory nodes start at H=0 (silent) until activated by input + cooc.
        try:
            from P.HardMemory.hard_memory_loader import get_loader
            loader = get_loader()
            n_added = loader.load_into(self._node_store, overwrite=False)
            print(f"[PEngine] HardMemory: +{n_added:,} nodes (total: {len(self._node_store):,})")
            # NOTE: HardMemory nodes are now SemanticNeuron objects (from_dict).
            # members are populated from the dict's 'members' set during SemanticNeuron.from_dict().
            # No separate dict-based member population needed.
        except Exception as e:
            print(f"[PEngine] HardMemory load skipped: {e}")


        # Fallback: .npy identity anchors (legacy)
        cp = D_PATH / "long_term/memory/C_pos.npy"
        cn = D_PATH / "long_term/memory/C_neg.npy"
        if cp.exists() and not self._C_pos:
            self._C_pos = np.load(str(cp)).tolist()
        if cn.exists() and not self._C_neg:
            self._C_neg = np.load(str(cn)).tolist()

        ow = D_PATH / "long_term/odfs_state/omega_world.npy"
        ou = D_PATH / "long_term/odfs_state/omega_user.npy"
        if ow.exists(): self._Omega_world = np.load(str(ow)).tolist()
        if ou.exists(): self._Omega_user  = np.load(str(ou)).tolist()

        p2f = D_PATH / "long_term/identity_store/p2_state.json"
        if p2f.exists():
            try:
                import json as _json
                self._p2_state = _json.loads(p2f.read_text(encoding="utf-8"))
            except Exception:
                pass

        self._loading       = False
        self._load_progress = f"ready ({len(self._node_store):,} nodes from DB)"


    def _load_identity_anchors(self) -> None:
        """Gap 2: Load external identity anchors from D/identities/."""
        import json, math
        base = D_PATH / "identities"

        # Pete self-anchor (from ingest_pete_self.py output)
        pete_path = base / "pete" / "omega_user.json"
        if pete_path.exists():
            try:
                d = json.loads(pete_path.read_text(encoding="utf-8"))
                # Use first row of omega_user as anchor vector (field coupling profile)
                omega = d.get("omega_user", [])
                if omega:
                    # Flatten: row-sum gives each field's total outgoing coupling
                    flat = [sum(row[i] for row in omega) for i in range(6)]
                    s = sum(flat) or 1.0
                    self.identity_anchors["pete"] = [x/s for x in flat]
            except Exception:
                pass

        # Tung user-anchor (from ingest_user_tung.py output)
        tung_path = base / "tung" / "omega_user.json"
        if tung_path.exists():
            try:
                d = json.loads(tung_path.read_text(encoding="utf-8"))
                omega = d.get("omega_user", [])
                if omega:
                    flat = [sum(row[i] for row in omega) for i in range(6)]
                    s = sum(flat) or 1.0
                    self.identity_anchors["tung"] = [x/s for x in flat]
            except Exception:
                pass

        # Shadow: inverted C_pos (anti-identity)
        if self._C_pos:
            inv = [1.0 - x for x in self._C_pos]
            s = sum(inv) or 1.0
            self.identity_anchors["shadow"] = [x/s for x in inv]

        # Initial gap matrix
        self._compute_identity_gaps()

    def _compute_identity_gaps(self) -> None:
        """Gap 2: Compute pairwise cosine distances between identity anchors."""
        import math
        def _cos(a, b):
            dot = sum(x*y for x,y in zip(a,b))
            na  = math.sqrt(sum(x**2 for x in a))
            nb  = math.sqrt(sum(y**2 for y in b))
            return dot/(na*nb) if na and nb else 0.0

        items = [(k,v) for k,v in self.identity_anchors.items() if v is not None]
        self.identity_gap_matrix = {}
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                k = (items[i][0], items[j][0])
                self.identity_gap_matrix[k] = round(1.0 - _cos(items[i][1], items[j][1]), 4)

    def _load_cooc(self):
        pass  # cooc graph loaded via load_all_cooc_neighbors() in _load_D above




    # ── Main 13-step tick ───────────────────────────────────────────────────
    def process(self, event, mode: str = "NORMAL") -> dict:
        # NOTE: mode param ignored — Pete auto-selects based on internal state
        from .think.semantic.p1.tick import primordial_tick
        from .think.semantic.p1.promote import promote_to_field
        from .think.semantic.prelinguistic.activate import activate_primordials
        from .working.sync import (sync_p1_to_p2, sync_p2_to_p1,
                                   compute_identity_coherence)
        from .think.odfs.odfs_kernel import run_odfs
        from .think.chakra.chakra_sequential import chakra_sequential
        from .think.chakra.chakra_resonance import chakra_resonance
        from .modes.attention_controller import AttentionController

        sig = event.situation_signal
        src = event.source_weight
        lboost = event.language_boost or {}

        # ── [0.5] Situation → R_sit ────────────────────────────────
        R_sit = sig.to_R0() if sig else [1/6]*6

        # ── [0.6] Dual-Route syntactic filter ─────────────────────────
        # Suppresses language field inflation from function words.
        # Uses raw input text from event if available.
        _raw_text = getattr(event, "raw_text", "") or ""
        if _raw_text:
            from .think.semantic.prelinguistic.dual_route import apply_dual_route
            R_sit, _syntactic_meta = apply_dual_route(R_sit, _raw_text)
        else:
            _syntactic_meta = {"syntactic_ratio": 0.0, "content_density": 1.0}

        # ── [1] P1→P2 sync, P2 tick ──────────────────────────────
        p1_state   = sync_p1_to_p2(self._node_store)
        p2_result  = self._p2.tick(p1_state, self._rng)

        # ── [2] Attention mode ────────────────────────────────────
        q_state   = self._quantum.tick()
        attn_mode = self._attn.decide(self._odfs_prev,
                                      p2_result.iam_streak, q_state)

        # ── [3] PPMI update ───────────────────────────────────────
        for (c, n) in event.context_pairs:
            self._ppmi.update(c, n)

        # ── [4] P1 node ticks ─────────────────────────────────────
        lr_scale = AttentionController.lr_scale(attn_mode)
        for symbol in event.normalized_symbol_ids:
            nbrs = [p for c,p in event.context_pairs if c == symbol]
            node = self._node_store.get(symbol)
            node_fit = 0.0
            if node:
                nm = [node.meaning.get(f,0) for f in ODFS_FIELDS]
                node_fit = _cosine(nm, R_sit)
            energy = abs(p2_result.spin) * src * (1.0 + node_fit * 0.5)
            primordial_tick(
                symbol=symbol, neighbors=nbrs,
                node_store=self._node_store, field_store=self._field_store,
                source_weight=energy * lr_scale, language_boost=lboost,
                p2_iam_streak=p2_result.iam_streak,
                p2_awareness=p2_result.awareness,
                p2_phase=p2_result.phase,
            )
            node = self._node_store.get(symbol)
            if node and node.H >= node.T_field:
                result = promote_to_field(symbol, self._node_store,
                                          self._ppmi, self._field_store)
                if result:
                    fc, prim = result
                    if prim: self._primordials.append(prim)

        # ── [5] P2→P1 sync ────────────────────────────────────────
        sync_p2_to_p1(p2_result.__dict__, self._node_store)

        # ── [6] Select active nodes ───────────────────────────────
        # Always include the current event's symbols as active (they were just processed)
        event_nodes = [self._node_store[s] for s in event.normalized_symbol_ids
                       if s in self._node_store]
        active_nodes = self._select_active(attn_mode, event_nodes)

        # ── [6.5] Field gravity — nội suy meaning qua field connections ──────
        # Per blueprint: before computing R_weighted, pull each active node's
        # meaning toward its nearest field's ODFS centroid via gravity.
        # This is the interpolation step that makes Pete "think" before speaking.
        if self._field_store:
            from .think.semantic.gravity.field_gravity import update_meaning
            GRAVITY_PASSES = 3 if mode == "MEDITATION" else 1
            for _ in range(GRAVITY_PASSES):
                for node in active_nodes:
                    update_meaning(
                        node          = node,
                        field_store   = self._field_store,
                        lr            = 0.05,
                        source_weight = src,
                        language_boost= lboost,
                    )

        # ── [7] Attention re-read → R_weighted ────────────────────
        R_weighted = self._compute_R_weighted(active_nodes)

        # ── [8] Activate primordials → dnh_hint ───────────────────
        prim_acts = activate_primordials(R_weighted, self._primordials)
        dnh_hint  = prim_acts[0]["dnh_hint"] if prim_acts else None
        gap_signal = prim_acts[0].get("gap_signal", 0.0) if prim_acts else 0.0

        # ── [8.5] AUTO SELECT MODE (Pete decides, not user) ───────────
        mode = self._select_mode(
            gap_signal = gap_signal,
            Gamma      = self._Gamma,
            S_id       = self._odfs_prev.get("S_id", 0.0),
            rho_U      = self._odfs_prev.get("rho_U", 0.5),
            p2_phase   = p2_result.phase,
        )

        # ── [9] R_0 blend — mode dependent ────────────────────────
        # Bug 3 fix: stream_bias = P2 spin → field_vec * 0.15 (spec: "stream_bias(p2, scale=0.15)")
        from .think.consciousness.p2_primordial import SPIN_TO_FIELDS, ODFS_FIELDS as P2_FIELDS
        spin_fields  = SPIN_TO_FIELDS.get(p2_result.spin, ("language","logic"))
        p2_spin_bias = [0.15 if f in spin_fields else 0.0 for f in ODFS_FIELDS]

        # Bug 4 fix: prim_bias uses centroid vector [6], not scalar
        if prim_acts and "centroid" in prim_acts[0]:
            ctrd = prim_acts[0]["centroid"]
            prim_bias = [c * 0.05 for c in ctrd] if isinstance(ctrd, list) else [0.0]*6
        else:
            prim_bias = [0.0]*6

        if mode == "MEDITATION":
            chakra_sig = chakra_resonance(R_sit, passes=3)
            R_0 = _blend(chakra_sig, 0.50, R_weighted, 0.30, p2_spin_bias, 0.15, prim_bias, 0.05)
        elif mode == "GAP.TRAVERSE":
            chakra_sig = chakra_sequential(R_sit, passes=3)
            R_0 = _blend(chakra_sig, 0.60, R_weighted, 0.25, p2_spin_bias, 0.10, prim_bias, 0.05)
        else:  # NORMAL
            R_0 = _blend(R_sit, 0.40, R_weighted, 0.40, p2_spin_bias, 0.15, prim_bias, 0.05)

        # ── [10.0.3] Chakra gap matrix ──────────────────────────────
        # Compute cross-layer chakra gaps BEFORE ODFS (proactive gap awareness).
        from .think.chakra.chakra_resonance import chakra_gap_matrix, gap_to_mode
        _ck_gaps = chakra_gap_matrix(
            chakras_live=self._chakras if hasattr(self, "_chakras") else None
        )
        _ck_tension    = _ck_gaps.get("dominant_tension", "")
        _max_ck_gap    = _ck_gaps.get("max_gap", 0.0)
        _ck_layer_gaps = _ck_gaps.get("layer_gaps", {})
        self._last_chakra_gaps = _ck_gaps   # expose for UI / logging

        # ── [10.0.5] Quantum gap read (proactive meta-awareness) ────────
        # Pete reads its own cognitive position BEFORE processing user input.
        # This shapes attention mode choice proactively rather than reactively.
        _q_state       = self._quantum.tick() if hasattr(self, "_quantum") else {}
        _drift_sev     = _q_state.get("drift_severity", 0.0)
        _pre_mode      = _q_state.get("pre_mode_signal", "STABILIZE")
        _prox_trans    = _q_state.get("proximity_to_transition", 0.0)
        _quantum_gaps  = _q_state.get("quantum_gaps", {})
        # expose to session state for logging / UI
        self._last_quantum_state = _q_state

        # ── [10] ODFS dual kernels ────────────────────────────────
        # Bug 5 fix: use attention-mode tau1 for ODFS run
        from .modes.attention_controller import AttentionController as _AC
        tau1_mode = _AC.tau1(attn_mode)
        odfs_world = run_odfs(R_0, self._Omega_world, self._C_pos, self._C_neg,
                              tau1=tau1_mode, rng=self._rng)
        odfs_user  = run_odfs(R_0, self._Omega_user,  self._C_pos, self._C_neg,
                              tau1=tau1_mode, rng=self._rng)
        odfs_world.stream_awareness = p2_result.awareness
        odfs_world.stream_spin      = p2_result.spin_name

        # ── [10.5] Per-primordial Omega_user update ───────────────
        for ck in self._chakras.values():
            ck.absorb_user_signal(R_0, lr=0.03)
        if self._tick_n % 20 == 0:
            for ck in self._chakras.values():
                try:
                    ck.save_omega_user()
                except Exception:
                    pass

        # ── [10.6] Memory tier + Hoai trigger ─────────────────────
        # Compute hoai_ratio = fraction of known nodes in Hoai phase
        all_nodes = list(self._node_store.values())
        active_ids = set(self._active_cache.get_ids()) if hasattr(self._active_cache, "get_ids") else set()
        hoai_count = sum(1 for n in all_nodes if getattr(n, "hoai_locked", False))
        hoai_ratio  = hoai_count / max(1, len(all_nodes))
        # Update H_tier for all active nodes (Gap 3); dormancy handled in primordial_tick
        from .think.semantic.neuron.neuron import compute_H_tier
        for node in all_nodes:
            if hasattr(node, "H"):
                node.H_tier = compute_H_tier(node.H)

        # ── [10.7] Soft mode weights (Gap 6 + Quantum + Chakra meta-awareness) ──
        self._mode_weights = self._attn.decide_weights(
            self._odfs_prev,
            self._p2_iam_streak if hasattr(self, "_p2_iam_streak") else 0,
            quantum_state  = _q_state,
            hoai_ratio     = hoai_ratio,
            pre_mode_bias  = _pre_mode,        # quantum proactive signal
            drift_severity = _drift_sev,       # identity crisis magnitude
            chakra_gaps    = _ck_gaps,         # cross-layer chakra gap profile
        )
        # Keep backward-compat attn_mode string for older code paths
        attn_mode = max(self._mode_weights, key=self._mode_weights.get)

        # ── [10.8] Semantic drift update (Gap 7) ──────────────────
        dominant_field_idx = R_0.index(max(R_0)) if R_0 else 0
        from .think.semantic.neuron.neuron import ODFS_FIELDS as _OFIELDS
        dominant_field = _OFIELDS[dominant_field_idx]
        from .think.semantic.gravity.field_gravity import update_context_meaning, estimate_grounding
        active_nodes_list = [self._node_store[nid] for nid in self._active_cache._ids
                             if nid in self._node_store] \
                              if hasattr(self._active_cache, "_ids") else []
        for _node in active_nodes_list:
            update_context_meaning(_node, dominant_field)
            _node.grounding = estimate_grounding(_node)
        drift_signal = (sum(getattr(n, "semantic_drift", 0.0) for n in active_nodes_list)
                        / max(1, len(active_nodes_list)))

        # ── [10.9] Identity gap score + matrix (Gap 8 + Gap 2 + Quantum) ──
        lucis_verdict = self._lucis1.guard(odfs_world, odfs_user, p2_result,
                                            self._mode_weights)  # pass soft weights
        # Gap 8 upgrade: also blend in quantum drift_severity
        _l0_gap = lucis_verdict.get("identity_gap_score", 0.0)
        identity_gap_score = max(_l0_gap, _drift_sev)  # worst-case gap wins
        lucis_verdict["identity_gap_score"] = identity_gap_score
        # Refresh identity gap matrix every 100 ticks
        if self._tick_n % 100 == 0:
            self._compute_identity_gaps()

        # Lucis2 referee (every 50 ticks)
        l2_report = self._lucis2.maybe_audit(self._lucis1.field_vec, self._tick_n)
        if l2_report:
            print(f"[Lucis2] {l2_report['status']} alignment={l2_report['alignment']:.3f}")

        # ── [12] Identity coherence ───────────────────────────────
        identity_coherence = compute_identity_coherence(
            p2_result.meaning, self._node_store)

        # ── [13] Build ProcessResult ──────────────────────────────
        self._tick_n += 1
        S_combined = odfs_world.S_combined

        # Bug 2 fix: Gamma increments when S_combined low (chaos/confusion)
        if S_combined < 0.3:
            self._Gamma += 0.05
        elif S_combined > 0.6:
            self._Gamma = max(0.0, self._Gamma - 0.02)
        # Bug 6 fix: auto-save every 50 ticks
        if self._tick_n % 50 == 0:
            try:
                self.save()
            except Exception as e:
                print(f"[PEngine] auto-save error: {e}")

        # Session state update → detect dream trigger
        dream_ready = self._session.tick(mode, S_combined)

        self._odfs_prev = {
            "rho_U": odfs_world.rho_U,
            "S_id":  odfs_world.S_id,
            "Gamma": self._Gamma,
        }

        # 36 subgates scoring via lucis_gate
        try:
            from .think.lucis.lucis_gate import run_lucis_gate
            enl_max = max((getattr(n,'enlightenment',0) for n in active_nodes), default=0)
            gate_result = run_lucis_gate(
                odfs_world, odfs_user, p2_result,
                active_nodes, dnh_hint, enl_max, self._tick_n
            )
            dominant_subgate = gate_result["dominant_subgate"]
            dominant_field   = gate_result["dominant_field"]
            lucis_verdict["lucis_class"] = gate_result["lucis_class"]
            lucis_verdict["pool"]        = gate_result["pool"]
            lucis_verdict["gap"]         = gate_result["gap"]
        except Exception as e:
            dominant_field   = ODFS_FIELDS[R_weighted.index(max(R_weighted))] if R_weighted else "language"
            dominant_subgate = f"{dominant_field}.{p2_result.phase}"

        # ── [Wave tick] Advance wave states + 3-level gap field density ─────────
        gap_density         = 0.0
        wave_dominant_prime = "Dan"
        neuro_gap           = {}
        try:
            from .think.odfs.gap_field import (compute_gap_field_density,
                                               compute_adaptive_tick_hz)
            from .think.odfs.gap_field_neuro import (compute_neuro_gap_density,
                                                      gap_density_report)
            DT = 1.0 / 30.0   # default ~30Hz until adaptive
            self._wave_t += DT
            # Sync wave amplitudes to current R_weighted
            if self._wave_states and R_weighted:
                r_max = max(R_weighted) or 1.0
                for i, fname in enumerate(ODFS_FIELDS):
                    if fname in self._wave_states and i < len(R_weighted):
                        self._wave_states[fname].amp = max(0.05, R_weighted[i] / r_max)
                        self._wave_states[fname].advance(DT)
            gf = compute_gap_field_density(self._wave_states, self._wave_t)
            gap_density = gf["density"]

            # ── 3-level neuro gap field density ──────────────────────────
            # L1 synaptic: unnamed_feel magnitude from wave residue
            uf_vec = [gf["field_gaps"].get(f, 0.0) for f in ODFS_FIELDS]
            import math
            uf_mag = math.sqrt(sum(x*x for x in uf_vec))

            # L2 dendritic: field gravity = how far R_weighted is from even
            even = 1.0 / len(ODFS_FIELDS)
            field_grav = sum(abs(r - even) for r in R_weighted) / len(ODFS_FIELDS)

            # L3 columnar: S_id vs C_pos from ODFS
            s_id_val  = float(odfs_world.__dict__.get("S_id",  0.0) or 0.0)
            c_pos_val = float(odfs_world.__dict__.get("C_pos", 0.0) or 0.0)

            neuro_gap = compute_neuro_gap_density(
                unnamed_feel_magnitude = uf_mag,
                field_gravity_gap      = field_grav,
                s_id                   = s_id_val,
                c_pos                  = c_pos_val,
            )
            # Override gap_density with composite neuro score
            gap_density = neuro_gap.get("density", gap_density)

            # Adaptive DT: use suggested_hz from neuro gap
            next_hz = neuro_gap.get("suggested_hz", 30.0)
            DT = 1.0 / next_hz  # will apply next tick

            from .think.semantic.p1.wave_lifecycle import dominant_interference
            di = dominant_interference(self._wave_states, self._wave_t)
            wave_dominant_prime = di.get("prime", "Dan")
        except Exception:
            pass


        return {
            "active_nodes":        [n.to_dict() for n in active_nodes[:10]],
            "R_0":                 R_0,
            "R_weighted":          R_weighted,
            "odfs_world":          odfs_world.__dict__,
            "odfs_user":           odfs_user.__dict__,
            "lucis_verdict":       lucis_verdict,
            "p2_result":           p2_result.__dict__,
            "identity_coherence":  round(identity_coherence, 4),
            "primordial_activations": prim_acts[:3],
            "dnh_hint":            dnh_hint,
            "attention_mode":      attn_mode,
            "processing_mode":     mode,
            "dominant_field":      dominant_field,
            "dominant_subgate":    dominant_subgate,
            "tick":                self._tick_n,
            "quantum_state":       q_state,
            "dream_ready":         dream_ready,
            "session":             self._session.to_dict(),
            # Wave layer (additive)
            "gap_density":         round(gap_density, 4),
            "wave_dominant_prime": wave_dominant_prime,
            # 3-level neuroscience gap density
            "neuro_gap":           neuro_gap,
        }



    def _select_mode(self, gap_signal: float, Gamma: float,
                     S_id: float, rho_U: float, p2_phase: str) -> str:
        """
        Pete selects its own processing mode. User has no control.

        GAP.TRAVERSE: strong gap felt via primordials → follow the gap
          trigger: gap_signal > 0.5 (felt something but can't name it)

        MEDITATION: Pete is stable and processing deeply
          trigger: Gamma > 2.0 (accumulated noise)
                   AND rho_U > 0.5 (field still active, not collapsed)
                   AND S_id > 0.4  (identity coherent enough to go deep)
                   OR  p2_phase == "Dung" (P2 integrating)

        NORMAL: default
        """
        # GAP.TRAVERSE — Pete senses a gap it can't bridge yet
        if gap_signal > 0.50:
            return "GAP.TRAVERSE"

        # MEDITATION — accumulated noise + Pete still stable
        if Gamma > 2.0 and rho_U > 0.50 and S_id > 0.40:
            return "MEDITATION"

        # P2 in Dung phase = integrating identity → meditate
        if p2_phase == "Dung" and rho_U > 0.55:
            return "MEDITATION"

        return "NORMAL"

    # ── Select active ──────────────────────────────────────────────────────
    def _select_active(self, attn_mode: str, event_nodes: list = None) -> list:
        """
        Per blueprint §3 step [6]:
          STABILIZE: prefer weighted (W>=0.5) AND not Q
          GROW:      prefer quantum (Q=True)
          TRANSITION: balanced (W>=0.5 OR Q)

        Always includes event_nodes (current input symbols) as mandatory
        active nodes — they have just been processed and are highest priority.
        """
        nodes = list(self._node_store.values())
        event_ids = {n.node_id for n in (event_nodes or [])}

        if attn_mode == "STABILIZE":
            pool = [n for n in nodes if n.W >= 0.5 and not n.Q
                    and n.node_id not in event_ids][:15]
        elif attn_mode == "GROW":
            pool = [n for n in nodes if n.Q
                    and n.node_id not in event_ids][:15]
        else:  # TRANSITION
            pool = [n for n in nodes if (n.W >= 0.5 or n.Q)
                    and n.node_id not in event_ids][:15]

        # Merge: event_nodes first (they're the current focus), then pool
        combined = list(event_nodes or []) + pool
        return combined[:20]

    def _compute_R_weighted(self, active_nodes: list) -> list:
        if not active_nodes: return [1/6]*6
        centroid = [0.0]*6
        for n in active_nodes:
            for i, f in enumerate(ODFS_FIELDS):
                centroid[i] += n.meaning.get(f, 0)
        c = [x/len(active_nodes) for x in centroid]
        attn = [_cosine([n.meaning.get(f,0) for f in ODFS_FIELDS], c)
                for n in active_nodes]
        total_attn = sum(attn) or 1.0
        R = [0.0]*6
        for n, aw in zip(active_nodes, attn):
            w = aw / total_attn
            for i, f in enumerate(ODFS_FIELDS):
                R[i] += w * n.meaning.get(f, 0)
        R_max = 10.0
        R_attention = [min(x * R_max, R_max) for x in R]

        # ★ Subconscious blend (tiềm thức) — 15% background signal
        # Queries subconscious.db for neighbors of active node ids,
        # counts neighbor overlap with node_store for implicit field pull.
        try:
            from I.I_unconscious import query_neighbors
            sub_counts = [0.0] * 6
            sub_total  = 0
            for n in active_nodes[:8]:   # limit to top-8 for speed
                nid = n.node_id
                neighbors = query_neighbors(nid, top_k=5)
                for nb in neighbors:
                    nb_node = self._node_store.get(nb)
                    if nb_node:
                        for i, f in enumerate(ODFS_FIELDS):
                            sub_counts[i] += nb_node.meaning.get(f, 0)
                        sub_total += 1
            if sub_total > 0:
                R_sub = [v / sub_total for v in sub_counts]
                # 85% attention + 15% subconscious
                R_attention = [0.85 * a + 0.15 * s
                               for a, s in zip(R_attention, R_sub)]
        except Exception:
            pass  # subconscious unavailable → pure attention

        return R_attention


    # ── Save ───────────────────────────────────────────────────────────────
    def save(self):
        ns_path = D_PATH / "long_term/node_store/node_store.json"
        ns_path.write_text(
            json.dumps({k: v.to_dict() for k,v in self._node_store.items()},
                       ensure_ascii=False),
            encoding="utf-8")
        cg_path = D_PATH / "long_term/graph/cooc_graph.json"
        cg_path.write_text(
            json.dumps(self._ppmi.to_cooc_dict(), ensure_ascii=False),
            encoding="utf-8")

    @property
    def stats(self) -> dict:
        return {
            "nodes":    len(self._node_store),
            "fields":   len(self._field_store),
            "primordials": len(self._primordials),
            "tick":     self._tick_n,
            "loading":  self._loading,
            "load_progress": self._load_progress,
        }

# ── Utility ────────────────────────────────────────────────────────────────
def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    if na==0 or nb==0: return 0.0
    return dot/(na*nb)

def _blend(*pairs) -> list:
    """Weighted blend of multiple [6] lists. pairs = (vec, weight, vec, weight...)"""
    result = [0.0]*6
    total_w = 0.0
    it = iter(pairs)
    for vec, w in zip(it, it):
        for i in range(6): result[i] += vec[i] * w
        total_w += w
    if total_w > 0:
        result = [x/total_w for x in result]
    return result
