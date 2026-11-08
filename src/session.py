"""Framework-independent practice measurements."""

from __future__ import annotations

import time
from dataclasses import dataclass

PHRASES = (
    "the quick brown fox jumps over the lazy dog",
    "we can meet at the park after lunch",
    "please bring a cup of tea for me",
)


@dataclass
class PracticeSession:
    """Track attempts without hiding corrected errors."""

    phrase_index: int = 0
    text: str = ""
    entries: int = 0
    errors: int = 0
    backspaces: int = 0
    started: float | None = None
    finished: float | None = None

    @property
    def target(self) -> str:
        """Return the current phrase with wraparound."""
        return PHRASES[self.phrase_index % len(PHRASES)]

    def enter(self, action: str, now: float | None = None) -> None:
        """Apply one action and stop timing at an exact match."""
        if self.finished is not None:
            return
        now = time.perf_counter() if now is None else now
        if self.started is None:
            self.started = now
        if action == "BACK":
            self.backspaces += 1
            self.text = self.text[:-1]
        else:
            char = " " if action == "SPACE" else action
            index = len(self.text)
            self.entries += 1
            if index >= len(self.target) or char != self.target[index]:
                self.errors += 1
            self.text += char
        if self.text == self.target:
            self.finished = now

    def wpm(self, now: float | None = None) -> float | None:
        """Calculate retained-character WPM after the first second."""
        if self.started is None:
            return None
        end = self.finished if self.finished is not None else now
        elapsed = (time.perf_counter() if end is None else end) - self.started
        return len(self.text) / 5 * 60 / elapsed if elapsed >= 1 else None
