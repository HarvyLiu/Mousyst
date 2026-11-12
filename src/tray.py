"""System tray controls and a temporary Mousyst monogram icon."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def app_icon() -> QIcon:
    """Draw a crisp placeholder icon at multiple display sizes."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64):
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#050505"))
        painter.drawRoundedRect(0, 0, size, size, size / 3, size / 3)
        font = QFont("Monotype Corsiva")
        font.setPixelSize(round(size * 0.78))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            0, -round(size * 0.08), size, size, Qt.AlignmentFlag.AlignCenter, "M"
        )
        painter.end()
        icon.addPixmap(image)
    return icon


class TrayControls:
    """Keep the app reachable when its panel is hidden."""

    def __init__(
        self, app: QApplication, panel: QQuickWindow, keyboard: QQuickWindow
    ) -> None:
        self.app = app
        self.panel = panel
        self.keyboard = keyboard
        self.menu = QMenu()
        self.show_action = self.menu.addAction("Show Mousyst")
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction("Quit Mousyst")
        self.show_action.triggered.connect(self.show_panel)
        self.quit_action.triggered.connect(self.quit)
        self.icon = QSystemTrayIcon(app.windowIcon(), app)
        self.icon.setToolTip("Mousyst · Middle-click to type")
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self.activated)
        app.aboutToQuit.connect(self.icon.hide)
        self.icon.show()

    def show_panel(self) -> None:
        """Bring the panel back through a tray click or menu action."""
        self.keyboard.hide()
        self.panel.showNormal()
        self.panel.raise_()
        self.panel.requestActivate()

    def activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Open the panel on a primary click, leaving right-click for the menu."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_panel()

    def quit(self) -> None:
        """Exit completely, including the global mouse hook."""
        self.keyboard.hide()
        self.icon.hide()
        self.app.quit()
