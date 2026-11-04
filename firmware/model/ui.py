"""UI layer: button gestures + view + manual mode override on top of HydrationTracker."""
from __future__ import annotations

from enum import Enum

from hydration import EventType, Mode


class View(str, Enum):
    PROGRESS = "progress"
    WEIGHT = "weight"


class UiController:
    def __init__(self, tracker):
        self.tr = tracker
        self.view = View.PROGRESS
        self.manual_mode: Mode | None = None
        self.manual_until = 0.0
        self.reminder_until = 0.0
        self.pairing = False

    def effective_mode(self, t: float) -> Mode:
        if self.manual_mode is not None and t < self.manual_until:
            return self.manual_mode
        return self.tr.mode

    def on_events(self, events, t: float) -> None:
        for ev in events:
            if ev.type is EventType.REMINDER_DUE:
                self.reminder_until = t + 8.0
            if ev.type in (EventType.CUP_PLACED, EventType.CUP_REMOVED):
                # a real cup action always releases a manual override
                self.manual_mode = None
                self.manual_until = 0.0

    def click(self, t: float) -> str:
        if t < self.reminder_until:
            self.reminder_until = 0.0
            return "snooze"
        self.view = View.WEIGHT if self.view is View.PROGRESS else View.PROGRESS
        return "toggle_view"

    def double_click(self, t: float) -> str:
        if self.effective_mode(t) is Mode.SCALE:
            self.manual_mode = None
            self.manual_until = 0.0
            return "auto_mode"
        self.manual_mode = Mode.SCALE
        self.manual_until = t + 600.0
        return "manual_scale"

    def long_2s(self, t: float) -> str:
        return "tare" if self.effective_mode(t) is Mode.SCALE else "cup_setup"

    def long_5s(self, t: float) -> str:
        self.pairing = True
        return "pairing"
