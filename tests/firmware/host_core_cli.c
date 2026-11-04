/*
 * host_core_cli.c — stdin/stdout driver for the pure-C core, used by
 * tests/firmware/differential.py to diff the C port against the Python
 * reference model on identical command traces.
 *
 * Commands (one per line):
 *   F <weight_g> <t>   feed one sample (+ ui_on_events)
 *   T <weight_g>       hydration_tare_cup()
 *   R <t>              reset_day()
 *   C <t>              ui_click()
 *   D <t>              ui_double_click()
 *   L2 <t>             ui_long_2s()
 *   L5 <t>             ui_long_5s()
 *   Z <until>          host-only hook: ui.reminder_until = until
 *   Q <t>              -> MODE <effective> <view> <pairing 0/1>
 *   S                  -> STATE <mode> <today_ml> <progress> <event_count>
 *
 * Output:
 *   EV <type> <t> <value> <detail>     (one per feed event)
 *   ACT <action>                       (click/double/long)
 *   MODE / STATE as above
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hydration.h"
#include "ui.h"

int main(void)
{
    hydration_tracker_t tr;
    ui_controller_t ui;
    char line[256];

    hydration_init(&tr, NULL);
    ui_init(&ui, &tr);

    while (fgets(line, sizeof(line), stdin) != NULL) {
        char kind[8] = {0};
        double a = 0.0, b = 0.0;
        int fields = sscanf(line, "%7s %lf %lf", kind, &a, &b);
        if (fields < 1) {
            continue;
        }

        if (strcmp(kind, "F") == 0 && fields >= 3) {
            hydration_event_t evs[HYDRATION_MAX_OUT];
            int n = hydration_feed(&tr, a, b, evs, HYDRATION_MAX_OUT);
            ui_on_events(&ui, evs, n, b);
            for (int i = 0; i < n; i++) {
                printf("EV %s %.9f %.9f %s\n", hydration_event_type_name(evs[i].type), evs[i].t,
                       evs[i].value, evs[i].detail);
            }
        } else if (strcmp(kind, "T") == 0 && fields >= 2) {
            hydration_tare_cup(&tr, a);
        } else if (strcmp(kind, "R") == 0 && fields >= 2) {
            hydration_reset_day(&tr, a);
        } else if (strcmp(kind, "C") == 0 && fields >= 2) {
            printf("ACT %s\n", ui_action_name(ui_click(&ui, a)));
        } else if (strcmp(kind, "D") == 0 && fields >= 2) {
            printf("ACT %s\n", ui_action_name(ui_double_click(&ui, a)));
        } else if (strcmp(kind, "L2") == 0 && fields >= 2) {
            printf("ACT %s\n", ui_action_name(ui_long_2s(&ui, a)));
        } else if (strcmp(kind, "L5") == 0 && fields >= 2) {
            printf("ACT %s\n", ui_action_name(ui_long_5s(&ui, a)));
        } else if (strcmp(kind, "Z") == 0 && fields >= 2) {
            ui.reminder_until = a;
        } else if (strcmp(kind, "Q") == 0 && fields >= 2) {
            printf("MODE %s %s %d\n", hydration_mode_name(ui_effective_mode(&ui, a)),
                   ui_view_name(ui.view), ui.pairing ? 1 : 0);
        } else if (strcmp(kind, "S") == 0) {
            printf("STATE %s %.9f %.9f %d\n", hydration_mode_name(tr.intake.mode), tr.intake.today_ml,
                   hydration_progress(&tr), tr.event_count);
        } else {
            fprintf(stderr, "bad command: %s", line);
            return 2;
        }
        fflush(stdout);
    }
    return 0;
}
