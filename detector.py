"""
detector.py — Name detection with fuzzy matching and cooldown.

Scans transcribed text for names from a user-provided list.
Uses rapidfuzz for typo-tolerant matching and enforces a cooldown
period to avoid repeated alarms for the same detection.
"""

import time
from rapidfuzz import fuzz


# Default cooldown in seconds after a detection
DEFAULT_COOLDOWN = 20
# Minimum fuzzy-match score (0–100) to count as a hit
DEFAULT_THRESHOLD = 80


class Detector:
    """Detects target names in transcript text."""

    def __init__(
        self,
        names: list[str] | None = None,
        cooldown: float = DEFAULT_COOLDOWN,
        threshold: int = DEFAULT_THRESHOLD,
    ):
        self.set_names(names or [])
        self.cooldown = cooldown
        self.threshold = threshold
        self._last_trigger: float = 0.0  # timestamp of last alarm

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def set_names(self, names: list[str]):
        """Update the list of target names (lowercased internally)."""
        self.names = [n.strip().lower() for n in names if n.strip()]

    def check(self, transcript: str) -> tuple[bool, str | None]:
        """
        Check *transcript* against the name list.

        Returns:
            (detected: bool, matched_phrase: str | None)
        """
        if not self.names or not transcript:
            return False, None

        now = time.time()
        if now - self._last_trigger < self.cooldown:
            return False, None  # still in cooldown

        transcript_lower = transcript.lower()

        # Exact substring check first (fast path)
        for name in self.names:
            if name in transcript_lower:
                self._last_trigger = now
                return True, transcript.strip()

        # Fuzzy match against each word window in the transcript
        words = transcript_lower.split()
        for name in self.names:
            name_word_count = len(name.split())
            for i in range(len(words) - name_word_count + 1):
                window = " ".join(words[i : i + name_word_count])
                score = fuzz.ratio(name, window)
                if score >= self.threshold:
                    self._last_trigger = now
                    return True, transcript.strip()

        return False, None

    def reset_cooldown(self):
        """Allow immediate re-detection (e.g. after user stops/starts)."""
        self._last_trigger = 0.0
