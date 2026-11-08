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
