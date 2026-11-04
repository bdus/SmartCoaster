"""
HX711 behavioural model (counts) + sensor interface/mock for host tests.

The real chip is NOT modelled at transistor level: this reproduces the
24-bit output code, gain/AVDD full scale, Gaussian input noise, offset,
temperature drift, saturation and quantization, so the *algorithm* can be
tested without hardware.

HX711 transfer (datasheet):
    code = 2^23 * Vdiff / (0.5 * AVDD / gain)      (saturates at +-2^23-1)
At AVDD=3.3 V, gain=128 the full-scale differential input is +-12.9 mV
(NOT +-20 mV; 20 mV is the 5 V case).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass
class HX711Config:
    avdd_v: float = 3.3
    gain: int = 128
    sensitivity_mv_v: float = 1.2       # HY928D full bridge
    rate_sps: int = 10
    noise_nv_rms: float = 50.0          # input-referred, datasheet
    offset_mv: float = 0.0
    drift_mv_per_c: float = 0.0
    temperature_c: float = 25.0
    seed: int | None = 12345

    @property
    def full_scale_mv(self) -> float:
        return 0.5 * self.avdd_v * 1000.0 / self.gain

    @property
    def mv_per_count(self) -> float:
        return self.full_scale_mv / (2 ** 23)


class HX711Model:
    """weight (g) -> 24-bit counts, with noise/drift/saturation."""

    def __init__(self, cfg: HX711Config | None = None):
        self.cfg = cfg or HX711Config()
        self.rng = random.Random(self.cfg.seed)

    def mv_for_grams(self, grams: float) -> float:
        # full bridge: Vout = Vex * 1.2 mV/V at 5 kg
        return self.cfg.avdd_v * self.cfg.sensitivity_mv_v * grams / 5000.0

    def read_counts(self, grams: float) -> int:
        c = self.cfg
        v = (
            self.mv_for_grams(grams)
            + c.offset_mv
            + c.drift_mv_per_c * (c.temperature_c - 25.0)
            + self.rng.gauss(0.0, c.noise_nv_rms * 1e-6)
        )
        code = int(round(v / c.mv_per_count))
        lim = 2 ** 23 - 1
        return max(-lim, min(lim, code))

    def count_for_grams(self, grams: float) -> float:
        """Noise-free counts, for calibration/derivation."""
        return self.mv_for_grams(grams) / self.cfg.mv_per_count


class WeightSensor(Protocol):
    def read_grams(self) -> float: ...
    def tare(self) -> None: ...


class HX711Mock:
    """Sensor interface fed by a scripted/continuous weight function."""

    def __init__(self, model: HX711Model | None = None):
        self.model = model or HX711Model()
        self._weight = 0.0
        self._offset_counts = 0

    def set_weight(self, grams: float) -> None:
        self._weight = grams

    def read_counts(self) -> int:
        return self.model.read_counts(self._weight)

    def read_grams(self) -> float:
        c = self.model.cfg
        counts = self.read_counts() - self._offset_counts
        return counts * c.mv_per_count / (c.avdd_v * c.sensitivity_mv_v) * 5000.0

    def tare(self) -> None:
        self._offset_counts = self.model.read_counts(self._weight)


class HX711Hardware:
    """Placeholder for the real bit-banged driver (GPIO4/5)."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("HX711Hardware is only available on the ESP32 target")


def run_trace(mock: HX711Mock, tracker, segments: Sequence[tuple[float, float]], dt: float = 0.1):
    """Feed a weight script through the HX711 model into a HydrationTracker."""
    events = []
    t = 0.0
    for weight, seconds in segments:
        mock.set_weight(weight)
        for _ in range(int(round(seconds / dt))):
            events += tracker.feed(mock.read_grams(), round(t, 3))
            t += dt
    return events
