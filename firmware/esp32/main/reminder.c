/* reminder.c — 1:1 with the Python model's reminder policy. */
#include "reminder.h"

void reminder_init(reminder_t *r)
{
    r->last_reminder_t = -1e9;
}

void reminder_reset(reminder_t *r)
{
    r->last_reminder_t = -1e9;
}

bool reminder_due(reminder_t *r, const hydration_config_t *cfg, double today_ml, double last_drink_t,
                  double t)
{
    if (today_ml >= cfg->goal_ml) {
        return false;
    }
    if (t - last_drink_t < cfg->reminder_min * 60.0) {
        return false;
    }
    if (t - r->last_reminder_t < cfg->reminder_cooldown_s) {
        return false;
    }
    r->last_reminder_t = t;
    return true;
}
