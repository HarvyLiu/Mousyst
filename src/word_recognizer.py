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


def word_path(word):
    return resample([CENTERS[c] for i, c in enumerate(word) if i == 0 or c != word[i - 1]])


class Recognizer:
    def __init__(self, words=None):
        if words is None:
            words = json.loads(
                (Path(__file__).parent / "data/vocabulary.json").read_text(
                    encoding="utf-8"
                )
            )["words"]
        self.words = words
        self.templates = np.asarray([word_path(word) for word in words])
        self._indices = {word: i for i, word in enumerate(words)}
        self._base = (self.words, self.templates, np.log1p(np.arange(len(words))) * 0.012)
        self._lexicon = self._base
        self._personal_words = ()
        self.learned = {}, (0.0, 0.0)

    def set_personal_words(self, words):
        words = tuple(words)
        if words == self._personal_words:
            return
        if not words:
            self._lexicon = self._base
        else:
            names = list(self.words)
            prior = list(self._base[2])
            extras = []
            for spelling in words:
                word = spelling.lower()
                index = self._indices.get(word)
                if index is None:
                    extras.append(word_path(word))
                    names.append(spelling)
                    prior.append(0.04)
                else:
                    names[index] = spelling
                    prior[index] -= 0.08
            templates = np.concatenate((self.templates, extras)) if extras else self.templates
            # Publish all three together. In-flight worker jobs retain their previous snapshot.
            self._lexicon = names, templates, prior
        self._personal_words = words

    def recognize(self, points):
        words, templates, prior = self._lexicon
        counts, bias = self.learned
        p = resample(points) - bias
        endpoint = np.linalg.norm(templates[:, 0] - p[0], axis=1) + np.linalg.norm(
            templates[:, -1] - p[-1], axis=1
        )
        coarse = (
            np.mean(np.linalg.norm(templates[:, ::4] - p[::4], axis=2), axis=1)
            + endpoint
        )
        shortlist = np.argsort(coarse)[:48]
        ranked = []
        for index in shortlist:
            t = templates[index]
            distances = np.linalg.norm(p[:, None] - t[None, :], axis=2)
            previous = np.full(33, np.inf)
            previous[0] = 0
            for row in distances:
                current = np.full(33, np.inf)
                for j, d in enumerate(row, 1):
                    current[j] = d + min(previous[j], current[j - 1], previous[j - 1])
                previous = current
            score = previous[-1] / 32 + endpoint[index] * 0.8 + prior[index]
            score -= 0.055 * np.log1p(counts.get(words[index].lower(), 0))
            ranked.append((score, int(index)))
        return [words[i] for _, i in sorted(ranked)[:3]]
