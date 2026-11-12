"""Offline shape recognition; all distances use keyboard units."""

import json
from pathlib import Path

import numpy as np

from keyboard_layout import CENTERS


def resample(points, count=32):
    p = np.asarray(points, dtype=float)
    distances = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    if distances[-1] == 0:
        return np.repeat(p[:1], count, axis=0)
    return np.column_stack(
        [
            np.interp(np.linspace(0, distances[-1], count), distances, p[:, i])
            for i in range(2)
        ]
    )


class Recognizer:
    def __init__(self, words=None):
        if words is None:
            words = json.loads(
                (Path(__file__).parent / "data/vocabulary.json").read_text(
                    encoding="utf-8"
                )
            )["words"]
        self.words = words
        self.templates = np.asarray(
            [
                resample(
                    [CENTERS[c] for i, c in enumerate(w) if i == 0 or c != w[i - 1]]
                )
                for w in words
            ]
        )

    def recognize(self, points):
        p = resample(points)
        endpoint = np.linalg.norm(self.templates[:, 0] - p[0], axis=1) + np.linalg.norm(
            self.templates[:, -1] - p[-1], axis=1
        )
        coarse = (
            np.mean(np.linalg.norm(self.templates[:, ::4] - p[::4], axis=2), axis=1)
            + endpoint
        )
        shortlist = np.argsort(coarse)[:48]
        ranked = []
        for index in shortlist:
            t = self.templates[index]
            distances = np.linalg.norm(p[:, None] - t[None, :], axis=2)
            previous = np.full(33, np.inf)
            previous[0] = 0
            for row in distances:
                current = np.full(33, np.inf)
                for j, d in enumerate(row, 1):
                    current[j] = d + min(previous[j], current[j - 1], previous[j - 1])
                previous = current
            score = previous[-1] / 32 + endpoint[index] * 0.8 + np.log1p(index) * 0.012
            ranked.append((score, int(index)))
        return [self.words[i] for _, i in sorted(ranked)[:3]]
