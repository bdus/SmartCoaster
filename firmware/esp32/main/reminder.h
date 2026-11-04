/*
 * reminder.h — "time to drink" policy, independent of weight/GPIO.
 *
 * Pure logic: mirrors HydrationTracker._emit_reminder() from the Python model
 * (goal not reached, interval since last drink, cooldown since last reminder).
 */
#pragma once

#include <stdbool.h>

#include "core_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    double last_reminder_t;
} reminder_t;

void reminder_init(reminder_t *r);
void reminder_reset(reminder_t *r);

/* True once per cooldown window when a reminder is due; updates the timestamp. */
bool reminder_due(reminder_t *r, const hydration_config_t *cfg, double today_ml, double last_drink_t,
                  double t);

#ifdef __cplusplus
}
#endif
