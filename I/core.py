"""I/core.py — IEngine: processes raw text into LearningEvent."""
from __future__ import annotations
from .contracts import LearningEvent
from .P.situation import extract_situation
from .P.normalize import normalize, tokenize, context_pairs
from .P.boundary import process_boundary
from .P.segment import process_segment

from .O.build import build_verified_symbols


class IEngine:
    def __init__(self):
        self._total_tokens = 0
        self._freq_map: dict = {}

    def process(self, text: str, source: str = "user",
                modality: str = "chat") -> LearningEvent:
        """
        Full I-layer pipeline per spec:
        1. extract_situation (BEFORE tokenization) ★
        2. boundary: language detection + source_weight
        3. normalize + tokenize
        4. segment: filter stop words, junk, repeated chars
        5. I/O/build: L(n) verification (freq^0.5 × CF × D × Surp × src_weight)
        6. context_pairs
        7. Build LearningEvent
        """
        # ★ Step 1: SituationSignal BEFORE tokenization
        sig = extract_situation(text)

        # Step 2: boundary — language + source weight
        boundary      = process_boundary(text, source)
        source_weight = boundary["source_weight"]
        lboost        = boundary["language_boost"]

        # Step 3: normalize + raw tokenize
        raw_tokens = tokenize(text)
        if not raw_tokens:
            raw_tokens = ["empty"]

        # Step 4: segment filter (stop words, junk, repetition)
        filtered_tokens = process_segment(raw_tokens)
        if not filtered_tokens:
            filtered_tokens = raw_tokens  # fallback to raw if all filtered

        # Step 5: context pairs + L(n) symbol verification
        pairs = context_pairs(filtered_tokens, window=3)
        self._total_tokens += len(filtered_tokens)
        for tok in filtered_tokens:
            self._freq_map[tok] = self._freq_map.get(tok, 0) + 1

        verified = build_verified_symbols(
            filtered_tokens, pairs, self._total_tokens, source_weight
        )
        if not verified:
            verified = filtered_tokens  # fallback if nothing passes (fresh Pete)

        # ★ Step 6: Subconscious expansion (tiềm thức)
        # Query subconscious.db for background semantic neighbors of verified symbols.
        # Appended AFTER verification — expands context without affecting L(n) scoring.
        try:
            from .I_unconscious import expand_context
            sub_pairs = expand_context(verified, pairs, top_k=5)
            pairs = pairs + sub_pairs
        except Exception:
            pass  # subconscious.db unavailable → continue without it

        return LearningEvent(
            normalized_symbol_ids = verified,
            context_pairs         = pairs,
            source_weight         = source_weight,
            language_boost        = lboost,
            modality              = modality,
            situation_signal      = sig,
            raw_text              = text,     # ← for dual-route filter in p_engine step 0.6
        )
