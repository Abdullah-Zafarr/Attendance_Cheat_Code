# 🔔 Attendance Cheat Code

I couldn't understand a single word from my online classes but attendance still mattered. So instead of rotting on a Zoom/Meet call for an hour pretending to pay attention, I built something that watches the call for me.

It captures your system audio in real-time, runs speech recognition on it, and the moment someone says your name — it goes off like a fire alarm. No APIs, no cloud, no internet needed. Everything runs offline on your machine.

Now I spend my lectures actually building stuff (like this) while my attendance stays clean.

![Attendance Alarm UI](assets/test%20case%20and%20ui.PNG)

### Why does this exist?

> Let's be real — online classes are 60 minutes of buffering audio and one professor-mumble away from a nap. But attendance? That still counts. I realized I was wasting hours "attending" classes where the ROI on paying attention was basically zero. So I built this to make sure I never miss the only 2 seconds of the lecture that actually matter: the roll call. Use your brain for things that have an actual return — let this handle the rest.

---

## What it does

- 🎙 **Captures system audio** — listens to whatever is playing through your speakers/headphones
- 🗣 **Real-time speech recognition** — choose between **Vosk** (fast & light) or **Whisper** (more accurate)
- 🔍 **Fuzzy name matching** — handles misspellings and transcription errors automatically
- 🔔 **Loud alarm** with a 20-second cooldown so it doesn't spam you
- 🖥 **Clean dark GUI** — start/stop, engine selector, name list, and detection log
- 🐧🪟 **Cross-platform** — Windows and Linux

---

## Before you start

- **Python 3.10+**
- **Windows**: You're good to go, it uses WASAPI loopback out of the box
- **Linux**: Make sure PulseAudio or PipeWire-PulseAudio is running

---

## Setup

Pretty straightforward:

### 1. Grab the repo

```bash
git clone <repo-url>
cd Attendance_Cheat_Code
```

### 2. Virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux
source venv/bin/activate
```

### 3. Install everything

```bash
pip install -r requirements.txt
```

### 4. Generate the alarm sound

```bash
python generate_alarm.py
```

Creates `alarm.wav` in the project folder. Only need to run it once.

### 5. Vosk model

First time you pick the Vosk engine, it auto-downloads the small English model (~40 MB). No manual setup needed.

---

## How to use it

```bash
python main.py
```

1. **Pick your engine** — Vosk for speed, Whisper for accuracy
2. **Type in your names** — one per line, add common misspellings too
3. **Hit Start** — it starts listening to your system audio
4. **Go do something useful** — when your name gets detected, the alarm handles the rest
5. **Hit Stop** — when class is over

### Tip: add name variations

Profs and transcription engines butcher names differently, so add a few spellings:

```
abdullah
abdulla
abdula
```

---

## Project structure

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
└── README.md
```

---

## Vosk vs Whisper

| | Vosk | Whisper |
|---|---|---|
| Speed | ⚡ Very fast | 🐢 Slower |
| Accuracy | Good | Better |
| CPU usage | Low | Higher |
| Latency | ~0.5s | ~3s |
| Best for | Lightweight / older PCs | Max accuracy |

Vosk works great for most cases. Whisper is there if you need that extra accuracy.

---

## Something not working?

### "No audio captured"
- Make sure audio is actually playing through your **default speakers/headphones**
- Linux: check if PulseAudio is alive → `pulseaudio --check`

### Vosk model won't download
- Grab it manually from https://alphacephei.com/vosk/models
- Extract `vosk-model-small-en-us-0.15` into the project folder

### Too many false alarms
- Use longer / more specific names instead of short ones
- Bump up the fuzzy match threshold in `detector.py` (default is 80)

### Linux audio issues
- Install PulseAudio: `sudo apt install pulseaudio`
- On PipeWire: `sudo apt install pipewire-pulse`

---

## Dependencies

| Package | What it does |
|---|---|
| `vosk` | Offline speech recognition (engine 1) |
| `faster-whisper` | Offline Whisper STT (engine 2) |
| `PyAudioWPatch` | WASAPI loopback capture on Windows |
| `soundcard` | Audio loopback on Linux |
| `rapidfuzz` | Fuzzy string matching |
| `pygame-ce` | Alarm sound playback |
| `numpy` | Audio data processing |

---

## License

MIT — do whatever you want with it.
