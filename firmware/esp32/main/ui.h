/*
 * ui.h — button gestures + view + manual mode override.
 * 1:1 port of firmware/model/ui.py, layered on top of hydration.h.
 */
#pragma once

#include <stdbool.h>

#include "hydration.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    UI_VIEW_PROGRESS = 0,
    UI_VIEW_WEIGHT,
} ui_view_t;

typedef enum {
    UI_ACTION_NONE = 0,
    UI_ACTION_TOGGLE_VIEW,
    UI_ACTION_SNOOZE,
    UI_ACTION_MANUAL_SCALE,
    UI_ACTION_AUTO_MODE,
    UI_ACTION_TARE,
    UI_ACTION_CUP_SETUP,
    UI_ACTION_PAIRING,
} ui_action_t;

typedef struct {
    hydration_tracker_t *tr;
    ui_view_t view;
    bool has_manual;
    hydration_mode_t manual_mode;
    double manual_until;
    double reminder_until;
    bool pairing;
} ui_controller_t;

void ui_init(ui_controller_t *ui, hydration_tracker_t *tr);

/* Mode shown to the user: manual override wins until it expires. */
hydration_mode_t ui_effective_mode(const ui_controller_t *ui, double t);

/* Apply tracker events (reminder banner + cup actions release manual mode). */
void ui_on_events(ui_controller_t *ui, const hydration_event_t *events, int n, double t);

ui_action_t ui_click(ui_controller_t *ui, double t);
ui_action_t ui_double_click(ui_controller_t *ui, double t);
ui_action_t ui_long_2s(ui_controller_t *ui, double t);
ui_action_t ui_long_5s(ui_controller_t *ui, double t);

const char *ui_action_name(ui_action_t action);
const char *ui_view_name(ui_view_t view);

#ifdef __cplusplus
}
#endif
