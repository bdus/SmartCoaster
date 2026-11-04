/*
 * weight_sensor.h — abstract weight-sensor interface (HAL).
 *
 * Pure C: no GPIO, no ESP-IDF, so the same interface is implemented by
 *   - hx711_hw.c   real HX711 over GPIO (DOUT/PD_SCK)
 *   - hx711_mock.c scripted/replay sensor for host tests and QEMU
 *
 * The three logic layers (weight_process, intake, reminder) never see this
 * interface directly: app_main converts grams and calls hydration_feed().
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    WS_OK = 0,
    WS_ERR_INVALID_ARG,
    WS_ERR_INVALID_STATE,
    WS_ERR_TIMEOUT,
    WS_ERR_NOT_READY,
    WS_ERR_IO,
} ws_err_t;

const char *ws_err_name(ws_err_t err);

typedef struct weight_sensor weight_sensor_t;

typedef struct {
    const char *name;
    /* One raw conversion (24-bit HX711 counts). */
    ws_err_t (*read_counts)(weight_sensor_t *self, int32_t *counts);
    /* Zero the sensor with `samples` averaged conversions. */
    ws_err_t (*tare)(weight_sensor_t *self, int samples);
    /* read_counts() + (counts - offset) / counts_per_g. */
    ws_err_t (*grams)(weight_sensor_t *self, double *grams);
    /* Non-blocking: is a conversion ready? */
    bool (*data_ready)(weight_sensor_t *self);
} weight_sensor_ops_t;

struct weight_sensor {
    const weight_sensor_ops_t *ops;
    void *impl;         /* driver-private state (hw or mock) */
    double offset_counts; /* tare offset, raw counts */
    double counts_per_g;  /* calibration; PROVISIONAL until bench calibration */
    uint32_t reads;
    uint32_t errors;
};

static inline ws_err_t weight_sensor_read_counts(weight_sensor_t *s, int32_t *counts)
{
    if (s == NULL || s->ops == NULL || s->ops->read_counts == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    ws_err_t err = s->ops->read_counts(s, counts);
    if (err == WS_OK) {
        s->reads++;
    } else {
        s->errors++;
    }
    return err;
}

static inline ws_err_t weight_sensor_tare(weight_sensor_t *s, int samples)
{
    if (s == NULL || s->ops == NULL || s->ops->tare == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    return s->ops->tare(s, samples);
}

static inline ws_err_t weight_sensor_grams(weight_sensor_t *s, double *grams)
{
    if (s == NULL || s->ops == NULL || s->ops->grams == NULL) {
        return WS_ERR_INVALID_STATE;
    }
    ws_err_t err = s->ops->grams(s, grams);
    if (err == WS_OK) {
        s->reads++;
    } else {
        s->errors++;
    }
    return err;
}

static inline bool weight_sensor_data_ready(weight_sensor_t *s)
{
    if (s == NULL || s->ops == NULL || s->ops->data_ready == NULL) {
        return false;
    }
    return s->ops->data_ready(s);
}

static inline const char *weight_sensor_name(const weight_sensor_t *s)
{
    return (s != NULL && s->ops != NULL && s->ops->name != NULL) ? s->ops->name : "?";
}

/* Shared conversion used by both drivers: grams = (counts - offset)/counts_per_g. */
static inline ws_err_t weight_sensor_counts_to_grams(const weight_sensor_t *s, int32_t counts,
                                                     double *grams)
{
    if (s == NULL || grams == NULL || s->counts_per_g <= 0.0) {
        return WS_ERR_INVALID_STATE;
    }
    *grams = ((double)counts - s->offset_counts) / s->counts_per_g;
    return WS_OK;
}

#ifdef __cplusplus
}
#endif
