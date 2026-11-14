"""Focus resolution for browser popups; no user applications or text are read."""

import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from accessibility import focused_input


def resolve(types, host_type=50033):
    children = [NS(CurrentControlType=t) for t in types]
    matches = NS(Length=len(children), GetElement=lambda i: children[i])
    host = NS(CurrentControlType=host_type, FindAll=lambda scope, condition: matches)
    api = NS(GetFocusedElement=lambda: host, CreatePropertyCondition=lambda *args: args)
    constants = NS(UIA_HasKeyboardFocusPropertyId=30008, TreeScope_Descendants=4)
    return focused_input(api, constants), host, children


def test_extension_popup_resolves_unique_focused_input():
    resolved, _, children = resolve([50030, 50004])
    assert resolved is children[1]


def test_does_not_guess_between_multiple_focused_inputs():
    resolved, host, _ = resolve([50004, 50004])
    assert resolved is host


def test_does_not_choose_an_unfocused_textbox_or_document():
    resolved, host, _ = resolve([50030])
    assert resolved is host


def test_regular_focused_input_does_not_search_children():
    resolved, host, _ = resolve([50004], host_type=50004)
    assert resolved is host
