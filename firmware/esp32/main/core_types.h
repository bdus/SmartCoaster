/*
 * core_types.h — shared domain types for the SmartCoaster firmware.
 *
 * No ESP-IDF / GPIO dependencies: included by the pure logic layers
 * (weight_process, intake, reminder, hydration) *and* by the host tests.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define HYDRATION_MAX_RAW 8     /* median window */
#define HYDRATION_MAX_STABLE 32 /* stability window */
#define HYDRATION_MAX_EVENTS 256
#define HYDRATION_MAX_OUT 8 /* max events produced by one feed() */

typedef enum {
    HYDRATION_MODE_EMPTY = 0,
    HYDRATION_MODE_HYDRATION,
    HYDRATION_MODE_SCALE,
} hydration_mode_t;

typedef enum {
    HYDRATION_EV_CUP_PLACED = 0,
    HYDRATION_EV_CUP_REMOVED,
    HYDRATION_EV_SIP,
    HYDRATION_EV_REFILL,
    HYDRATION_EV_MODE_CHANGE,
    HYDRATION_EV_REMINDER_DUE,
    HYDRATION_EV_TARE,
} hydration_event_type_t;

typedef struct {
    hydration_event_type_t type;
    double t;           /* seconds */
    double value;       /* g / ml / progress, meaning depends on type */
    const char *detail; /* "" or "SCALE" / "behind" */
} hydration_event_t;

typedef struct {
    double cup_tare_g;       /* configured empty cup (300 g default) */
    double cup_max_water_g;  /* cup + max water (1500 g) */
    double cup_tolerance_g;  /* +/- tolerance around tare (5 g) */
    double empty_threshold_g; /* below this => nothing on the pad (30 g) */
    double sip_threshold_g;  /* min delta to count as sip/refill (10 g) */
    double goal_ml;          /* daily goal (2200 ml) */
    double reminder_min;     /* reminder interval (60 min) */
    double sample_dt_s;      /* 0.1 s */
    int filter_n;            /* median window (5 raw samples) */
    int stable_n;            /* derived: max(3, round(stable_window_s/dt)) */
    double stable_window_s;  /* 0.3 s */
    double stable_range_g;   /* max-min within window (2 g) */
    double spike_g;          /* reject raw sample this far from median (40 g) */
    double reminder_cooldown_s; /* 600 s */
} hydration_config_t;

void hydration_config_default(hydration_config_t *cfg);
/* Recompute derived fields (stable_n); call after overriding cfg fields. */
void hydration_config_finalize(hydration_config_t *cfg);

const char *hydration_mode_name(hydration_mode_t mode);
const char *hydration_event_type_name(hydration_event_type_t type);

/* Bounded append used by every layer that emits events. */
static inline void hydration_event_push(hydration_event_t *out, int out_cap, int *n,
                                        hydration_event_type_t type, double t, double value,
                                        const char *detail)
{
    if (*n < out_cap) {
        out[*n].type = type;
        out[*n].t = t;
        out[*n].value = value;
        out[*n].detail = detail;
        (*n)++;
    }
}

#ifdef __cplusplus
}
#endif
