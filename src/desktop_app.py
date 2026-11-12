"""Compact mouse keyboard desktop host and explicit target-bound input adapter."""

import argparse
import json
import sys
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QLockFile,
    QPoint,
    QStandardPaths,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QGuiApplication, QPalette
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from accessibility import FocusObserver
from desktop import DesktopInput, MiddleButtonHook
from practice import Controller
from settings import DEFAULTS, Settings
from tray import app_icon
from window_behavior import KeyboardActivationFilter


class DesktopController(Controller):
    desktopChanged = Signal()
    hideRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, smoke=False):
        super().__init__()
        self.changed.connect(self.desktopChanged.emit)
        self.settings = Settings()
        self.output = None if smoke else DesktopInput()
        self.observer = None if smoke else FocusObserver()
        self.owner = None
        self.current_field = None
        self.suppressed = None
        self.repeat_key = ""
        self.repeating = False
        self.repeat_timer = QTimer(self)
        self.repeat_timer.timeout.connect(self.repeat_tick)
        self.status = self.settings.error or "Middle-click a text field to type."

    @Property("QVariantMap", notify=desktopChanged)
    def preferences(self):
        return self.settings.value

    @Property(str, notify=desktopChanged)
    def settingsJson(self):
        return json.dumps(self.preferences, indent=2)

    @Property(bool, notify=desktopChanged)
    def isRepeating(self):
        return self.repeating

    @Slot(float, float, result=str)
    def aim(self, x, y):
        from keyboard_layout import CENTERS

        candidates = sorted(
            CENTERS, key=lambda c: (CENTERS[c][0] - x) ** 2 + (CENTERS[c][1] - y) ** 2
        )
        best = candidates[0]
        bx, by = CENTERS[best]
        if abs(bx - x) > 0.6 or abs(by - y) > 0.6:
            return ""
        if (
            not self.preferences["hitboxAssist"]
            or self.modifiers
            or getattr(self, "password", False)
        ):
            return best
        if abs(bx - x) < 0.4 and abs(by - y) < 0.4:
            return best
        prefix = self.editor.text.split(" ")[-1].lower()
        weights = {c: 1.0 for c in candidates[:2]}
        if self.recognizer:
            for rank, word in enumerate(self.recognizer.words[:5000]):
                if (
                    word.startswith(prefix)
                    and len(word) > len(prefix)
                    and word[len(prefix)] in weights
                ):
                    weights[word[len(prefix)]] += 1 / (rank + 1)
        return min(
            candidates[:2],
            key=lambda c: (CENTERS[c][0] - x) ** 2
            + (CENTERS[c][1] - y) ** 2
            - 0.02 * weights[c],
        )

    @Slot(str)
    def saveSettings(self, text):
        try:
            self.settings.save(json.loads(text))
            self.cancel()
            self.status = "Settings saved."
        except (OSError, ValueError, TypeError) as exc:
            self.status = "Settings: " + str(exc)
        self.changed.emit()

    @Slot()
    def reloadSettings(self):
        self.cancel()
        self.settings.reload()
        self.status = self.settings.error or "Configuration reloaded."
        self.changed.emit()

    @Slot(str, "QVariant")
    def setPreference(self, name, value):
        self.saveSettings(json.dumps(dict(self.preferences, **{name: value})))

    @Slot(str, str)
    def setSymbol(self, key, value):
        symbols = dict(self.preferences["symbols"])
        symbols[key] = value
        self.setPreference("symbols", symbols)

    @Slot()
    def importSettings(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            None, "Import Mousyst settings", "", "JSON (*.json)"
        )
        if path:
            try:
                self.saveSettings(Path(path).read_text(encoding="utf-8"))
            except OSError as exc:
                self.status = str(exc)
                self.changed.emit()

    @Slot()
    def exportSettings(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            None, "Export Mousyst settings", "mousyst-settings.json", "JSON (*.json)"
        )
        if path:
            try:
                Path(path).write_text(self.settingsJson, encoding="utf-8")
            except OSError as exc:
                self.status = str(exc)
                self.changed.emit()

    @Slot()
    def resetSettings(self):
        self.saveSettings(json.dumps(DEFAULTS))

    @Slot()
    def configFolder(self):
        self.settings.path.parent.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.settings.path.parent)))

    def snapshot(self):
        return self.observer.verify() if self.observer else None

    def send_text(self, text):
        if self.output:
            units = text.encode("utf-16-le", errors="surrogatepass")
            for index in range(0, len(units), 2):
                char = chr(int.from_bytes(units[index : index + 2], "little"))
                self.output.send("SPACE" if char == " " else char)

    def dispatch(self, callback):
        try:
            callback()
            return True
        except (RuntimeError, OSError) as exc:
            self.cancel()
            self.status = str(exc)
            self.changed.emit()
            return False

    @Slot(str)
    def key(self, value):
        self.owner = None
        if value == "Shift":
            super().key(value)
            return
        if value in ("Ctrl", "Alt", "Win"):
            self.modifier(value)
            return
        if self.modifiers:
            mods = list(self.activeModifiers) + (["Shift"] if self.shift else [])
            self.invalidate()
            if self.output:
                self.dispatch(lambda: self.output.chord(value, mods))
            self.modifiers.clear()
            self.shift = False
            self.changed.emit()
            return
        named = (
            "Back",
            "Enter",
            "Tab",
            "Escape",
            "Left",
            "Right",
            "Up",
            "Down",
            "Home",
            "End",
            "Delete",
            "PageUp",
            "PageDown",
            "NumLock",
            "Add",
            "Subtract",
            "Multiply",
            "Divide",
            "Decimal",
        )
        if (
            value in named
            or value.startswith("F")
            and value[1:].isdigit()
            or value.startswith("Num")
        ):
            self.invalidate()
            if value == "Escape":
                self.hideRequested.emit()
                return
            if self.output:
                self.dispatch(
                    lambda: self.output.chord(value, ["Shift"] if self.shift else [])
                )
            self.shift = False
            if value == "Back":
                self.editor.backspace()
            else:
                self.editor.external("")
            self.changed.emit()
            return
        text = value.upper() if self.shift else value
        before = self.editor.text
        self.editor.insert(text)
        after = self.editor.text
        if after != before:

            def send():
                if before and not after.startswith(before) and self.output:
                    self.output.chord("Back", [])
                self.send_text(text)

            if not self.dispatch(send):
                self.editor.external(before)
        self.shift = False
        self.invalidate()
        self.changed.emit()

    @Slot(str)
    def secondary(self, letter):
        self.cancel()
        symbol = self.preferences["symbols"].get(letter, "")
        if symbol:
            self.key(symbol)

    @Slot(int, int, object, float)
    def receive(self, generation, revision, words, latency):
        if generation < 0:
            super().receive(generation, revision, words, latency)
            if generation == -1:
                self.status = (
                    "Middle-click to show or hide · Right-click a letter for its symbol"
                )
                self.changed.emit()
            return
        if generation != self.generation or revision != self.editor.revision:
            return
        before = self.snapshot()
        pending = getattr(self, "pending_field", None)
        if (
            self.output
            and pending
            and (
                not before
                or before["identity"] != pending["identity"]
                or before["prefix"] != pending["prefix"]
                or before.get("caret") != pending.get("caret")
            )
        ):
            self.cancel()
            return
        if before and before["password"]:
            self.cancel()
            return
        old = self.editor.text
        super().receive(generation, revision, words, latency)
        addition = self.editor.text[len(old) :]
        if addition and not self.dispatch(lambda: self.send_text(addition)):
            self.editor.external(old)
            return
        self.owner = None
        if before and before["prefix"] is not None:
            self.owner = dict(before, prefix=(before["prefix"] + addition)[-512:])
            self.owner["caret"] = before["caret"] + len(addition)
        elif self.output:
            self.candidates = []
            self.status = "Word entered. Alternatives unavailable in this text control."
        self.changed.emit()

    @Slot("QVariantList")
    def stroke(self, points):
        if getattr(self, "password", False):
            self.status = "Password field: use exact clicks; prediction is disabled."
            self.changed.emit()
            return
        self.pending_field = self.snapshot()
        super().stroke(points)

    @Slot(int)
    def alternative(self, index):
        if not 0 <= index < len(self.candidates):
            return
        current = self.snapshot()
        if self.output and (
            not self.owner
            or not current
            or current["identity"] != self.owner["identity"]
            or current["prefix"] != self.owner["prefix"]
            or current.get("caret") != self.owner.get("caret")
        ):
            self.owner = None
            self.invalidate()
            self.status = "Caret or field changed; alternatives cleared."
            self.changed.emit()
            return
        if self.editor.span is None:
            return
        start, end = self.editor.span
        old = self.editor.text[start:end]
        new = self.candidates[index] + " "
        if old.startswith(" "):
            new = " " + new

        def replace():
            if self.output:
                for _ in old:
                    self.output.chord("Back", [])
            self.send_text(new)

        if self.dispatch(replace):
            self.editor.replace(self.candidates[index])
            if self.owner:
                self.owner["prefix"] = (self.owner["prefix"][: -len(old)] + new)[-512:]
                self.owner["caret"] += len(new) - len(old)
        self.changed.emit()

    @Slot()
    def undoWord(self):
        if self.editor.span is None:
            return
        current = self.snapshot()
        if self.output and (
            not current
            or not self.owner
            or current["identity"] != self.owner["identity"]
            or current["prefix"] != self.owner["prefix"]
            or current.get("caret") != self.owner.get("caret")
        ):
            self.cancel()
            return
        start, end = self.editor.span
        if self.output:
            self.dispatch(
                lambda: [self.output.chord("Back", []) for _ in range(end - start)]
            )
        self.editor.undo()
        self.owner = None
        self.invalidate()
        self.changed.emit()

    @Slot(str)
    def hold(self, key):
        self.releaseHold()
        self.repeat_key = key
        self.repeating = False
        if key in ("Back", "Left", "Right", "Up", "Down"):
            self.key(key)
        if not self.modifiers:
            self.repeat_timer.start(int(self.preferences["repeatDelay"]))

    def repeat_tick(self):
        if not self.repeat_key:
            return
        self.repeating = True
        value = self.repeat_key.upper() if self.shift else self.repeat_key
        self.key(value)
        self.repeat_key = value
        self.repeat_timer.setInterval(int(self.preferences["repeatInterval"]))

    @Slot()
    def releaseHold(self):
        self.repeat_timer.stop()
        self.repeat_key = ""

    @Slot(int)
    def scrub(self, steps):
        self.releaseHold()
        for _ in range(abs(steps)):
            self.key("Right" if steps > 0 else "Left")

    @Slot()
    def cancel(self):
        if hasattr(self, "repeat_timer"):
            self.releaseHold()
        self.owner = None
        super().cancel()
        self.status = (
            "Middle-click to show or hide · Right-click a letter for its symbol"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--test-layout-report", type=Path)
    args = parser.parse_args()
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Mousyst")
    app.setWindowIcon(app_icon())
    palette = QPalette()
    for role, color in (
        (QPalette.Window, "#171719"),
        (QPalette.Base, "#25252b"),
        (QPalette.AlternateBase, "#202025"),
        (QPalette.Text, "#eeeeef"),
        (QPalette.WindowText, "#eeeeef"),
        (QPalette.Button, "#2c2c33"),
        (QPalette.ButtonText, "#eeeeef"),
        (QPalette.Highlight, "#666674"),
        (QPalette.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(
        str(
            Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
            / "mousyst-desktop.lock"
        )
    )
    if not args.smoke_test and not lock.tryLock(100):
        socket = QLocalSocket()
        socket.connectToServer("MousystDesktop")
        if socket.waitForConnected(300):
            socket.write(b"show")
            socket.waitForBytesWritten(300)
        return 0
    controller = DesktopController(args.smoke_test)
    if args.smoke_test:
        controller.settings.path = Path("build/desktop/smoke-settings.json")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("mousyst", controller)
    warnings = []
    engine.warnings.connect(
        lambda errors: warnings.extend(e.toString() for e in errors)
    )
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui/Desktop.qml")))
    if not engine.rootObjects():
        Path("build/desktop-errors.json").write_text(json.dumps(warnings))
        controller.executor.shutdown(wait=True)
        return 1
    window = engine.rootObjects()[0]
    activation = KeyboardActivationFilter(
        window, lambda: controller.output.target if controller.output else 0
    )
    app.installNativeEventFilter(activation)
    window.visibleChanged.connect(activation.apply)
    if args.test_layout_report:

        def report_layout():
            from PySide6.QtCore import QPointF
            from PySide6.QtQuick import QQuickItem

            board = window.findChild(QQuickItem, "desktopLetters")
            if not window.isVisible() or not board:
                return
            pitch = float(window.property("pitch"))
            point = board.mapToGlobal(QPointF(1.5 * pitch, 0.5 * pitch))
            args.test_layout_report.write_text(
                json.dumps({"q": [round(point.x()), round(point.y())]})
            )

        for signal in (
            window.visibleChanged,
            window.xChanged,
            window.yChanged,
            window.widthChanged,
            window.heightChanged,
        ):
            signal.connect(lambda: QTimer.singleShot(60, report_layout))

    def hide():
        controller.suppressed = controller.current_field
        controller.cancel()
        window.hide()

    def show(hwnd=None):
        if controller.output and not controller.output.capture(
            hwnd or int(__import__("desktop").user32.GetForegroundWindow())
        ):
            return
        field = controller.snapshot()
        controller.password = bool(field and field["password"])
        if field:
            controller.current_field = field["identity"]
        point = QCursor.pos()
        screen = QGuiApplication.screenAt(point) or app.primaryScreen()
        bounds = screen.availableGeometry()
        window.setPosition(
            QPoint(
                max(
                    bounds.left(),
                    min(
                        point.x() - window.width() // 2, bounds.right() - window.width()
                    ),
                ),
                max(
                    bounds.top(), min(point.y() + 20, bounds.bottom() - window.height())
                ),
            )
        )
        controller.editor.external("")
        controller.cancel()
        activation.apply()
        window.show()

    controller.hideRequested.connect(hide)
    server = QLocalServer()
    if not args.smoke_test:
        QLocalServer.removeServer("MousystDesktop")
        server.listen("MousystDesktop")

        def activate_existing():
            connection = server.nextPendingConnection()
            if connection:
                connection.disconnectFromServer()
            window.setProperty("settingsOpen", True)

        server.newConnection.connect(activate_existing)
    menu = QMenu()
    menu.addAction("Show keyboard", lambda: show())
    menu.addAction("Settings", lambda: window.setProperty("settingsOpen", True))
    menu.addAction("Quit", app.quit)
    tray = QSystemTrayIcon(app.windowIcon(), app)
    tray.setContextMenu(menu)
    tray.setToolTip("Mousyst · middle-click to type")
    tray.activated.connect(
        lambda reason: show() if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()
    hook = MiddleButtonHook()
    hook.toggled.connect(lambda hwnd: hide() if window.isVisible() else show(int(hwnd)))
    hook.failed.connect(
        lambda message: setattr(controller, "status", message)
        or controller.changed.emit()
    )
    if not args.smoke_test:

        hook.start()
        app.aboutToQuit.connect(hook.stop)
        app.aboutToQuit.connect(controller.observer.stop)
        guard = QTimer()
        guard.setInterval(100)
        guard.timeout.connect(
            lambda: (
                hide()
                if window.isVisible()
                and not window.property("settingsOpen")
                and controller.output.target
                and not controller.output.is_current()
                else None
            )
        )
        guard.start()
    else:
        window.show()

        def smoke():
            from PySide6.QtCore import QPointF, Qt
            from PySide6.QtQuick import QQuickItem
            from PySide6.QtTest import QTest

            from keyboard_layout import CENTERS

            folder = Path("build/desktop")
            folder.mkdir(parents=True, exist_ok=True)
            try:
                board = window.findChild(QQuickItem, "desktopLetters")
                x, y = CENTERS["q"]
                pitch = float(window.property("pitch"))
                point = board.mapToScene(QPointF((x + 1) * pitch, y * pitch)).toPoint()
                enter = window.findChild(QQuickItem, "desktopEnter")
                back = window.findChild(QQuickItem, "desktopBackspace")
                stable = (
                    board.mapToScene(QPointF(0, 0)),
                    enter.mapToScene(QPointF(0, 0)),
                    window.height(),
                )
                for words in (["hello"], ["hello", "help", "held"]):
                    controller.candidates = words
                    controller.changed.emit()
                    QTest.qWait(25)
                    assert (
                        board.mapToScene(QPointF(0, 0)),
                        enter.mapToScene(QPointF(0, 0)),
                        window.height(),
                    ) == stable, "Suggestions moved the keyboard"
                controller.editor.external("hello ")
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    back.mapToScene(
                        QPointF(back.width() / 2, back.height() / 2)
                    ).toPoint(),
                )
                QTest.qWait(25)
                assert not controller.candidates
                assert (
                    board.mapToScene(QPointF(0, 0)),
                    enter.mapToScene(QPointF(0, 0)),
                    window.height(),
                ) == stable, "Backspace moved Enter"
                controller.editor.external("")
                QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, point)
                for letter in "efve":
                    px, py = CENTERS[letter]
                    QTest.mouseMove(
                        window,
                        board.mapToScene(
                            QPointF((px + 1) * pitch, py * pitch)
                        ).toPoint(),
                        18,
                    )
                QTest.qWait(20)
                window.grabWindow().save(str(folder / "glide.png"))
                visible_points = board.property("visualPoints").toVariant()
                assert 1 < len(visible_points) <= 48, "Trail was not sampled or bounded"
                QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, point)
                controller.cancel()
                controller.editor.external("")
                QTest.qWait(300)
                assert not board.property(
                    "visualPoints"
                ).toVariant(), "Glide trail did not fade"
                QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point)
                assert controller.editor.text == "1", controller.editor.text
                QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
                assert controller.editor.text == "1q", controller.editor.text
                QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, point)
                QTest.qWait(570)
                QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, point)
                assert len(controller.editor.text) >= 4, controller.editor.text
                controller.cancel()
                toggle = window.findChild(QQuickItem, "numericLayerToggle")
                number_board = window.findChild(QQuickItem, "desktopNumbers")
                format_toggle = window.findChild(QQuickItem, "numberFormatToggle")

                def click_item(item):
                    QTest.mouseClick(
                        window,
                        Qt.LeftButton,
                        Qt.NoModifier,
                        item.mapToScene(
                            QPointF(item.width() / 2, item.height() / 2)
                        ).toPoint(),
                    )
                    QTest.qWait(25)

                fixed = (window.height(), toggle.mapToScene(QPointF(0, 0)))
                click_item(toggle)
                assert (
                    window.property("numbers")
                    and number_board.isVisible()
                    and not board.isVisible()
                )
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "Number layer expanded or moved controls"
                before = controller.editor.text
                digit_point = (
                    QPointF(4 * pitch, 1.875 * pitch)
                    if controller.preferences["numberFormat"] == "Numpad"
                    else QPointF(0.5 * pitch, 0.5 * pitch)
                )
                QTest.mouseClick(
                    window,
                    Qt.LeftButton,
                    Qt.NoModifier,
                    number_board.mapToScene(digit_point).toPoint(),
                )
                QTest.qWait(25)
                assert (
                    controller.editor.text == before + "1"
                ), "Number layer did not type digit"
                click_item(format_toggle)
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "Numpad switch expanded keyboard"
                click_item(toggle)
                assert (
                    not window.property("numbers")
                    and board.isVisible()
                    and not number_board.isVisible()
                )
                assert (
                    window.height(),
                    toggle.mapToScene(QPointF(0, 0)),
                ) == fixed, "ABC failed to restore same geometry"
                window.setProperty("numbers", True)
                for preset in ("Standard", "Full", "Compact"):
                    controller.settings.value = dict(
                        controller.preferences, layout=preset, numberFormat="Numpad"
                    )
                    controller.changed.emit()
                    QTest.qWait(20)
                window.grabWindow().save(str(folder / "keyboard.png"))
                window.setProperty("numbers", False)
                controller.settings.value = dict(controller.preferences)
                controller.changed.emit()
                QTest.qWait(30)
                window.grabWindow().save(str(folder / "keyboard-clean.png"))
                window.setProperty("settingsOpen", True)
                QTest.qWait(80)
                from PySide6.QtQuick import QQuickWindow

                settings_window = window.findChild(QQuickWindow, "desktopSettings")
                settings_window.grabWindow().save(str(folder / "settings.png"))
                window.setProperty("settingsOpen", False)
                (folder / "smoke.json").write_text(
                    json.dumps(
                        {
                            "ok": True,
                            "checks": [
                                "right-click symbol",
                                "click",
                                "hold repeat",
                                "three layouts",
                                "numpad",
                                "matching line icons",
                                "bounded crossing trail and fade-out",
                                "fixed suggestion area and Enter position after Backspace",
                                "ABC/numbers replace keys without expansion; digit entry; numpad switch",
                            ],
                        }
                    )
                )
                app.exit(0)
            except (AssertionError, AttributeError, RuntimeError) as exc:
                (folder / "smoke.json").write_text(
                    json.dumps({"ok": False, "error": str(exc)})
                )
                app.exit(1)

        QTimer.singleShot(1800, smoke)
    result = app.exec()
    controller.executor.shutdown(wait=True, cancel_futures=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
