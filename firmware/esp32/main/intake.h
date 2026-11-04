/*
 * intake.h — cup presence / sip / refill / daily total (weight domain only).
 *
 * Pure logic: no GPIO, no ESP-IDF, no filtering. Consumes *stable* grams from
 * weight_process and mirrors the Python HydrationTracker feed() branch 1:1.
 */
#pragma once

#include <stdbool.h>

#include "core_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    hydration_mode_t mode;
    bool cup_present;
    bool has_last_weight; /* Python: last_weight is not None */
    double last_weight;
    double last_stable;
    double today_ml;
    double last_drink_t;
} intake_t;

void intake_init(intake_t *in);
void intake_reset_day(intake_t *in, double t);

/* One stable sample -> 0..3 events (cup_removed / sip / refill / cup_placed /
 * mode_change). Returns the event count. */
int intake_update(intake_t *in, const hydration_config_t *cfg, double stable_g, double t,
                  hydration_event_t *out, int out_cap);

double intake_progress(const intake_t *in, const hydration_config_t *cfg);

#ifdef __cplusplus
}
#endif
