"""Offline Mandarin conversion and swipe lookup using the Chewing phrase dictionary."""
import math
from functools import lru_cache
from pathlib import Path

ROWS = ("ㄅㄉˇˋㄓˊ˙ㄚㄞㄢㄦ", "ㄆㄊㄍㄐㄔㄗㄧㄛㄟㄣ",
        "ㄇㄋㄎㄑㄕㄘㄨㄜㄠㄤ", "ㄈㄌㄏㄒㄖㄙㄩㄝㄡㄥ")
SYMBOLS = frozenset("".join(ROWS))


@lru_cache(maxsize=1)
def dictionary():
    entries = {}
    with (Path(__file__).parent / "data/zhuyin.csv").open(encoding="utf8") as source:
        for line in source:
            fields = line.strip().split(",")
            if len(fields) != 3 or not fields[1].isdigit():
                continue
            word, frequency, reading = fields
            if word in SYMBOLS:
                continue
            choices = entries.setdefault(reading.replace(" ", ""), {})
            choices[word] = max(int(frequency), choices.get(word, 0))
    return {key: sorted(choices.items(), key=lambda entry: -entry[1])
            for key, choices in entries.items()}


@lru_cache(maxsize=1)
def swipe_buckets():
    buckets = {}
    for reading, entries in dictionary().items():
        if len(reading) > 1:
            buckets.setdefault(reading[0] + reading[-1], []).append([reading, entries[0][1]])
    return buckets


@lru_cache(maxsize=1)
def syllables():
    return [[key, max(freq for word, freq in entries if len(word) == 1)]
            for key, entries in dictionary().items() if any(len(word) == 1 for word, _ in entries)]


@lru_cache(maxsize=512)
def decode(reading):
    """Keep the best complete word segmentations at each symbol boundary."""
    lexicon = dictionary()
    if reading in lexicon:
        entries = lexicon[reading]
        return tuple(word for word, _ in entries), (15-math.log1p(entries[0][1]))/len(entries[0][0])
    paths = [[] for _ in range(len(reading) + 1)]
    paths[0] = [(0.0, "")]
    for end in range(1, len(paths)):
        best = {}
        for start in range(end):
            if not paths[start]:
                continue
            for word, freq in lexicon.get(reading[start:end], ())[:4]:
                cost = 15 - math.log1p(freq)
                for previous, prefix in paths[start]:
                    phrase = prefix + word
                    best[phrase] = min(best.get(phrase, math.inf), previous + cost)
        paths[end] = sorted((cost, phrase) for phrase, cost in best.items())[:12]
    return (tuple(phrase for _, phrase in paths[-1]),
            paths[-1][0][0]/len(paths[-1][0][1]) if paths[-1] else math.inf)


def compose(reading):
    return decode(reading)[0]


def convert(options):
    ranked = sorted(enumerate(options), key=lambda item:
                    .45 * math.log1p(item[0]) + decode(item[1])[1] * .38)
    matches = [(reading, compose(reading)) for _, reading in ranked]
    matches = [(reading, words) for reading, words in matches if words]
    if not matches:
        return options[0], []
    # Give alternative readings a visible slot before their long homophone lists.
    words = list(matches[0][1][:2])
    words.extend(items[0] for _, items in matches[:5])
    words.extend(word for _, items in matches for word in items)
    return matches[0][0], list(dict.fromkeys(words))
