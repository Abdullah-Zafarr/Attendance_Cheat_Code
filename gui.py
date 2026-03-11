"""
gui.py — Tkinter GUI for Attendance Alarm.

Provides Start/Stop buttons, an engine selector (Vosk / Whisper),
a names text box, a status indicator, and a scrollable log window.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import datetime
import threading

from audio_capture import AudioCapture
from speech_recognizer import RecognizerWorker, ENGINES, ENGINE_VOSK
from detector import Detector
from alarm import Alarm


# ====================================================================== #
#  Colour palette
# ====================================================================== #
BG          = "#1e1e2e"
BG_DARKER   = "#181825"
FG          = "#cdd6f4"
ACCENT      = "#89b4fa"
GREEN       = "#a6e3a1"
RED         = "#f38ba8"
SURFACE     = "#313244"
OVERLAY     = "#45475a"

DEFAULT_NAMES = "abdullah\nabdulla\nabdula\nali\nahmed"


class AttendanceAlarmApp:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Attendance Alarm")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry("520x700")

        # Shared queue for audio data
        self._audio_queue: queue.Queue = queue.Queue(maxsize=200)

        # Thread-safe queue for log messages from background threads
        self._log_queue: queue.Queue = queue.Queue()

        # Components (created on start)
        self._capture: AudioCapture | None = None
        self._worker: RecognizerWorker | None = None
        self._detector = Detector()
        self._alarm = Alarm()

        self._listening = False

        self._build_ui()

        # Poll for transcript updates from the worker thread
        self._poll_id: str | None = None

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # ---------- Title ----------
        title = tk.Label(
            self.root, text="🔔  Attendance Alarm", font=("Segoe UI", 18, "bold"),
            bg=BG, fg=ACCENT,
        )
        title.pack(pady=(18, 6))

        # ---------- Engine selector ----------
        engine_frame = tk.Frame(self.root, bg=BG)
        engine_frame.pack(pady=(0, 6))

        tk.Label(
            engine_frame, text="Engine:", font=("Segoe UI", 10),
            bg=BG, fg=FG,
        ).pack(side=tk.LEFT, padx=(0, 6))

        self._engine_var = tk.StringVar(value=ENGINE_VOSK)
        self._engine_combo = ttk.Combobox(
            engine_frame,
            textvariable=self._engine_var,
            values=ENGINES,
            state="readonly",
            width=14,
        )
        self._engine_combo.pack(side=tk.LEFT)

        # Style the combobox
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=SURFACE,
            background=SURFACE,
            foreground=FG,
            arrowcolor=ACCENT,
        )

        # ---------- Status ----------
        self._status_var = tk.StringVar(value="⏹  Stopped")
        self._status_label = tk.Label(
            self.root,
            textvariable=self._status_var,
            font=("Segoe UI", 12, "bold"),
            bg=BG, fg=RED,
        )
        self._status_label.pack(pady=(2, 8))

        # ---------- Buttons ----------
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=(0, 10))

        self._start_btn = tk.Button(
            btn_frame, text="▶  Start", font=("Segoe UI", 11, "bold"),
            bg=GREEN, fg="#1e1e2e", activebackground="#77d590",
            relief="flat", padx=20, pady=6, cursor="hand2",
            command=self._on_start,
        )
        self._start_btn.pack(side=tk.LEFT, padx=8)

        self._stop_btn = tk.Button(
            btn_frame, text="⏹  Stop", font=("Segoe UI", 11, "bold"),
            bg=RED, fg="#1e1e2e", activebackground="#e06080",
            relief="flat", padx=20, pady=6, cursor="hand2",
            state=tk.DISABLED, command=self._on_stop,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=8)

        # ---------- Names ----------
        tk.Label(
            self.root, text="Names to detect (one per line):",
            font=("Segoe UI", 10), bg=BG, fg=FG,
        ).pack(anchor="w", padx=20, pady=(4, 2))

        self._names_text = tk.Text(
            self.root, height=5, width=50,
            font=("Consolas", 10), bg=SURFACE, fg=FG,
            insertbackground=FG, relief="flat", bd=0,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=OVERLAY,
        )
        self._names_text.pack(padx=20, pady=(0, 10))
        self._names_text.insert("1.0", DEFAULT_NAMES)

        # ---------- Log ----------
        tk.Label(
            self.root, text="Detection log:",
            font=("Segoe UI", 10), bg=BG, fg=FG,
        ).pack(anchor="w", padx=20, pady=(0, 2))

        self._log_text = scrolledtext.ScrolledText(
            self.root, height=14, width=50,
            font=("Consolas", 9), bg=BG_DARKER, fg=FG,
            insertbackground=FG, relief="flat", bd=0,
            highlightthickness=1, highlightcolor=ACCENT,
            highlightbackground=OVERLAY,
            state=tk.DISABLED,
        )
        self._log_text.pack(padx=20, pady=(0, 14))

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  Thread-safe logging
    # ------------------------------------------------------------------ #
    def _thread_log(self, message: str):
        """Called from background threads — puts message in a queue."""
        self._log_queue.put(message)

    def _log(self, message: str):
        """Write to the log widget (must be called from main thread)."""
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, message + "\n")
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #
    def _on_start(self):
        if self._listening:
            return

        # Parse names
        raw = self._names_text.get("1.0", tk.END)
        names = [n.strip() for n in raw.splitlines() if n.strip()]
        if not names:
            self._log("⚠  No names entered — add at least one name.")
            return

        self._detector.set_names(names)
        self._detector.reset_cooldown()

        # Drain any stale audio
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        # Start audio capture with logging
        self._capture = AudioCapture(
            self._audio_queue,
            on_log=self._thread_log,
        )
        self._capture.start()

        # Start recognizer worker
        engine = self._engine_var.get()
        self._worker = RecognizerWorker(
            audio_queue=self._audio_queue,
            engine=engine,
            on_transcript=self._on_transcript,
            on_error=self._on_error_from_thread,
            on_log=self._thread_log,
        )
        self._worker.start()

        self._listening = True
        self._status_var.set(f"🎙  Listening ({engine})")
        self._status_label.configure(fg=GREEN)
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self._engine_combo.configure(state=tk.DISABLED)
        self._names_text.configure(state=tk.DISABLED)

        self._log(f"▶  Started — engine: {engine}, monitoring {len(names)} name(s)")

        # Start polling for transcript callbacks (they come from another thread)
        self._pending_transcripts: list[str] = []
        self._poll()

    def _on_stop(self):
        if not self._listening:
            return

        self._listening = False

        if self._worker:
            self._worker.stop()
            self._worker = None
        if self._capture:
            self._capture.stop()
            self._capture = None

        self._status_var.set("⏹  Stopped")
        self._status_label.configure(fg=RED)
        self._start_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)
        self._engine_combo.configure(state="readonly")
        self._names_text.configure(state=tk.NORMAL)

        if self._poll_id:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None

        self._log("⏹  Stopped listening.")

    def _on_close(self):
        self._on_stop()
        self._alarm.cleanup()
        self.root.destroy()

    # ------------------------------------------------------------------ #
    #  Transcript handling  (called from worker thread)
    # ------------------------------------------------------------------ #
    def _on_transcript(self, text: str):
        """Called from the recognizer thread — just queue the text."""
        if not hasattr(self, "_pending_transcripts"):
            self._pending_transcripts = []
        self._pending_transcripts.append(text)

    def _on_error_from_thread(self, msg: str):
        """Called from the recognizer thread on fatal error."""
        self._log_queue.put(f"❌  {msg}")
        # Schedule stop on the main thread
        self.root.after(0, self._on_stop)

    def _poll(self):
        """Periodically check for new transcripts and log messages."""
        if not self._listening:
            return

        # Process log messages from background threads
        while not self._log_queue.empty():
            try:
                msg = self._log_queue.get_nowait()
                self._log(msg)
            except queue.Empty:
                break

        # Process any pending transcripts
        while hasattr(self, "_pending_transcripts") and self._pending_transcripts:
            text = self._pending_transcripts.pop(0)
            self._process_transcript(text)

        self._poll_id = self.root.after(200, self._poll)

    def _process_transcript(self, text: str):
        """Run detection on a transcript and trigger alarm if matched."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        # Show ALL transcripts in the log so user can see recognition is working
        self._log(f"💬 {ts} — heard: \"{text}\"")

        detected, phrase = self._detector.check(text)
        if detected:
            self._log(f'🚨 {ts} — NAME DETECTED: "{phrase}"')
            self._alarm.play()

    # ------------------------------------------------------------------ #
    #  (end of class)
    # ------------------------------------------------------------------ #
