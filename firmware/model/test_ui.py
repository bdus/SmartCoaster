import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hydration import Config, EventType, HydrationTracker, Mode
from ui import UiController, View

DT = 0.1


def feed(tr, ui, weight, seconds, t):
    evs = []
    for _ in range(int(seconds / DT)):
        e = tr.feed(weight, round(t, 3))
        ui.on_events(e, t)
        evs += e
        t += DT
    return evs, t


def test_single_click_toggles_view_and_snoozes():
    tr = HydrationTracker(Config())
    ui = UiController(tr)
    assert ui.click(0) == "toggle_view"
    assert ui.view is View.WEIGHT
    assert ui.click(1) == "toggle_view"
    assert ui.view is View.PROGRESS
    ui.reminder_until = 100
    assert ui.click(50) == "snooze"
    assert ui.reminder_until == 0


def test_double_click_manual_scale_and_timeout():
    tr = HydrationTracker(Config())
    ui = UiController(tr)
    _, t = feed(tr, ui, 600, 3, 0.0)          # cup present, auto HYDRATION
    assert tr.mode is Mode.HYDRATION
    assert ui.double_click(t) == "manual_scale"
    assert ui.effective_mode(t) is Mode.SCALE
    assert ui.effective_mode(t + 599) is Mode.SCALE
    assert ui.effective_mode(t + 601) is Mode.HYDRATION   # timeout -> auto
    ui.double_click(t + 700)
    assert ui.effective_mode(t + 700) is Mode.SCALE
    ui.double_click(t + 701)                  # toggle back
    assert ui.effective_mode(t + 701) is Mode.HYDRATION


def test_cup_action_releases_manual_mode():
    tr = HydrationTracker(Config())
    ui = UiController(tr)
    _, t = feed(tr, ui, 600, 3, 0.0)
    ui.double_click(t)
    assert ui.effective_mode(t) is Mode.SCALE
    _, t = feed(tr, ui, 0, 3, t)              # cup removed
    assert ui.manual_mode is None
    assert ui.effective_mode(t) is Mode.EMPTY


def test_long_press_actions():
    tr = HydrationTracker(Config())
    ui = UiController(tr)
    _, t = feed(tr, ui, 600, 3, 0.0)
    assert ui.long_2s(t) == "cup_setup"
    assert ui.long_5s(t) == "pairing" and ui.pairing
    ui.double_click(t)
    assert ui.long_2s(t) == "tare"
