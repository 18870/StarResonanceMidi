"""Instrument classification helpers.

This module maps MIDI channel/program information to the app-level classes:
`drum`, `bass`, `guitar`, `keys`, and `unknown`.
"""

from __future__ import annotations

from typing import Literal

try:
    import music21
except ImportError:
    music21 = None

SplitClass = Literal["drum", "bass", "guitar", "keys", "unknown"]


class InstrumentClassifier:
    """Classify MIDI channels/programs with music21 and GM fallbacks."""

    def __init__(self):
        """Initialize classifier with music21 support."""
        self.music21 = music21
        self.has_music21 = self.music21 is not None

    def classify_program(self, program: int) -> tuple[SplitClass, float]:
        """
        Classify a MIDI program number to an instrument class.

        Args:
            program: MIDI program number (0-127)

        Returns:
            Tuple of (split_class, confidence) where confidence is 0.0-1.0
        """
        if self.has_music21:
            return self._classify_with_music21(program)
        else:
            return self._classify_with_fallback(program)

    def _classify_with_music21(self, program: int) -> tuple[SplitClass, float]:
        """Classify a program using music21's instrument mapping."""
        if self.music21 is None:
            return self._classify_with_fallback(program)

        try:
            from music21 import instrument as m21_instrument

            # Resolve instrument metadata from MIDI program number.
            inst = m21_instrument.instrumentFromMidiProgram(program)
            if inst is None:
                return self._classify_by_program_range(program) or ("unknown", 0.0)

            raw_name = getattr(inst, "instrumentName", None) or getattr(inst, "bestName", lambda: "")()
            instrument_name = str(raw_name).lower() if raw_name else ""
            instr_class = inst.inGMPercMap

            # Map the resolved instrument metadata to app classes.
            return self._map_music21_to_class(inst, instrument_name, instr_class, program)
        except Exception:
            # Keep classification robust even if music21 parsing fails.
            return self._classify_with_fallback(program)

    def _map_music21_to_class(
        self, inst, instrument_name: str, in_gm_perc_map: bool, program: int | None = None
    ) -> tuple[SplitClass, float]:
        """Map music21 instrument to our 5 classes with confidence based on evidence."""
        instrument_name = instrument_name.lower()
        confidence = 0.0
        split_class = "unknown"

        # 1) Percussion map signal (strongest).
        if in_gm_perc_map:
            return ("drum", 0.98)

        # 2) Name keyword signal.
        drum_keywords = ["drum", "percussion", "kick", "snare", "cymbal", "hi-hat"]
        bass_keywords = ["bass", "acoustic bass", "electric bass", "double bass", "upright bass"]
        guitar_keywords = ["guitar", "acoustic guitar", "electric guitar", "nylon", "steel", "distortion"]
        keys_keywords = ["piano", "keys", "keyboard", "organ", "synth", "synthesizer", "electric piano"]

        # Count keyword hits per class.
        drum_hits = sum(1 for kw in drum_keywords if kw in instrument_name)
        bass_hits = sum(1 for kw in bass_keywords if kw in instrument_name)
        guitar_hits = sum(1 for kw in guitar_keywords if kw in instrument_name)
        keys_hits = sum(1 for kw in keys_keywords if kw in instrument_name)

        # Pick the class with the highest keyword hit count.
        candidates: list[tuple[SplitClass, int]] = [
            ("drum", drum_hits),
            ("bass", bass_hits),
            ("guitar", guitar_hits),
            ("keys", keys_hits),
        ]
        best_class, best_hits = max(candidates, key=lambda x: x[1])

        if best_hits > 0:
            split_class = best_class
            # 1 hit=0.70, 2 hits=0.80, 3+ hits=0.90
            confidence = min(0.90, 0.70 + (best_hits - 1) * 0.10)
            return (split_class, confidence)

        # 3) GM program range signal.
        if program is not None:
            program_conf = self._classify_by_program_range(program)
            if program_conf is not None:
                return program_conf

        # No clear signal; preserve channel as unknown.
        return ("unknown", 0.25)

    def _classify_by_program_range(self, program: int) -> tuple[SplitClass, float] | None:
        """Classify based on GM standard program ranges with confidence based on specificity."""
        # GM program ranges are 0-indexed. More specific ranges get higher confidence.

        if 32 <= program <= 39:  # Electric Bass (8 programs, very specific)
            return ("bass", 0.92)
        elif 40 <= program <= 47:  # Acoustic/Electric Guitar (8 programs, very specific)
            return ("guitar", 0.92)
        elif 0 <= program <= 8:  # Acoustic/Electric Piano
            return ("keys", 0.88)
        elif 9 <= program <= 15:  # Chromatic Percussion
            return ("keys", 0.75)
        elif 16 <= program <= 23:  # Organ
            return ("keys", 0.90)
        elif 24 <= program <= 31:  # Guitar-like, but less specific than 40-47
            return ("guitar", 0.75)
        elif 48 <= program <= 55:  # Strings mapped to keys in the current 5-class model
            return ("keys", 0.60)
        elif 56 <= program <= 63:  # Brass mapped to keys in the current 5-class model
            return ("keys", 0.55)
        elif 64 <= program <= 79:  # Synth Lead / Synth Pad
            return ("keys", 0.85)
        elif 80 <= program <= 87:  # Synth Pad
            return ("keys", 0.85)
        elif 88 <= program <= 95:  # Chromatic Percussion
            return ("keys", 0.70)
        else:
            return None  # Unknown

    def _classify_with_fallback(self, program: int) -> tuple[SplitClass, float]:
        """Classify using GM standard program ranges (fallback when music21 unavailable)."""
        # First try deterministic GM range mapping.
        result = self._classify_by_program_range(program)
        if result is not None:
            return result
        # Keep unresolved programs visible as unknown.
        return ("unknown", 0.20)

    def classify_channel(self, channel_1_based: int, program: int) -> tuple[SplitClass, float]:
        """
        Classify a MIDI channel considering both channel number and program.

        Args:
            channel_1_based: MIDI channel (1-16)
            program: MIDI program number (0-127)

        Returns:
            Tuple of (split_class, confidence)
        """
        # GM convention: channel 10 is percussion.
        if channel_1_based == 10:
            return ("drum", 0.99)

        # Non-percussion channels use program-based classification.
        return self.classify_program(program)
