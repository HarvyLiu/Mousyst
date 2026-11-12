"""Evaluate explicitly labelled, opt-in recorded strokes (never training data)."""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from word_recognizer import Recognizer

parser = argparse.ArgumentParser()
parser.add_argument("recordings", type=Path)
args = parser.parse_args()
data = json.loads(args.recordings.read_text(encoding="utf-8"))
recognizer = Recognizer()
latencies, hits, top3 = [], [], []
for record in data["opt_in_strokes"]:
    expected = record.get("expected_word")
    if not expected:
        continue
    start = time.perf_counter()
    words = recognizer.recognize(record["points"])
    latencies.append((time.perf_counter() - start) * 1000)
    hits.append(words[0] == expected)
    top3.append(expected in words)
if not hits:
    parser.error("Label each held-out stroke with expected_word before evaluating.")
print(
    json.dumps(
        {
            "strokes": len(hits),
            "top1": statistics.mean(hits),
            "top3": statistics.mean(top3),
            "p95_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95 + 0.999) - 1)],
        },
        indent=2,
    )
)
