"""Bounded local preferences for English swipe candidates and pointer aim."""

import json
import math
import re

from keyboard_layout import CENTERS


LEARNABLE = re.compile(r"(?=.{1,32}$)[a-z]+(?:'[a-z]+)?")


class SwipeLearning:
    def __init__(self, directory):
        self.path = directory / "swipe-learning.json"
        self.state = ({}, (0.0, 0.0))
        try:
            if self.path.stat().st_size > 65536:
                return
            counts, bias = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(counts, dict) or len(counts) > 512 or any(
                not LEARNABLE.fullmatch(w) or type(n) is not int or not 1 <= n <= 24
                for w, n in counts.items()
            ):
                return
            if len(bias) == 2 and all(math.isfinite(v) and abs(v) <= 0.25 for v in bias):
                self.state = counts, tuple(bias)
        except (OSError, ValueError, TypeError):
            pass

    def remember(self, word, endpoints, corrected):
        word = word.lower()
        if not LEARNABLE.fullmatch(word):
            return
        counts, bias = self.state
        counts = counts.copy()
        previous = counts.pop(word, 0)
        if len(counts) == 512:
            del counts[min(counts, key=counts.get)]
        counts[word] = min(24, previous + (3 if corrected else 1))
        centers = (CENTERS[word[0]], CENTERS[word[-1]])
        updated = []
        for axis in range(2):
            error = sum(p[axis] - c[axis] for p, c in zip(endpoints, centers, strict=True)) / 2
            updated.append(0.9 * bias[axis] + 0.1 * max(-0.25, min(0.25, error)))
        state = counts, tuple(updated)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state), encoding="utf-8")
        temp.replace(self.path)
        self.state = state

    def clear(self):
        self.path.unlink(missing_ok=True)
        self.state = {}, (0.0, 0.0)
