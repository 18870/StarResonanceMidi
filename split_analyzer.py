from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, cast

import mido

from split_params import ParamsBundle, SplitClass, get_params


@dataclass(frozen=True)
class ChannelFeatureSummary:
    channel_1_based: int
    note_count: int
    min_pitch: int | None
    max_pitch: int | None
    avg_pitch: float | None
    low_pitch_ratio: float
    high_pitch_ratio: float
    drum_pitch_ratio: float
    program_hist: dict[int, int]
    name_tokens: tuple[str, ...]


@dataclass(frozen=True)
class ChannelDecision:
    channel_1_based: int
    label: str
    split_class: SplitClass
    confidence: float
    margin: float
    note_count: int
    score_map: dict[SplitClass, float]


@dataclass(frozen=True)
class SplitAnalysisResult:
    midi_path: str
    decisions: tuple[ChannelDecision, ...]
    selected_targets: tuple[str, ...]


class SplitAnalyzer:
    """Channel-centric split analyzer skeleton.

    Current file provides structure and extension points.
    Wire this into main controller after scoring rules are implemented.
    """

    def __init__(self, params: ParamsBundle | None = None) -> None:
        self.params = params or get_params("coherence_first")

    def analyze_file(self, midi_path: str, max_targets: int | None = None) -> SplitAnalysisResult:
        midi = mido.MidiFile(midi_path)
        channel_features = self._collect_channel_features(midi)
        decisions = tuple(self._classify_channel(feature) for feature in channel_features)
        feature_map = {feature.channel_1_based: feature for feature in channel_features}

        limit = max_targets if max_targets is not None else self.params.limits.default_max_outputs
        selected = self._select_targets(decisions, feature_map, limit)
        return SplitAnalysisResult(
            midi_path=str(Path(midi_path).expanduser().resolve(strict=False)),
            decisions=decisions,
            selected_targets=tuple(selected),
        )

    def _collect_channel_features(self, midi: mido.MidiFile) -> list[ChannelFeatureSummary]:
        """Collect per-channel note statistics.

        This intentionally keeps only a minimal feature set for now.
        Extend here with rhythm density, polyphony proxy, and drum-map ratios.
        """
        channel_notes: dict[int, list[int]] = {}
        channel_counts: dict[int, int] = {}
        channel_programs: dict[int, dict[int, int]] = {}
        channel_name_tokens: dict[int, set[str]] = {}

        for track in midi.tracks:
            track_name = ""
            track_channels: set[int] = set()
            for msg in track:
                if getattr(msg, "is_meta", False) and getattr(msg, "type", "") == "track_name":
                    track_name = str(getattr(msg, "name", "") or "")
                    continue
                if getattr(msg, "type", "") != "note_on":
                    if getattr(msg, "type", "") == "program_change":
                        channel = int(getattr(msg, "channel", -1) or -1)
                        program = int(getattr(msg, "program", -1) or -1)
                        if channel >= 0 and program >= 0:
                            track_channels.add(channel)
                            program_hist = channel_programs.setdefault(channel, {})
                            program_hist[program] = program_hist.get(program, 0) + 1
                    continue
                if int(getattr(msg, "velocity", 0) or 0) <= 0:
                    continue
                channel = int(getattr(msg, "channel", -1) or -1)
                note = int(getattr(msg, "note", -1) or -1)
                if channel < 0 or note < 0:
                    continue
                track_channels.add(channel)
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                channel_notes.setdefault(channel, []).append(note)

            if track_name.strip():
                tokens = self._tokenize(track_name)
                for channel in track_channels:
                    channel_name_tokens.setdefault(channel, set()).update(tokens)

        output: list[ChannelFeatureSummary] = []
        for channel, notes in channel_notes.items():
            if not notes:
                continue
            low_ratio = sum(1 for n in notes if n <= 52) / len(notes)
            high_ratio = sum(1 for n in notes if n >= 72) / len(notes)
            drum_ratio = sum(1 for n in notes if 35 <= n <= 81) / len(notes)
            output.append(
                ChannelFeatureSummary(
                    channel_1_based=channel + 1,
                    note_count=channel_counts.get(channel, 0),
                    min_pitch=min(notes),
                    max_pitch=max(notes),
                    avg_pitch=sum(notes) / len(notes),
                    low_pitch_ratio=low_ratio,
                    high_pitch_ratio=high_ratio,
                    drum_pitch_ratio=drum_ratio,
                    program_hist=dict(channel_programs.get(channel, {})),
                    name_tokens=tuple(sorted(channel_name_tokens.get(channel, set()))),
                )
            )

        output.sort(key=lambda item: item.note_count, reverse=True)
        return output

    def _classify_channel(self, feature: ChannelFeatureSummary) -> ChannelDecision:
        """Classify one channel.

        3-layer scoring: protocol + name + physical.
        """
        protocol_map: dict[SplitClass, float] = {
            "drum": 0.0,
            "bass": 0.0,
            "guitar": 0.0,
            "keys": 0.0,
            "unknown": 0.0,
        }
        name_map: dict[SplitClass, float] = {
            "drum": 0.0,
            "bass": 0.0,
            "guitar": 0.0,
            "keys": 0.0,
            "unknown": 0.0,
        }
        physical_map: dict[SplitClass, float] = {
            "drum": 0.0,
            "bass": 0.0,
            "guitar": 0.0,
            "keys": 0.0,
            "unknown": 0.0,
        }

        self._score_protocol(feature, protocol_map)
        self._score_name(feature, name_map)
        self._score_physical(feature, physical_map)

        score_map: dict[SplitClass, float] = {
            "drum": self._clamp01(
                protocol_map["drum"] * self.params.weights.protocol
                + name_map["drum"] * self.params.weights.name
                + physical_map["drum"] * self.params.weights.physical
            ),
            "bass": self._clamp01(
                protocol_map["bass"] * self.params.weights.protocol
                + name_map["bass"] * self.params.weights.name
                + physical_map["bass"] * self.params.weights.physical
            ),
            "guitar": self._clamp01(
                protocol_map["guitar"] * self.params.weights.protocol
                + name_map["guitar"] * self.params.weights.name
                + physical_map["guitar"] * self.params.weights.physical
            ),
            "keys": self._clamp01(
                protocol_map["keys"] * self.params.weights.protocol
                + name_map["keys"] * self.params.weights.name
                + physical_map["keys"] * self.params.weights.physical
            ),
            "unknown": 0.0,
        }

        ranked = sorted(
            ((k, v) for k, v in score_map.items() if k != "unknown"),
            key=lambda item: item[1],
            reverse=True,
        )
        best_raw, best_score = ranked[0]
        best = cast(SplitClass, best_raw)
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = max(0.0, best_score - second_score)

        min_margin = self.params.thresholds.min_margin
        if feature.channel_1_based == self.params.protocol.drum_channel_1_based:
            min_margin = self.params.thresholds.drum_margin_relax

        confidence = best_score
        if confidence < self.params.thresholds.min_confidence or margin < min_margin:
            best = "unknown"
            confidence = max(0.0, confidence)

        return ChannelDecision(
            channel_1_based=feature.channel_1_based,
            label=f"Channel {feature.channel_1_based}",
            split_class=best,
            confidence=confidence,
            margin=margin,
            note_count=feature.note_count,
            score_map=score_map,
        )

    def _score_protocol(self, feature: ChannelFeatureSummary, out: dict[SplitClass, float]) -> None:
        if feature.channel_1_based == self.params.protocol.drum_channel_1_based:
            out["drum"] += self.params.protocol.drum_channel_score

        if feature.drum_pitch_ratio >= self.params.protocol.drum_note_ratio_strong:
            out["drum"] += self.params.protocol.drum_note_ratio_bonus

        program_total = sum(feature.program_hist.values())
        if program_total <= 0:
            return

        bass_hits = self._range_hits(feature.program_hist, self.params.protocol.bass_program_range)
        guitar_hits = self._range_hits(feature.program_hist, self.params.protocol.guitar_program_range)
        keys_hits = self._range_hits(feature.program_hist, self.params.protocol.keys_program_range)

        out["bass"] += self.params.protocol.program_bonus_bass * (bass_hits / program_total)
        out["guitar"] += self.params.protocol.program_bonus_guitar * (guitar_hits / program_total)
        out["keys"] += self.params.protocol.program_bonus_keys * (keys_hits / program_total)

    def _score_name(self, feature: ChannelFeatureSummary, out: dict[SplitClass, float]) -> None:
        tokens = set(feature.name_tokens)
        if not tokens:
            return

        out["drum"] += self._token_score(tokens, self.params.names.drum_tokens)
        out["bass"] += self._token_score(tokens, self.params.names.bass_tokens)
        out["guitar"] += self._token_score(tokens, self.params.names.guitar_tokens)
        out["keys"] += self._token_score(tokens, self.params.names.keys_tokens)

        for key in ("drum", "bass", "guitar", "keys"):
            out[key] = min(self.params.names.token_cap_per_class, out[key])

    def _score_physical(self, feature: ChannelFeatureSummary, out: dict[SplitClass, float]) -> None:
        avg_pitch = feature.avg_pitch
        if avg_pitch is None:
            return

        if (
            avg_pitch <= self.params.physical.bass_avg_pitch_max
            and feature.low_pitch_ratio >= self.params.physical.bass_low_ratio_min
        ):
            out["bass"] += self.params.physical.bass_bonus

        if (
            self.params.physical.guitar_avg_pitch_min <= avg_pitch <= self.params.physical.guitar_avg_pitch_max
            and feature.high_pitch_ratio <= self.params.physical.guitar_high_ratio_max
        ):
            out["guitar"] += self.params.physical.guitar_bonus

        if self.params.physical.keys_avg_pitch_min <= avg_pitch <= self.params.physical.keys_avg_pitch_max:
            out["keys"] += self.params.physical.keys_bonus

        if feature.drum_pitch_ratio >= self.params.physical.drum_pitch_ratio_min:
            out["drum"] += self.params.physical.drum_bonus

    def _token_score(self, tokens: set[str], candidates: Iterable[str]) -> float:
        hits = len(tokens & set(candidates))
        if hits <= 0:
            return 0.0
        return hits * self.params.names.strong_hit_score

    @staticmethod
    def _range_hits(program_hist: dict[int, int], value_range: tuple[int, int]) -> int:
        lo, hi = value_range
        return sum(count for program, count in program_hist.items() if lo <= program <= hi)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {token for token in normalized.split() if token}

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _select_targets(
        self,
        decisions: tuple[ChannelDecision, ...],
        feature_map: dict[int, ChannelFeatureSummary],
        limit: int,
    ) -> list[str]:
        """Select channel targets with continuity guard and intra-class split support."""
        hard_limit = max(0, min(limit, self.params.limits.hard_max_outputs))
        if hard_limit <= 0:
            return []

        guarded = self._apply_continuity_guard(decisions)
        if not guarded:
            return []

        seed_channels = self._seed_channels_by_intra_class(guarded, feature_map)

        ordered = sorted(
            guarded,
            key=lambda d: (d.confidence, d.margin, d.note_count),
            reverse=True,
        )

        selected_channels: list[int] = []
        for channel in seed_channels:
            if channel not in selected_channels:
                selected_channels.append(channel)

        for decision in ordered:
            if decision.channel_1_based not in selected_channels:
                selected_channels.append(decision.channel_1_based)
            if len(selected_channels) >= hard_limit:
                break

        min_keep = min(self.params.limits.min_outputs, len(ordered))
        if len(selected_channels) < min_keep:
            for decision in ordered:
                if decision.channel_1_based not in selected_channels:
                    selected_channels.append(decision.channel_1_based)
                if len(selected_channels) >= min_keep:
                    break

        return [f"ch:{channel}" for channel in selected_channels[:hard_limit]]

    def _apply_continuity_guard(self, decisions: tuple[ChannelDecision, ...]) -> list[ChannelDecision]:
        """Suppress weak fragmented branches to avoid over-splitting and choppy playback."""
        total_notes = sum(decision.note_count for decision in decisions)
        if total_notes <= 0:
            return []

        kept: list[ChannelDecision] = []
        for decision in decisions:
            if decision.split_class == "unknown":
                continue

            note_ratio = decision.note_count / total_notes
            weak_by_ratio = note_ratio < self.params.continuity.min_segment_note_ratio
            weak_by_conf = decision.confidence < self.params.continuity.weak_branch_merge_threshold
            if weak_by_ratio and weak_by_conf:
                continue
            kept.append(decision)

        if kept:
            return kept

        # Always keep at least one best branch when all are weak.
        best = max(decisions, key=lambda d: (d.confidence, d.margin, d.note_count))
        return [best]

    def _seed_channels_by_intra_class(
        self,
        decisions: list[ChannelDecision],
        feature_map: dict[int, ChannelFeatureSummary],
    ) -> list[int]:
        """Pick representative channels from same-class sub-groups when separable."""
        if not self.params.intra_class.enabled:
            return []

        seeds: list[int] = []
        classes: tuple[SplitClass, ...] = ("bass", "guitar", "keys", "drum")
        for split_class in classes:
            group = [d for d in decisions if d.split_class == split_class]
            if len(group) < 2:
                continue

            total_notes = sum(d.note_count for d in group)
            if total_notes < self.params.intra_class.min_notes:
                continue

            with_pitch = [d for d in group if feature_map.get(d.channel_1_based) and feature_map[d.channel_1_based].avg_pitch is not None]
            if len(with_pitch) < 2:
                continue

            with_pitch.sort(key=lambda d: feature_map[d.channel_1_based].avg_pitch or 0.0)
            mid = len(with_pitch) // 2
            low_group = with_pitch[:mid]
            high_group = with_pitch[mid:]
            if not low_group or not high_group:
                continue

            low_avg = sum((feature_map[d.channel_1_based].avg_pitch or 0.0) for d in low_group) / len(low_group)
            high_avg = sum((feature_map[d.channel_1_based].avg_pitch or 0.0) for d in high_group) / len(high_group)
            separation = abs(high_avg - low_avg) / 127.0
            if separation < self.params.intra_class.min_separation:
                continue

            low_best = max(low_group, key=lambda d: (d.confidence, d.margin, d.note_count))
            high_best = max(high_group, key=lambda d: (d.confidence, d.margin, d.note_count))
            seeds.append(low_best.channel_1_based)
            seeds.append(high_best.channel_1_based)

        return seeds
