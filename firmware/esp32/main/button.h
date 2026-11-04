/*
 * button.h — single push button (GPIO10, active low) gesture decoder.
 *
 * 30 ms debounce (design doc §5.3), click / double-click / long-2s / long-5s.
 * Poll every ~10 ms; the decoder is time-based, not sample-count based.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    BUTTON_EVENT_NONE = 0,
    BUTTON_EVENT_CLICK,
    BUTTON_EVENT_DOUBLE_CLICK,
    BUTTON_EVENT_LONG_2S,
    BUTTON_EVENT_LONG_5S,
} button_event_t;

typedef struct {
    int gpio;
    bool pressed;        /* debounced */
    bool raw;            /* last raw level: true = pressed */
    uint32_t raw_since;  /* ms of last raw change */
    uint32_t press_ms;
    uint32_t release_ms;
    bool long2_fired;
    bool long5_fired;
    bool waiting_double; /* released once, waiting for the 2nd click */
    bool second_press;   /* current press is the 2nd of a potential double */
} button_t;

#define BUTTON_DEBOUNCE_MS 30
#define BUTTON_DOUBLE_MS 350

esp_err_t button_init(button_t *btn, int gpio);

/* Advance the gesture state machine; returns at most one event per call. */
button_event_t button_poll(button_t *btn, uint32_t now_ms);

const char *button_event_name(button_event_t ev);

#ifdef __cplusplus
}
#endif
