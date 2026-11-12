"""Native non-activating keyboard surface; settings remain a normal window."""

import ctypes as ct
from ctypes import wintypes as wt

from PySide6.QtCore import QAbstractNativeEventFilter

from desktop import user32


class KeyboardActivationFilter(QAbstractNativeEventFilter):
    def __init__(self, window, target=lambda: 0):
        super().__init__()
        self.window = window
        self.hwnd = 0
        self.target = target

    def nativeEventFilter(self, event_type, message):
        msg = wt.MSG.from_address(int(message))
        if msg.hWnd == self.hwnd and msg.message == 0x21:
            return True, 3
        if msg.hWnd == self.hwnd and (
            msg.message == 7 or msg.message == 6 and (msg.wParam & 0xFFFF) != 0
        ):
            target = self.target()
            if target and user32.IsWindow(target):
                user32.SetForegroundWindow.argtypes = [wt.HWND]
                user32.SetForegroundWindow(target)
        return False, 0

    def apply(self):
        hwnd = int(self.window.winId())
        self.hwnd = hwnd
        user32.GetWindowLongPtrW.argtypes = [wt.HWND, ct.c_int]
        user32.GetWindowLongPtrW.restype = ct.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [wt.HWND, ct.c_int, ct.c_ssize_t]
        user32.SetWindowLongPtrW.restype = ct.c_ssize_t
        style = user32.GetWindowLongPtrW(hwnd, -20)
        user32.SetWindowLongPtrW(hwnd, -20, style | 0x08000000 | 0x80)
