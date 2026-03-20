from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SplitClass = Literal["drum", "bass", "guitar", "keys", "unknown"]


PARAMS_VERSION = "v0"


@dataclass(frozen=True)
class GlobalWeights:
    protocol: float = 0.50
    name: float = 0.25
    physical: float = 0.25


@dataclass(frozen=True)
class DecisionThresholds:
    min_confidence: float = 0.45
    min_margin: float = 0.12
    drum_margin_relax: float = 0.08


@dataclass(frozen=True)
class SplitLimits:
    default_max_outputs: int = 6
    min_outputs: int = 2
    hard_max_outputs: int = 8


@dataclass(frozen=True)
class ContinuityGuard:
    min_segment_beats: int = 8
    min_segment_note_ratio: float = 0.10
    min_segment_duration_sec: float = 6.0
    max_switches_per_16_beats: int = 3
    switch_penalty: float = 0.12
    weak_branch_merge_threshold: float = 0.18


@dataclass(frozen=True)
class IntraClassSplit:
    enabled: bool = True
    max_subclusters_per_class: int = 2
    min_notes: int = 80
    min_duration_sec: float = 10.0
    min_separation: float = 0.28
    min_stability: float = 0.65


@dataclass(frozen=True)
class ProtocolHints:
    drum_channel_1_based: int = 10
    drum_channel_score: float = 1.0
    drum_note_ratio_strong: float = 0.35
    drum_note_ratio_bonus: float = 0.40
    bass_program_range: tuple[int, int] = (32, 39)
    guitar_program_range: tuple[int, int] = (24, 31)
    keys_program_range: tuple[int, int] = (0, 7)
    program_bonus_bass: float = 0.55
    program_bonus_guitar: float = 0.50
    program_bonus_keys: float = 0.50


@dataclass(frozen=True)
class NameHints:
    drum_tokens: tuple[str, ...] = ("drum", "drums", "perc", "percussion", "kick", "snare", "hihat", "hh", "tom", "cymbal")
    bass_tokens: tuple[str, ...] = ("bass", "contrabass", "upright", "sub", "bs")
    guitar_tokens: tuple[str, ...] = ("guitar", "gtr", "gt", "leadgtr", "rhythmgtr", "acgtr", "elgtr")
    keys_tokens: tuple[str, ...] = ("piano", "keys", "keyboard", "ep", "organ", "synth", "clav", "pn")
    strong_hit_score: float = 0.40
    token_cap_per_class: float = 0.60


@dataclass(frozen=True)
class PhysicalThresholds:
    bass_avg_pitch_max: float = 52.0
    bass_low_ratio_min: float = 0.55
    bass_bonus: float = 0.45
    guitar_avg_pitch_min: float = 50.0
    guitar_avg_pitch_max: float = 76.0
    guitar_high_ratio_max: float = 0.40
    guitar_bonus: float = 0.35
    keys_avg_pitch_min: float = 52.0
    keys_avg_pitch_max: float = 84.0
    keys_bonus: float = 0.35
    drum_pitch_ratio_min: float = 0.25
    drum_bonus: float = 0.30


@dataclass(frozen=True)
class ParamsBundle:
    mode: Literal["coherence_first", "separation_first"] = "coherence_first"
    weights: GlobalWeights = GlobalWeights()
    thresholds: DecisionThresholds = DecisionThresholds()
    limits: SplitLimits = SplitLimits()
    continuity: ContinuityGuard = ContinuityGuard()
    intra_class: IntraClassSplit = IntraClassSplit()
    protocol: ProtocolHints = ProtocolHints()
    names: NameHints = NameHints()
    physical: PhysicalThresholds = PhysicalThresholds()


DEFAULT_PARAMS = ParamsBundle()


def get_params(mode: Literal["coherence_first", "separation_first"] = "coherence_first") -> ParamsBundle:
    """Return parameter bundle for a mode.

    Keep this indirection so future tuning profiles can diverge without touching callers.
    """
    if mode == "separation_first":
        return ParamsBundle(
            mode=mode,
            thresholds=DecisionThresholds(min_confidence=0.40, min_margin=0.10, drum_margin_relax=0.06),
            limits=SplitLimits(default_max_outputs=8, min_outputs=2, hard_max_outputs=8),
            continuity=ContinuityGuard(
                min_segment_beats=4,
                min_segment_note_ratio=0.08,
                min_segment_duration_sec=4.0,
                max_switches_per_16_beats=5,
                switch_penalty=0.08,
                weak_branch_merge_threshold=0.12,
            ),
        )
    return DEFAULT_PARAMS
