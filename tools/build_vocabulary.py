"""Reproduce the fixed English vocabulary and preserve source attribution."""

import json
import shutil
from pathlib import Path

import wordfreq
from wordfreq import top_n_list

root = Path(__file__).resolve().parents[1] / "src/data"
root.mkdir(parents=True, exist_ok=True)
words = [w for w in top_n_list("en", 60000) if w.isascii() and w.isalpha()][:20000]
payload = {
    "source": "wordfreq 3.1.1 — https://github.com/rspeer/wordfreq",
    "license": "CC BY-SA 4.0; see bundled wordfreq notices. Derived English word subset.",
    "words": words,
}
(root / "vocabulary.json").write_text(json.dumps(payload), encoding="utf-8")
package = Path(wordfreq.__file__).parent
for source in (package.parent / "wordfreq-3.1.1.dist-info").rglob("*"):
    if source.is_file() and (
        "license" in source.name.lower() or "notice" in source.name.lower()
    ):
        shutil.copyfile(source, root / source.name)
print(f"Bundled {len(words)} words")
