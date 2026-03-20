"""Author: etanolo (https://github.com/etanolo)
Purpose: StarResonanceMidi engine that maps MIDI notes and timing into keyboard actions.
Constraints:
- Keep playback loop deterministic and callback-driven for UI integration.
- Avoid direct UI dependencies; communicate through typed callbacks only.
- Keep timing and key-mapping behavior stable unless explicitly changing engine logic.
License: AGPL-3.0-or-later
"""

import mido
import random
import threading
import time
from pathlib import Path
from typing import Callable

from pynput.keyboard import Controller, Key

# ----- Constants -----
OCTAVE_KEYS = [
    'z', '1', 'x', '2', 'c', 'v', '3', 'b', '4', 'n', '5', 'm',
    'a', '6', 's', '7', 'd', 'f', '8', 'g', '9', 'h', '0', 'j',
    'q', 'i', 'w', 'o', 'e', 'r', 'p', 't', '[', 'y', ']', 'u'
]

PlayStateCallback = Callable[[bool], None]
ProgressCallback = Callable[[float, float], None]
TrackInfoCallback = Callable[[str, str], None]
ErrorCallback = Callable[[str], None]
FinishCallback = Callable[[], None]


class MidiEngine:
    """Convert MIDI events into keyboard actions with humanization."""

    PRE_ROLL_SECONDS = 4.0

    def __init__(self):
        """Initialize state machine, tuning values, and callbacks."""
        self.keyboard = Controller()

        # Runtime stop signal.
        self._stop_event = threading.Event()

        # Humanization tuning (can be updated by GUI).
        self.jitter_stdev = 0.012
        self.chord_stagger = 0.025

        # Toggle-style sustain pedal state tracked by app logic.
        self.sustain_is_on = False

        # Key state machine.
        self.current_state = "BASE"
        self.hesitation_min = 0.08
        self.hesitation_max = 0.20

        # Controller-facing callbacks.
        self.on_play_state_change: PlayStateCallback | None = None
        self.on_progress: ProgressCallback | None = None
        self.on_track_info: TrackInfoCallback | None = None
        self.on_error: ErrorCallback | None = None
        self.on_finished: FinishCallback | None = None

    # ----- Callback helpers -----
    def _safe_emit(self, callback: Callable[..., None] | None, *args: object) -> None:
        """Emit callback safely without crashing playback thread."""
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            # Keep engine robust even if UI callback fails.
            return

    def _emit_progress(self, elapsed: float, total: float) -> None:
        """Emit clamped progress values."""
        clamped_elapsed = max(0.0, elapsed)
        safe_total = max(0.0, total)
        self._safe_emit(self.on_progress, clamped_elapsed, safe_total)

    # ----- Timing and key safety -----
    def precise_sleep(self, duration: float) -> None:
        """Sleep with short spin tail for tighter timing precision."""
        if duration <= 0:
            return

        target_time = time.perf_counter() + duration

        # Sleep most of the duration, then spin-wait the final milliseconds.
        sleep_time = duration - 0.015
        if sleep_time > 0:
            time.sleep(sleep_time)

        while time.perf_counter() < target_time:
            if self._stop_event.is_set():
                break
            pass

    def release_all_keys(self) -> None:
        """Release all potentially pressed keys and reset state."""
        self.keyboard.release(Key.space)
        self.keyboard.release(Key.shift_l)
        self.keyboard.release(Key.ctrl_l)
        self.keyboard.release(',')
        self.keyboard.release('.')

        for k in OCTAVE_KEYS:
            self.keyboard.release(k)

    def reset_state_to_base(self) -> None:
        """Force octave/state toggles back to BASE after playback."""
        if self.current_state == "SHIFT":
            self.keyboard.tap(Key.shift_l)
        elif self.current_state == "CTRL":
            self.keyboard.tap(Key.ctrl_l)
        elif self.current_state == "HIGH":
            self.keyboard.tap(',')
        elif self.current_state == "LOW":
            self.keyboard.tap('.')
        self.current_state = "BASE"

    def prime_sustain_pedal(self) -> None:
        """Enable toggle-style sustain pedal only when currently off."""
        if self.sustain_is_on:
            return

        self.keyboard.release(Key.space)
        self.precise_sleep(0.02)
        self.keyboard.press(Key.space)
        self.precise_sleep(0.05)
        self.keyboard.release(Key.space)
        self.sustain_is_on = True

    # ----- State machine and note mapping -----
    def switch_state(self, target: str) -> None:
        """Switch keyboard modifier state with brief humanized delays."""
        if self.current_state == target:
            return

        self.precise_sleep(random.uniform(self.hesitation_min, self.hesitation_max))

        # 1) Release current state.
        if self.current_state == "SHIFT":
            self.keyboard.tap(Key.shift_l)
        elif self.current_state == "CTRL":
            self.keyboard.tap(Key.ctrl_l)
        elif self.current_state == "HIGH":
            self.keyboard.tap(',')
        elif self.current_state == "LOW":
            self.keyboard.tap('.')

        self.precise_sleep(random.uniform(0.01, 0.03))
        self.current_state = "BASE"

        if target == "BASE":
            return

        # 2) Enter target state.
        if target == "SHIFT":
            self.keyboard.tap(Key.shift_l)
        elif target == "CTRL":
            self.keyboard.tap(Key.ctrl_l)
        elif target == "HIGH":
            self.keyboard.tap('.')
        elif target == "LOW":
            self.keyboard.tap(',')

        self.current_state = target
        self.precise_sleep(random.uniform(0.02, 0.06))

    def humanized_press(self, midi_note: int) -> None:
        """Press mapped key for a MIDI note with variable hold time."""
        target_state = "BASE"
        offset = 48

        if 48 <= midi_note <= 83:
            target_state = "BASE"
            offset = 48
        elif 60 <= midi_note <= 95:
            target_state = "SHIFT"
            offset = 60
        elif 36 <= midi_note <= 71:
            target_state = "CTRL"
            offset = 36
        elif 84 <= midi_note <= 108:
            target_state = "HIGH"
            offset = 84
        elif 21 <= midi_note <= 47:
            target_state = "LOW"
            offset = 12
        else:
            return

        # Dynamic hold time: shorter for high notes.
        if midi_note > 72:
            p_min, p_max = 0.02, 0.05
        else:
            p_min, p_max = 0.05, 0.10

        self.switch_state(target_state)
        
        key_idx = midi_note - offset
        if 0 <= key_idx < len(OCTAVE_KEYS):
            key = OCTAVE_KEYS[key_idx]
            self.keyboard.press(key)
            self.precise_sleep(random.uniform(p_min, p_max))
            self.keyboard.release(key)

    # ----- Playback lifecycle -----
    def play(self, midi_path: str) -> None:
        """Blocking playback loop intended to run in a worker thread."""
        self._stop_event.clear()
        self._safe_emit(self.on_play_state_change, True)

        try:
            mid = mido.MidiFile(midi_path)
        except Exception as e:
            err = str(e)
            self._safe_emit(self.on_error, err)
            self._safe_emit(self.on_play_state_change, False)
            self._safe_emit(self.on_finished)
            return

        track_title = Path(midi_path).name
        self._safe_emit(self.on_track_info, track_title, midi_path)

        total_duration = float(getattr(mid, "length", 0.0) or 0.0)
        elapsed = 0.0
        self._emit_progress(elapsed, total_duration)

        # Brief pre-roll to allow user to focus game window.
        self.precise_sleep(self.PRE_ROLL_SECONDS)

        if self._stop_event.is_set():
            self._safe_emit(self.on_play_state_change, False)
            self._safe_emit(self.on_finished)
            return

        self.prime_sustain_pedal()

        try:
            for msg in mid.play():
                if self._stop_event.is_set():
                    break

                # mido.MidiFile.play() already handles base timing sleeps.
                msg_time = float(getattr(msg, "time", 0.0) or 0.0)
                extra_delay = 0.0
                if msg_time > 0:
                    extra_delay = max(0.0, random.gauss(0, self.jitter_stdev))
                else:
                    extra_delay = random.uniform(0.002, self.chord_stagger)

                if extra_delay > 0:
                    self.precise_sleep(extra_delay)

                elapsed += msg_time + extra_delay
                self._emit_progress(elapsed, total_duration)

                msg_type = getattr(msg, "type", None)
                msg_velocity = getattr(msg, "velocity", 0)
                msg_note = getattr(msg, "note", None)
                if msg_type == "note_on" and msg_velocity > 0 and isinstance(msg_note, int):
                    self.humanized_press(msg_note)

        finally:
            self.release_all_keys()
            self.reset_state_to_base()
            self._emit_progress(total_duration, total_duration)
            self._safe_emit(self.on_play_state_change, False)
            self._safe_emit(self.on_finished)

    def stop(self) -> None:
        """Request stop for the running playback loop."""
        self._stop_event.set()