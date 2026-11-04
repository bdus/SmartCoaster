/*
 * oled.h — SSD1306 128x32 monochrome OLED (I2C, 0x3C), 5x7 ASCII font.
 *
 * Skeleton driver: full-frame buffer + one flush per UI update. The real UI
 * needs a CJK font module (design doc uses Chinese labels); this milestone
 * renders ASCII only.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define OLED_WIDTH 128
#define OLED_HEIGHT 32
#define OLED_PAGES (OLED_HEIGHT / 8)

esp_err_t oled_init(int sda_gpio, int scl_gpio, uint8_t i2c_addr);
bool oled_ready(void);

void oled_clear(void);
void oled_text(int x, int page, const char *text);
void oled_bar(int x, int page, int width, int height, float fraction);
void oled_flush(void);

/* SSD1306 display on/off (0xAF/0xAE); screen blanking for power saving. */
void oled_display_on(void);
void oled_display_off(void);

/* Initialise + draw a static splash; returns false if the panel is absent.
 * A missing panel is non-fatal (the coaster still weighs and reminds). */
bool oled_selftest(void);

#ifdef __cplusplus
}
#endif
