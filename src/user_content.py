"""Versioned local shortcut and phrase libraries. Data changes are atomic."""

import json
import string
import tempfile
from pathlib import Path
from uuid import uuid4

MODIFIERS = ("Ctrl", "Alt", "Shift", "Win")
KEYS = (
    list(string.ascii_uppercase + string.digits)
    + [
        "Back",
        "Tab",
        "Enter",
        "Escape",
        "Space",
        "Left",
        "Right",
        "Up",
        "Down",
        "Home",
        "End",
        "Delete",
        "PageUp",
        "PageDown",
    ]
    + [f"F{i}" for i in range(1, 13)]
)
EDITS = (
    ("Copy", "C", ["Ctrl"]),
    ("Cut", "X", ["Ctrl"]),
    ("Paste", "V", ["Ctrl"]),
    ("Select all", "A", ["Ctrl"]),
    ("App undo", "Z", ["Ctrl"]),
    ("App redo", "Y", ["Ctrl"]),
    ("Previous word", "Left", ["Ctrl"]),
    ("Next word", "Right", ["Ctrl"]),
    ("Select left", "Left", ["Shift"]),
    ("Select right", "Right", ["Shift"]),
    ("Delete word left", "Back", ["Ctrl"]),
)
DEFAULT_FAVORITES = [
    {"id": label.lower(), "label": label, "key": key, "modifiers": mods}
    for label, key, mods in [
        ("Copy", "C", ["Ctrl"]),
        ("Paste", "V", ["Ctrl"]),
        ("Undo", "Z", ["Ctrl"]),
        ("Screenshot", "S", ["Win", "Shift"]),
    ]
]
LIMITS = {"favorites": 12, "phrases": 100}
MAX_BYTES = 1024 * 1024


def clean_string(value, length, allow_empty=False, multiline=False):
    if (
        not isinstance(value, str)
        or len(value) > length
        or (not allow_empty and not value.strip())
    ):
        raise ValueError(f"Enter a value of up to {length} characters.")
    permitted = "\n\t" if multiline else ""
    if any(
        (ord(char) < 32 and char not in permitted) or char == "\x7f" for char in value
    ):
        raise ValueError("Unsupported control character.")
    value.encode("utf-8")
    return value


def validate(kind, document):
    if (
        not isinstance(document, dict)
        or set(document) != {"version", kind}
        or type(document["version"]) is not int
        or document["version"] != 1
    ):
        raise ValueError("Unsupported library format.")
    items = document[kind]
    if not isinstance(items, list) or len(items) > LIMITS[kind]:
        raise ValueError(f"A maximum of {LIMITS[kind]} entries is supported.")
    seen = set()
    for item in items:
        fields = {"id", "label"} | (
            {"key", "modifiers"}
            if kind == "favorites"
            else {"text", "category", "pinned"}
        )
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError("Invalid entry fields.")
        identifier = clean_string(item["id"], 64)
        if identifier in seen:
            raise ValueError("Duplicate entry ID.")
        seen.add(identifier)
        clean_string(item["label"], 60)
        if kind == "phrases":
            clean_string(item["text"], 2000, multiline=True)
            clean_string(item["category"], 50, allow_empty=True)
            if type(item["pinned"]) is not bool:
                raise ValueError("Invalid pin setting.")
        else:
            mods = item["modifiers"]
            if (
                item["key"] not in KEYS
                or not isinstance(mods, list)
                or not mods
                or not all(m in MODIFIERS for m in mods)
                or len(set(mods)) != len(mods)
            ):
                raise ValueError("Choose a key and at least one modifier.")
    return items


def read_library(kind, path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Library exceeds 1 MB.")
    return validate(kind, json.loads(data.decode("utf-8-sig")))


def write_library(kind, path, items):
    doc = {"version": 1, kind: items}
    validate(kind, doc)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temp = Path(stream.name)
            json.dump(doc, stream, indent=2, ensure_ascii=False)
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


class UserLibrary:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.items = {"favorites": list(DEFAULT_FAVORITES), "phrases": []}
        self.errors = []
        for kind in self.items:
            path = self.path(kind)
            if path.exists():
                try:
                    self.items[kind] = read_library(kind, path)
                except (OSError, ValueError):
                    self.errors.append(f"Could not read {path.name}.")

    def path(self, kind):
        if kind not in LIMITS:
            raise ValueError("Unknown library.")
        return self.directory / (kind + ".json")

    def replace(self, kind, items):
        write_library(kind, self.path(kind), items)
        self.items[kind] = items

    def find(self, kind, identifier):
        for index, entry in enumerate(self.items[kind]):
            if entry["id"] == identifier:
                return index
        raise ValueError("This entry no longer exists.")

    def save(self, kind, identifier, fields):
        items = self.items[kind].copy()
        item = dict(fields, id=identifier or uuid4().hex)
        if identifier:
            items[self.find(kind, identifier)] = item
        else:
            items.append(item)
        self.replace(kind, items)
        return item["id"]

    def change(self, kind, identifier, operation):
        items = self.items[kind].copy()
        index = self.find(kind, identifier)
        if operation == "delete":
            items.pop(index)
        elif operation == "pin" and kind == "phrases":
            items[index] = dict(items[index], pinned=not items[index]["pinned"])
        elif operation in ("up", "down"):
            indices = [
                i
                for i, entry in enumerate(items)
                if kind != "phrases" or entry["pinned"] == items[index]["pinned"]
            ]
            destination = indices.index(index) + (1 if operation == "down" else -1)
            if destination not in range(len(indices)):
                return
            other = indices[destination]
            items[index], items[other] = items[other], items[index]
        else:
            raise ValueError("Unknown action.")
        self.replace(kind, items)
