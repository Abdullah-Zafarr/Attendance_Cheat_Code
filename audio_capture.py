"""
audio_capture.py — System audio loopback capture module.

Captures audio from the default speaker output (WASAPI loopback) so the app
can listen to whatever is playing on the computer (e.g. Google Meet, Zoom).

Uses PyAudioWPatch on Windows for reliable WASAPI loopback.
Falls back to soundcard on Linux.
"""

import threading
import queue
import numpy as np
import sys
import struct

# Audio settings expected by Vosk / Whisper
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # seconds per chunk
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)


class AudioCapture:
    """Captures system audio output via loopback and pushes PCM chunks to a queue."""

    def __init__(self, audio_queue: queue.Queue, sample_rate: int = SAMPLE_RATE,
                 on_log=None):
        self.audio_queue = audio_queue
        self.sample_rate = sample_rate
        self._running = False
        self._thread: threading.Thread | None = None
        self._log = on_log or (lambda msg: None)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def start(self):
        """Start capturing audio in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the capture loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #
    def _capture_loop(self):
        """Pick the best capture method for the platform."""
        if sys.platform == "win32":
            self._capture_windows()
        else:
            self._capture_linux()

    def _capture_windows(self):
        """Use PyAudioWPatch WASAPI loopback on Windows."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            self._log("❌ PyAudioWPatch not installed. Run: pip install PyAudioWPatch")
            self._running = False
            return

        p = pyaudio.PyAudio()

        try:
            # Find the default WASAPI loopback device
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )
            self._log(f"🔊 Speaker: {default_speakers['name']}")

            # Find the loopback device for the default speakers
            loopback = None
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if (dev.get("isLoopbackDevice", False) and
                        dev["name"].startswith(default_speakers["name"])):
                    loopback = dev
                    break

            if loopback is None:
                self._log("❌ No loopback device found. Check audio settings.")
                self._running = False
                p.terminate()
                return

            self._log(f"🎧 Loopback: {loopback['name']}")

            # Open the loopback stream
            # Use the device's native sample rate and channels, then resample
            device_rate = int(loopback["defaultSampleRate"])
            device_channels = loopback["maxInputChannels"]
            chunk_size = int(device_rate * CHUNK_DURATION)

            self._log(f"📊 Device rate: {device_rate} Hz, channels: {device_channels}")

            stream = p.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                input=True,
                input_device_index=loopback["index"],
                frames_per_buffer=chunk_size,
            )

            self._log("✅ Audio capture started!")
            chunk_count = 0

            while self._running:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)

                    # Convert to numpy array
                    samples = np.frombuffer(data, dtype=np.int16)

                    # Convert to mono if stereo
                    if device_channels > 1:
                        samples = samples.reshape(-1, device_channels)
                        samples = samples.mean(axis=1).astype(np.int16)

                    # Resample to target rate if needed
                    if device_rate != self.sample_rate:
                        num_target = int(len(samples) * self.sample_rate / device_rate)
                        indices = np.linspace(0, len(samples) - 1, num_target).astype(int)
                        samples = samples[indices]

                    pcm = samples.tobytes()
                    self.audio_queue.put(pcm)

                    chunk_count += 1
                    # Log audio level periodically
                    if chunk_count % 10 == 1:
                        peak = np.max(np.abs(samples))
                        self._log(f"🎤 Audio level: {peak} (chunk #{chunk_count})")

                except Exception as e:
                    if not self._running:
                        break
                    self._log(f"⚠ Audio read error: {e}")
                    continue

            stream.stop_stream()
            stream.close()

        except Exception as e:
            self._log(f"❌ Audio capture error: {e}")
        finally:
            p.terminate()
            self._running = False

    def _capture_linux(self):
        """Use soundcard on Linux (PulseAudio loopback)."""
        try:
            # Patch numpy for soundcard compatibility
            np.fromstring = np.frombuffer
            import soundcard as sc
        except ImportError:
            self._log("❌ soundcard not installed. Run: pip install soundcard")
            self._running = False
            return

        try:
            speaker = sc.default_speaker()
            self._log(f"🔊 Speaker: {speaker.name}")

            mic = sc.get_microphone(id=speaker.id, include_loopback=True)
            self._log(f"🎧 Loopback: {mic.name}")

            with mic.recorder(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                blocksize=CHUNK_SAMPLES,
            ) as recorder:
                self._log("✅ Audio capture started!")
                chunk_count = 0

                while self._running:
                    try:
                        data = recorder.record(numframes=CHUNK_SAMPLES)

                        if data.ndim > 1:
                            data = data[:, 0]

                        pcm = (data * 32767).astype(np.int16).tobytes()
                        self.audio_queue.put(pcm)

                        chunk_count += 1
                        if chunk_count % 10 == 1:
                            peak = np.max(np.abs(data))
                            self._log(f"🎤 Audio level: {peak:.4f} (chunk #{chunk_count})")

                    except Exception as e:
                        if not self._running:
                            break
                        self._log(f"⚠ Audio read error: {e}")
                        continue

        except Exception as e:
            self._log(f"❌ Audio capture error: {e}")
            self._running = False
