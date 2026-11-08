"""Windows input dispatch and a minimal middle-button hook."""

from __future__ import annotations

import ctypes as ct
import os
import threading
from ctypes import wintypes as wt

from PySide6.QtCore import QObject, Signal

user32 = ct.WinDLL("user32", use_last_error=True)
kernel32 = ct.WinDLL("kernel32", use_last_error=True)
ULONG_PTR = ct.c_size_t
LRESULT = ct.c_ssize_t
HOOKPROC = ct.WINFUNCTYPE(LRESULT, ct.c_int, wt.WPARAM, wt.LPARAM)


class KeyboardInput(ct.Structure):
    """Native KEYBDINPUT with pointer-sized extra information."""

    _fields_ = [
        ("vk", wt.WORD),
        ("scan", wt.WORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("extra", ULONG_PTR),
    ]


class MouseInput(ct.Structure):
    """Native MOUSEINPUT, also sets INPUT union alignment and size."""

    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("data", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("extra", ULONG_PTR),
    ]


class InputUnion(ct.Union):
    """Input payload union."""

    _fields_ = [("ki", KeyboardInput), ("mi", MouseInput)]


class Input(ct.Structure):
    """Native INPUT structure for SendInput."""

    _fields_ = [("type", wt.DWORD), ("payload", InputUnion)]


user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
user32.IsWindow.argtypes = [wt.HWND]
user32.SendInput.argtypes = [wt.UINT, ct.POINTER(Input), ct.c_int]
user32.SendInput.restype = wt.UINT
user32.GetAsyncKeyState.argtypes = [ct.c_int]
user32.GetAsyncKeyState.restype = wt.SHORT
user32.SetWindowsHookExW.argtypes = [ct.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ct.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.GetMessageW.argtypes = [ct.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.PeekMessageW.argtypes = [ct.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HMODULE
kernel32.GetCurrentThreadId.restype = wt.DWORD


class DesktopInput:
    """Send only to the foreground window explicitly selected at activation."""

    def __init__(self) -> None:
        self.target = 0

    def capture(self, hwnd: int) -> bool:
        """Reject this application's windows and invalid targets."""
        process = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ct.byref(process))
        self.target = hwnd if process.value not in (0, os.getpid()) else 0
        return bool(self.target and user32.IsWindow(self.target))

    def is_current(self) -> bool:
        """Avoid redirecting a gesture when the foreground app changes."""
        return bool(
            self.target
            and user32.IsWindow(self.target)
            and user32.GetForegroundWindow() == self.target
        )

    def send(self, action: str) -> None:
        """Inject a character or backspace, never using the clipboard."""
        if not self.is_current():
            raise RuntimeError(
                "Target changed. Middle-click in the text field to resume."
            )
        if any(
            user32.GetAsyncKeyState(key) & 0x8000
            for key in (0x10, 0x11, 0x12, 0x5B, 0x5C)
        ):
            raise RuntimeError(
                "Release Shift, Ctrl, Alt and Windows keys before typing."
            )
        char = " " if action == "SPACE" else action
        vk, scan, flags = (8, 0, 0) if action == "BACK" else (0, ord(char), 4)
        events = (Input * 2)(
            Input(1, InputUnion(ki=KeyboardInput(vk, scan, flags, 0, 0))),
            Input(1, InputUnion(ki=KeyboardInput(vk, scan, flags | 2, 0, 0))),
        )
        if user32.SendInput(2, events, ct.sizeof(Input)) != 2:
            raise RuntimeError(
                "Windows blocked typing. Elevated apps may require matching permissions."
            )


class MiddleButtonHook(QObject):
    """Capture middle clicks on a dedicated message-loop thread."""

    toggled = Signal(object)
    moved = Signal(int, int)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.thread_id = 0
        self.track_motion = False
        self.worker_thread = threading.Thread(
            target=self.run, name="Mousyst mouse hook", daemon=True
        )

    def start(self) -> None:
        """Start listening; only middle-button events are consumed."""
        self.worker_thread.start()

    def run(self) -> None:
        """Keep the native callback alive until WM_QUIT and always unhook."""
        message = wt.MSG()
        user32.PeekMessageW(ct.byref(message), None, 0, 0, 0)
        self.thread_id = kernel32.GetCurrentThreadId()
        pressed = False

        def callback(code: int, event: int, data: int) -> int:
            nonlocal pressed
            if code >= 0 and event == 0x200 and self.track_motion:
                position = ct.cast(data, ct.POINTER(wt.POINT)).contents
                self.moved.emit(position.x, position.y)
            if code >= 0 and event == 0x207:
                pressed = True
                return 1
            if code >= 0 and event == 0x208 and pressed:
                pressed = False
                self.toggled.emit(int(user32.GetForegroundWindow() or 0))
                return 1
            return int(user32.CallNextHookEx(None, code, event, data))

        callback_pointer = HOOKPROC(callback)
        hook = user32.SetWindowsHookExW(
            14, callback_pointer, kernel32.GetModuleHandleW(None), 0
        )
        if not hook:
            self.failed.emit(
                "Could not register middle-click. Restart Mousyst to try again."
            )
            return
        try:
            while user32.GetMessageW(ct.byref(message), None, 0, 0) > 0:
                user32.TranslateMessage(ct.byref(message))
                user32.DispatchMessageW(ct.byref(message))
        finally:
            user32.UnhookWindowsHookEx(hook)

    def stop(self) -> None:
        """Release the hook and restore ordinary middle-click behavior."""
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
            self.worker_thread.join(timeout=2)
