/*
 * board.h — pin map for the B-version coaster (single source of truth for firmware).
 *
 * Source: electronics/pinmap.md (draft, 2026-11-04). GPIO numbers are
 * PROVISIONAL until the KiCad schematic is frozen; keep them here only.
 */
#pragma once

/* HX711 2-wire load-cell front end (10 Hz, gain 128). */
#define BOARD_HX711_DOUT_GPIO 4
#define BOARD_HX711_SCK_GPIO 5

/* SSD1306 0.91" 128x32 OLED on I2C0. */
#define BOARD_I2C_PORT 0
#define BOARD_I2C_SDA_GPIO 8
#define BOARD_I2C_SCL_GPIO 9
#define BOARD_OLED_I2C_ADDR 0x3C

/* Single push button, active low (internal pull-up, 30 ms debounce). */
#define BOARD_BUTTON_GPIO 10

/* Battery sense: 100k/100k divider + 100 nF on ADC1 channel 0. */
#define BOARD_BATTERY_ADC_GPIO 1
#define BOARD_BATTERY_DIVIDER 2.0f

/* Sample loop rates. */
#define BOARD_WEIGHT_PERIOD_MS 100 /* 10 Hz, matches HX711 RATE=GND */
#define BOARD_TICK_PERIOD_MS 10    /* button/UI tick */
