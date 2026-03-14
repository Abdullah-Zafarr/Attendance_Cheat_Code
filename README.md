# 🔔 Attendance Alarm

A lightweight desktop app that listens to your system audio during online classes (Google Meet, Zoom, etc.) and triggers a loud alarm when your name is spoken.

**No APIs required** — it captures the audio coming out of your speakers/headphones directly.

![Attendance Alarm UI](assets/test%20case%20and%20ui.PNG)


---

## Features

- 🎙 **System audio capture** — listens to whatever plays on your computer
- 🗣 **Real-time speech recognition** — choose between **Vosk** (fast & light) or **Whisper** (more accurate)
- 🔍 **Fuzzy name matching** — handles transcription typos automatically
- 🔔 **Loud alarm** with 20-second cooldown to prevent spam
- 🖥 **Clean dark GUI** with Start/Stop, engine selector, name list, and detection log
- 🐧🪟 **Cross-platform** — works on Windows and Linux

---

## Prerequisites

- **Python 3.10+**
- **Windows**: No extra setup needed (uses WASAPI loopback)
- **Linux**: PulseAudio or PipeWire-PulseAudio must be running

---

## Installation

### 1. Clone / Download

```bash
git clone <repo-url>
cd Attendance_Cheat_Code
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate the alarm sound

```bash
python generate_alarm.py
```

This creates `alarm.wav` in the project folder (run once).

### 5. Vosk model (auto-downloaded)

The first time you use the **Vosk** engine, the small English model (~40 MB) is downloaded automatically. No manual setup needed.

---

## Usage

```bash
python main.py
```

1. **Select engine** — pick *Vosk* (faster, lighter) or *Whisper* (more accurate)
2. **Edit names** — type one name per line in the text box
3. **Click Start** — the app begins listening to your system audio
4. **Attend your class** — when any listed name is detected, the alarm sounds
5. **Click Stop** — to pause listening

### Example names list

```
abdullah
abdulla
abdula
ali
ahmed
```

---

## Project Structure

```
Attendance_Cheat_Code/
├── main.py                 # Entry point
├── gui.py                  # Tkinter GUI
├── audio_capture.py        # System audio loopback
├── speech_recognizer.py    # Vosk + Whisper engines
├── detector.py             # Name matching + cooldown
├── alarm.py                # Alarm playback
├── generate_alarm.py       # Alarm WAV generator
├── alarm.wav               # Generated alarm sound
├── requirements.txt        # Dependencies
└── README.md               # This file
```

---

## Engine Comparison

| Feature | Vosk | Whisper |
|---|---|---|
| Speed | ⚡ Very fast | 🐢 Moderate |
| Accuracy | Good | Better |
| CPU usage | Low | Higher |
| Latency | ~0.5 s | ~3 s |
| Best for | Lightweight / older PCs | Maximum accuracy |

---

## Troubleshooting

### "No audio captured"
- Make sure audio is playing through your **default speaker/headphones**
- On Linux, ensure **PulseAudio** is running: `pulseaudio --check`

### Vosk model download fails
- Download manually from https://alphacephei.com/vosk/models
- Extract `vosk-model-small-en-us-0.15` into the project folder

### False positives
- Use longer/more specific names rather than very short ones
- Increase the fuzzy match threshold in `detector.py` (default: 80)

### Linux audio issues
- Install PulseAudio: `sudo apt install pulseaudio`
- If using PipeWire: `sudo apt install pipewire-pulse`

---

## Dependencies

| Package | Purpose |
|---|---|
| `vosk` | Offline speech recognition (engine 1) |
| `faster-whisper` | Offline Whisper STT (engine 2) |
| `PyAudioWPatch` | Reliable WASAPI loopback capture (Windows) |
| `soundcard` | Cross-platform audio loopback capture (Linux) |
| `rapidfuzz` | Fuzzy string matching |
| `pygame-ce` | Alarm sound playback |
| `numpy` | Audio data processing |

---

## License

MIT — use freely.
