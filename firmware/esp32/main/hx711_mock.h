/*
 * hx711_mock.h — scripted weight sensor for host tests and QEMU.
 *
 * Inject a sequence of (weight, sample-count) segments to model:
 *   empty pad, cup placed, water added/refilled, sip, cup removed/replaced,
 *   single-sample jumps (spikes), deterministic noise, slow drift,
 *   mechanical/electrical saturation and count quantisation.
 *
 * Pure C: no GPIO, no ESP-IDF.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "weight_sensor.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    double weight_g;
    uint32_t samples; /* how many conversions to hold this weight (>=1) */
} hx711_mock_segment_t;

typedef struct {
    double counts_per_g;
    double offset_counts;
    double noise_g;          /* uniform +/- noise, 0 = off */
    double drift_g_per_sample; /* linear drift, 0 = off */
    double saturation_g;     /* clamp |g|, 0 = off */
    double quantize_g;       /* round grams to this step, 0 = off */
    double sample_dt_s;      /* used only for diagnostics/documentation */
    uint32_t seed;           /* deterministic noise seed */
} hx711_mock_config_t;

typedef struct {
    const double *weights;
    size_t weight_count;
    size_t weight_pos;

    const hx711_mock_segment_t *segments;
    size_t segment_count;
    size_t segment_index;
    uint32_t segment_left;
    double current_weight;

    bool loop;
    bool exhausted;
    bool use_constant;
    double constant_weight;
    double hardware_offset_counts; /* fixed zero of the simulated bridge */
    double noise_g;
    double drift_g_per_sample;
    double saturation_g;
    double quantize_g;
    double sample_dt_s;
    uint32_t rng_state;
    uint32_t conversions;
} hx711_mock_t;

void hx711_mock_config_default(hx711_mock_config_t *cfg);

/* `mock` must outlive `sensor` (no dynamic allocation). */
ws_err_t hx711_mock_init(weight_sensor_t *sensor, hx711_mock_t *mock,
                         const hx711_mock_config_t *cfg);

ws_err_t hx711_mock_set_weights(weight_sensor_t *sensor, const double *weights, size_t count,
                                bool loop);
/* Convenience: hold one constant weight forever (architecture doc §2). */
ws_err_t hx711_mock_set_weight(weight_sensor_t *sensor, double weight_g);
ws_err_t hx711_mock_set_segments(weight_sensor_t *sensor, const hx711_mock_segment_t *segments,
                                 size_t count, bool loop);
ws_err_t hx711_mock_set_noise(weight_sensor_t *sensor, double noise_g);
ws_err_t hx711_mock_set_drift(weight_sensor_t *sensor, double drift_g_per_sample);
ws_err_t hx711_mock_set_saturation(weight_sensor_t *sensor, double saturation_g);
ws_err_t hx711_mock_set_quantize(weight_sensor_t *sensor, double quantize_g);

/* Number of conversions consumed so far / whether the script has ended. */
uint32_t hx711_mock_conversions(const weight_sensor_t *sensor);
bool hx711_mock_exhausted(const weight_sensor_t *sensor);
double hx711_mock_current_weight(const weight_sensor_t *sensor);

#ifdef __cplusplus
}
#endif
