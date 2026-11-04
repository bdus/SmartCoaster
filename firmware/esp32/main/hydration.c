/*
 * hydration.c — facade wiring weight_process -> intake -> reminder.
 *
 * Ordering is significant and matches the Python reference exactly:
 *   1. push the raw sample through the filter
 *   2. spike / unstable samples return early (and skip the reminder check)
 *   3. stable samples update the intake state machine
 *   4. the reminder check runs *after* the intake update
 *   5. every produced event is appended to the tracker history in order
 */
#include "hydration.h"

#include <string.h>

void hydration_init(hydration_tracker_t *tr, const hydration_config_t *cfg)
{
    memset(tr, 0, sizeof(*tr));
    if (cfg != NULL) {
        tr->cfg = *cfg;
    } else {
        hydration_config_default(&tr->cfg);
    }
    hydration_config_finalize(&tr->cfg);

    weight_process_init(&tr->filter, &tr->cfg);
    intake_init(&tr->intake);
    reminder_init(&tr->reminder);
    tr->last_event_t = 0.0;
    tr->event_count = 0;
    tr->event_overflow = false;
}

static void tracker_emit(hydration_tracker_t *tr, const hydration_event_t *ev)
{
    tr->last_event_t = ev->t;
    if (tr->event_count < HYDRATION_MAX_EVENTS) {
        tr->events[tr->event_count++] = *ev;
    } else {
        tr->event_overflow = true;
    }
}

void hydration_reset_day(hydration_tracker_t *tr, double t)
{
    intake_reset_day(&tr->intake, t);
    reminder_reset(&tr->reminder);
}

void hydration_tare_cup(hydration_tracker_t *tr, double empty_weight_g)
{
    hydration_event_t ev;
    tr->cfg.cup_tare_g = empty_weight_g;
    ev.type = HYDRATION_EV_TARE;
    ev.t = tr->last_event_t;
    ev.value = empty_weight_g;
    ev.detail = "";
    tracker_emit(tr, &ev);
}

hydration_mode_t hydration_mode(const hydration_tracker_t *tr)
{
    return tr->intake.mode;
}

bool hydration_cup_present(const hydration_tracker_t *tr)
{
    return tr->intake.cup_present;
}

double hydration_today_ml(const hydration_tracker_t *tr)
{
    return tr->intake.today_ml;
}

double hydration_last_stable(const hydration_tracker_t *tr)
{
    return tr->intake.last_stable;
}

double hydration_progress(const hydration_tracker_t *tr)
{
    return intake_progress(&tr->intake, &tr->cfg);
}

int hydration_feed(hydration_tracker_t *tr, double raw_weight_g, double t,
                   hydration_event_t *out, int out_cap)
{
    hydration_event_t local[HYDRATION_MAX_OUT];
    int n = 0;

    if (out == NULL || out_cap <= 0) {
        out = local;
        out_cap = HYDRATION_MAX_OUT;
    }
    if (out_cap > HYDRATION_MAX_OUT) {
        out_cap = HYDRATION_MAX_OUT;
    }

    double median = 0.0;
    weight_sample_class_t cls = weight_process_push(&tr->filter, raw_weight_g, &median);
    if (cls != WEIGHT_SAMPLE_STABLE) {
        /* Spike or not yet stable: no event and, like the Python model, no
         * reminder check on this sample. */
        return 0;
    }

    n = intake_update(&tr->intake, &tr->cfg, median, t, out, out_cap);

    if (reminder_due(&tr->reminder, &tr->cfg, tr->intake.today_ml, tr->intake.last_drink_t, t)) {
        hydration_event_push(out, out_cap, &n, HYDRATION_EV_REMINDER_DUE, t,
                             intake_progress(&tr->intake, &tr->cfg), "behind");
    }

    for (int i = 0; i < n; i++) {
        tracker_emit(tr, &out[i]);
    }
    return n;
}
