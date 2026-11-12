"""Validated, atomic user settings shared by the desktop UI and config file."""

import json
import os
import re
from pathlib import Path

DEFAULTS = {
    "version": 1,
    "layout": "Compact",
    "scale": 1.0,
    "background": "#171719",
    "accent": "#eeeeef",
    "hitboxAssist": False,
    "repeatDelay": 450,
    "repeatInterval": 50,
    "scrubPixels": 8,
    "numberFormat": "Rows",
    "symbols": dict(
        zip(
            "qwertyuiopasdfghjklzxcvbnm",
            list("1234567890+-*/=()^%[]<>!?@"),
            strict=True,
        )
    ),
}


def validate(value: dict) -> dict:
    """Reject unknown fields and invalid values instead of partially applying them."""
    value = dict(value)
    for legacy in ("autoPop", "autoNoticeSeen"):
        if legacy in value:
            if type(value[legacy]) is not bool:
                raise ValueError(legacy + ": expected true/false")
            value.pop(legacy)
    result = dict(DEFAULTS, **value)
    if set(value) - set(DEFAULTS):
        raise ValueError("Unknown setting")
    if result["version"] != 1:
        raise ValueError("Unsupported settings version")
    for key, choices in [
        ("layout", ("Compact", "Standard", "Full")),
        ("numberFormat", ("Rows", "Numpad")),
    ]:
        if result[key] not in choices:
            raise ValueError(key + ": invalid choice")
    for key, low, high in [
        ("scale", 0.65, 1.6),
        ("repeatDelay", 200, 1500),
        ("repeatInterval", 25, 500),
        ("scrubPixels", 3, 40),
    ]:
        if type(result[key]) not in (int, float) or not low <= result[key] <= high:
            raise ValueError(key + ": out of range")
    for key in ("hitboxAssist",):
        if type(result[key]) is not bool:
            raise ValueError(key + ": expected true/false")
    for key in ("background", "accent"):
        if not isinstance(result[key], str) or not re.fullmatch(
            r"#[0-9a-fA-F]{6}", result[key]
        ):
            raise ValueError(key + ": expected #RRGGBB")
    if not isinstance(result["symbols"], dict) or any(
        k not in DEFAULTS["symbols"] or not isinstance(v, str) or len(v) != 1
        for k, v in result["symbols"].items()
    ):
        raise ValueError("symbols: map letters to single characters")
    result["symbols"] = dict(DEFAULTS["symbols"], **result["symbols"])
    return result


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = (
            path
            or Path(os.environ.get("APPDATA", str(Path.home())))
            / "Mousyst/settings.json"
        )
        self.value = validate({})
        self.error = ""
        self.reload()

    def reload(self):
        try:
            if self.path.exists():
                self.value = validate(json.loads(self.path.read_text(encoding="utf-8")))
            self.error = ""
        except (ValueError, OSError, TypeError) as exc:
            self.error = str(exc)

    def save(self, value: dict):
        checked = validate(value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(checked, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.value = checked
