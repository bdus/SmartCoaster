/* core_types.c — config defaults and enum names (pure C, host-testable). */
#include "core_types.h"

#include <math.h>
#include <string.h>

void hydration_config_finalize(hydration_config_t *cfg)
{
    double n;

    if (cfg->filter_n < 1) {
        cfg->filter_n = 1;
    }
    if (cfg->filter_n > HYDRATION_MAX_RAW) {
        cfg->filter_n = HYDRATION_MAX_RAW;
    }
    if (!(cfg->sample_dt_s > 0.0)) {
        cfg->sample_dt_s = 0.1;
    }
    if (!(cfg->stable_window_s > 0.0)) {
        cfg->stable_window_s = 0.3;
    }

    /* Python: n = max(3, int(round(stable_window_s / sample_dt_s))) */
    n = cfg->stable_window_s / cfg->sample_dt_s;
    int in = (int)nearbyint(n); /* FE_TONEAREST == Python round() for positives */
    if (in < 3) {
        in = 3;
    }
    if (in > HYDRATION_MAX_STABLE) {
        in = HYDRATION_MAX_STABLE;
    }
    cfg->stable_n = in;
}

void hydration_config_default(hydration_config_t *cfg)
{
    if (cfg == NULL) {
        return;
    }
    memset(cfg, 0, sizeof(*cfg));
    cfg->cup_tare_g = 300.0;
    cfg->cup_max_water_g = 1500.0;
    cfg->cup_tolerance_g = 5.0;
    cfg->empty_threshold_g = 30.0;
    cfg->sip_threshold_g = 10.0;
    cfg->goal_ml = 2200.0;
    cfg->reminder_min = 60.0;
    cfg->sample_dt_s = 0.1;
    cfg->filter_n = 5;
    cfg->stable_window_s = 0.3;
    cfg->stable_range_g = 2.0;
    cfg->spike_g = 40.0;
    cfg->reminder_cooldown_s = 600.0;
    hydration_config_finalize(cfg);
}

const char *hydration_mode_name(hydration_mode_t mode)
{
    switch (mode) {
    case HYDRATION_MODE_EMPTY:
        return "EMPTY";
    case HYDRATION_MODE_HYDRATION:
        return "HYDRATION";
    case HYDRATION_MODE_SCALE:
        return "SCALE";
    default:
        return "?";
    }
}

const char *hydration_event_type_name(hydration_event_type_t type)
{
    switch (type) {
    case HYDRATION_EV_CUP_PLACED:
        return "cup_placed";
    case HYDRATION_EV_CUP_REMOVED:
        return "cup_removed";
    case HYDRATION_EV_SIP:
        return "sip";
    case HYDRATION_EV_REFILL:
        return "refill";
    case HYDRATION_EV_MODE_CHANGE:
        return "mode_change";
    case HYDRATION_EV_REMINDER_DUE:
        return "reminder_due";
    case HYDRATION_EV_TARE:
        return "tare";
    default:
        return "?";
    }
}
