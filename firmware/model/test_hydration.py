"""pytest for the hydration state machine (deterministic 10 Hz traces)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from hydration import Config, EventType, HydrationTracker, Mode

DT = 0.1


def run(tracker, segments):
    """segments: list of (weight_g, duration_s). Returns events."""
    events = []
    t = 0.0
    for weight, dur in segments:
        for _ in range(int(round(dur / DT))):
            events += tracker.feed(weight, round(t, 3))
            t += DT
    return events


def types(events):
    return [e.type for e in events]


def test_cup_place_sip_and_progress():
    tr = HydrationTracker(Config())
    ev = run(tr, [(600, 3)])                       # cup 300 + 300 g water
    assert EventType.CUP_PLACED in types(ev)
    assert tr.mode is Mode.HYDRATION
    ev = run(tr, [(600, 1)])                       # idle
    assert EventType.SIP not in types(ev)
    run(tr, [(0, 3), (550, 3)])                    # lift, drink 50, put back
    sip = [e for e in tr.events if e.type is EventType.SIP]
    assert len(sip) == 1 and abs(sip[0].value - 50) < 0.5
    assert abs(tr.today_ml - 50) < 0.5
    assert abs(tr.progress - 50 / 2200) < 1e-6


def test_refill_is_not_intake():
    tr = HydrationTracker(Config())
    run(tr, [(600, 3), (0, 3), (700, 3)])
    assert tr.today_ml == 0
    assert any(e.type is EventType.REFILL for e in tr.events)
    assert not any(e.type is EventType.SIP for e in tr.events)


def test_noise_does_not_trigger():
    tr = HydrationTracker(Config())
    run(tr, [(600, 3)])
    noise = [(300 + (1 if i % 2 else -1), 5) for i in range(1)]
    # 300 +/- 1 g, alternating, for 10 s
    t = 3.0
    ev = []
    for i in range(100):
        ev += tr.feed(600 + (1 if i % 2 else -1), round(t, 3))
        t += DT
    assert not any(e.type in (EventType.SIP, EventType.REFILL) for e in ev)
    assert tr.today_ml == 0


def test_single_spike_rejected():
    tr = HydrationTracker(Config())
    run(tr, [(600, 3)])
    ev = tr.feed(1100, 4.0)                 # one bad sample
    assert ev == [] or all(e.type is not EventType.SIP for e in ev)
    run(tr, [(600, 2)])
    assert tr.today_ml == 0


def test_foreign_object_switches_to_scale_and_back():
    tr = HydrationTracker(Config())
    run(tr, [(600, 3)])
    ev = run(tr, [(2000, 3)])              # above cup+water range
    assert tr.mode is Mode.SCALE
    assert any(e.type is EventType.MODE_CHANGE and e.detail == "SCALE" for e in ev)
    ev = run(tr, [(600, 3)])
    assert tr.mode is Mode.HYDRATION


def test_reminder_fires_after_interval_and_resets_on_sip():
    cfg = Config(reminder_min=60)
    tr = HydrationTracker(cfg)
    run(tr, [(600, 3)])
    ev = run(tr, [(600, 3700)])            # > 60 min with no drink
    assert any(e.type is EventType.REMINDER_DUE for e in ev)
    run(tr, [(0, 2), (550, 3)])            # sip 50 resets the clock
    ev = run(tr, [(550, 100)])
    assert not any(e.type is EventType.REMINDER_DUE for e in ev)


def test_cup_tare_setup():
    tr = HydrationTracker(Config(cup_tare_g=250))
    tr.tare_cup(250)
    run(tr, [(500, 3), (0, 2), (450, 3)])
    sip = [e for e in tr.events if e.type is EventType.SIP]
    assert len(sip) == 1 and abs(sip[0].value - 50) < 0.5
