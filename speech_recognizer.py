"""
speech_recognizer.py — Speech-to-text module with Vosk / Whisper toggle.

Provides a common interface with two implementations:
  • VoskRecognizer  — lightweight, streaming-friendly
  • WhisperRecognizer — more accurate, processes buffered chunks

A factory function `create_recognizer()` lets the GUI pick the engine.
"""

import os
import queue
import threading
import json
import struct
import tempfile
import wave
import numpy as np

# ====================================================================== #
#  VOSK implementation
# ====================================================================== #

VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_MODEL_URL = (
    f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
)
SAMPLE_RATE = 16000


def _vosk_model_dir() -> str:
    """Return the path to the vosk model directory, downloading if needed."""
    base = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base, VOSK_MODEL_NAME)

    if os.path.isdir(model_path):
        return model_path

    # Auto-download
    import zipfile
    import urllib.request
    import io

    print(f"Downloading Vosk model ({VOSK_MODEL_NAME})... this is one-time only.")
    resp = urllib.request.urlopen(VOSK_MODEL_URL)
    z = zipfile.ZipFile(io.BytesIO(resp.read()))
    z.extractall(base)
    print("✓ Vosk model ready.")
    return model_path


class VoskRecognizer:
    """Streaming speech recognizer using Vosk."""

    def __init__(self):
        from vosk import Model, KaldiRecognizer, SetLogLevel

        SetLogLevel(-1)  # suppress vosk logs
        model_path = _vosk_model_dir()
        self._model = Model(model_path)
        self._rec = KaldiRecognizer(self._model, SAMPLE_RATE)

    def recognize_chunk(self, pcm_bytes: bytes) -> str | None:
        """
        Feed a PCM chunk. Returns transcript text when a phrase is
        finalized, or None for partial / empty results.
        """
        if self._rec.AcceptWaveform(pcm_bytes):
            result = json.loads(self._rec.Result())
            text = result.get("text", "").strip()
            return text if text else None
        else:
            # Partial result — we can optionally use it
            partial = json.loads(self._rec.PartialResult())
            text = partial.get("partial", "").strip()
            return text if text else None

    def reset(self):
        """Reset recognizer state for a fresh start."""
        from vosk import KaldiRecognizer

        self._rec = KaldiRecognizer(self._model, SAMPLE_RATE)


# ====================================================================== #
#  WHISPER (faster-whisper) implementation
# ====================================================================== #


class WhisperRecognizer:
    """
    Speech recognizer using faster-whisper.
    Buffers audio and transcribes in ~3 s windows.
    """

    def __init__(self, model_size: str = "base.en"):
        from faster_whisper import WhisperModel

        # Use CPU by default; int8 quantisation keeps it fast
        self._model = WhisperModel(
            model_size, device="cpu", compute_type="int8"
        )
        self._buffer = bytearray()
        self._buffer_limit = SAMPLE_RATE * 2 * 3  # 3 seconds of 16-bit mono

    def recognize_chunk(self, pcm_bytes: bytes) -> str | None:
        """
        Buffer audio. When enough has accumulated (~3 s), run whisper
        and return the transcript.
        """
        self._buffer.extend(pcm_bytes)

        if len(self._buffer) < self._buffer_limit:
            return None  # not enough audio yet

        # Convert buffer to float32 numpy array
        pcm = np.frombuffer(bytes(self._buffer), dtype=np.int16)
        audio = pcm.astype(np.float32) / 32768.0
        self._buffer.clear()

        segments, _ = self._model.transcribe(
            audio,
            beam_size=1,
            language="en",
            vad_filter=True,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text if text else None

    def reset(self):
        """Clear internal audio buffer."""
        self._buffer.clear()


# ====================================================================== #
#  Factory
# ====================================================================== #

ENGINE_VOSK = "Vosk"
ENGINE_WHISPER = "Whisper"
ENGINES = [ENGINE_VOSK, ENGINE_WHISPER]


def create_recognizer(engine: str = ENGINE_VOSK):
    """
    Create a recognizer for the given engine name.
    Returns an object with `.recognize_chunk(bytes)` and `.reset()`.
    """
    if engine == ENGINE_WHISPER:
        return WhisperRecognizer()
    return VoskRecognizer()


# ====================================================================== #
#  Threaded wrapper used by the GUI
# ====================================================================== #


class RecognizerWorker:
    """
    Pulls audio from a queue, feeds it to the selected recognizer,
    and calls `on_transcript(text)` whenever speech is detected.
    """

    def __init__(
        self,
        audio_queue: queue.Queue,
        engine: str = ENGINE_VOSK,
        on_transcript=None,
        on_error=None,
        on_log=None,
    ):
        self.audio_queue = audio_queue
        self.engine = engine
        self.on_transcript = on_transcript or (lambda t: None)
        self.on_error = on_error or (lambda e: None)
        self.on_log = on_log or (lambda m: None)
        self._running = False
        self._thread: threading.Thread | None = None
        self._recognizer = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self):
        self.on_log(f"🔄 Loading {self.engine} engine...")
        try:
            self._recognizer = create_recognizer(self.engine)
        except Exception as exc:
            self.on_error(f"Failed to load {self.engine}: {exc}")
            self._running = False
            return

        self.on_log(f"✅ {self.engine} engine ready!")
        chunk_count = 0

        while self._running:
            try:
                pcm = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                chunk_count += 1
                text = self._recognizer.recognize_chunk(pcm)
                if text:
                    self.on_transcript(text)
            except Exception as e:
                self.on_log(f"⚠ Recognizer error: {e}")
                continue
