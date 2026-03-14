# 🔔 Attendance Cheat Code: Technical Briefing

This document provides a technical overview of the **Attendance Cheat Code** project, a system designed to monitor live audio from online classes and trigger an alarm when specific names are detected.

---

## 📂 File Overview

| File | Purpose |
| :--- | :--- |
| `main.py` | The application entry point. Initializes and runs the GUI. |
| `gui.py` | The main coordinator. Implements the Tkinter-based user interface and manages the lifecycle of background threads. |
| `audio_capture.py` | Handles real-time system audio loopback capture using WASAPI (Windows) or PulseAudio (Linux). |
| `speech_recognizer.py` | Contains the speech-to-text logic, offering both **Vosk** (fast, offline) and **Whisper** (high accuracy) engines. |
| `detector.py` | Implements fuzzy name matching and manages detection cooldowns to prevent alarm spamming. |
| `alarm.py` | Manages audio playback of the alert sound using `pygame`. |
| `generate_alarm.py` | A utility script to generate the `alarm.wav` file. |
| `requirements.txt` | Lists the Python dependencies required for the project. |

---

## 🏗️ Functions & Classes

### `AttendanceAlarmApp` (`gui.py`)
The central class that builds the UI and orchestrates the system.
- `_on_start() / _on_stop()`: Manages the startup and teardown of capture and recognition threads.
- `_poll()`: A main-thread timer loop that checks for transcripts and log messages from background threads.
- `_process_transcript()`: Routes transcribed text to the detector and triggers the alarm if a match is found.

### `AudioCapture` (`audio_capture.py`)
A threaded class that captures system-level audio.
- `_capture_windows()`: Uses `PyAudioWPatch` to hook into the Windows WASAPI loopback device.
- `_capture_linux()`: Uses the `soundcard` library to access PulseAudio loopback.
- It pushes raw PCM chunks (16kHz, Mono, 16-bit) into a shared `queue.Queue`.

### `RecognizerWorker` (`speech_recognizer.py`)
A background worker that consumes audio chunks from the queue and feeds them into the selected STT engine.
- Supported Engines:
  - `VoskRecognizer`: Uses the Kaldi-based Vosk model for low-latency streaming recognition.
  - `WhisperRecognizer`: Buffers ~3 seconds of audio and processes it using `faster-whisper`.

### `Detector` (`detector.py`)
Encapsulates the logic for identifying names in text.
- `check(transcript)`: Performs an exact substring match followed by a fuzzy ratio match using `rapidfuzz`.
- `set_names()`: Normalizes and stores the list of target names provided by the user.

### `Alarm` (`alarm.py`)
A simple wrapper for `pygame.mixer`.
- `play()`: Plays the `alarm.wav` file in a non-blocking manner.

---

## 📦 Dependencies & Imports

| Dependency | Role in Project | Used In |
| :--- | :--- | :--- |
| `pyaudiowpatch` | Essential for Windows audio loopback (WASAPI). | `audio_capture.py` |
| `soundcard` | Used for Linux audio loopback (PulseAudio). | `audio_capture.py`, `test_audio.py` |
| `vosk` | Offline, high-speed speech recognition. | `speech_recognizer.py` |
| `faster-whisper` | Highly accurate, transformer-based speech recognition. | `speech_recognizer.py` |
| `rapidfuzz` | Provides the typo-tolerant matching logic. | `detector.py` |
| `pygame-ce` | Handles low-latency audio playback for the alarm. | `alarm.py` |
| `numpy` | Used for audio buffer manipulation and resampling. | `audio_capture.py`, `speech_recognizer.py` |

---

## 🔄 File Interconnections

The system uses a **Producer-Consumer** architecture across multiple threads to ensure the UI remains responsive:

1.  **Audio Producer**: `AudioCapture` runs in its own thread, capturing PCM data and pushing it to a thread-safe `_audio_queue`.
2.  **STT Consumer**: `RecognizerWorker` pulls data from the `_audio_queue`, processes it via `Vosk` or `Whisper`, and sends transcripts back to the GUI via a callback.
3.  **UI Dispatcher**: The `AttendanceAlarmApp` receives transcripts and log messages. It uses the `Detector` to scan for names and calls `Alarm.play()` if a match is confirmed.

---

## 🚀 System Workflow

1.  **Initialization**: `main.py` launches the GUI.
2.  **Configuration**: User selects the engine (Vosk/Whisper) and inputs target names.
3.  **Capture Start**: On "Start", `AudioCapture` identifies the default output device and begins streaming mono audio at 16,000Hz.
4.  **Recognition**: The `RecognizerWorker` loads the selected model and processes chunks. Vosk provides streaming partials, while Whisper transcribes in windows.
5.  **Detection**: The `Detector` compares every phrase against the name list. If the fuzzy match score exceeds the threshold (default: 80), a detection is flagged.
6.  **Alerting**: The GUI plays the alarm and updates the log. A 20-second cooldown is enforced to prevent repeated triggers from the same context.

---

## 🛠️ Technical Considerations

-   **Platform Differences**:
    -   **Windows**: Relies on `PyAudioWPatch` for loopback.
    -   **Linux**: Relies on `soundcard` and requires PulseAudio/PipeWire.
-   **Performance**:
    -   **Vosk**: Latency ~0.5s, very low CPU usage. Ideal for older hardware.
    -   **Whisper**: Latency ~3s, requires more computational power but handles accents and noise significantly better.
-   **Hardware Requirements**:
    -   Microphone access is *not* required; the system listens to "what you hear" (loopback).
    -   Vosk model is ~40MB (downloaded automatically on first use).
-   **Limitations**:
    -   If system volume is extremely low or muted, the captured signal may be too weak for high-quality recognition.
    -   Extremely fast-talking or overlapping speakers may reduce accuracy.

---

## 📊 Suggested Diagrams

To further clarify the architecture, the following diagrams are recommended:
1.  **Data Flow Diagram**: Showing the traversal of audio data from the Speaker Output → Loopback → Queue → Recognizer → Transcript → Detector.
2.  **State Machine Diagram**: Representing the application states: `STOPPED`, `LOADING_MODEL`, `LISTENING`, and `ALARMING` (Cooldown).
