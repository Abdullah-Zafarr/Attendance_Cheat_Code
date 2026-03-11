"""
generate_alarm.py — Generate a loud multi-tone alarm WAV file.

Run this once to create alarm.wav used by the application.

    python generate_alarm.py
"""

import os
import wave
import struct
import math

# Output path
_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(_DIR, "alarm.wav")

# Audio parameters
SAMPLE_RATE = 44100
DURATION = 2.0        # seconds
AMPLITUDE = 0.9       # 0.0 – 1.0
FREQUENCIES = [880, 1100, 880, 1100]  # alternating tones
BEEPS = 4             # number of beep cycles
BEEP_ON = 0.25        # seconds of tone
BEEP_OFF = 0.15       # seconds of silence


def generate():
    """Generate alarm.wav."""
    samples = []
    cycle_len = BEEP_ON + BEEP_OFF
    total_samples = int(SAMPLE_RATE * BEEPS * cycle_len)

    for i in range(total_samples):
        t = i / SAMPLE_RATE
        cycle_idx = int(t / cycle_len)
        time_in_cycle = t - cycle_idx * cycle_len

        if time_in_cycle < BEEP_ON:
            freq = FREQUENCIES[cycle_idx % len(FREQUENCIES)]
            # Mix two harmonics for a richer alarm tone
            val = AMPLITUDE * (
                0.6 * math.sin(2 * math.pi * freq * t)
                + 0.4 * math.sin(2 * math.pi * freq * 1.5 * t)
            )
        else:
            val = 0.0

        sample = int(val * 32767)
        sample = max(-32768, min(32767, sample))
        samples.append(sample)

    # Write WAV
    with wave.open(OUTPUT_PATH, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    print(f"✓ Alarm sound saved to: {OUTPUT_PATH}")
    print(f"  Duration : {BEEPS * cycle_len:.2f}s")
    print(f"  Samples  : {len(samples)}")


if __name__ == "__main__":
    generate()
