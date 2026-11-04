/*
 * battery.h — LiPo voltage via ADC1 channel 0 (GPIO1, 1:2 divider).
 * PROVISIONAL: divider ratio and the LiPo discharge curve must be checked on
 * the real board (AGENTS.md rule 7).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool ready;
    float divider;
    int raw;
    int millivolts; /* battery-side mV (after divider) */
} battery_t;

esp_err_t battery_init(battery_t *bat, int adc_gpio, float divider);
esp_err_t battery_read(battery_t *bat);

/* Rough LiPo state of charge, 0..100 %, from battery-side mV. */
int battery_percent(int millivolts);

#ifdef __cplusplus
}
#endif
