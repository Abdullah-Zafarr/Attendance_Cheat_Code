"""
alarm.py — Alarm playback module.

Uses pygame.mixer to play a .wav alarm file.
Non-blocking so the main application loop continues.
"""

import os
import pygame


# Path to alarm sound (same directory as this script)
_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ALARM_PATH = os.path.join(_DIR, "alarm.wav")


class Alarm:
    """Plays an alarm sound using pygame."""

    def __init__(self, sound_path: str = DEFAULT_ALARM_PATH):
        self.sound_path = sound_path
        self._initialized = False
        self._sound = None

    def _ensure_init(self):
        """Lazily initialize pygame mixer."""
        if not self._initialized:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
            self._initialized = True
        if self._sound is None and os.path.exists(self.sound_path):
            self._sound = pygame.mixer.Sound(self.sound_path)

    def play(self):
        """Play the alarm sound (non-blocking)."""
        try:
            self._ensure_init()
            if self._sound is not None:
                self._sound.play()
        except Exception:
            pass  # don't crash the app if audio fails

    def stop(self):
        """Silence any playing alarm."""
        try:
            if self._initialized:
                pygame.mixer.stop()
        except Exception:
            pass

    def cleanup(self):
        """Release mixer resources."""
        try:
            if self._initialized:
                pygame.mixer.quit()
                self._initialized = False
                self._sound = None
        except Exception:
            pass
