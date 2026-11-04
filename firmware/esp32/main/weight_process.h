/*
 * weight_process.h — raw samples -> median + stability + spike rejection.
 *
 * Pure logic: no GPIO, no ESP-IDF. Mirrors WeightFilter.feed()/stable() in
 * firmware/model/hydration.py exactly (median of N, then a short window of
 * medians; a sample farther than spike_g from the median is a spike).
 */
#pragma once

#include <stdbool.h>

#include "core_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    WEIGHT_SAMPLE_SPIKE = 0, /* |raw - median| > spike_g: drop this sample   */
    WEIGHT_SAMPLE_UNSTABLE,  /* window range still too large: no decision    */
    WEIGHT_SAMPLE_STABLE,    /* filtered weight is stable: safe to consume   */
} weight_sample_class_t;

typedef struct {
    int filter_n;   /* median window, from cfg.filter_n */
    int stable_n;   /* median-window length for stability, from cfg.stable_n */
    double stable_range_g;
    double spike_g;

    double raw[HYDRATION_MAX_RAW];
    int raw_len;
    double filt[HYDRATION_MAX_STABLE];
    int filt_len;
} weight_process_t;

void weight_process_init(weight_process_t *wp, const hydration_config_t *cfg);
void weight_process_reset(weight_process_t *wp);

/* Push one raw sample; returns the classification and the current median. */
weight_sample_class_t weight_process_push(weight_process_t *wp, double raw_g, double *median_g);

bool weight_process_stable(const weight_process_t *wp);
double weight_process_median(const weight_process_t *wp);

#ifdef __cplusplus
}
#endif
