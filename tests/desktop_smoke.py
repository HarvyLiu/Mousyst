"""Opt-in native integration test using only a disposable text window."""

from __future__ import annotations

import ctypes as ct
import json
import subprocess
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path


def target(path: Path) -> None:
    """Publish only this fixture's text, never existing application content."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Mousyst disposable input test")
    text = tk.Text(root)
    text.pack()
    text.focus_force()
    root.after(100, text.focus_force)

    def snapshot() -> None:
        path.write_text(json.dumps(text.get("1.0", "end-1c")))
        root.after(50, snapshot)

    snapshot()
    root.mainloop()


def verify() -> None:
    """Verify actual SendInput, focus retention, and the middle-button hook."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from PySide6.QtCore import QCoreApplication

    from desktop import (
        DesktopInput,
        Input,
        InputUnion,
        MiddleButtonHook,
        MouseInput,
        user32,
    )

    app = QCoreApplication([])
    path = Path("build/desktop-target.json").resolve()
    child = subprocess.Popen([sys.executable, __file__, "--target", str(path)])
    hook = MiddleButtonHook()
    try:
        user32.FindWindowW.argtypes = [ct.c_wchar_p, ct.c_wchar_p]
        user32.FindWindowW.restype = ct.c_void_p
        user32.SetForegroundWindow.argtypes = [ct.c_void_p]
        deadline = time.monotonic() + 10
        hwnd = None
        while not hwnd and time.monotonic() < deadline:
            hwnd = user32.FindWindowW(None, "Mousyst disposable input test")
            time.sleep(0.05)
        assert hwnd

        def focus_target() -> None:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                user32.SetForegroundWindow(hwnd)
                if user32.GetForegroundWindow() == hwnd:
                    return
                time.sleep(0.05)
            raise AssertionError("Windows did not focus the disposable test window")

        focus_target()
        output = DesktopInput()
        assert output.capture(hwnd) and output.is_current()
        for action in ("c", "SPACE", "a", "BACK"):
            output.send(action)
        time.sleep(0.3)
        assert json.loads(path.read_text()) == "c "
        assert output.is_current(), "Input stole the text window's focus"
        triggers: list[object] = []
        failures: list[str] = []
        hook.toggled.connect(triggers.append)
        hook.failed.connect(failures.append)
        hook.start()
        time.sleep(0.2)
        events = (Input * 2)(
            Input(0, InputUnion(mi=MouseInput(0, 0, 0, 0x20, 0, 0))),
            Input(0, InputUnion(mi=MouseInput(0, 0, 0, 0x40, 0, 0))),
        )
        assert user32.SendInput(2, events, ct.sizeof(Input)) == 2
        deadline = time.monotonic() + 1
        while not triggers and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert triggers == [hwnd] and not failures, (triggers, failures)
        print(
            "Desktop integration passed: real text, space, backspace, focus, middle-click hook"
        )
        if len(sys.argv) > 2 and sys.argv[1] == "--app":
            hook.stop()
            application = Path(sys.argv[2]).resolve()
            command = (
                [str(application)]
                if application.suffix == ".exe"
                else [sys.executable, str(application)]
            )
            command.append("--show-panel")
            preview = subprocess.Popen(command)
            try:
                time.sleep(2)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    panel = user32.FindWindowW(
                        None, "Mousyst — Qt Quick typing preview"
                    )
                    if panel:
                        break
                    time.sleep(0.1)
                time.sleep(0.5)
                focus_target()
                assert (
                    output.is_current()
                ), "Test text field did not get foreground focus"
                assert user32.SendInput(2, events, ct.sizeof(Input)) == 2
                user32.IsWindowVisible.argtypes = [ct.c_void_p]
                user32.GetWindowRect.argtypes = [ct.c_void_p, ct.POINTER(wt.RECT)]
                deadline = time.monotonic() + 5
                keyboard = None
                while time.monotonic() < deadline:
                    keyboard = user32.FindWindowW(None, "Mousyst — radial keyboard")
                    if keyboard and user32.IsWindowVisible(keyboard):
                        break
                    time.sleep(0.05)
                assert keyboard and user32.IsWindowVisible(
                    keyboard
                ), "Middle-click did not open the keyboard"
                assert output.is_current(), "Overlay stole focus"
                rect = wt.RECT()
                user32.GetWindowRect(keyboard, ct.byref(rect))
                scale = (rect.right - rect.left) / 560

                def move(x: int, y: int, pause: float = 0.08) -> None:
                    left, top = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
                    width, height = user32.GetSystemMetrics(
                        78
                    ), user32.GetSystemMetrics(79)
                    dx = round((rect.left + x * scale - left) * 65535 / (width - 1))
                    dy = round((rect.top + y * scale - top) * 65535 / (height - 1))
                    event = Input(0, InputUnion(mi=MouseInput(dx, dy, 0, 0xC001, 0, 0)))
                    assert user32.SendInput(1, ct.byref(event), ct.sizeof(Input)) == 1
                    time.sleep(pause)

                for x, y in [
                    (280, 300),
                    (280, 200),
                    (280, 120),
                    (280, 75),
                    (280, 300),
                    (280, 429),
                    (280, 300),
                    (280, 200),
                    (200, 145),
                    (164, 95),
                    (280, 300),
                    (180, 200),
                ]:
                    move(x, y)
                time.sleep(0.2)
                # The second A gesture may aim at a neighboring letter; the
                # one-layer Backspace must remove it either way.
                assert json.loads(path.read_text()) == "c c ", path.read_text()
                assert output.is_current()
                for x, y in [
                    (280, 300),
                    (280, -100),
                    (280, 300),
                    (280, 429),
                    (280, 300),
                    (280, 200),
                    (375, 152),
                    (424, 199),
                    (280, 300),
                    (280, 200),
                    (185, 152),
                    (136, 199),
                ]:
                    move(x, y, 0.003)
                time.sleep(0.4)
                assert json.loads(path.read_text()) == "c c c ea", path.read_text()
                user32.SendInput(2, events, ct.sizeof(Input))
                time.sleep(0.2)
                assert not user32.IsWindowVisible(
                    keyboard
                ), "Middle-click did not hide the keyboard"
                print(
                    "Full app passed: direct output, focus, fast 3ms gestures, window overshoot, both fan sides, one-ring controls, tray-compatible dismiss"
                )
            finally:
                preview.terminate()
                preview.wait(timeout=5)
    finally:
        hook.stop()
        child.terminate()
        child.wait(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--target":
        target(Path(sys.argv[2]))
    else:
        verify()
