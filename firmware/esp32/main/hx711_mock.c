/* hx711_mock.c — deterministic scripted weight sensor (no hardware access). */
#include "hx711_mock.h"

#include <math.h>
#include <string.h>

#define HX711_COUNTS_MAX 8388607.0
#define HX711_COUNTS_MIN -8388608.0

static double rng_unit(hx711_mock_t *m)
{
    /* Numerical Recipes LCG; deterministic across host and target. */
    m->rng_state = m->rng_state * 1664525u + 1013904223u;
    return (double)(m->rng_state >> 8) / 16777216.0; /* [0, 1) */
}

static double next_base_weight(hx711_mock_t *m)
{
    if (m->use_constant) {
        return m->constant_weight;
    }
    if (m->segments != NULL && m->segment_count > 0) {
        bool looped = false;
        for (;;) {
            if (m->segment_left > 0) {
                m->segment_left--;
                return m->current_weight;
            }
            if (m->segment_index >= m->segment_count) {
                if (m->loop && !looped) {
                    m->segment_index = 0;
                    looped = true;
                    continue;
                }
                m->exhausted = true;
                return m->current_weight;
            }
            const hx711_mock_segment_t *seg = &m->segments[m->segment_index++];
            m->current_weight = seg->weight_g;
            if (seg->samples == 0) {
                continue;
            }
            m->segment_left = seg->samples - 1; /* this call consumes one sample */
            return m->current_weight;
        }
    }

    if (m->weights != NULL && m->weight_count > 0) {
        if (m->weight_pos >= m->weight_count) {
            if (m->loop) {
                m->weight_pos = 0;
            } else {
                m->exhausted = true;
                return m->weights[m->weight_count - 1];
            }
        }
        return m->weights[m->weight_pos++];
    }

    m->exhausted = true;
    return 0.0;
}

static ws_err_t mock_read_counts(weight_sensor_t *self, int32_t *counts)
{
    hx711_mock_t *m = (hx711_mock_t *)self->impl;

    if (m == NULL || counts == NULL) {
        return WS_ERR_INVALID_STATE;
    }

    double w = next_base_weight(m);
    if (m->drift_g_per_sample != 0.0) {
        w += m->drift_g_per_sample * (double)m->conversions;
    }
    if (m->noise_g > 0.0) {
        w += (rng_unit(m) * 2.0 - 1.0) * m->noise_g;
    }
    if (m->saturation_g > 0.0) {
        if (w > m->saturation_g) {
            w = m->saturation_g;
        } else if (w < -m->saturation_g) {
            w = -m->saturation_g;
        }
    }
    if (m->quantize_g > 0.0) {
        w = round(w / m->quantize_g) * m->quantize_g;
    }

    /* The software tare offset is applied by counts_to_grams(); the mock's
     * own hardware zero is the fixed `hardware_offset_counts`. */
    double raw = m->hardware_offset_counts + w * self->counts_per_g;
    if (raw > HX711_COUNTS_MAX) {
        raw = HX711_COUNTS_MAX;
    }
    if (raw < HX711_COUNTS_MIN) {
        raw = HX711_COUNTS_MIN;
    }
    *counts = (int32_t)llround(raw);
    m->conversions++;
    return WS_OK;
}

static ws_err_t mock_tare(weight_sensor_t *self, int samples)
{
    hx711_mock_t *m = (hx711_mock_t *)self->impl;
    double sum = 0.0;

    if (m == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    if (samples < 1) {
        samples = 5;
    }
    for (int i = 0; i < samples; i++) {
        int32_t counts = 0;
        ws_err_t err = mock_read_counts(self, &counts);
        if (err != WS_OK) {
            return err;
        }
        sum += (double)counts;
    }
    self->offset_counts = sum / (double)samples;
    return WS_OK;
}

static ws_err_t mock_grams(weight_sensor_t *self, double *grams)
{
    int32_t counts = 0;
    ws_err_t err = mock_read_counts(self, &counts);
    if (err != WS_OK) {
        return err;
    }
    return weight_sensor_counts_to_grams(self, counts, grams);
}

static bool mock_data_ready(weight_sensor_t *self)
{
    (void)self;
    return true; /* a scripted sensor always has a value ready */
}

static const weight_sensor_ops_t s_mock_ops = {
    .name = "hx711-mock",
    .read_counts = mock_read_counts,
    .tare = mock_tare,
    .grams = mock_grams,
    .data_ready = mock_data_ready,
};

void hx711_mock_config_default(hx711_mock_config_t *cfg)
{
    cfg->counts_per_g = 515.4; /* same PROVISIONAL default as the HW driver (5 kg cell) */
    cfg->offset_counts = 0.0;
    cfg->noise_g = 0.0;
    cfg->drift_g_per_sample = 0.0;
    cfg->saturation_g = 0.0;
    cfg->quantize_g = 0.0;
    cfg->sample_dt_s = 0.1;
    cfg->seed = 0xC0A57E12u;
}

ws_err_t hx711_mock_init(weight_sensor_t *sensor, hx711_mock_t *mock,
                         const hx711_mock_config_t *cfg)
{
    if (sensor == NULL || mock == NULL) {
        return WS_ERR_INVALID_ARG;
    }
    hx711_mock_config_t defaults;
    if (cfg == NULL) {
        hx711_mock_config_default(&defaults);
        cfg = &defaults;
    }

    memset(mock, 0, sizeof(*mock));
    mock->noise_g = cfg->noise_g;
    mock->drift_g_per_sample = cfg->drift_g_per_sample;
    mock->saturation_g = cfg->saturation_g;
    mock->quantize_g = cfg->quantize_g;
    mock->sample_dt_s = cfg->sample_dt_s;
    mock->hardware_offset_counts = cfg->offset_counts;
    mock->rng_state = cfg->seed != 0 ? cfg->seed : 0xC0A57E12u;

    sensor->ops = &s_mock_ops;
    sensor->impl = mock;
    sensor->offset_counts = cfg->offset_counts;
    sensor->counts_per_g = cfg->counts_per_g > 0.0 ? cfg->counts_per_g : 515.4;
    sensor->reads = 0;
    sensor->errors = 0;
    return WS_OK;
}

static hx711_mock_t *mock_of(weight_sensor_t *sensor)
{
    if (sensor == NULL || sensor->ops != &s_mock_ops || sensor->impl == NULL) {
        return NULL;
    }
    return (hx711_mock_t *)sensor->impl;
}

ws_err_t hx711_mock_set_weights(weight_sensor_t *sensor, const double *weights, size_t count,
                                bool loop)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL || weights == NULL || count == 0) {
        return WS_ERR_INVALID_ARG;
    }
    m->weights = weights;
    m->weight_count = count;
    m->weight_pos = 0;
    m->segments = NULL;
    m->segment_count = 0;
    m->segment_index = 0;
    m->segment_left = 0;
    m->loop = loop;
    m->exhausted = false;
    m->use_constant = false;
    return WS_OK;
}

ws_err_t hx711_mock_set_segments(weight_sensor_t *sensor, const hx711_mock_segment_t *segments,
                                 size_t count, bool loop)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL || segments == NULL || count == 0) {
        return WS_ERR_INVALID_ARG;
    }
    m->segments = segments;
    m->segment_count = count;
    m->segment_index = 0;
    m->segment_left = 0;
    m->weights = NULL;
    m->weight_count = 0;
    m->weight_pos = 0;
    m->loop = loop;
    m->exhausted = false;
    m->use_constant = false;
    return WS_OK;
}

ws_err_t hx711_mock_set_weight(weight_sensor_t *sensor, double weight_g)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    m->use_constant = true;
    m->constant_weight = weight_g;
    m->segments = NULL;
    m->segment_count = 0;
    m->weights = NULL;
    m->weight_count = 0;
    m->exhausted = false;
    return WS_OK;
}

ws_err_t hx711_mock_set_noise(weight_sensor_t *sensor, double noise_g)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL || noise_g < 0.0) {
        return WS_ERR_INVALID_ARG;
    }
    m->noise_g = noise_g;
    return WS_OK;
}

ws_err_t hx711_mock_set_drift(weight_sensor_t *sensor, double drift_g_per_sample)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    m->drift_g_per_sample = drift_g_per_sample;
    return WS_OK;
}

ws_err_t hx711_mock_set_saturation(weight_sensor_t *sensor, double saturation_g)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL || saturation_g < 0.0) {
        return WS_ERR_INVALID_ARG;
    }
    m->saturation_g = saturation_g;
    return WS_OK;
}

ws_err_t hx711_mock_set_quantize(weight_sensor_t *sensor, double quantize_g)
{
    hx711_mock_t *m = mock_of(sensor);
    if (m == NULL || quantize_g < 0.0) {
        return WS_ERR_INVALID_ARG;
    }
    m->quantize_g = quantize_g;
    return WS_OK;
}

uint32_t hx711_mock_conversions(const weight_sensor_t *sensor)
{
    const hx711_mock_t *m = (const hx711_mock_t *)sensor->impl;
    return m != NULL ? m->conversions : 0;
}

bool hx711_mock_exhausted(const weight_sensor_t *sensor)
{
    const hx711_mock_t *m = (const hx711_mock_t *)sensor->impl;
    return m != NULL && m->exhausted;
}

double hx711_mock_current_weight(const weight_sensor_t *sensor)
{
    const hx711_mock_t *m = (const hx711_mock_t *)sensor->impl;
    return m != NULL ? m->current_weight : 0.0;
}
