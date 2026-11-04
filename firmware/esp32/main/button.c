/* button.c — debounced gesture decoder. */
#include "button.h"

#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "button";

esp_err_t button_init(button_t *btn, int gpio)
{
    btn->gpio = gpio;
    btn->pressed = false;
    btn->raw = false;
    btn->raw_since = 0;
    btn->press_ms = 0;
    btn->release_ms = 0;
    btn->long2_fired = false;
    btn->long5_fired = false;
    btn->waiting_double = false;
    btn->second_press = false;

    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << gpio,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ONLY, /* button to GND */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&cfg);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "init gpio=%d (active low, %d ms debounce)", gpio, BUTTON_DEBOUNCE_MS);
    }
    return err;
}

static button_event_t on_press(button_t *btn, uint32_t now_ms)
{
    btn->press_ms = now_ms;
    btn->long2_fired = false;
    btn->long5_fired = false;
    btn->second_press = btn->waiting_double;
    return BUTTON_EVENT_NONE;
}

static button_event_t on_release(button_t *btn, uint32_t now_ms)
{
    button_event_t ev = BUTTON_EVENT_NONE;

    if (btn->long2_fired) {
        /* Long press already produced its event; not a click. */
        btn->waiting_double = false;
        btn->second_press = false;
        return BUTTON_EVENT_NONE;
    }
    if (btn->second_press) {
        ev = BUTTON_EVENT_DOUBLE_CLICK;
        btn->waiting_double = false;
        btn->second_press = false;
        return ev;
    }
    btn->waiting_double = true;
    btn->release_ms = now_ms;
    return BUTTON_EVENT_NONE;
}

button_event_t button_poll(button_t *btn, uint32_t now_ms)
{
    bool raw = (gpio_get_level(btn->gpio) == 0);

    if (raw != btn->raw) {
        btn->raw = raw;
        btn->raw_since = now_ms;
    }
    /* Only accept a level that has been stable for the debounce window. */
    if (raw != btn->pressed && (uint32_t)(now_ms - btn->raw_since) >= BUTTON_DEBOUNCE_MS) {
        btn->pressed = raw;
        if (btn->pressed) {
            return on_press(btn, now_ms);
        }
        return on_release(btn, now_ms);
    }

    if (btn->pressed) {
        uint32_t held = (uint32_t)(now_ms - btn->press_ms);
        if (!btn->long5_fired && held >= 5000) {
            btn->long5_fired = true;
            btn->long2_fired = true;
            return BUTTON_EVENT_LONG_5S;
        }
        if (!btn->long2_fired && held >= 2000) {
            btn->long2_fired = true;
            return BUTTON_EVENT_LONG_2S;
        }
    } else if (btn->waiting_double &&
               (uint32_t)(now_ms - btn->release_ms) > BUTTON_DOUBLE_MS) {
        btn->waiting_double = false;
        return BUTTON_EVENT_CLICK;
    }
    return BUTTON_EVENT_NONE;
}

const char *button_event_name(button_event_t ev)
{
    switch (ev) {
    case BUTTON_EVENT_NONE:
        return "none";
    case BUTTON_EVENT_CLICK:
        return "click";
    case BUTTON_EVENT_DOUBLE_CLICK:
        return "double_click";
    case BUTTON_EVENT_LONG_2S:
        return "long_2s";
    case BUTTON_EVENT_LONG_5S:
        return "long_5s";
    default:
        return "?";
    }
}
