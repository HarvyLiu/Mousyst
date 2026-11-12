"""Disposable standard Win32 Edit control for accessibility/input integration."""

import ctypes as ct
import json
import sys
import tkinter as tk
from pathlib import Path

root = tk.Tk()
root.title("Mousyst disposable input test")
root.geometry("600x300")
root.update()
api = ct.windll.user32
api.CreateWindowExW.argtypes = [
    ct.c_ulong,
    ct.c_wchar_p,
    ct.c_wchar_p,
    ct.c_ulong,
    ct.c_int,
    ct.c_int,
    ct.c_int,
    ct.c_int,
    ct.c_void_p,
    ct.c_void_p,
    ct.c_void_p,
    ct.c_void_p,
]
api.CreateWindowExW.restype = ct.c_void_p
api.SetFocus.argtypes = [ct.c_void_p]
api.GetWindowTextLengthW.argtypes = [ct.c_void_p]
api.GetWindowTextW.argtypes = [ct.c_void_p, ct.c_wchar_p, ct.c_int]
edit = api.CreateWindowExW(
    0, "EDIT", "", 0x50000004, 0, 0, 580, 280, root.winfo_id(), None, None, None
)
assert edit


def snapshot():
    text = ct.create_unicode_buffer(api.GetWindowTextLengthW(edit) + 1)
    api.GetWindowTextW(edit, text, len(text))
    Path(sys.argv[1]).write_text(json.dumps(text.value))
    root.after(50, snapshot)


root.after(150, root.focus_force)
root.after(250, lambda: api.SetFocus(edit))
snapshot()
root.mainloop()
