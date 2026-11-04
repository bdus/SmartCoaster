/*
 * host_mock_test.c — weight_sensor HAL + hx711_mock coverage on the host.
 *
 * Exercises the injected scenarios required for the mock:
 *   empty cup / add water / drink / remove / put back / jump / noise / drift /
 *   saturation / quantisation, and checks they flow correctly through
 *   weight_process -> intake -> reminder.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "hx711_mock.h"
#include "hydration.h"
#include "weight_process.h"
#include "weight_sensor.h"

#define DT 0.1
#define MAX_EVENTS 128

static int g_checks;
static int g_failures;

#define CHECK(cond)                                                       \
    do {                                                                  \
        g_checks++;                                                       \
        if (!(cond)) {                                                    \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);       \
            g_failures++;                                                 \
        }                                                                 \
    } while (0)

#define CHECK_NEAR(a, b, tol)                                                       \
    do {                                                                            \
        g_checks++;                                                                 \
        if (fabs((double)(a) - (double)(b)) > (tol)) {                              \
            printf("  FAIL %s:%d: %s=%.6f vs %s=%.6f (tol %.6f)\n", __FILE__,        \
                   __LINE__, #a, (double)(a), #b, (double)(b), (double)(tol));       \
            g_failures++;                                                           \
        }                                                                           \
    } while (0)

typedef struct {
    hydration_event_t ev[MAX_EVENTS];
    int n;
} event_list_t;

typedef struct {
    hydration_tracker_t tr;
    weight_sensor_t sensor;
    hx711_mock_t mock;
    double t;
    event_list_t events;
} rig_t;

static void rig_init(rig_t *rig, double noise_g, double drift_g_per_sample, double saturation_g,
                     double quantize_g)
{
    memset(rig, 0, sizeof(*rig));
    hx711_mock_config_t cfg;
    hx711_mock_config_default(&cfg);
    cfg.noise_g = noise_g;
    cfg.drift_g_per_sample = drift_g_per_sample;
    cfg.saturation_g = saturation_g;
    cfg.quantize_g = quantize_g;

    hydration_config_t hcfg;
    hydration_config_default(&hcfg);
    hydration_init(&rig->tr, &hcfg);
    hx711_mock_init(&rig->sensor, &rig->mock, &cfg);
}

/* One sample: read grams through the HAL, then run the pure pipeline. */
static void rig_step(rig_t *rig)
{
    double grams = 0.0;
    if (weight_sensor_grams(&rig->sensor, &grams) != WS_OK) {
        return;
    }
    hydration_event_t evs[HYDRATION_MAX_OUT];
    int n = hydration_feed(&rig->tr, grams, rig->t, evs, HYDRATION_MAX_OUT);
    for (int i = 0; i < n && rig->events.n < MAX_EVENTS; i++) {
        rig->events.ev[rig->events.n++] = evs[i];
    }
    rig->t += DT;
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

static const hydration_event_t *find_type(const event_list_t *list, hydration_event_type_t type)
{
    for (int i = 0; i < list->n; i++) {
        if (list->ev[i].type == type) {
            return &list->ev[i];
        }
    }
    return NULL;
}

static void feed_segments(rig_t *rig, const hx711_mock_segment_t *segs, size_t n)
{
    hx711_mock_set_segments(&rig->sensor, segs, n, false);
    for (size_t i = 0; i < n; i++) {
        for (uint32_t k = 0; k < segs[i].samples; k++) {
            rig_step(rig);
        }
    }
}

/* ------------------------------------------------------------------ tests */

/* HAL contract: read_counts -> grams -> tare -> grams. */
static void test_hal_roundtrip_and_tare(void)
{
    static const hx711_mock_segment_t segs[] = {{300.0, 40}};
    rig_t rig;
    rig_init(&rig, 0.0, 0.0, 0.0, 0.0);
    hx711_mock_set_segments(&rig.sensor, segs, 1, false);

    int32_t counts = 0;
    CHECK(weight_sensor_read_counts(&rig.sensor, &counts) == WS_OK);
    CHECK_NEAR((double)counts, 300.0 * rig.sensor.counts_per_g, 2.0);

    double grams = 0.0;
    CHECK(weight_sensor_grams(&rig.sensor, &grams) == WS_OK);
    CHECK_NEAR(grams, 300.0, 0.01);

    CHECK(weight_sensor_tare(&rig.sensor, 5) == WS_OK);
    CHECK(weight_sensor_grams(&rig.sensor, &grams) == WS_OK);
    CHECK_NEAR(grams, 0.0, 0.01);

    static const double heavier[] = {350.0};
    hx711_mock_set_weights(&rig.sensor, heavier, 1, false);
    CHECK(weight_sensor_grams(&rig.sensor, &grams) == WS_OK);
    CHECK_NEAR(grams, 50.0, 0.01);
    CHECK(strcmp(weight_sensor_name(&rig.sensor), "hx711-mock") == 0);
    CHECK(strcmp(ws_err_name(WS_ERR_TIMEOUT), "TIMEOUT") == 0);
}

/* Quantisation: integer HX711 counts are the real resolution limit. */
static void test_mock_quantisation(void)
{
    static const double weights[] = {600.0, 600.2, 599.8};
    rig_t rig;
    rig_init(&rig, 0.0, 0.0, 0.0, 0.0);
    hx711_mock_set_weights(&rig.sensor, weights, 3, false);

    for (int i = 0; i < 3; i++) {
        double g = 0.0;
        CHECK(weight_sensor_grams(&rig.sensor, &g) == WS_OK);
        double one_count = 1.0 / rig.sensor.counts_per_g;
        CHECK(fabs(g - round(g * rig.sensor.counts_per_g) / rig.sensor.counts_per_g) <
              1e-9); /* exactly representable in counts */
        CHECK(fabs(g - weights[i]) <= 0.5 * one_count);
    }

    /* Coarse 0.5 g steps (e.g. a different load cell/filter) must not drift. */
    rig_t quant;
    rig_init(&quant, 0.0, 0.0, 0.0, 0.5);
    static const double coarse[] = {600.2, 600.2, 600.2};
    hx711_mock_set_weights(&quant.sensor, coarse, 3, false);
    double g = 0.0;
    CHECK(weight_sensor_grams(&quant.sensor, &g) == WS_OK);
    CHECK_NEAR(g, 600.0, 0.25);
}

/* Noise: deterministic +/-1 g on a stable cup must not create sip/refill. */
static void test_mock_noise_does_not_trigger(void)
{
    static const hx711_mock_segment_t segs[] = {{600.0, 400}};
    rig_t rig;
    rig_init(&rig, 1.0, 0.0, 0.0, 0.0);
    feed_segments(&rig, segs, 1);

    CHECK(count_type(&rig.events, HYDRATION_EV_CUP_PLACED) == 1);
    CHECK(count_type(&rig.events, HYDRATION_EV_SIP) == 0);
    CHECK(count_type(&rig.events, HYDRATION_EV_REFILL) == 0);
    CHECK_NEAR(hydration_today_ml(&rig.tr), 0.0, 1e-9);
    CHECK(hydration_mode(&rig.tr) == HYDRATION_MODE_HYDRATION);
}

/* Slow drift: 0.005 g/sample * 600 = 3 g, below the 10 g sip threshold. */
static void test_mock_drift_does_not_trigger_sip(void)
{
    static const hx711_mock_segment_t segs[] = {{600.0, 600}};
    rig_t rig;
    rig_init(&rig, 0.0, 0.005, 0.0, 0.0);
    feed_segments(&rig, segs, 1);

    CHECK(count_type(&rig.events, HYDRATION_EV_SIP) == 0);
    CHECK(count_type(&rig.events, HYDRATION_EV_REFILL) == 0);
    CHECK_NEAR(hydration_today_ml(&rig.tr), 0.0, 1e-9);
    /* last_stable should have followed the drift (~3 g), not jumped. */
    CHECK(fabs(hydration_last_stable(&rig.tr) - 603.0) < 0.5);
}

/* Mechanical/electrical saturation: a huge load clamps to the configured limit
 * and lands outside the cup range -> SCALE. */
static void test_mock_saturation_switches_to_scale(void)
{
    static const hx711_mock_segment_t segs[] = {{600.0, 40}, {5000.0, 60}};
    rig_t rig;
    rig_init(&rig, 0.0, 0.0, 2000.0, 0.0);
    feed_segments(&rig, segs, 2);

    CHECK(hydration_mode(&rig.tr) == HYDRATION_MODE_SCALE);
    CHECK(count_type(&rig.events, HYDRATION_EV_MODE_CHANGE) == 1);
    CHECK_NEAR(hydration_last_stable(&rig.tr), 2000.0, 1e-6);
}

/* 24-bit count saturation, independent of the gram clamp. */
static void test_mock_24bit_saturation(void)
{
    static const hx711_mock_segment_t segs[] = {{20000.0, 1}};
    rig_t rig;
    rig_init(&rig, 0.0, 0.0, 0.0, 0.0);
    hx711_mock_set_segments(&rig.sensor, segs, 1, false);

    int32_t counts = 0;
    CHECK(weight_sensor_read_counts(&rig.sensor, &counts) == WS_OK);
    CHECK(counts == 8388607);
    double g = 0.0;
    static const hx711_mock_segment_t again[] = {{20000.0, 1}};
    hx711_mock_set_segments(&rig.sensor, again, 1, false);
    CHECK(weight_sensor_grams(&rig.sensor, &g) == WS_OK);
    CHECK(g < 20000.0); /* clamped by the 24-bit ADC range */
}

/* Single-sample jump: median filter must swallow it (no SCALE / no sip). */
static void test_mock_single_sample_jump_rejected(void)
{
    static const hx711_mock_segment_t segs[] = {
        {600.0, 60}, {3000.0, 1}, {600.0, 60},
    };
    rig_t rig;
    rig_init(&rig, 0.0, 0.0, 0.0, 0.0);
    feed_segments(&rig, segs, 3);

    CHECK(count_type(&rig.events, HYDRATION_EV_MODE_CHANGE) == 0);
    CHECK(hydration_mode(&rig.tr) == HYDRATION_MODE_HYDRATION);
    CHECK(count_type(&rig.events, HYDRATION_EV_SIP) == 0);
}

/* Full cup lifecycle scripted through the mock: empty -> cup -> drink ->
 * remove -> put back lighter (sip) -> refill. */
static void test_mock_cup_lifecycle(void)
{
    static const hx711_mock_segment_t segs[] = {
        {0.0, 15},   /* empty pad */
        {600.0, 30}, /* cup placed (300 g cup + 300 g water) */
        {0.0, 15},   /* lift */
        {550.0, 30}, /* put back: sip 50 g */
        {0.0, 15},   /* lift */
        {700.0, 30}, /* put back heavier: refill 150 g, no intake */
    };
    rig_t rig;
    rig_init(&rig, 0.5, 0.0, 0.0, 0.0);
    feed_segments(&rig, segs, 6);

    CHECK(count_type(&rig.events, HYDRATION_EV_CUP_PLACED) == 3);
    CHECK(count_type(&rig.events, HYDRATION_EV_CUP_REMOVED) == 2);
    CHECK(count_type(&rig.events, HYDRATION_EV_SIP) == 1);
    CHECK(count_type(&rig.events, HYDRATION_EV_REFILL) == 1);

    const hydration_event_t *sip = find_type(&rig.events, HYDRATION_EV_SIP);
    CHECK(sip != NULL && fabs(sip->value - 50.0) < 1.0);
    CHECK_NEAR(hydration_today_ml(&rig.tr), 50.0, 1.0);
    CHECK(hydration_mode(&rig.tr) == HYDRATION_MODE_HYDRATION);
}

/* Weight calculation: the mock's counts are deterministic given the seed. */
static void test_mock_deterministic_noise(void)
{
    static const double weights[] = {600.0};
    rig_t a;
    rig_t b;
    rig_init(&a, 1.0, 0.0, 0.0, 0.0);
    rig_init(&b, 1.0, 0.0, 0.0, 0.0);
    hx711_mock_set_weights(&a.sensor, weights, 1, true);
    hx711_mock_set_weights(&b.sensor, weights, 1, true);

    for (int i = 0; i < 50; i++) {
        double ga = 0.0, gb = 0.0;
        CHECK(weight_sensor_grams(&a.sensor, &ga) == WS_OK);
        CHECK(weight_sensor_grams(&b.sensor, &gb) == WS_OK);
        CHECK(ga == gb);
    }
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
        {"test_hal_roundtrip_and_tare", test_hal_roundtrip_and_tare},
        {"test_mock_quantisation", test_mock_quantisation},
        {"test_mock_noise_does_not_trigger", test_mock_noise_does_not_trigger},
        {"test_mock_drift_does_not_trigger_sip", test_mock_drift_does_not_trigger_sip},
        {"test_mock_saturation_switches_to_scale", test_mock_saturation_switches_to_scale},
        {"test_mock_24bit_saturation", test_mock_24bit_saturation},
        {"test_mock_single_sample_jump_rejected", test_mock_single_sample_jump_rejected},
        {"test_mock_cup_lifecycle", test_mock_cup_lifecycle},
        {"test_mock_deterministic_noise", test_mock_deterministic_noise},
    };
    int n = (int)(sizeof(cases) / sizeof(cases[0]));
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
