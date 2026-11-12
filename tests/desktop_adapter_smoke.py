"""Opt-in integration test: inject only into a disposable fixture we create."""

import ctypes as ct
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtCore import QCoreApplication

from desktop import user32
from desktop_app import DesktopController


def main():
    app = QCoreApplication([])
    path = Path("build/desktop/adapter-target.json").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    child = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name("native_edit_fixture.py")),
            str(path),
        ]
    )
    controller = DesktopController()
    try:
        user32.FindWindowW.argtypes = [ct.c_wchar_p, ct.c_wchar_p]
        user32.FindWindowW.restype = ct.c_void_p
        user32.SetForegroundWindow.argtypes = [ct.c_void_p]
        hwnd = 0
        for _ in range(100):
            hwnd = user32.FindWindowW(None, "Mousyst disposable input test")
            if hwnd:
                break
            time.sleep(0.05)
        assert hwnd
        time.sleep(0.4)
        from desktop import Input, InputUnion, MouseInput

        user32.SetWindowPos.argtypes = [
            ct.c_void_p,
            ct.c_void_p,
            ct.c_int,
            ct.c_int,
            ct.c_int,
            ct.c_int,
            ct.c_uint,
        ]
        user32.SetWindowPos(hwnd, -1, 100, 100, 600, 300, 0x40)
        user32.SetCursorPos(150, 160)
        click = (Input * 2)(
            Input(0, InputUnion(mi=MouseInput(0, 0, 0, 2, 0, 0))),
            Input(0, InputUnion(mi=MouseInput(0, 0, 0, 4, 0, 0))),
        )
        user32.SendInput(2, click, ct.sizeof(Input))
        time.sleep(0.15)
        for _ in range(30):
            user32.SetForegroundWindow(hwnd)
            if user32.GetForegroundWindow() == hwnd:
                break
            time.sleep(0.05)
        assert controller.output.capture(hwnd) and controller.output.is_current(), (
            hwnd,
            user32.GetForegroundWindow(),
            controller.output.target,
        )
        controller.output.chord("a", ["Ctrl"])
        controller.output.chord("Back", [])
        for c in "hello":
            controller.key(c)
        time.sleep(0.2)
        assert json.loads(path.read_text()) == "hello"
        controller.key("Ctrl")
        controller.key("a")
        controller.key("x")
        time.sleep(0.2)
        assert json.loads(path.read_text()) == "x"
        controller.scrub(-1)
        controller.key("z")
        time.sleep(0.2)
        assert json.loads(path.read_text()) == "zx"
        field = controller.snapshot()
        assert field and field["hwnd"] == hwnd
        controller.output.chord("a", ["Ctrl"])
        controller.output.chord("Back", [])
        controller.editor.external("")
        time.sleep(0.1)
        controller.pending_field = controller.snapshot()
        controller.receive(
            controller.generation,
            controller.editor.revision,
            ["hello", "help", "held"],
            10,
        )
        time.sleep(0.15)
        assert json.loads(path.read_text()) == "hello "
        controller.alternative(1)
        time.sleep(0.15)
        assert json.loads(path.read_text()) == "help ", (
            controller.status,
            controller.owner,
            controller.snapshot(),
            json.loads(path.read_text()),
        )
        controller.scrub(-1)
        controller.alternative(0)
        time.sleep(0.1)
        assert json.loads(path.read_text()) == "help ", "Stale candidate modified text"
        controller.observer.start()
        app.processEvents()
        report = {
            "ok": True,
            "checks": [
                "real Unicode typing",
                "Ctrl+A",
                "caret scrub",
                "UI Automation snapshot",
                "focus event hook",
            ],
        }
        if "--app" in sys.argv:
            from desktop import Input, InputUnion, MouseInput

            application = Path(sys.argv[sys.argv.index("--app") + 1]).resolve()
            layout_report = Path("build/desktop/layout-test.json").resolve()
            layout_report.unlink(missing_ok=True)
            preview = subprocess.Popen(
                [str(application), "--test-layout-report", str(layout_report)]
                if application.suffix == ".exe"
                else [
                    sys.executable,
                    str(application),
                    "--test-layout-report",
                    str(layout_report),
                ]
            )
            try:
                time.sleep(3)
                user32.SetForegroundWindow(hwnd)
                user32.IsWindowVisible.argtypes = [ct.c_void_p]
                events = (Input * 2)(
                    Input(0, InputUnion(mi=MouseInput(0, 0, 0, 0x20, 0, 0))),
                    Input(0, InputUnion(mi=MouseInput(0, 0, 0, 0x40, 0, 0))),
                )
                keyboard = 0
                for _ in range(40):
                    keyboard = user32.FindWindowW(None, "Mousyst")
                    if keyboard and user32.IsWindowVisible(keyboard):
                        break
                    time.sleep(0.05)
                autopop = bool(keyboard and user32.IsWindowVisible(keyboard))
                assert not autopop, "Automatic opening should be removed"
                if not autopop:
                    assert user32.SendInput(2, events, ct.sizeof(Input)) == 2
                    time.sleep(0.5)
                    keyboard = user32.FindWindowW(None, "Mousyst")
                assert keyboard and user32.IsWindowVisible(keyboard), (
                    "Desktop keyboard did not open",
                    preview.poll(),
                    hwnd,
                    user32.GetForegroundWindow(),
                    keyboard,
                )
                assert user32.GetForegroundWindow() == hwnd, (
                    "Desktop keyboard stole focus",
                    hwnd,
                    user32.GetForegroundWindow(),
                    keyboard,
                )

                def key_rect():
                    from ctypes.wintypes import RECT

                    for _ in range(30):
                        if layout_report.exists():
                            break
                        time.sleep(0.05)
                    x, y = json.loads(layout_report.read_text())["q"]
                    return RECT(x - 3, y - 3, x + 3, y + 3)

                rect = key_rect()
                assert rect.right > rect.left, "Keyboard key bounds missing"
                baseline = json.loads(path.read_text())
                user32.SetCursorPos(
                    (rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2
                )
                for _ in range(3):
                    assert user32.SendInput(2, click, ct.sizeof(Input)) == 2
                    time.sleep(0.18)
                    assert user32.IsWindowVisible(
                        keyboard
                    ), "Clicking a key hid the keyboard"
                    assert user32.GetForegroundWindow() == hwnd, (
                        "Clicking a key stole focus",
                        user32.GetForegroundWindow(),
                        hwnd,
                        keyboard,
                    )
                assert (
                    json.loads(path.read_text()).count("q") == baseline.count("q") + 3
                ), json.loads(path.read_text())
                assert user32.SendInput(2, events, ct.sizeof(Input)) == 2
                time.sleep(0.3)
                assert not user32.IsWindowVisible(
                    keyboard
                ), "Middle click did not hide keyboard"
                assert user32.SendInput(2, events, ct.sizeof(Input)) == 2
                time.sleep(0.4)
                assert user32.IsWindowVisible(
                    keyboard
                ), "Middle click did not summon keyboard again"
                report["desktop_host"] = {
                    "auto_open": autopop,
                    "middle_click": True,
                    "preserved_focus": True,
                    "real_key_clicks": 3,
                    "middle_click_resummon": True,
                }
            finally:
                preview.terminate()
                preview.wait(timeout=5)
        Path("build/desktop/adapter-smoke.json").write_text(json.dumps(report))
        print(json.dumps(report))
    finally:
        controller.observer.stop()
        controller.executor.shutdown(wait=True, cancel_futures=True)
        child.terminate()
        child.wait(timeout=5)


if __name__ == "__main__":
    main()
