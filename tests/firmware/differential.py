#!/usr/bin/env python3
"""
differential.py — replay identical command traces through

  * the authoritative Python model (firmware/model/hydration.py + ui.py), and
  * the C port (firmware/esp32/main/hydration.c + ui.c, via host_core_cli),

and require byte-level agreement on every event / UI action / state readout.

The first 11 scenarios mirror the 11 pytest cases one-to-one (including the
reference helper's quirk that `run()` restarts t at 0 on every call).  Extra
scenarios add long random-walk / threshold / reminder-cooldown traces.

Usage:
    PYTHONPATH= /data/Documents/tools/sim-venv/bin/python tests/firmware/differential.py
Exit code 0 = C and Python agree on every record.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "firmware" / "model"
CORE_DIR = ROOT / "firmware" / "esp32" / "main"
sys.path.insert(0, str(MODEL_DIR))

from hydration import Config, EventType, HydrationTracker, Mode  # noqa: E402
from ui import UiController, View  # noqa: E402

DT = 0.1
TOL = 1e-6


# --------------------------------------------------------------------------
# Trace builders
# --------------------------------------------------------------------------
def segments(segs, t0=0.0):
    """Mirror of test_hydration.run(): list of (weight, duration) -> F commands."""
    cmds = []
    t = t0
    for weight, duration in segs:
        for _ in range(int(round(duration / DT))):
            cmds.append(("F", float(weight), round(t, 3)))
            t += DT
    return cmds


def scenario_cup_place_sip():
    return (
        segments([(600, 3)])
        + segments([(600, 1)])
        + segments([(0, 3), (550, 3)])
        + [("S",)]
    )


def scenario_refill():
    return segments([(600, 3), (0, 3), (700, 3)]) + [("S",)]


def scenario_noise():
    cmds = segments([(600, 3)])
    t = 3.0
    for i in range(100):
        cmds.append(("F", 600.0 + (1.0 if i % 2 else -1.0), round(t, 3)))
        t += DT
    return cmds + [("S",)]


def scenario_spike():
    return segments([(600, 3)]) + [("F", 1100.0, 4.0)] + segments([(600, 2)]) + [("S",)]


def scenario_foreign():
    return (
        segments([(600, 3)])
        + segments([(2000, 3)])
        + segments([(600, 3)])
        + [("S",)]
    )


def scenario_reminder():
    return (
        segments([(600, 3)])
        + segments([(600, 3700)])
        + segments([(0, 2), (550, 3)])
        + segments([(550, 100)])
        + [("S",)]
    )


def scenario_tare():
    return [("T", 250.0)] + segments([(500, 3), (0, 2), (450, 3)]) + [("S",)]


def scenario_clicks():
    # test_single_click_toggles_view_and_snoozes (reminder_until set via the
    # host-only Z hook, mirroring the direct attribute write in test_ui.py).
    return [("C", 0.0), ("Q", 0.0), ("C", 1.0), ("Q", 1.0), ("Z", 100.0), ("C", 50.0), ("Q", 50.0)]


def scenario_double_click():
    cmds = segments([(600, 3)])  # t ends at 3.0
    t = 3.0
    cmds += [("D", t), ("Q", t), ("Q", t + 599.0), ("Q", t + 601.0)]
    cmds += [("D", t + 700.0), ("Q", t + 700.0), ("D", t + 701.0), ("Q", t + 701.0)]
    return cmds + [("S",)]


def scenario_manual_release():
    cmds = segments([(600, 3)])
    t = 3.0
    cmds += [("D", t), ("Q", t)]
    cmds += segments([(0, 3)], t0=t)
    t += 3.0
    return cmds + [("Q", t), ("S",)]


def scenario_long_press():
    cmds = segments([(600, 3)])
    t = 3.0
    cmds += [("L2", t), ("L5", t), ("Q", t), ("D", t), ("L2", t), ("S",)]
    return cmds


def scenario_random_walk():
    """Continuous 10 Hz trace with jitter, lifts, sips, refills and a foreign object."""
    cmds = []
    t = 0.0

    def feed(weight, n=1):
        nonlocal t
        for _ in range(n):
            cmds.append(("F", float(weight), round(t, 3)))
            t += DT

    def seg(weight, duration):
        feed(weight, int(round(duration / DT)))

    def jitter(base, duration):
        n = int(round(duration / DT))
        for i in range(n):
            feed(base + (1.0 if i % 2 else -1.0))

    seg(600, 3)
    jitter(600, 120)
    seg(0, 1)          # lift
    seg(0, 20)         # empty
    seg(550, 10)       # sip 50
    seg(550, 30)
    seg(2000, 5)       # foreign object -> SCALE
    seg(550, 5)        # back to HYDRATION
    seg(0, 1)          # lift
    seg(700, 5)        # refill 150
    jitter(700, 900)   # idle until reminder
    cmds.append(("S",))
    return cmds


def scenario_thresholds():
    """Values around every comparison boundary in feed()."""
    cmds = []
    t = 0.0
    for weight in [0, 29.9, 30.0, 29.99, 295.0, 294.99, 300.0, 1800.0, 1800.01, 2000.0, 0.0, 400.0]:
        for _ in range(10):  # 1 s each
            cmds.append(("F", float(weight), round(t, 3)))
            t += DT
    cmds.append(("S",))
    return cmds


def scenario_reminder_cooldown():
    cmds = segments([(600, 3)]) + segments([(600, 1300)]) + [("S",)]
    return cmds


def scenario_spike_burst():
    cmds = segments([(600, 3)])
    spikes = [1100.0, 500.0, 1300.0, 100.0, 900.0, 600.0, 600.0, 600.0]
    for spike in spikes:
        cmds.append(("F", spike, 4.0))
    cmds += segments([(600, 5)]) + [("S",)]
    return cmds


def scenario_tare_reset():
    return (
        [("T", 250.0)]
        + segments([(500, 3)])
        + [("R", 5.0)]
        + segments([(450, 3)])
        + [("S",)]
    )


SCENARIOS = [
    # --- the 11 pytest cases ------------------------------------------------
    ("py01_cup_place_sip_and_progress", scenario_cup_place_sip),
    ("py02_refill_is_not_intake", scenario_refill),
    ("py03_noise_does_not_trigger", scenario_noise),
    ("py04_single_spike_rejected", scenario_spike),
    ("py05_foreign_object_scale", scenario_foreign),
    ("py06_reminder_and_reset", scenario_reminder),
    ("py07_cup_tare_setup", scenario_tare),
    ("py08_single_click", scenario_clicks),
    ("py09_double_click_manual_scale", scenario_double_click),
    ("py10_cup_action_releases_manual", scenario_manual_release),
    ("py11_long_press_actions", scenario_long_press),
    # --- extra parity traces ------------------------------------------------
    ("x01_random_walk", scenario_random_walk),
    ("x02_thresholds", scenario_thresholds),
    ("x03_reminder_cooldown", scenario_reminder_cooldown),
    ("x04_spike_burst", scenario_spike_burst),
    ("x05_tare_reset", scenario_tare_reset),
]


# --------------------------------------------------------------------------
# Expected output from the Python reference model
# --------------------------------------------------------------------------
def execute_python(cmds):
    tr = HydrationTracker(Config())
    ui = UiController(tr)
    out = []

    for cmd in cmds:
        kind = cmd[0]
        if kind == "F":
            _, weight, t = cmd
            events = tr.feed(weight, t)
            ui.on_events(events, t)
            for ev in events:
                out.append(("EV", ev.type.value, ev.t, ev.value, ev.detail))
        elif kind == "T":
            tr.tare_cup(cmd[1])
        elif kind == "R":
            tr.reset_day(cmd[1])
        elif kind == "C":
            out.append(("ACT", ui.click(cmd[1])))
        elif kind == "D":
            out.append(("ACT", ui.double_click(cmd[1])))
        elif kind == "L2":
            out.append(("ACT", ui.long_2s(cmd[1])))
        elif kind == "L5":
            out.append(("ACT", ui.long_5s(cmd[1])))
        elif kind == "Q":
            out.append(
                (
                    "MODE",
                    ui.effective_mode(cmd[1]).value,
                    ui.view.value,
                    "1" if ui.pairing else "0",
                )
            )
        elif kind == "Z":
            ui.reminder_until = cmd[1]
        elif kind == "S":
            out.append(
                ("STATE", tr.mode.value, tr.today_ml, tr.progress, str(len(tr.events)))
            )
        else:
            raise ValueError(cmd)
    return out


# --------------------------------------------------------------------------
# C CLI
# --------------------------------------------------------------------------
def build_cli(tmpdir: Path) -> Path:
    cc = os.environ.get("CC", "cc")
    exe = tmpdir / "host_core_cli"
    cmd = [
        cc,
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(CORE_DIR),
        str(CORE_DIR / "core_types.c"),
        str(CORE_DIR / "weight_process.c"),
        str(CORE_DIR / "intake.c"),
        str(CORE_DIR / "reminder.c"),
        str(CORE_DIR / "hydration.c"),
        str(CORE_DIR / "ui.c"),
        str(Path(__file__).with_name("host_core_cli.c")),
        "-lm",
        "-o",
        str(exe),
    ]
    subprocess.run(cmd, check=True)
    return exe


def encode(cmds) -> str:
    lines = []
    for cmd in cmds:
        if cmd[0] in ("S",):
            lines.append("S")
        elif cmd[0] == "F":
            lines.append(f"F {cmd[1]:.17g} {cmd[2]:.17g}")
        elif cmd[0] in ("T", "R", "C", "D", "L2", "L5", "Q", "Z"):
            lines.append(f"{cmd[0]} {cmd[1]:.17g}")
        else:
            raise ValueError(cmd)
    return "\n".join(lines) + "\n"


def parse_c_output(text):
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("EV "):
            parts = line.split(" ", 4)
            if len(parts) < 5:
                raise ValueError(f"bad EV line: {line!r}")
            out.append(("EV", parts[1], float(parts[2]), float(parts[3]), parts[4].strip()))
        elif line.startswith("ACT "):
            out.append(("ACT", line.split(" ", 1)[1].strip()))
        elif line.startswith("MODE "):
            parts = line.split()
            out.append(("MODE", parts[1], parts[2], parts[3]))
        elif line.startswith("STATE "):
            parts = line.split()
            out.append(("STATE", parts[1], float(parts[2]), float(parts[3]), parts[4]))
        else:
            raise ValueError(f"unexpected output: {line!r}")
    return out


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------
def compare(name, expected, actual):
    errors = []
    if len(expected) != len(actual):
        errors.append(f"record count: python={len(expected)} C={len(actual)}")
    for i, (exp, act) in enumerate(zip(expected, actual)):
        if exp[0] != act[0]:
            errors.append(f"#{i} kind: python={exp[0]} C={act[0]}")
            continue
        if exp[0] == "EV":
            if exp[1] != act[1]:
                errors.append(f"#{i} event type: python={exp[1]} C={act[1]}")
            if abs(exp[2] - act[2]) > TOL:
                errors.append(f"#{i} t: python={exp[2]!r} C={act[2]!r}")
            if abs(exp[3] - act[3]) > TOL:
                errors.append(f"#{i} value: python={exp[3]!r} C={act[3]!r}")
            if exp[4] != act[4]:
                errors.append(f"#{i} detail: python={exp[4]!r} C={act[4]!r}")
        elif exp[0] == "STATE":
            if exp[1] != act[1]:
                errors.append(f"#{i} mode: python={exp[1]} C={act[1]}")
            if abs(exp[2] - act[2]) > TOL:
                errors.append(f"#{i} today_ml: python={exp[2]!r} C={act[2]!r}")
            if abs(exp[3] - act[3]) > TOL:
                errors.append(f"#{i} progress: python={exp[3]!r} C={act[3]!r}")
            if exp[4] != act[4]:
                errors.append(f"#{i} event history count: python={exp[4]} C={act[4]}")
        else:  # ACT / MODE
            if tuple(exp[1:]) != tuple(act[1:]):
                errors.append(f"#{i} {exp[0]}: python={exp[1:]} C={act[1:]}")
    return errors


def main() -> int:
    if not CORE_DIR.is_dir():
        print(f"C core not found: {CORE_DIR}", file=sys.stderr)
        return 2

    tmpdir = Path(tempfile.mkdtemp(prefix="smartcoaster-diff-"))
    try:
        exe = build_cli(tmpdir)
        total_records = 0
        failures = 0

        for name, builder in SCENARIOS:
            cmds = builder()
            expected = execute_python(cmds)
            proc = subprocess.run(
                [str(exe)], input=encode(cmds), capture_output=True, text=True, timeout=120
            )
            if proc.returncode != 0:
                print(f"FAIL {name}: C CLI exit {proc.returncode}: {proc.stderr}")
                failures += 1
                continue
            actual = parse_c_output(proc.stdout)
            errors = compare(name, expected, actual)
            total_records += len(expected)
            if errors:
                failures += 1
                print(f"FAIL {name}: {len(errors)} mismatch(es), {len(expected)} records")
                for err in errors[:8]:
                    print(f"     {err}")
            else:
                print(f"PASS {name}: {len(expected)} records match")

        print(
            f"\n{len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios match, "
            f"{total_records} records compared"
        )
        return 0 if failures == 0 else 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
