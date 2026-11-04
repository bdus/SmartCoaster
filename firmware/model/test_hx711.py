import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from hydration import Config, EventType, HydrationTracker
from hx711 import HX711Config, HX711Mock, HX711Model, run_trace


def test_full_scale_and_counts():
    m = HX711Model(HX711Config(noise_nv_rms=0))
    assert abs(m.cfg.full_scale_mv - 12.89) < 0.01
    c0 = m.read_counts(0)
    c5 = m.read_counts(5000)
    assert abs(c0) <= 1
    assert abs(c5 - 2.577e6) < 2000      # ~2.58 M counts at 5 kg
    # saturation above full scale
    assert m.read_counts(20000) == 2 ** 23 - 1
    assert m.read_counts(-20000) == -(2 ** 23 - 1)


def test_noise_is_about_expected():
    m = HX711Model(HX711Config(seed=1))
    vals = [m.read_counts(600) for _ in range(2000)]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    grams_per_count = 5000.0 / m.count_for_grams(5000)
    sigma_g = (var ** 0.5) * grams_per_count
    # 50 nVrms -> ~0.06 g rms
    assert 0.02 < sigma_g < 0.15, sigma_g


def test_drift_shifts_zero():
    cold = HX711Model(HX711Config(noise_nv_rms=0, drift_mv_per_c=0.002, temperature_c=15))
    warm = HX711Model(HX711Config(noise_nv_rms=0, drift_mv_per_c=0.002, temperature_c=35))
    assert abs((warm.read_counts(0) - cold.read_counts(0)) * cold.cfg.mv_per_count - 0.04) < 1e-6


def test_mock_end_to_end_sip():
    tr = HydrationTracker(Config())
    mock = HX711Mock(HX711Model(HX711Config(seed=7)))
    ev = run_trace(mock, tr, [(600, 3), (0, 3), (550, 3)])
    sips = [e for e in ev if e.type is EventType.SIP]
    assert len(sips) == 1
    assert abs(sips[0].value - 50) < 1.5
    assert abs(tr.today_ml - 50) < 1.5


def test_mock_refill_and_foreign():
    tr = HydrationTracker(Config())
    mock = HX711Mock(HX711Model(HX711Config(seed=8)))
    run_trace(mock, tr, [(600, 3), (0, 3), (700, 3)])
    assert tr.today_ml == 0
    ev = run_trace(mock, tr, [(2000, 3)])
    assert tr.mode.value == "SCALE"
    assert any(e.type is EventType.MODE_CHANGE for e in ev)
