import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Callable

import flet as ft
from pynput.keyboard import Key as PynputKey
from pynput.keyboard import Listener as KeyboardListener

from core import MidiEngine
from gui import HarmonyGui, StatusLevel


class AppController:
    """Coordinate UI interactions, playlist flow, and engine callbacks."""

    DEFAULT_TRANSITION_GAP_SECONDS = 1.5
    STATUS_AUTO_CLEAR_SECONDS = 3.0
    INTERRUPT_POLL_SECONDS = 0.05
    PROGRESS_UI_INTERVAL_SECONDS = 0.08
    MIDI_ALLOWED_EXTENSIONS = ["mid", "midi"]

    def __init__(self, page: ft.Page):
        """Initialize controller state and connect all event pipelines."""
        self.page = page
        self.gui = HarmonyGui(page)
        self.engine = MidiEngine()

        self.current_midi_path: str | None = None
        self.playlist_paths: list[str] = []
        self.transition_gap_seconds = self.DEFAULT_TRANSITION_GAP_SECONDS

        self.play_thread: threading.Thread | None = None
        self.is_playing = False
        self.stop_requested = threading.Event()
        self._status_token = 0
        self._pending_progress: tuple[float, float] | None = None
        self._progress_pump_running = False
        self._hotkey_listener: KeyboardListener | None = None

        self._bind_gui_hooks()
        self._bind_engine_callbacks()
        self._start_emergency_stop_listener()
        if self._hotkey_listener is None:
            self._show_message(self._tr("msg_hotkey_unavailable"), "warning")

    # ----- Wiring -----
    def _bind_gui_hooks(self) -> None:
        """Bind GUI hooks to controller handlers."""
        self.gui.on_play_click = self._handle_play_click
        self.gui.on_import_click = self._handle_import_click
        self.gui.on_jitter_change = self._handle_jitter_change
        self.gui.on_stagger_change = self._handle_stagger_change
        self.gui.on_library_track_select = self._handle_library_track_select
        self.gui.on_library_play_click = self._handle_library_play_click
        self.gui.on_status_close = self._handle_status_close

    def _bind_engine_callbacks(self) -> None:
        """Bind engine callbacks to UI-safe handlers."""
        # Playback state is owned by the controller to avoid flicker between tracks.
        self.engine.on_progress = self._queue_progress_update
        self.engine.on_error = lambda message: self._run_on_ui(self._show_message, self._tr("msg_engine_error", message), "error")

    # ----- Utilities -----
    def _tr(self, key: str, *args: object) -> str:
        """Translate a locale key via GUI language context."""
        return self.gui.t(key, *args)

    def _run_on_ui(self, fn: Callable[..., None], *args: object) -> None:
        """Execute function on UI thread when API is available."""
        call_from_thread = getattr(self.page, "call_from_thread", None)
        if callable(call_from_thread):
            call_from_thread(fn, *args)
            return

        run_task = getattr(self.page, "run_task", None)
        if callable(run_task):
            async def invoke() -> None:
                fn(*args)

            try:
                run_task(invoke)
                return
            except Exception:
                pass

        # Last-resort fallback for runtimes without thread-dispatch helpers.
        fn(*args)

    def _start_emergency_stop_listener(self) -> None:
        """Start global ESC listener so playback can stop without UI focus."""
        if self._hotkey_listener is not None:
            return

        def on_press(key: Any) -> None:
            if key == PynputKey.esc:
                self._request_stop("msg_hotkey_stopped")

        try:
            self._hotkey_listener = KeyboardListener(on_press=on_press)
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
        except Exception:
            # Listener may fail due to system permissions; user should grant accessibility permission.
            self._hotkey_listener = None

    def _request_stop(self, message_key: str) -> None:
        """Request a graceful stop once and surface a localized status message."""
        if not self.is_playing:
            return

        if self.stop_requested.is_set():
            return

        self.stop_requested.set()
        self.engine.stop()
        self._run_on_ui(self._show_message, self._tr(message_key), "warning")

    # ----- GUI Event Handlers -----
    def _handle_play_click(self, _: Any) -> None:
        """Start/stop playlist playback from Play button."""
        if self.is_playing:
            self._request_stop("msg_stopping_playlist")
            return

        if not self.playlist_paths:
            self._show_message(self._tr("msg_import_at_least_one"), "warning")
            return

        if self.play_thread and self.play_thread.is_alive():
            self._show_message(self._tr("msg_thread_still_running"), "warning")
            return

        self.stop_requested.clear()
        self.is_playing = True
        self.gui.set_playing_state(True)
        self._show_message(self._tr("msg_switch_to_game", self.engine.PRE_ROLL_SECONDS), "warning")

        self.play_thread = threading.Thread(
            target=self._play_playlist_worker,
            daemon=True,
        )
        self.play_thread.start()

    def _handle_import_click(self, _: Any) -> None:
        """Open file picker for MIDI playlist import."""
        self.page.run_task(self._pick_midi_files)

    def _handle_jitter_change(self, value: float) -> None:
        """Propagate jitter tuning from UI to engine."""
        self.engine.jitter_stdev = max(0.0, value)

    def _handle_stagger_change(self, value: float) -> None:
        """Propagate stagger tuning from UI to engine."""
        self.engine.chord_stagger = max(0.0, value)

    def _handle_status_close(self, _: Any) -> None:
        """Handle manual close for persistent error status."""
        self._status_token += 1
        self.gui.clear_status_message()

    def _handle_library_track_select(self, track_path: str) -> None:
        """Move selected library track to playlist head and sync play view."""
        if not track_path:
            return

        if track_path not in self.playlist_paths:
            return

        remaining = [path for path in self.playlist_paths if path != track_path]
        self.playlist_paths = [track_path, *remaining]
        self.current_midi_path = track_path

        self.gui.set_library_tracks(self.playlist_paths)
        self.gui.set_playback_snapshot(0.0, 0.0, 0.0)

        first_name = Path(track_path).name
        subtitle = self._tr("msg_playlist_count", len(self.playlist_paths))
        self.gui.set_track_info(f"[1/{len(self.playlist_paths)}] {first_name}", subtitle)

    def _handle_library_play_click(self, track_path: str) -> None:
        """Select a track from library and jump to play view."""
        self._handle_library_track_select(track_path)
        self.gui.show_play_view()

    # ----- Playback Worker -----
    def _play_playlist_worker(self) -> None:
        """Play all tracks sequentially with optional transition gaps."""
        playlist = list(self.playlist_paths)
        total_tracks = len(playlist)

        try:
            for idx, midi_path in enumerate(playlist, start=1):
                if self.stop_requested.is_set():
                    break

                if not Path(midi_path).is_file():
                    self._run_on_ui(self._show_message, self._tr("msg_engine_error", f"File not found: {midi_path}"), "error")
                    break

                self.current_midi_path = midi_path
                track_name = Path(midi_path).name
                display_title = f"[{idx}/{total_tracks}] {track_name}"
                self._run_on_ui(self.gui.set_track_info, display_title, midi_path)

                try:
                    self.engine.play(midi_path)
                except Exception as exc:
                    self._run_on_ui(self._show_message, self._tr("msg_engine_error", str(exc)), "error")
                    break

                if self.stop_requested.is_set():
                    break

                if idx < total_tracks:
                    self._run_on_ui(
                        self._show_message,
                        self._tr("msg_track_finished_next", idx, self.transition_gap_seconds),
                    )
                    if not self._interruptible_sleep(self.transition_gap_seconds):
                        break

            if self.stop_requested.is_set():
                self._run_on_ui(self._show_message, self._tr("msg_playlist_stopped"), "warning")
            else:
                self._run_on_ui(self._show_message, self._tr("msg_playlist_completed"))
        finally:
            self._run_on_ui(self._set_idle_state)

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep in short intervals so stop requests can interrupt quickly."""
        end_time = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end_time:
            if self.stop_requested.is_set():
                return False
            time.sleep(self.INTERRUPT_POLL_SECONDS)
        return True

    def _set_idle_state(self) -> None:
        """Return controller/UI to idle state after playlist loop exits."""
        self.is_playing = False
        self.play_thread = None
        self.gui.set_playing_state(False)

    # ----- Import Flow -----
    async def _pick_midi_files(self) -> None:
        """Pick one or more MIDI files and initialize playlist metadata."""
        selected_paths = await asyncio.to_thread(self._pick_with_native_dialog)

        if not selected_paths:
            self._show_message(self._tr("msg_read_path_failed"), "error")
            return

        existing = list(self.playlist_paths)
        existing_set = set(existing)
        appended = [path for path in selected_paths if path not in existing_set]
        self.playlist_paths = [*existing, *appended]

        if self.current_midi_path not in self.playlist_paths:
            self.current_midi_path = self.playlist_paths[0]

        self.gui.set_library_tracks(self.playlist_paths)

        current_index = 1
        if self.current_midi_path and self.current_midi_path in self.playlist_paths:
            current_index = self.playlist_paths.index(self.current_midi_path) + 1

        first_name = Path(self.current_midi_path).name if self.current_midi_path else ""
        subtitle = self._tr("msg_playlist_count", len(self.playlist_paths))
        self.gui.set_track_info(f"[{current_index}/{len(self.playlist_paths)}] {first_name}", subtitle)
        self.gui.set_progress(0.0)
        self.gui.set_time_labels(0.0, 0.0)
        self._show_message(self._tr("msg_imported_count", len(appended)))

    def _pick_with_native_dialog(self) -> list[str]:
        """Pick MIDI files via native dialog to avoid runtime-specific Flet picker issues."""
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            filetypes = [("MIDI Files", "*.mid *.midi"), ("All Files", "*.*")]
            selected = filedialog.askopenfilenames(
                title=self._tr("msg_pick_midi_dialog"),
                filetypes=filetypes,
            )
            root.destroy()
            return [str(path) for path in selected if isinstance(path, str) and path]
        except Exception:
            return []

    # ----- Engine/UI Sync -----
    def _queue_progress_update(self, elapsed_seconds: float, total_seconds: float) -> None:
        """Store latest progress and start a throttled UI pump if needed."""
        self._pending_progress = (elapsed_seconds, total_seconds)
        if self._progress_pump_running:
            return

        self._progress_pump_running = True
        self.page.run_task(self._progress_ui_pump)

    async def _progress_ui_pump(self) -> None:
        """Flush latest progress to UI at a limited frame rate."""
        try:
            while self.is_playing or self._pending_progress is not None:
                pending = self._pending_progress
                self._pending_progress = None
                if pending is not None:
                    elapsed_seconds, total_seconds = pending
                    progress = (elapsed_seconds / total_seconds) if total_seconds > 0 else 0.0
                    self.gui.set_playback_snapshot(progress, elapsed_seconds, total_seconds)
                await asyncio.sleep(self.PROGRESS_UI_INTERVAL_SECONDS)
        finally:
            self._progress_pump_running = False
            if self._pending_progress is not None and self.is_playing:
                self._progress_pump_running = True
                self.page.run_task(self._progress_ui_pump)

    # ----- Status Messaging -----
    def _show_message(self, message: str, level: StatusLevel = "info") -> None:
        """Show leveled status text; auto-clear non-error messages."""
        self.gui.set_status_message(message, level=level)
        self._status_token += 1
        token = self._status_token
        if level != "error" and message:
            self.page.run_task(self._auto_clear_status, token, self.STATUS_AUTO_CLEAR_SECONDS)

    async def _auto_clear_status(self, token: int, delay_seconds: float) -> None:
        """Clear non-error status after delay if still latest message."""
        await asyncio.sleep(max(0.0, delay_seconds))
        if token != self._status_token:
            return
        self.gui.clear_status_message()


def main(page: ft.Page) -> None:
    """Flet app bootstrap entry."""
    AppController(page)


if __name__ == "__main__":
    ft.run(main)
