/*
 * hx711_hw.h — real HX711 weight sensor (GPIO bit-bang, 25 pulses).
 *
 * This is the only file in the sensing path that touches GPIO.  It implements
 * the abstract weight_sensor_t interface from weight_sensor.h.
 */
#pragma once

#include <stdint.h>

#include "weight_sensor.h"

#ifdef __cplusplus
extern "C" {
#endif

/* PROVISIONAL calibration, shared with firmware/model/hx711.py:
 * HY928D full bridge 1.2 mV/V @ 5 kg, AVDD = 3.3 V, gain 128
 *   full scale = 0.5 * 3300 mV / 128 = 12.89 mV -> 2^23 counts
 *   sensitivity = 3.3 V * 1.2 mV/V / 5000 g = 0.000792 mV/g
 *   counts_per_g = 0.000792 / (12.890625 / 2^23) ~= 515.4
 * Calibrate with a reference weight on the real board (AGENTS.md rule 7). */
#define HX711_HW_DEFAULT_COUNTS_PER_G 515.4

/* Single HX711 instance per board; state is static (no heap). */
ws_err_t hx711_hw_init(weight_sensor_t *sensor, int dout_gpio, int sck_gpio);
ws_err_t hx711_hw_set_scale(weight_sensor_t *sensor, double counts_per_g);

#ifdef __cplusplus
}
#endif
