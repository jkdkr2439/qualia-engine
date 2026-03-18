# qualia-engine

> A cognitive architecture that simulates the human thinking process — from raw sensation to conscious output.

Not an LLM wrapper. Not a RAG pipeline. Not another transformer variant.

This is a bottom-up attempt to model **what actually happens inside a mind** — the pre-linguistic flicker before a thought becomes a word, the gravitational pull between ideas, the gap between knowing and saying, the moment a concept crystallizes from noise into meaning.

Each subsystem in this architecture is a standalone idea that has no direct equivalent in current AI literature:

- **ODFS** — a field-based meaning engine where concepts exist as ontological drift attractors, not static vectors
- **Gap Fields** — models the *tension* between what is known and what is missing, treating incompleteness as a first-class cognitive signal
- **Lucis Layers** — a three-stage verdict system modeled after how consciousness filters, audits, and commits to a thought before it surfaces
- **Semantic Gravity** — meaning is not stored, it is *pulled into existence* by the gravitational relationship between active nodes
- **Quantum Particles** — identity and attention modeled as entangled states that collapse under observation
- **P2 Primordial Consciousness** — session-level self-awareness that tracks the system's own becoming, not just its outputs
- **Symbol Learning via L(n)** — symbols earn their existence through a formula combining frequency, surprise, context depth, and source trust

Any one of these, implemented and published properly, is a research paper. Together, they are something else entirely.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Init databases
python D/bootstrap.py

# 3. Start server + open monitor UI
start.bat          # Windows — auto-opens http://localhost:8000
# or manually:
python I/server.py
```

> **Monitor UI** → [http://localhost:8000](http://localhost:8000) — real-time dashboard tracking all internal metrics (ODFS, P2, Lucis, Gap Field, active nodes, 36 subgates)

> **Full logic flow** → see [FLOW.md](./FLOW.md)

---

## Architecture Summary

| Layer | Entry | Description | Key Subsystems |
|-------|-------|-------------|---------------|
| **I** | `I/core.py` | 7-step input pipeline → `LearningEvent` | SituationSignal, L(n) formula, boundary detect, subconscious expand |
| **P** | `P/p_engine.py` | 13-step cognitive tick — the brain | ODFS dual kernels, P2 consciousness, 7 chakras, Lucis verdict, quantum particles, wave states, semantic gravity, memory tiers |
| **O** | `O/gate/`, `O/compose/` | Output generation pipeline | 5 gates (THINK/FEEL/SAY/DO/SHOW), pattern match, surface realizer, literary scorer, P-space anti-echo |
| **D** | `D/db.py` | SQLite data layer (WAL) | 6 tables: nodes, cooc, grammar, role_positions, identity, patterns |

| Subsystem | File | What it does |
|-----------|------|-------------|
| ODFS Kernel | `P/think/odfs/odfs_kernel.py` | RK4 field dynamics, ASSIMILATE/QUARANTINE/EXCRETE verdict |
| SemanticNeuron | `P/think/semantic/neuron/neuron.py` | Node with 6D meaning, lifecycle phases Vo→Sinh→Dan→Chuyen→Dung→Hoai |
| P2 Consciousness | `P/think/consciousness/p2_primordial.py` | Session self-awareness, spin, IAM streak |
| Lucis Gate | `P/think/lucis/lucis_gate.py` | 5 roles + 36 subgates (6 fields × 6 phases) + GapEngine |
| Chakra System | `P/think/chakra/` | 7 chakras, each with own Ω_user kernel + 7 seed sets |
| Gap Field | `P/think/odfs/gap_field.py` | 3-level neuro gap density (L1/L2/L3) |
| Subconscious | `P/think/subconscious.py` | Background 70k-word pool; 15% blend into R_weighted |
| Symbol Learning | `I/O/build.py` | `L(n) = freq^0.5 × CF × D × Surp × source_weight` |

---

## Architecture: I → P → O → D

```
Input (I)           Processing (P)           Output (O)
─────────────       ──────────────────────   ──────────────────
Raw text            Semantic neurons         Gate routing
  ↓                 ODFS field dynamics        THINK / FEEL
Situation signal    Consciousness (P2)          SAY / DO / SHOW
  ↓                 Subconscious queries       ↓
Symbol formation    Chakra resonance         Surface realizer
  ↓                 Memory consolidation       Literary scoring
LearningEvent  →→→  Lucis verdict      →→→  P-space output

                         ↕
                   Data Layer (D)
                   ─────────────
                   Node store (SQLite)
                   Co-occurrence matrix
                   Grammar scores
                   Identity + memory DBs
```

---

## Core Concepts

### Semantic Neurons
Each concept is a `SemanticNeuron` — not a vector embedding, but a structured object with:
- **ODFS keys**: Ontology · Depth · Field · Salience
- **Gap fields**: the "tension" between what is known and what is missing
- **Wave lifecycle**: nodes are born, activated, promoted, and decay over time

### ODFS — Ontological Drift Field System
The processing core. Nodes exist in a field with gravity, repulsion, and resonance. Meaning emerges from **field dynamics**, not lookup tables.

> **Naming note:** The acronym oscillates between *Field* and *Form* depending on context — both are valid readings. "Field" emphasizes the spatial/dynamic substrate; "Form" emphasizes the ontological shape a concept takes as it drifts. No final decision has been made. When you see ODFS written as "Ontological Drift Form System" elsewhere in the codebase or papers, it means the same thing.


### Consciousness Layers
- **P1** — prelinguistic activation: raw symbol firing
- **P2** — primordial consciousness: session-level self-awareness, identity tracking
- **Lucis** — the verdict layer: decides what surfaces into output (lucis_0 → lucis_1 → lucis_2)
- **Subconscious** — background queries that surface without direct attention

### Symbol Learning
Symbols are learned from statistical patterns (PMI estimation, co-occurrence), shaped by:
- Source weight (trust level of input source)
- Surprise factor
- Context frequency
- The `L(n)` formula: `freq^0.5 × CF × D × Surp × source_weight`

### Output Generation
Not template-fill. The output pipeline:
1. Active nodes → gate routing (cosine similarity)
2. ODFS context → dominant gate detection
3. MasterPattern matching → SentenceSkeleton
4. Slot filling → surface realization
5. Literary scoring (coherence, surprise, rhythm, gap_tension)
6. P-space anti-echo filter (avoids repeating itself)

---

## Structure

```
Pete_Lucison/
├── I/                      Input layer
│   ├── core.py             IEngine — 13-step input pipeline
│   ├── contracts.py        Data contracts (SituationSignal, LearningEvent)
│   ├── I_unconscious.py    Void/subconscious context expansion
│   ├── server.py           FastAPI server (/chat, /stats, /graph, /trace)
│   ├── P/                  Input processing
│   │   ├── situation.py    Emotion, valence, urgency extraction
│   │   ├── normalize.py    NFC normalization, tokenization
│   │   ├── boundary.py     Language detection, source weighting
│   │   └── segment.py      Symbol segmentation, stop filtering
│   └── O/                  Input verification
│       └── build.py        Symbol scoring via L(n) formula
│
├── P/                      Processing / Thinking layer
│   ├── p_engine.py         PEngine — master orchestrator (13-step tick)
│   ├── think/
│   │   ├── semantic/
│   │   │   ├── neuron/     SemanticNeuron dataclass + meaning helpers
│   │   │   ├── p1/         Prelinguistic activation, wave lifecycle
│   │   │   ├── prelinguistic/  Dual-route activation, node building
│   │   │   └── gravity/    Field gravity dynamics
│   │   ├── odfs/           ODFS kernel, gap fields, wave states
│   │   ├── consciousness/  P2 primordial consciousness
│   │   ├── lucis/          Lucis verdict layers (0/1/2), dream engine
│   │   ├── chakra/         Chakra resonance + 7 seed sets
│   │   ├── memory/         Memory consolidation
│   │   └── subconscious.py Subconscious background layer
│   ├── working/            Runtime working memory (session state, cache)
│   ├── modes/              Attention controller
│   └── HardMemory/         Hard memory loader
│
├── O/                      Output layer
│   ├── gate/               Output gates (THINK/FEEL/SAY/DO/SHOW) + router
│   └── compose/            Full generation pipeline
│       ├── pattern_registry.py   MasterPattern definitions
│       ├── pattern_matcher.py    Best-match selection
│       ├── pattern_generator.py  SentenceSkeleton generation
│       ├── surface_realizer.py   Full fractal sentence pipeline
│       ├── p_space_realizer.py   P-space anti-echo generation
│       ├── literary_scorer.py    Coherence/surprise/rhythm/gap_tension
│       ├── variant_generator.py  8 sentence variant structures
│       ├── grammar_learner.py    Grammar store (SQLite-backed)
│       ├── lexicalize.py         Dynamic lexicalization
│       └── ...
│
└── D/                      Data layer
    ├── db.py               PeteDB — central SQLite (nodes, cooc, grammar, identity)
    ├── db_gateway.py       Gateway managing 7 databases
    ├── bootstrap.py        System initialization (matrices, empty stores)
    └── build_patterns.py   Build initial MasterPatterns
```

---

## Getting Started

```bash
pip install -r requirements.txt

# Initialize databases
python D/bootstrap.py

# Run the server
python I/server.py
# → http://localhost:8000
```

---

## Philosophy

Most AI systems today are **stateless retrieval machines** — they don't think, they look up.

Pete Lucison explores a different question:

> What if meaning was not stored but **generated** — moment to moment — from the dynamic tension between what is known, what is missing, and what the system is becoming?

This is an open architecture. Every layer can be extended, replaced, or reimagined.

---

## Origin

Built by an independent researcher with no academic affiliation, no publications, and no interest in either.

Working across:

**Physics & Mathematics**
quantum mechanics · wave physics & interference · oscillatory systems · differential equations (RK4 integration) · linear algebra · signal processing · statistical mechanics · nonlinear dynamics & bifurcation theory · control theory

**Neuroscience & Consciousness**
consciousness studies · phenomenology · cognitive neuroscience · neural oscillations · EEG frequency bands (theta / alpha / beta / gamma) · memory consolidation · embodied cognition

**Philosophy**
philosophy of mind · epistemology · metaphysics · ethics & value theory · phenomenology (Husserl-style intentionality) · Eastern philosophical frameworks (Buddhist/Vietnamese consciousness models)

**Linguistics & NLP**
computational linguistics · semantics · pragmatics · speech act theory · literary linguistics · stylometry · co-occurrence statistics

**Information Theory & AI**
information theory (PMI / entropy) · information geometry · reinforcement learning · attention mechanisms · embedding space theory · associative learning · systems theory · cybernetics

**Domain-hybrid concepts invented along the way**: ODFS (Ontological Drift Field System), semantic gravity, gap fields, Lucis verdict layers, P-space anti-echo, primordial consciousness phases.

Zero syntax knowledge. Not a single line written by hand — 100% AI-coded, because learning syntax felt like a waste of time when the ideas were the point.

Currently busy and too lazy to finish it alone, so throwing it out here for anyone who wants to pick it up and play with it.

**~40% complete** relative to the original vision. The bones are there. The rest is up to whoever finds this interesting.

**Author:** Kevin T.N.
**Contact:** jkdkr2439@gmail.com · keedavinci@gmail.com

---

## Foundation Papers

The `z. Foundation_Paper/` directory contains the theoretical basis for this architecture — formal frameworks written to serve one purpose: figuring out how to build this thing.

These papers are **not peer-reviewed**. They make no claims about absolute truth, physical completeness, or empirical validation. They are working documents — a way of thinking out loud rigorously enough to turn ideas into code.

The frameworks defined here — ODFS, Prime Family, Two-Substrate Theory, DCIP, SCFL, Fractal Semantic Coordinates — exist solely to answer the question: *what would a system need to simulate human consciousness?* Not to prove anything about the world. Not to claim priority. Just to build.

If something in there is useful to you, use it.

---

## Status

Work in progress. Contributions welcome — especially from people who think differently about how minds work.

---

## License

**GNU Affero General Public License v3.0 (AGPL-3.0)**

Free to use, study, modify, and build upon — but if you deploy this (or any derivative) as a networked service or product, you must open-source your entire codebase under the same license.

You cannot take this, close the source, and ship a product. That's the point.
