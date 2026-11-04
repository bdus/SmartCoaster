/* intake.c — 1:1 with the cup/sip/refill branch of Python feed(). */
#include "intake.h"

void intake_init(intake_t *in)
{
    in->mode = HYDRATION_MODE_EMPTY;
    in->cup_present = false;
    in->has_last_weight = false;
    in->last_weight = 0.0;
    in->last_stable = 0.0;
    in->today_ml = 0.0;
    in->last_drink_t = 0.0;
}

void intake_reset_day(intake_t *in, double t)
{
    in->today_ml = 0.0;
    in->last_drink_t = t;
}

double intake_progress(const intake_t *in, const hydration_config_t *cfg)
{
    if (cfg->goal_ml <= 0.0) {
        return 0.0;
    }
    double p = in->today_ml / cfg->goal_ml;
    return p > 1.0 ? 1.0 : p;
}

int intake_update(intake_t *in, const hydration_config_t *cfg, double w, double t,
                  hydration_event_t *out, int out_cap)
{
    int n = 0;

    if (w < cfg->empty_threshold_g) {
        if (in->cup_present) {
            in->cup_present = false;
            in->mode = HYDRATION_MODE_EMPTY;
            in->last_weight = in->last_stable;
            in->has_last_weight = true;
            hydration_event_push(out, out_cap, &n, HYDRATION_EV_CUP_REMOVED, t, in->last_stable,
                                 "");
        } else {
            in->mode = HYDRATION_MODE_EMPTY;
        }
        in->last_stable = w;
        return n;
    }

    bool in_cup_range = (w >= cfg->cup_tare_g - cfg->cup_tolerance_g) &&
                        (w <= cfg->cup_tare_g + cfg->cup_max_water_g);
    if (in_cup_range) {
        if (!in->cup_present) {
            in->cup_present = true;
            in->mode = HYDRATION_MODE_HYDRATION;
            if (in->has_last_weight) {
                double delta = in->last_weight - w;
                if (delta >= cfg->sip_threshold_g) {
                    in->today_ml += delta;
                    in->last_drink_t = t;
                    hydration_event_push(out, out_cap, &n, HYDRATION_EV_SIP, t, delta, "");
                } else if (-delta >= cfg->sip_threshold_g) {
                    hydration_event_push(out, out_cap, &n, HYDRATION_EV_REFILL, t, -delta, "");
                }
            }
            in->last_weight = w;
            in->has_last_weight = true;
            hydration_event_push(out, out_cap, &n, HYDRATION_EV_CUP_PLACED, t, w, "");
        } else {
            in->last_weight = w;
            in->has_last_weight = true;
        }
        in->mode = HYDRATION_MODE_HYDRATION;
        in->last_stable = w;
        return n;
    }

    if (in->mode != HYDRATION_MODE_SCALE) {
        in->mode = HYDRATION_MODE_SCALE;
        in->cup_present = false;
        hydration_event_push(out, out_cap, &n, HYDRATION_EV_MODE_CHANGE, t, w, "SCALE");
    }
    in->last_stable = w;
    return n;
}
