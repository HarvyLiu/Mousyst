"""Configuration must fail atomically and desktop interactions stay testable."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from settings import Settings, validate


def test_settings_roundtrip_and_bad_reload(tmp_path):
    path = tmp_path / "settings.json"
    config = Settings(path)
    config.save(dict(config.value, layout="Full", scale=1.2))
    assert Settings(path).value["layout"] == "Full"
    path.write_text("{bad json")
    config.reload()
    assert config.error and config.value["scale"] == 1.2


def test_legacy_auto_open_cannot_be_enabled():
    migrated = validate({"autoPop": True, "autoNoticeSeen": False})
    assert "autoPop" not in migrated and "autoNoticeSeen" not in migrated


def test_personal_dictionary_roundtrip_and_invalid_import(tmp_path):
    settings = Settings(tmp_path / "settings.json")
    settings.save(dict(settings.value, personalWords=["Mousyst", "OpenAI"]))
    assert Settings(settings.path).value["personalWords"] == ["Mousyst", "OpenAI"]
    for invalid in (["Word", "word"], ["can't"], ["A" * 33], "word", ["x"] * 257):
        with pytest.raises(ValueError):
            settings.save(dict(settings.value, personalWords=invalid))
    assert Settings(settings.path).value["personalWords"] == ["Mousyst", "OpenAI"]


@pytest.mark.parametrize(
    "value",
    [
        {"version": 2},
        {"scale": 8},
        {"repeatDelay": 0},
        {"accent": "mint"},
        {"autoPop": "yes"},
        {"symbols": {"a": "ab"}},
        {"layout": "Unknown"},
    ],
)
def test_invalid_config(value):
    with pytest.raises(ValueError):
        validate(value)
