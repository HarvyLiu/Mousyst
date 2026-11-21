"""Rank exact Traditional Chinese readings using the bundled Chewing dictionary."""
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
            key = reading.replace(" ", "")
            choices = entries.setdefault(key, {})
            choices[word] = max(int(frequency), choices.get(word, 0))
    return {key: sorted(choices, key=choices.get, reverse=True)
            for key, choices in entries.items()}
