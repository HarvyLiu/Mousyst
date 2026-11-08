"""Qt Quick entry point for the Mousyst typing preview."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QPoint, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication, QSurfaceFormat
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from desktop import DesktopInput, MiddleButtonHook, user32
from gesture import Gesture
from session import PracticeSession
from tray import TrayControls, app_icon
from ui_geometry import fan_items, group_items


class Controller(QObject):
    """Expose gesture state and practice results to QML."""

    stateChanged = Signal()
    groupChanged = Signal()
    practiceChanged = Signal()
    flashChanged = Signal()

    def __init__(self, practice: bool = False, tray_available: bool = False) -> None:
        super().__init__()
        self.gesture = Gesture()
        self.session = PracticeSession()
        self.flash_text = ""
        self.output = None if practice else DesktopInput()
        self.tray_available = tray_available
        self.message = (
            "Click a text field in another app, then middle-click to open the keyboard."
        )
        self.flash_timer = QTimer(self)
        self.flash_timer.setSingleShot(True)
        self.flash_timer.timeout.connect(self.clear_flash)
        self.stats_timer = QTimer(self)
        self.stats_timer.setInterval(500)
        self.stats_timer.timeout.connect(self.practiceChanged.emit)

    @Property(list, constant=True)
    def groups(self) -> list[dict[str, object]]:
        """Fixed vector paths and labels for the base ring."""
        return group_items()

    @Property(bool, constant=True)
    def practiceMode(self) -> bool:
        """Keep smoke tests isolated from external applications."""
        return self.output is None

    @Property(bool, constant=True)
    def trayAvailable(self) -> bool:
        """Keep a visible fallback panel if the system tray is unavailable."""
        return self.tray_available

    @Property(str, notify=practiceChanged)
    def status(self) -> str:
        """Activation instructions or an input failure."""
        return self.message

    @Property(list, notify=groupChanged)
    def fan(self) -> list[dict[str, object]]:
        """Expanded group's stable geometry."""
        return fan_items(self.gesture.group)

    @Property(int, notify=groupChanged)
    def activeGroup(self) -> int:
        """Selected group, or -1 for none."""
        return self.gesture.group if self.gesture.group is not None else -1

    @Property(bool, notify=stateChanged)
    def armed(self) -> bool:
        """Whether a boundary crossing can enter a character."""
        return self.gesture.armed

    @Property(str, notify=stateChanged)
    def selected(self) -> str:
        """Currently highlighted character or action."""
        return self.gesture.selected or ""

    @Property(str, notify=flashChanged)
    def flash(self) -> str:
        """Brief nonblocking confirmation."""
        return self.flash_text

    @Property(str, notify=practiceChanged)
    def typed(self) -> str:
        """Current practice text."""
        return self.session.text

    @Property(str, notify=practiceChanged)
    def target(self) -> str:
        """Current phrase."""
        return self.session.target

    @Property(bool, notify=practiceChanged)
    def complete(self) -> bool:
        """Whether the phrase matches exactly."""
        return self.output is None and self.session.finished is not None

    @Property(str, notify=practiceChanged)
    def speed(self) -> str:
        """Retained-text words per minute."""
        value = self.session.wpm()
        return f"{value:.1f}" if value is not None else "—"

    @Property(str, notify=practiceChanged)
    def mistakes(self) -> str:
        """Cumulative wrong insertions."""
        return str(self.session.errors)

    @Property(str, notify=practiceChanged)
    def corrections(self) -> str:
        """Backspace count."""
        return str(self.session.backspaces)

    @Slot(float, float)
    def move(self, x: float, y: float) -> None:
        """Apply pointer movement, emitting only changed state."""
        if self.output is None and self.session.finished is not None:
            return
        before = (self.gesture.group, self.gesture.armed, self.gesture.selected)
        action = self.gesture.move(x, y)
        if action is not None:
            if self.output is not None:
                try:
                    self.output.send(action)
                except RuntimeError as exc:
                    self.message = str(exc)
                    self.practiceChanged.emit()
                    self.cancel()
                    return
                self.session.text = (
                    self.session.text[:-1]
                    if action == "BACK"
                    else self.session.text + (" " if action == "SPACE" else action)
                )
            else:
                self.session.enter(action)
            self.flash_text = {"SPACE": "␣", "BACK": "⌫"}.get(action, action.upper())
            self.flashChanged.emit()
            self.practiceChanged.emit()
            if self.session.finished is not None:
                self.stats_timer.stop()
            elif self.output is None and not self.stats_timer.isActive():
                self.stats_timer.start()
        if before[0] != self.gesture.group:
            self.groupChanged.emit()
        if before != (self.gesture.group, self.gesture.armed, self.gesture.selected):
            self.stateChanged.emit()

    @Slot()
    def cancel(self) -> None:
        """Require a fresh center visit after hiding or losing focus."""
        old_group = self.gesture.group
        self.gesture.cancel()
        self.flash_timer.stop()
        if old_group is not None:
            self.groupChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def clear_flash(self) -> None:
        """Clear entry confirmation without blocking input."""
        self.flash_text = ""
        self.flashChanged.emit()

    @Slot()
    def reset(self) -> None:
        """Clear the current attempt."""
        self.session = PracticeSession(phrase_index=self.session.phrase_index)
        self.stats_timer.stop()
        self.cancel()
        self.clear_flash()
        self.practiceChanged.emit()

    @Slot()
    def nextPhrase(self) -> None:
        """Advance the phrase and reset measurements."""
        self.session.phrase_index += 1
        self.reset()


def main() -> int:
    """Load the GPU-rendered UI and optionally run a packaged smoke check."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--show-panel", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshot-dir", type=Path)
    args = parser.parse_args()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    surface = QSurfaceFormat()
    surface.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(surface)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Mousyst")
    app.setWindowIcon(app_icon())
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    app.setQuitOnLastWindowClosed(not tray_available)
    controller = Controller(practice=args.smoke_test, tray_available=tray_available)
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(
        lambda errors: warnings.extend(e.toString() for e in errors)
    )
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui" / "Main.qml")))
    if not engine.rootObjects():
        if args.report:
            args.report.write_text(json.dumps({"ok": False, "warnings": warnings}))
        return 1
    root = engine.rootObjects()[0]
    keyboard = root.findChild(QQuickWindow, "keyboard")
    assert keyboard is not None
    assert isinstance(root, QQuickWindow)
    if args.show_panel:
        root.show()
        root.requestActivate()
    tray = TrayControls(app, root, keyboard) if tray_available else None
    pointer_timer = QTimer()
    pointer_timer.setInterval(16)
    hook = MiddleButtonHook()
    last_position: tuple[int, int] | None = None

    def check_target() -> None:
        if controller.output is not None and not controller.output.is_current():
            keyboard.hide()
            return
        if controller.output is not None and user32.GetAsyncKeyState(0x1B) & 0x8000:
            keyboard.hide()

    def mouse_moved(native_x: int, native_y: int) -> None:
        nonlocal last_position
        if not keyboard.isVisible() or controller.output is None:
            return
        check_target()
        if not keyboard.isVisible():
            return
        # Windows hook coordinates are physical pixels; Qt window positions
        # and gesture dimensions are device-independent pixels.
        position = QPoint(native_x, native_y)
        for screen in QGuiApplication.screens():
            bounds = screen.geometry()
            ratio = screen.devicePixelRatio()
            if (
                bounds.x() <= native_x < bounds.x() + bounds.width() * ratio
                and bounds.y() <= native_y < bounds.y() + bounds.height() * ratio
            ):
                position = QPoint(
                    round(bounds.x() + (native_x - bounds.x()) / ratio),
                    round(bounds.y() + (native_y - bounds.y()) / ratio),
                )
                break
        position -= keyboard.position()
        current = (position.x(), position.y())
        if current == last_position:
            return
        last_position = current
        if keyboard.property("moving"):
            controller.cancel()
        else:
            # Feed even an overshoot outside the window through hit testing;
            # discarding that final event used to drop fast outward slices.
            controller.move(current[0] - 280, current[1] - 300)

    def update_polling() -> None:
        nonlocal last_position
        last_position = None
        hook.track_motion = keyboard.isVisible() and not args.smoke_test
        if keyboard.isVisible() and not args.smoke_test:
            pointer_timer.start()
        else:
            pointer_timer.stop()
            controller.cancel()

    pointer_timer.timeout.connect(check_target)
    keyboard.visibleChanged.connect(update_polling)
    update_polling()

    def toggle_keyboard(hwnd: object) -> None:
        if keyboard.isVisible():
            keyboard.hide()
            return
        assert controller.output is not None
        if not controller.output.capture(int(str(hwnd))):
            return
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        assert screen is not None
        bounds = screen.availableGeometry()
        x = max(
            bounds.left(), min(cursor.x() - 280, bounds.right() - keyboard.width() + 1)
        )
        y = max(
            bounds.top(), min(cursor.y() - 300, bounds.bottom() - keyboard.height() + 1)
        )
        keyboard.setPosition(QPoint(x, y))
        controller.cancel()
        controller.message = (
            "Typing into the selected app. Middle-click or Esc to hide."
        )
        controller.practiceChanged.emit()
        keyboard.show()
        controller.move(
            cursor.x() - keyboard.x() - 280, cursor.y() - keyboard.y() - 300
        )

    if not args.smoke_test:
        hook.toggled.connect(toggle_keyboard, Qt.ConnectionType.QueuedConnection)
        hook.moved.connect(mouse_moved, Qt.ConnectionType.QueuedConnection)

        def hook_error(message: str) -> None:
            controller.message = message
            controller.practiceChanged.emit()

        hook.failed.connect(hook_error)
        hook.start()
        app.aboutToQuit.connect(hook.stop)

    if args.smoke_test:

        def smoke() -> None:
            result: dict[str, object] = {"ok": False}
            try:
                assert keyboard.isVisible()
                assert keyboard.color().alpha() == 0
                controller.move(0, 0)
                controller.move(0, -100)
                controller.move(0, -180)
                controller.move(0, -225)
                assert controller.session.text == "c"
                assert controller.flash_text == "C"
                controller.cancel()
                assert controller.flash_text == "C"
                controller.move(0, -240)
                assert controller.session.text == "c"
                keyboard.hide()
                assert not keyboard.isVisible()
                keyboard.show()
                keyboard.requestActivate()
                app.processEvents()
                controller.cancel()
                assert controller.session.text == "c" and not controller.gesture.armed
                controller.nextPhrase()
                assert controller.session.text == ""
                assert controller.flash_text == ""
                controller.move(0, 0)
                controller.move(0, 129)
                assert controller.session.text == " " and controller.flash_text == "␣"
                controller.move(0, 0)
                controller.move(-100, -100)
                assert controller.session.text == "" and controller.flash_text == "⌫"
                controller.reset()
                controller.move(0, 0)
                controller.move(0, -100)
                controller.move(0, -180)
                if args.screenshot_dir:
                    args.screenshot_dir.mkdir(parents=True, exist_ok=True)
                    until = time.monotonic() + 0.4
                    while time.monotonic() < until:
                        app.processEvents()
                    controller.move(0, 0)
                    controller.move(0, -100)
                    controller.move(0, -180)
                    until = time.monotonic() + 0.2
                    while time.monotonic() < until:
                        app.processEvents()
                    assert keyboard.grabWindow().save(
                        str(args.screenshot_dir / "keyboard.png")
                    )
                    assert isinstance(root, QQuickWindow)
                    assert root.grabWindow().save(
                        str(args.screenshot_dir / "practice.png")
                    )
                assert not warnings, "\n".join(warnings)
                if tray is not None:
                    assert tray.icon.isVisible() and not tray.icon.icon().isNull()
                    root.close()
                    app.processEvents()
                    assert not root.isVisible() and tray.icon.isVisible()
                    tray.show_action.trigger()
                    assert root.isVisible()
                result = {
                    "ok": True,
                    "checks": [
                        "QML load",
                        "transparency",
                        "entry",
                        "return lock",
                        "hide/reopen",
                        "reset",
                        (
                            "tray close/reopen"
                            if tray
                            else "visible fallback without tray"
                        ),
                    ],
                    "warnings": warnings,
                }
            except (AssertionError, OSError, RuntimeError, ValueError) as exc:
                result["error"] = str(exc)
                result["warnings"] = warnings
            if args.report:
                args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
            if sys.stdout is not None:
                print(json.dumps(result))
            if result["ok"] and tray is not None:
                tray.quit_action.trigger()
            else:
                app.exit(0 if result["ok"] else 1)

        QTimer.singleShot(700, smoke)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
