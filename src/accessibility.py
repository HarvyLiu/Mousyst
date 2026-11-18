"""Event-driven Windows field discovery. COM calls run on one worker thread."""

import ctypes as ct
import os
from concurrent.futures import ThreadPoolExecutor

from comtypes import COMError
from PySide6.QtCore import QObject, Signal

from desktop import user32


def focused_input(api, uia):
    """Chromium popups can report their host pane as the global focus.

    Only descend inside that focused host, and only accept one genuinely focused
    input. Never pick a textbox simply because it is present in a window.
    """
    element = api.GetFocusedElement()
    if element.CurrentControlType not in (50032, 50033):
        return element
    condition = api.CreatePropertyCondition(uia.UIA_HasKeyboardFocusPropertyId, True)
    matches = element.FindAll(uia.TreeScope_Descendants, condition)
    inputs = []
    for index in range(matches.Length):
        candidate = matches.GetElement(index)
        if candidate.CurrentControlType in (50003, 50004):
            inputs.append(candidate)
    return inputs[0] if len(inputs) == 1 else element


class FocusObserver(QObject):
    focused = Signal(object)
    wake = Signal()

    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.api = None
        self.callback = None
        self.hook = None
        self.wake.connect(self.refresh)

    def snapshot(self):
        import comtypes
        from comtypes.client import CreateObject
        from comtypes.gen import UIAutomationClient as uia

        if self.api is None:
            comtypes.CoInitialize()
            self.api = CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
        element = focused_input(self.api, uia)
        if element.CurrentProcessId == os.getpid():
            return None
        identity = tuple(element.GetRuntimeId())
        password = bool(element.CurrentIsPassword)
        result = {
            "identity": identity,
            "password": password,
            "hwnd": int(user32.GetForegroundWindow()),
            "prefix": None,
            "caret": None,
            "editable": False,
        }
        if password:
            result["editable"] = True
            return result
        try:
            pattern = element.GetCurrentPattern(10002).QueryInterface(
                uia.IUIAutomationValuePattern
            )
            result["editable"] = not pattern.CurrentIsReadOnly
            value = pattern.CurrentValue
            native = int(element.CurrentNativeWindowHandle or 0)
            if native and "edit" in element.CurrentClassName.lower():
                selected = ct.c_size_t()
                user32.SendMessageTimeoutW.argtypes = [
                    ct.c_void_p,
                    ct.c_uint,
                    ct.c_size_t,
                    ct.c_ssize_t,
                    ct.c_uint,
                    ct.c_uint,
                    ct.POINTER(ct.c_size_t),
                ]
                user32.SendMessageTimeoutW.restype = ct.c_ssize_t
                if user32.SendMessageTimeoutW(
                    native, 0xB0, 0, 0, 2, 100, ct.byref(selected)
                ):
                    start, end = (
                        selected.value & 0xFFFF,
                        (selected.value >> 16) & 0xFFFF,
                    )
                    if start == end and start != 65535 and start <= len(value):
                        result["prefix"] = value[:start][-512:]
                        result["caret"] = start
        except (comtypes.COMError, ValueError, AttributeError):
            result["editable"] = element.CurrentControlType in (50004, 50030) and bool(
                element.CurrentIsKeyboardFocusable
            )
        try:
            pattern = element.GetCurrentPattern(10014).QueryInterface(
                uia.IUIAutomationTextPattern
            )
            ranges = pattern.GetSelection()
            if ranges.Length == 1:
                selected = ranges.GetElement(0)
                if selected.CompareEndpoints(0, selected, 1) == 0:
                    prefix = pattern.DocumentRange.Clone()
                    prefix.MoveEndpointByRange(1, selected, 0)
                    content = prefix.GetText(-1)
                    result["prefix"] = content[-512:]
                    result["caret"] = len(content)
        except (comtypes.COMError, ValueError, AttributeError):
            pass
        return result

    def read(self):
        try:
            return self.snapshot()
        except (OSError, ValueError, TypeError, AttributeError, RuntimeError, COMError):
            return None

    def verify(self):
        try:
            return self.executor.submit(self.read).result(timeout=0.25)
        except TimeoutError:
            return None

    def refresh(self):
        self.executor.submit(lambda: self.focused.emit(self.read()))

    def start(self):
        callback_type = ct.WINFUNCTYPE(
            None,
            ct.c_void_p,
            ct.c_ulong,
            ct.c_void_p,
            ct.c_long,
            ct.c_long,
            ct.c_ulong,
            ct.c_ulong,
        )
        self.callback = callback_type(lambda *args: self.wake.emit())
        user32.SetWinEventHook.restype = ct.c_void_p
        user32.SetWinEventHook.argtypes = [
            ct.c_ulong,
            ct.c_ulong,
            ct.c_void_p,
            callback_type,
            ct.c_ulong,
            ct.c_ulong,
            ct.c_ulong,
        ]
        self.hook = user32.SetWinEventHook(0x8005, 0x8005, None, self.callback, 0, 0, 2)
        self.refresh()

    def stop(self):
        if self.hook:
            user32.UnhookWinEvent.argtypes = [ct.c_void_p]
            user32.UnhookWinEvent(self.hook)
        self.executor.shutdown(wait=False, cancel_futures=True)
