/*
 * halo.h — 3-channel PWM window halo (RGB, low-side MOSFETs).
 * LEDC @ 5 kHz, 10-bit duty. Brightness/breathing is computed by the caller.
 */
#pragma once

#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint8_t r, g, b;
} halo_rgb_t;

esp_err_t halo_init(int r_gpio, int g_gpio, int b_gpio);

/* 0..255 per channel. */
void halo_set(uint8_t r, uint8_t g, uint8_t b);
void halo_set_rgb(halo_rgb_t c);
void halo_off(void);

/* Breathing level for phase 0..1 (raised-cosine). */
uint8_t halo_breath_level(float phase);

/* Design-doc colours (amber = behind, blue = normal, green = goal). */
halo_rgb_t halo_color_behind(void);
halo_rgb_t halo_color_normal(void);
halo_rgb_t halo_color_goal(void);

#ifdef __cplusplus
}
#endif
