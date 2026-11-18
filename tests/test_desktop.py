"""Windows dispatch must preserve focus and reject stale targets."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import desktop


def test_input_size_matches_windows_abi() -> None:
    assert ctypes.sizeof(desktop.Input) == (
        40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    )


def test_dispatch_guard_and_packet(monkeypatch: pytest.MonkeyPatch) -> None:
    packets: list[tuple[int, int, int]] = []

    def send(count: int, events: object, size: int) -> int:
        assert count == 2 and size == ctypes.sizeof(desktop.Input)
        assert isinstance(events, ctypes.Array)
        for event in events:
            packets.append(
                (event.payload.ki.vk, event.payload.ki.scan, event.payload.ki.flags)
            )
        return count

    api = SimpleNamespace(
        IsWindow=lambda hwnd: True,
        GetForegroundWindow=lambda: 123,
        GetAsyncKeyState=lambda key: 0,
        SendInput=send,
    )
    monkeypatch.setattr(desktop, "user32", api)
    output = desktop.DesktopInput()
    output.target = 123
    output.send("a")
    output.send("BACK")
    assert packets == [(0, 97, 4), (0, 97, 6), (8, 0, 0), (8, 0, 2)]
    api.GetForegroundWindow = lambda: 124
    with pytest.raises(RuntimeError, match="Target changed"):
        output.send("b")
    assert len(packets) == 4
    api.GetForegroundWindow = lambda: 123
    api.GetAsyncKeyState = lambda key: 0x8000
    with pytest.raises(RuntimeError, match="Release"):
        output.send("b")


@pytest.mark.parametrize(
    "key,vk,state", [("[", 219, 0), ("/", 191, 0), (",", 188, 0), ("?", 191, 1)]
)
def test_punctuation_shortcuts_use_keyboard_layout(monkeypatch, key, vk, state):
    packets = []

    def send(count, event, size):
        native = ctypes.cast(event, ctypes.POINTER(desktop.Input)).contents
        packets.append((native.payload.ki.vk, native.payload.ki.flags))
        return count

    api = SimpleNamespace(
        IsWindow=lambda hwnd: True,
        GetForegroundWindow=lambda: 123,
        GetAsyncKeyState=lambda key: 0,
        GetWindowThreadProcessId=lambda hwnd, pid: 7,
        GetKeyboardLayout=lambda thread: 99,
        VkKeyScanExW=lambda char, layout: vk | (state << 8),
        SendInput=send,
    )
    monkeypatch.setattr(desktop, "user32", api)
    output = desktop.DesktopInput()
    output.target = 123
    output.chord(key, ["Ctrl"])
    codes = [code for code, flags in packets if not flags & 2]
    assert codes == ([17, 16, vk] if state else [17, vk])
    assert packets[-1] == (17, 2)


def test_unmappable_shortcut_sends_nothing(monkeypatch):
    api = SimpleNamespace(
        GetWindowThreadProcessId=lambda hwnd, pid: 7,
        GetKeyboardLayout=lambda thread: 99,
        VkKeyScanExW=lambda char, layout: -1,
        SendInput=lambda *args: pytest.fail("must not inject unsupported shortcut"),
    )
    monkeypatch.setattr(desktop, "user32", api)
    with pytest.raises(RuntimeError, match="Unsupported shortcut key"):
        desktop.DesktopInput().chord("/", ["Ctrl"])
