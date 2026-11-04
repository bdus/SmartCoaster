/*
 * hydration.h — public facade of the hydration domain.
 *
 * Composition (all pure logic, no GPIO):
 *
 *     weight_process.c   raw samples -> median / stability / spike gate
 *              |
 *              v   (stable grams only)
 *     intake.c           cup presence, sip / refill, daily ml, EMPTY/HYDRATION/SCALE
 *              |
 *              v
 *     reminder.c         "time to drink" policy
 *
 * hydration.c wires the three layers together and keeps the event history that
 * the UI and BLE layers consume.  The behaviour is a 1:1 port of
 * firmware/model/hydration.py; tests/firmware/differential.py enforces it.
 */
#pragma once

#include "core_types.h"
#include "intake.h"
#include "reminder.h"
#include "weight_process.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    hydration_config_t cfg;
    weight_process_t filter;
    intake_t intake;
    reminder_t reminder;

    double last_event_t;

    /* Event history (Python: self.events). Saturates in place, like a fixed
     * firmware buffer; `event_overflow` flags saturation. */
    hydration_event_t events[HYDRATION_MAX_EVENTS];
    int event_count;
    bool event_overflow;
} hydration_tracker_t;

/* --- lifecycle --------------------------------------------------------- */
void hydration_init(hydration_tracker_t *tr, const hydration_config_t *cfg);
void hydration_reset_day(hydration_tracker_t *tr, double t);
void hydration_tare_cup(hydration_tracker_t *tr, double empty_weight_g);

/* --- read-only view ---------------------------------------------------- */
hydration_mode_t hydration_mode(const hydration_tracker_t *tr);
bool hydration_cup_present(const hydration_tracker_t *tr);
double hydration_today_ml(const hydration_tracker_t *tr);
double hydration_last_stable(const hydration_tracker_t *tr);
double hydration_progress(const hydration_tracker_t *tr);

/* --- per-sample update -------------------------------------------------
 * Returns the number of events written to `out` (<= out_cap). The same events
 * are also appended to tr->events. */
int hydration_feed(hydration_tracker_t *tr, double raw_weight_g, double t,
                   hydration_event_t *out, int out_cap);

#ifdef __cplusplus
}
#endif
