/*
 * app_main.c — SmartCoaster firmware skeleton (ESP32-S3, ESP-IDF v6.1).
 *
 * Layering (see firmware/REPORT.md):
 *
 *   weight_sensor.h  HAL: read_counts() / tare() / grams()
 *      ├── hx711_hw.c    GPIO4/5 bit-bang (real board)
 *      └── hx711_mock.c  scripted sensor (host tests + QEMU demo)
 *              ↓ grams
 *   weight_process.c  median + stability window + spike gate (pure)
 *              ↓ stable grams
 *   intake.c          cup / sip / refill / daily ml / mode (pure)
 *              ↓
 *   reminder.c        "time to drink" policy (pure)
 *              ↓ events
 *   hydration.c       facade + event history
 *              ↓
 *   ui.c              gestures / view / manual mode (pure)  +  app_main rendering
 *
 * Loop model:
 *   - 10 ms tick : button gesture decoder + halo animation
 *   - 100 ms     : one weight conversion -> hydration_feed() -> UI
 *   - 200 ms     : OLED redraw (only when the frame changes)
 *
 * No BLE, no NVS persistence, no light sleep yet (see firmware/REPORT.md).
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "battery.h"
#include "ble.h"
#include "board.h"
#include "button.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "halo.h"
#include "hx711_hw.h"
#include "hx711_mock.h"
#include "hydration.h"
#include "oled.h"
#include "storage.h"
#include "ui.h"
#include "weight_sensor.h"

static const char *TAG = "coaster";

typedef struct {
    hydration_tracker_t tracker;
    ui_controller_t ui;
    weight_sensor_t sensor;
    hx711_mock_t mock; /* only used when CONFIG_SMARTCOASTER_WEIGHT_MOCK=y */
    battery_t bat;
    ble_t ble;
    button_t btn;

    bool sensor_ok;
    bool oled_ok;
    bool bat_ok;

    double now_s;
    int64_t now_us;
    uint32_t now_ms;

    /* UI-only ephemeral state. */
    double last_sip_ml;
    double last_sip_until;
    double celebrate_until;
    bool goal_celebrated;

    uint32_t last_render_ms;
    uint32_t last_halo_ms;
    uint32_t last_hx_warn_ms;
    uint32_t last_bat_ms;
    uint32_t last_status_ms;

    char frame[4][24]; /* what is currently on screen, for change detection */

    uint32_t boot_epoch; /* Unix time at boot (0 until the app sets it) */
    uint32_t day_id;     /* YYYY-day counter = epoch / 86400 */
    bool time_set;
} app_ctx_t;

static app_ctx_t s_app;

#if CONFIG_SMARTCOASTER_WEIGHT_MOCK
/* QEMU/demo script at 10 Hz: empty pad -> cup -> sip -> refill -> foreign
 * object -> back to cup -> removed. Loops are intentionally disabled so the
 * trace ends in a quiet empty state. */
static const hx711_mock_segment_t k_demo_segments[] = {
    {0.0, 20},    {600.0, 60},  {600.0, 60},  {0.0, 30},   {550.0, 60},
    {0.0, 20},    {700.0, 60},  {2000.0, 40}, {700.0, 60}, {0.0, 30},
};
#endif

/* ------------------------------------------------------------------------- */
/* helpers                                                                   */
/* ------------------------------------------------------------------------- */

static void render_frame(app_ctx_t *app, double now_s)
{
    const hydration_tracker_t *tr = &app->tracker;
    hydration_mode_t mode = ui_effective_mode(&app->ui, now_s);
    bool reminder = now_s < app->ui.reminder_until;
    int weight_g = (int)lround(hydration_last_stable(tr));
    int today_ml = (int)lround(hydration_today_ml(tr));
    int goal_ml = (int)lround(tr->cfg.goal_ml);
    int pct = (int)lround(hydration_progress(tr) * 100.0);
    char line[4][24] = {{0}};

    if (!app->oled_ok) {
        return;
    }

    if (app->ui.pairing) {
        snprintf(line[0], sizeof(line[0]), "PAIRING...");
        snprintf(line[1], sizeof(line[1]), "SMARTCOASTER");
        snprintf(line[2], sizeof(line[2]), ble_is_connected(&app->ble) ? "CONNECTED" : "0xFF00 ADVERTISING");
    } else if (reminder) {
        snprintf(line[0], sizeof(line[0]), "DRINK WATER");
        snprintf(line[1], sizeof(line[1]), "TODAY %d/%d ML", today_ml, goal_ml);
        snprintf(line[2], sizeof(line[2]), "%d%%  CLICK=SNOOZE", pct);
    } else if (mode == HYDRATION_MODE_SCALE) {
        snprintf(line[0], sizeof(line[0]), "SCALE");
        snprintf(line[1], sizeof(line[1]), "%d G", weight_g);
        snprintf(line[2], sizeof(line[2]), "TARE: HOLD K1");
    } else if (mode == HYDRATION_MODE_HYDRATION) {
        if (now_s < app->last_sip_until) {
            snprintf(line[0], sizeof(line[0]), "+%d ML", (int)lround(app->last_sip_ml));
            snprintf(line[1], sizeof(line[1]), "TODAY %d/%d ML", today_ml, goal_ml);
            snprintf(line[2], sizeof(line[2]), "%d%%", pct);
        } else if (hydration_today_ml(tr) >= tr->cfg.goal_ml) {
            snprintf(line[0], sizeof(line[0]), "GOAL DONE");
            snprintf(line[1], sizeof(line[1]), "TODAY %d/%d ML", today_ml, goal_ml);
            snprintf(line[2], sizeof(line[2]), "%d%%", pct);
        } else {
            snprintf(line[0], sizeof(line[0]), "TODAY %d/%d ML", today_ml, goal_ml);
            snprintf(line[1], sizeof(line[1]), "%d%%", pct);
            snprintf(line[2], sizeof(line[2]), "CLICK=WEIGHT");
        }
    } else {
        snprintf(line[0], sizeof(line[0]), "PLACE CUP");
        snprintf(line[1], sizeof(line[1]), "TODAY %d/%d ML", today_ml, goal_ml);
        if (app->bat_ok) {
            battery_read(&app->bat);
            snprintf(line[2], sizeof(line[2]), "BAT %d%%", battery_percent(app->bat.millivolts));
        } else {
            snprintf(line[2], sizeof(line[2]), "NO BATTERY SENSE");
        }
    }

    if (memcmp(line, app->frame, sizeof(line)) == 0) {
        return; /* no change: leave the panel alone */
    }
    memcpy(app->frame, line, sizeof(line));

    oled_clear();
    oled_text(0, 0, line[0]);
    oled_text(0, 1, line[1]);
    oled_text(0, 2, line[2]);
    oled_bar(0, 3, OLED_WIDTH, 5, (float)hydration_progress(tr));
    oled_flush();
}

static void render_halo(app_ctx_t *app, double now_s)
{
    halo_rgb_t c;

    if (app->ui.pairing) {
        c = halo_color_normal();
        halo_set((uint8_t)(c.r / 4), (uint8_t)(c.g / 4), (uint8_t)(c.b / 4));
        return;
    }
    if (now_s < app->celebrate_until) {
        double span = app->celebrate_until - now_s;
        float phase = (float)(1.0 - span / 3.0);
        c = halo_color_goal();
        uint8_t level = halo_breath_level(phase);
        halo_set((uint8_t)((c.r * level) / 255), (uint8_t)((c.g * level) / 255),
                 (uint8_t)((c.b * level) / 255));
        return;
    }
    if (now_s < app->ui.reminder_until) {
        /* 3 s breathing, once per reminder (cooldown handled by reminder.c). */
        double elapsed = 8.0 - (app->ui.reminder_until - now_s);
        if (elapsed <= 3.0) {
            c = halo_color_behind();
            uint8_t level = halo_breath_level((float)(elapsed / 3.0));
            halo_set((uint8_t)((c.r * level) / 255), (uint8_t)((c.g * level) / 255),
                     (uint8_t)((c.b * level) / 255));
        } else {
            halo_off();
        }
        return;
    }
    halo_off();
}

static void log_events(app_ctx_t *app, const hydration_event_t *evs, int n)
{
    for (int i = 0; i < n; i++) {
        const hydration_event_t *ev = &evs[i];
        if (ev->type == HYDRATION_EV_SIP) {
            app->last_sip_ml = ev->value;
            app->last_sip_until = app->now_s + 6.0;
        }
        ESP_LOGI(TAG, "event=%s t=%.2f value=%.1f detail=%s mode=%s today=%.1f ml",
                 hydration_event_type_name(ev->type), ev->t, ev->value, ev->detail,
                 hydration_mode_name(hydration_mode(&app->tracker)),
                 hydration_today_ml(&app->tracker));
    }
    if (!app->goal_celebrated && hydration_today_ml(&app->tracker) >= app->tracker.cfg.goal_ml &&
        app->tracker.cfg.goal_ml > 0.0) {
        app->goal_celebrated = true;
        app->celebrate_until = app->now_s + 3.0;
        ESP_LOGI(TAG, "daily goal reached: %.0f/%.0f ml", hydration_today_ml(&app->tracker),
                 app->tracker.cfg.goal_ml);
    }
}

/* ------------------------------------------------------------------------- */
/* input / sampling                                                          */
/* ------------------------------------------------------------------------- */

static void handle_button(app_ctx_t *app, button_event_t ev)
{
    ui_action_t action = UI_ACTION_NONE;

    switch (ev) {
    case BUTTON_EVENT_CLICK:
        action = ui_click(&app->ui, app->now_s);
        break;
    case BUTTON_EVENT_DOUBLE_CLICK:
        action = ui_double_click(&app->ui, app->now_s);
        break;
    case BUTTON_EVENT_LONG_2S:
        action = ui_long_2s(&app->ui, app->now_s);
        break;
    case BUTTON_EVENT_LONG_5S:
        action = ui_long_5s(&app->ui, app->now_s);
        break;
    default:
        return;
    }
    ESP_LOGI(TAG, "button=%s action=%s mode=%s view=%s", button_event_name(ev),
             ui_action_name(action), hydration_mode_name(ui_effective_mode(&app->ui, app->now_s)),
             ui_view_name(app->ui.view));

    if (action == UI_ACTION_TARE) {
        if (app->sensor_ok) {
            ws_err_t err = weight_sensor_tare(&app->sensor, 5);
            ESP_LOGI(TAG, "scale tare: %s (offset=%.0f counts)", ws_err_name(err),
                     app->sensor.offset_counts);
        }
    } else if (action == UI_ACTION_CUP_SETUP) {
        if (hydration_cup_present(&app->tracker)) {
            hydration_tare_cup(&app->tracker, hydration_last_stable(&app->tracker));
            ESP_LOGI(TAG, "cup tare set to %.0f g", app->tracker.cfg.cup_tare_g);
        } else {
            ESP_LOGW(TAG, "cup setup ignored: no cup on the pad");
        }
    } else if (action == UI_ACTION_SNOOZE) {
        ESP_LOGI(TAG, "reminder snoozed (banner cleared)");
    }
    /* Force a redraw on the next tick. */
    memset(app->frame, 0, sizeof(app->frame));
}

static void sample_weight(app_ctx_t *app)
{
    double grams = 0.0;

    if (!app->sensor_ok) {
        return;
    }
    if (!weight_sensor_data_ready(&app->sensor)) {
        return; /* 10 Hz chip; we poll faster on purpose */
    }
    ws_err_t err = weight_sensor_grams(&app->sensor, &grams);
    if (err != WS_OK) {
        if ((uint32_t)(app->now_ms - app->last_hx_warn_ms) > 5000) {
            app->last_hx_warn_ms = app->now_ms;
            ESP_LOGW(TAG, "weight read failed: %s (reads=%lu errors=%lu)", ws_err_name(err),
                     (unsigned long)app->sensor.reads, (unsigned long)app->sensor.errors);
        }
        return;
    }

    hydration_event_t evs[HYDRATION_MAX_OUT];
    int n = hydration_feed(&app->tracker, grams, app->now_s, evs, HYDRATION_MAX_OUT);
    ui_on_events(&app->ui, evs, n, app->now_s);
    log_events(app, evs, n);
}

static bool init_weight_sensor(app_ctx_t *app)
{
#if CONFIG_SMARTCOASTER_WEIGHT_MOCK
    hx711_mock_config_t cfg;
    hx711_mock_config_default(&cfg);
    cfg.noise_g = 0.5; /* +/- 0.5 g deterministic noise */
    if (hx711_mock_init(&app->sensor, &app->mock, &cfg) != WS_OK) {
        ESP_LOGE(TAG, "mock weight sensor init failed");
        return false;
    }
    hx711_mock_set_segments(&app->sensor, k_demo_segments,
                            sizeof(k_demo_segments) / sizeof(k_demo_segments[0]), false);
    ESP_LOGW(TAG, "SCRIPTED weight sensor active (QEMU/demo build, not real hardware)");
    return true;
#else
    ws_err_t err = hx711_hw_init(&app->sensor, BOARD_HX711_DOUT_GPIO, BOARD_HX711_SCK_GPIO);
    if (err != WS_OK) {
        ESP_LOGE(TAG, "HX711 init failed: %s", ws_err_name(err));
        return false;
    }
    hx711_hw_set_scale(&app->sensor, HX711_HW_DEFAULT_COUNTS_PER_G);
    return true;
#endif
}

/* ------------------------------------------------------------------------- */
/* app_main                                                                  */
/* ------------------------------------------------------------------------- */

void app_main(void)
{
    app_ctx_t *app = &s_app;
    memset(app, 0, sizeof(*app));

    ESP_LOGI(TAG, "SmartCoaster firmware skeleton — ESP32-S3 / ESP-IDF %s", esp_get_idf_version());

    hydration_config_t cfg;
    hydration_config_default(&cfg);
    hydration_init(&app->tracker, &cfg);
    if (storage_init() == ESP_OK) {
        storage_load(&app->tracker);
        storage_load_time(&app->boot_epoch, &app->day_id);
        app->time_set = (app->boot_epoch != 0);
    }
    ui_init(&app->ui, &app->tracker);

    app->sensor_ok = init_weight_sensor(app);

    if (oled_init(BOARD_I2C_SDA_GPIO, BOARD_I2C_SCL_GPIO, BOARD_OLED_I2C_ADDR) == ESP_OK &&
        oled_selftest()) {
        app->oled_ok = true;
    } else {
        ESP_LOGE(TAG, "OLED unavailable; continuing headless");
    }

    button_init(&app->btn, BOARD_BUTTON_GPIO);
    if (halo_init(BOARD_HALO_R_GPIO, BOARD_HALO_G_GPIO, BOARD_HALO_B_GPIO) == ESP_OK) {
        halo_set(0, 0, 0);
    }
    app->bat_ok =
        (battery_init(&app->bat, BOARD_BATTERY_ADC_GPIO, BOARD_BATTERY_DIVIDER) == ESP_OK);
    app->bat_ok = app->bat_ok && (battery_read(&app->bat) == ESP_OK);

    if (ble_init(&app->ble) == ESP_OK) {
        ble_set_tracker(&app->ble, &app->tracker);
        ESP_LOGI(TAG, "BLE GATT ready (SmartCoaster, 0xFF00)");
    } else {
        ESP_LOGW(TAG, "BLE init failed — App pairing unavailable");
    }

    ESP_LOGI(TAG, "sensor=%s pins: HX711 dout=%d sck=%d, I2C sda=%d scl=%d, btn=%d, halo=%d/%d/%d, bat=ADC1_%d",
             weight_sensor_name(&app->sensor), BOARD_HX711_DOUT_GPIO, BOARD_HX711_SCK_GPIO,
             BOARD_I2C_SDA_GPIO, BOARD_I2C_SCL_GPIO, BOARD_BUTTON_GPIO, BOARD_HALO_R_GPIO,
             BOARD_HALO_G_GPIO, BOARD_HALO_B_GPIO, BOARD_BATTERY_ADC_GPIO);

    const int64_t start_us = esp_timer_get_time();
    int64_t next_sample_us = start_us;
    app->last_render_ms = 0;
    app->last_halo_ms = 0;
    app->last_bat_ms = 0;
    app->last_status_ms = 0;

    while (true) {
        int64_t now_us = esp_timer_get_time();
        app->now_us = now_us;
        app->now_s = (double)now_us / 1000000.0;
        app->now_ms = (uint32_t)((now_us - start_us) / 1000);

        button_event_t ev = button_poll(&app->btn, app->now_ms);
        if (ev != BUTTON_EVENT_NONE) {
            handle_button(app, ev);
        }

        if (now_us >= next_sample_us) {
            sample_weight(app);
            next_sample_us += (int64_t)BOARD_WEIGHT_PERIOD_MS * 1000;
            static uint32_t last_store_ms = 0;
            if (app->now_ms - last_store_ms > 60000) {
                last_store_ms = app->now_ms;
                storage_save(&app->tracker);
            }
            static uint32_t last_ble_ms = 0;
            if (app->now_ms - last_ble_ms > 1000) {
                last_ble_ms = app->now_ms;
                ble_update(&app->ble, (uint16_t)lround(hydration_last_stable(&app->tracker)),
                           (uint16_t)lround(hydration_today_ml(&app->tracker)),
                           (uint16_t)lround(app->tracker.cfg.goal_ml));

                /* Time sync from the app (0xFF06, Unix seconds) + day rollover. */
                if (app->ble.epoch_valid) {
                    app->ble.epoch_valid = false;
                    app->boot_epoch = app->ble.epoch - (uint32_t)app->now_s;
                    app->time_set = true;
                }
                if (app->time_set) {
                    uint32_t now_epoch = app->boot_epoch + (uint32_t)app->now_s;
                    uint32_t day = now_epoch / 86400u;
                    if (day != app->day_id) {
                        hydration_reset_day(&app->tracker, app->now_s);
                        app->day_id = day;
                        storage_save_time(now_epoch, day);
                        ESP_LOGI(TAG, "new day %lu; intake reset", (unsigned long)day);
                    }
                }
            }
            if (next_sample_us < now_us) {
                next_sample_us = now_us + (int64_t)BOARD_WEIGHT_PERIOD_MS * 1000;
            }
        }

        if ((uint32_t)(app->now_ms - app->last_halo_ms) >= 20) {
            app->last_halo_ms = app->now_ms;
            render_halo(app, app->now_s);
        }

        if ((uint32_t)(app->now_ms - app->last_render_ms) >= 200) {
            render_frame(app, app->now_s);
            app->last_render_ms = app->now_ms;
        }

        if ((uint32_t)(app->now_ms - app->last_bat_ms) >= 60000) {
            app->last_bat_ms = app->now_ms;
            if (app->bat_ok) {
                battery_read(&app->bat);
                ESP_LOGI(TAG, "battery %d mV (%d%%)", app->bat.millivolts,
                         battery_percent(app->bat.millivolts));
            }
        }

        /* Periodic status line: the QEMU smoke test greps these. */
        if ((uint32_t)(app->now_ms - app->last_status_ms) >= 5000) {
            app->last_status_ms = app->now_ms;
            ESP_LOGI(TAG,
                     "status t=%.1f mode=%s weight=%.1f g today=%.0f/%.0f ml sensor=%s reads=%lu",
                     app->now_s, hydration_mode_name(hydration_mode(&app->tracker)),
                     hydration_last_stable(&app->tracker), hydration_today_ml(&app->tracker),
                     app->tracker.cfg.goal_ml, weight_sensor_name(&app->sensor),
                     (unsigned long)app->sensor.reads);
        }

        vTaskDelay(pdMS_TO_TICKS(BOARD_TICK_PERIOD_MS));
    }
}
