/* ui.c — 1:1 port of firmware/model/ui.py. */
#include "ui.h"

#include <stddef.h>

void ui_init(ui_controller_t *ui, hydration_tracker_t *tr)
{
    ui->tr = tr;
    ui->view = UI_VIEW_PROGRESS;
    ui->has_manual = false;
    ui->manual_mode = HYDRATION_MODE_EMPTY;
    ui->manual_until = 0.0;
    ui->reminder_until = 0.0;
    ui->pairing = false;
}

hydration_mode_t ui_effective_mode(const ui_controller_t *ui, double t)
{
    if (ui->has_manual && t < ui->manual_until) {
        return ui->manual_mode;
    }
    return hydration_mode(ui->tr);
}

void ui_on_events(ui_controller_t *ui, const hydration_event_t *events, int n, double t)
{
    int i;

    for (i = 0; i < n; i++) {
        const hydration_event_t *ev = &events[i];
        if (ev->type == HYDRATION_EV_REMINDER_DUE) {
            ui->reminder_until = t + 8.0;
        }
        if (ev->type == HYDRATION_EV_CUP_PLACED || ev->type == HYDRATION_EV_CUP_REMOVED) {
            /* A real cup action always releases a manual override. */
            ui->has_manual = false;
            ui->manual_until = 0.0;
        }
    }
}

ui_action_t ui_click(ui_controller_t *ui, double t)
{
    if (t < ui->reminder_until) {
        ui->reminder_until = 0.0;
        return UI_ACTION_SNOOZE;
    }
    ui->view = (ui->view == UI_VIEW_PROGRESS) ? UI_VIEW_WEIGHT : UI_VIEW_PROGRESS;
    return UI_ACTION_TOGGLE_VIEW;
}

ui_action_t ui_double_click(ui_controller_t *ui, double t)
{
    if (ui_effective_mode(ui, t) == HYDRATION_MODE_SCALE) {
        ui->has_manual = false;
        ui->manual_until = 0.0;
        return UI_ACTION_AUTO_MODE;
    }
    ui->has_manual = true;
    ui->manual_mode = HYDRATION_MODE_SCALE;
    ui->manual_until = t + 600.0;
    return UI_ACTION_MANUAL_SCALE;
}

ui_action_t ui_long_2s(ui_controller_t *ui, double t)
{
    (void)ui;
    (void)t;
    if (ui_effective_mode(ui, t) == HYDRATION_MODE_SCALE) {
        return UI_ACTION_TARE;
    }
    return UI_ACTION_CUP_SETUP;
}

ui_action_t ui_long_5s(ui_controller_t *ui, double t)
{
    (void)t;
    ui->pairing = true;
    return UI_ACTION_PAIRING;
}

const char *ui_action_name(ui_action_t action)
{
    switch (action) {
    case UI_ACTION_NONE:
        return "none";
    case UI_ACTION_TOGGLE_VIEW:
        return "toggle_view";
    case UI_ACTION_SNOOZE:
        return "snooze";
    case UI_ACTION_MANUAL_SCALE:
        return "manual_scale";
    case UI_ACTION_AUTO_MODE:
        return "auto_mode";
    case UI_ACTION_TARE:
        return "tare";
    case UI_ACTION_CUP_SETUP:
        return "cup_setup";
    case UI_ACTION_PAIRING:
        return "pairing";
    default:
        return "?";
    }
}

const char *ui_view_name(ui_view_t view)
{
    switch (view) {
    case UI_VIEW_PROGRESS:
        return "progress";
    case UI_VIEW_WEIGHT:
        return "weight";
    default:
        return "?";
    }
}
