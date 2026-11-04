/*
 * host_core_test.c — host-side unit tests for the pure-C hydration/ui core.
 *
 * Mirrors the 11 pytest cases in firmware/model/test_hydration.py and
 * test_ui.py, compiled directly against main/hydration.c + main/ui.c (no
 * ESP-IDF). Build & run: tests/firmware/run_host_tests.sh
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "hydration.h"
#include "ui.h"

#define DT 0.1
#define MAX_RUN_EVENTS 128

static int g_checks;
static int g_failures;

#define CHECK(cond)                                                                  \
    do {                                                                             \
        g_checks++;                                                                  \
        if (!(cond)) {                                                               \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);                 \
            g_failures++;                                                            \
        }                                                                            \
    } while (0)

typedef struct {
    hydration_event_t ev[MAX_RUN_EVENTS];
    int n;
    bool overflow;
} event_list_t;

static void evlist_add(event_list_t *list, const hydration_event_t *evs, int n)
{
    for (int i = 0; i < n; i++) {
        if (list->n < MAX_RUN_EVENTS) {
            list->ev[list->n++] = evs[i];
        } else {
            list->overflow = true;
        }
    }
}

static double py_round3(double t)
{
    return round(t * 1000.0) / 1000.0;
}

/* Python test helper run(): t restarts at 0 for every call. */
static event_list_t run_segments(hydration_tracker_t *tr, const double *weights,
                                 const double *durations, int segments)
{
    event_list_t list = {0};
    double t = 0.0;

    for (int s = 0; s < segments; s++) {
        int samples = (int)round(durations[s] / DT);
        for (int k = 0; k < samples; k++) {
            hydration_event_t evs[HYDRATION_MAX_OUT];
            int n = hydration_feed(tr, weights[s], py_round3(t), evs, HYDRATION_MAX_OUT);
            evlist_add(&list, evs, n);
            t += DT;
        }
    }
    return list;
}

static event_list_t run1(hydration_tracker_t *tr, double weight, double duration)
{
    return run_segments(tr, &weight, &duration, 1);
}

static int count_type(const event_list_t *list, hydration_event_type_t type)
{
    int n = 0;
    for (int i = 0; i < list->n; i++) {
        if (list->ev[i].type == type) {
            n++;
        }
    }
    return n;
}

static bool has_type(const event_list_t *list, hydration_event_type_t type)
{
    return count_type(list, type) > 0;
}

static const hydration_event_t *find_type(const event_list_t *list, hydration_event_type_t type)
{
    for (int i = 0; i < list->n; i++) {
        if (list->ev[i].type == type) {
            return &list->ev[i];
        }
    }
    return NULL;
}

static int count_history_type(const hydration_tracker_t *tr, hydration_event_type_t type)
{
    int n = 0;
    for (int i = 0; i < tr->event_count; i++) {
        if (tr->events[i].type == type) {
            n++;
        }
    }
    return n;
}

/* ------------------------------------------------------------------ tests */

/* test_cup_place_sip_and_progress */
static void test_cup_place_sip_and_progress(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);

    event_list_t ev = run1(&tr, 600, 3); /* cup 300 g + 300 g water */
    CHECK(has_type(&ev, HYDRATION_EV_CUP_PLACED));
    CHECK(tr.intake.mode == HYDRATION_MODE_HYDRATION);

    ev = run1(&tr, 600, 1); /* idle */
    CHECK(!has_type(&ev, HYDRATION_EV_SIP));

    run_segments(&tr, (double[]){0, 550}, (double[]){3, 3}, 2); /* lift, drink 50, put back */
    CHECK(count_history_type(&tr, HYDRATION_EV_SIP) == 1);
    /* find sip in history */
    const hydration_event_t *hsip = NULL;
    for (int i = 0; i < tr.event_count; i++) {
        if (tr.events[i].type == HYDRATION_EV_SIP) {
            hsip = &tr.events[i];
        }
    }
    CHECK(hsip != NULL && fabs(hsip->value - 50.0) < 0.5);
    CHECK(fabs(tr.intake.today_ml - 50.0) < 0.5);
    CHECK(fabs(hydration_progress(&tr) - 50.0 / 2200.0) < 1e-9);
}

/* test_refill_is_not_intake */
static void test_refill_is_not_intake(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);

    event_list_t ev = run_segments(&tr, (double[]){600, 0, 700}, (double[]){3, 3, 3}, 3);
    CHECK(tr.intake.today_ml == 0.0);
    CHECK(has_type(&ev, HYDRATION_EV_REFILL));
    CHECK(!has_type(&ev, HYDRATION_EV_SIP));
}

/* test_noise_does_not_trigger */
static void test_noise_does_not_trigger(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    run1(&tr, 600, 3);

    event_list_t ev = {0};
    double t = 3.0;
    for (int i = 0; i < 100; i++) {
        hydration_event_t evs[HYDRATION_MAX_OUT];
        int n = hydration_feed(&tr, 600.0 + (i % 2 ? -1.0 : 1.0), py_round3(t), evs,
                               HYDRATION_MAX_OUT);
        evlist_add(&ev, evs, n);
        t += DT;
    }
    CHECK(!has_type(&ev, HYDRATION_EV_SIP));
    CHECK(!has_type(&ev, HYDRATION_EV_REFILL));
    CHECK(tr.intake.today_ml == 0.0);
}

/* test_single_spike_rejected */
static void test_single_spike_rejected(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    run1(&tr, 600, 3);

    hydration_event_t evs[HYDRATION_MAX_OUT];
    int n = hydration_feed(&tr, 1100, 4.0, evs, HYDRATION_MAX_OUT);
    for (int i = 0; i < n; i++) {
        CHECK(evs[i].type != HYDRATION_EV_SIP);
    }
    run1(&tr, 600, 2);
    CHECK(tr.intake.today_ml == 0.0);
}

/* test_foreign_object_switches_to_scale_and_back */
static void test_foreign_object_switches_to_scale_and_back(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    run1(&tr, 600, 3);

    event_list_t ev = run1(&tr, 2000, 3); /* above cup+water range */
    CHECK(tr.intake.mode == HYDRATION_MODE_SCALE);
    const hydration_event_t *mc = find_type(&ev, HYDRATION_EV_MODE_CHANGE);
    CHECK(mc != NULL && strcmp(mc->detail, "SCALE") == 0);

    ev = run1(&tr, 600, 3);
    CHECK(tr.intake.mode == HYDRATION_MODE_HYDRATION);
}

/* test_reminder_fires_after_interval_and_resets_on_sip */
static void test_reminder_fires_after_interval_and_resets_on_sip(void)
{
    hydration_config_t cfg;
    hydration_config_default(&cfg);
    cfg.reminder_min = 60;
    hydration_config_finalize(&cfg);

    hydration_tracker_t tr;
    hydration_init(&tr, &cfg);
    run1(&tr, 600, 3);

    event_list_t ev = run1(&tr, 600, 3700); /* > 60 min with no drink */
    CHECK(has_type(&ev, HYDRATION_EV_REMINDER_DUE));

    run_segments(&tr, (double[]){0, 550}, (double[]){2, 3}, 2); /* sip 50 resets clock */
    ev = run1(&tr, 550, 100);
    CHECK(!has_type(&ev, HYDRATION_EV_REMINDER_DUE));
}

/* test_cup_tare_setup */
static void test_cup_tare_setup(void)
{
    hydration_config_t cfg;
    hydration_config_default(&cfg);
    cfg.cup_tare_g = 250;
    hydration_config_finalize(&cfg);

    hydration_tracker_t tr;
    hydration_init(&tr, &cfg);
    hydration_tare_cup(&tr, 250);
    run_segments(&tr, (double[]){500, 0, 450}, (double[]){3, 2, 3}, 3);

    CHECK(count_history_type(&tr, HYDRATION_EV_SIP) == 1);
    for (int i = 0; i < tr.event_count; i++) {
        if (tr.events[i].type == HYDRATION_EV_SIP) {
            CHECK(fabs(tr.events[i].value - 50.0) < 0.5);
        }
    }
}

/* --- UI tests ------------------------------------------------------------ */

static double feed_ui(hydration_tracker_t *tr, ui_controller_t *ui, double weight, double seconds,
                      double t)
{
    int samples = (int)(seconds / DT);
    for (int i = 0; i < samples; i++) {
        hydration_event_t evs[HYDRATION_MAX_OUT];
        int n = hydration_feed(tr, weight, py_round3(t), evs, HYDRATION_MAX_OUT);
        ui_on_events(ui, evs, n, t);
        t += DT;
    }
    return t;
}

/* test_single_click_toggles_view_and_snoozes */
static void test_single_click_toggles_view_and_snoozes(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    ui_controller_t ui;
    ui_init(&ui, &tr);

    CHECK(ui_click(&ui, 0) == UI_ACTION_TOGGLE_VIEW);
    CHECK(ui.view == UI_VIEW_WEIGHT);
    CHECK(ui_click(&ui, 1) == UI_ACTION_TOGGLE_VIEW);
    CHECK(ui.view == UI_VIEW_PROGRESS);
    ui.reminder_until = 100;
    CHECK(ui_click(&ui, 50) == UI_ACTION_SNOOZE);
    CHECK(ui.reminder_until == 0.0);
}

/* test_double_click_manual_scale_and_timeout */
static void test_double_click_manual_scale_and_timeout(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    ui_controller_t ui;
    ui_init(&ui, &tr);

    double t = feed_ui(&tr, &ui, 600, 3, 0.0);
    CHECK(tr.intake.mode == HYDRATION_MODE_HYDRATION);
    CHECK(ui_double_click(&ui, t) == UI_ACTION_MANUAL_SCALE);
    CHECK(ui_effective_mode(&ui, t) == HYDRATION_MODE_SCALE);
    CHECK(ui_effective_mode(&ui, t + 599) == HYDRATION_MODE_SCALE);
    CHECK(ui_effective_mode(&ui, t + 601) == HYDRATION_MODE_HYDRATION);
    ui_double_click(&ui, t + 700);
    CHECK(ui_effective_mode(&ui, t + 700) == HYDRATION_MODE_SCALE);
    CHECK(ui_double_click(&ui, t + 701) == UI_ACTION_AUTO_MODE);
    CHECK(ui_effective_mode(&ui, t + 701) == HYDRATION_MODE_HYDRATION);
}

/* test_cup_action_releases_manual_mode */
static void test_cup_action_releases_manual_mode(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    ui_controller_t ui;
    ui_init(&ui, &tr);

    double t = feed_ui(&tr, &ui, 600, 3, 0.0);
    ui_double_click(&ui, t);
    CHECK(ui_effective_mode(&ui, t) == HYDRATION_MODE_SCALE);
    t = feed_ui(&tr, &ui, 0, 3, t); /* cup removed */
    CHECK(!ui.has_manual);
    CHECK(ui_effective_mode(&ui, t) == HYDRATION_MODE_EMPTY);
}

/* test_long_press_actions */
static void test_long_press_actions(void)
{
    hydration_tracker_t tr;
    hydration_init(&tr, NULL);
    ui_controller_t ui;
    ui_init(&ui, &tr);

    double t = feed_ui(&tr, &ui, 600, 3, 0.0);
    CHECK(ui_long_2s(&ui, t) == UI_ACTION_CUP_SETUP);
    CHECK(ui_long_5s(&ui, t) == UI_ACTION_PAIRING && ui.pairing);
    ui_double_click(&ui, t);
    CHECK(ui_long_2s(&ui, t) == UI_ACTION_TARE);
}

/* ------------------------------------------------------------------------- */

typedef void (*test_fn_t)(void);
typedef struct {
    const char *name;
    test_fn_t fn;
} test_case_t;

int main(void)
{
    static const test_case_t cases[] = {
        {"test_cup_place_sip_and_progress", test_cup_place_sip_and_progress},
        {"test_refill_is_not_intake", test_refill_is_not_intake},
        {"test_noise_does_not_trigger", test_noise_does_not_trigger},
        {"test_single_spike_rejected", test_single_spike_rejected},
        {"test_foreign_object_switches_to_scale_and_back",
         test_foreign_object_switches_to_scale_and_back},
        {"test_reminder_fires_after_interval_and_resets_on_sip",
         test_reminder_fires_after_interval_and_resets_on_sip},
        {"test_cup_tare_setup", test_cup_tare_setup},
        {"test_single_click_toggles_view_and_snoozes", test_single_click_toggles_view_and_snoozes},
        {"test_double_click_manual_scale_and_timeout", test_double_click_manual_scale_and_timeout},
        {"test_cup_action_releases_manual_mode", test_cup_action_releases_manual_mode},
        {"test_long_press_actions", test_long_press_actions},
    };
    const int n = (int)(sizeof(cases) / sizeof(cases[0]));

    int passed = 0;
    for (int i = 0; i < n; i++) {
        int before = g_failures;
        cases[i].fn();
        bool ok = (g_failures == before);
        if (ok) {
            passed++;
        }
        printf("%s %s\n", ok ? "PASS" : "FAIL", cases[i].name);
    }
    printf("\n%d checks, %d failures, %d/%d tests passed\n", g_checks, g_failures, passed, n);
    return passed == n ? 0 : 1;
}
