"""
Reference model of the SmartCoaster hydration state machine.

Pure Python (no hardware deps) so it can be tested deterministically and
ported 1:1 to C/ESP-IDF. The key behaviour under test is the *weight-driven*
switching between HYDRATION and SCALE and the filtering of drinking deltas.

Run the tests:
    /data/Documents/tools/sim-venv/bin/pytest firmware/model -q
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from statistics import median


class Mode(str, Enum):
    EMPTY = "EMPTY"
    HYDRATION = "HYDRATION"
    SCALE = "SCALE"


class EventType(str, Enum):
    CUP_PLACED = "cup_placed"
    CUP_REMOVED = "cup_removed"
    SIP = "sip"
    REFILL = "refill"
    MODE_CHANGE = "mode_change"
    REMINDER_DUE = "reminder_due"
    TARE = "tare"


@dataclass
class Config:
    cup_tare_g: float = 300.0          # configured empty cup
    cup_max_water_g: float = 1500.0    # cup + max water
    cup_tolerance_g: float = 5.0
    empty_threshold_g: float = 30.0
    sip_threshold_g: float = 10.0
    goal_ml: float = 2200.0
    reminder_min: float = 60.0
    sample_dt_s: float = 0.1
    filter_n: int = 5                  # median window (raw samples)
    stable_window_s: float = 0.3       # stability window
    stable_range_g: float = 2.0
    spike_g: float = 40.0              # reject a raw sample this far from median
    reminder_cooldown_s: float = 600.0


@dataclass
class Event:
    type: EventType
    t: float
    value: float = 0.0
    detail: str = ""


class WeightFilter:
    """Median-of-N (spike rejection) + short stability window."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.raw: deque[float] = deque(maxlen=cfg.filter_n)
        n = max(3, int(round(cfg.stable_window_s / cfg.sample_dt_s)))
        self.filt: deque[float] = deque(maxlen=n)

    def push(self, w: float) -> float:
        self.raw.append(w)
        m = median(self.raw)
        self.filt.append(m)
        return m

    def stable(self) -> bool:
        if len(self.filt) < self.filt.maxlen:
            return False
        return (max(self.filt) - min(self.filt)) <= self.cfg.stable_range_g

    def reset(self) -> None:
        self.raw.clear()
        self.filt.clear()


class HydrationTracker:
    """Weight-driven mode/state machine. Feed one sample at a time."""

    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or Config()
        self.filter = WeightFilter(self.cfg)
        self.mode = Mode.EMPTY
        self.cup_present = False
        self.last_weight: float | None = None
        self.last_stable = 0.0
        self.today_ml = 0.0
        self.last_drink_t = 0.0
        self.last_reminder_t = -1e9
        self.last_event_t = 0.0
        self.events: list[Event] = []

    # ------------------------------------------------------------------ utils
    @property
    def progress(self) -> float:
        if self.cfg.goal_ml <= 0:
            return 0.0
        return min(1.0, self.today_ml / self.cfg.goal_ml)

    def _emit(self, ev: Event) -> None:
        self.events.append(ev)
        self.last_event_t = ev.t

    def tare_cup(self, empty_weight_g: float) -> None:
        """Called by the app / long-press setup with an empty cup on the pad."""
        self.cfg.cup_tare_g = empty_weight_g
        self._emit(Event(EventType.TARE, self.last_event_t, empty_weight_g))

    def reset_day(self, t: float) -> None:
        self.today_ml = 0.0
        self.last_drink_t = t
        self.last_reminder_t = -1e9

    # ------------------------------------------------------------------- feed
    def feed(self, raw_weight_g: float, t: float) -> list[Event]:
        out: list[Event] = []
        w = self.filter.push(raw_weight_g)

        if abs(raw_weight_g - w) > self.cfg.spike_g:
            return out
        if not self.filter.stable():
            return out

        cfg = self.cfg
        if w < cfg.empty_threshold_g:
            if self.cup_present:
                self.cup_present = False
                self.mode = Mode.EMPTY
                self.last_weight = self.last_stable
                out.append(Event(EventType.CUP_REMOVED, t, self.last_stable))
            else:
                self.mode = Mode.EMPTY
            self.last_stable = w
        else:
            in_cup_range = (
                cfg.cup_tare_g - cfg.cup_tolerance_g
                <= w
                <= cfg.cup_tare_g + cfg.cup_max_water_g
            )
            if in_cup_range:
                if not self.cup_present:
                    self.cup_present = True
                    self.mode = Mode.HYDRATION
                    if self.last_weight is not None:
                        delta = self.last_weight - w
                        if delta >= cfg.sip_threshold_g:
                            self.today_ml += delta
                            self.last_drink_t = t
                            out.append(Event(EventType.SIP, t, delta))
                        elif -delta >= cfg.sip_threshold_g:
                            out.append(Event(EventType.REFILL, t, -delta))
                    self.last_weight = w
                    out.append(Event(EventType.CUP_PLACED, t, w))
                else:
                    self.last_weight = w
                self.mode = Mode.HYDRATION
                self.last_stable = w
            else:
                if self.mode != Mode.SCALE:
                    self.mode = Mode.SCALE
                    self.cup_present = False
                    out.append(Event(EventType.MODE_CHANGE, t, w, "SCALE"))
                self.last_stable = w

        self._emit_reminder(t, out)
        for ev in out:
            self._emit(ev)
        return out

    def _emit_reminder(self, t: float, out: list[Event]) -> None:
        cfg = self.cfg
        if self.today_ml >= cfg.goal_ml:
            return
        if t - self.last_drink_t < cfg.reminder_min * 60:
            return
        if t - self.last_reminder_t < cfg.reminder_cooldown_s:
            return
        self.last_reminder_t = t
        out.append(Event(EventType.REMINDER_DUE, t, self.progress, "behind"))
