/*
 * hx711_hw.c — bit-banged HX711 driver implementing weight_sensor_t.
 *
 * Protocol: when DOUT goes low a conversion is ready; 24 clocks shift out the
 * two's-complement value (MSB first) and the 25th pulse selects channel A /
 * gain 128 for the next conversion.
 */
#include "hx711_hw.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "hx711";

#define HX711_READY_TIMEOUT_US 150000 /* one 10 Hz conversion period + margin */
#define HX711_CLOCK_DELAY_US 1

typedef struct {
    int dout_gpio;
    int sck_gpio;
} hx711_hw_impl_t;

static hx711_hw_impl_t s_impl;

static void clock_pulse(void)
{
    gpio_set_level(s_impl.sck_gpio, 1);
    esp_rom_delay_us(HX711_CLOCK_DELAY_US);
    gpio_set_level(s_impl.sck_gpio, 0);
    esp_rom_delay_us(HX711_CLOCK_DELAY_US);
}

static bool hw_data_ready(weight_sensor_t *self)
{
    (void)self;
    return gpio_get_level(s_impl.dout_gpio) == 0;
}

static ws_err_t hw_read_counts(weight_sensor_t *self, int32_t *counts)
{
    (void)self;
    int64_t deadline;
    uint32_t value = 0;
    int i;

    deadline = esp_timer_get_time() + HX711_READY_TIMEOUT_US;
    while (gpio_get_level(s_impl.dout_gpio) != 0) {
        if (esp_timer_get_time() > deadline) {
            return WS_ERR_TIMEOUT;
        }
        vTaskDelay(1);
    }

    for (i = 0; i < 24; i++) {
        gpio_set_level(s_impl.sck_gpio, 1);
        esp_rom_delay_us(HX711_CLOCK_DELAY_US);
        value = (value << 1) | (uint32_t)(gpio_get_level(s_impl.dout_gpio) & 0x01);
        gpio_set_level(s_impl.sck_gpio, 0);
        esp_rom_delay_us(HX711_CLOCK_DELAY_US);
    }
    clock_pulse(); /* 25th pulse: channel A, gain 128 */

    if (value & 0x800000UL) {
        value |= 0xFF000000UL;
    }
    *counts = (int32_t)value;
    return WS_OK;
}

static ws_err_t hw_tare(weight_sensor_t *self, int samples)
{
    double sum = 0.0;
    int ok = 0;

    if (samples < 1) {
        samples = 5;
    }
    for (int i = 0; i < samples; i++) {
        int32_t counts = 0;
        ws_err_t err = hw_read_counts(self, &counts);
        if (err == WS_OK) {
            sum += (double)counts;
            ok++;
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    if (ok == 0) {
        ESP_LOGE(TAG, "tare failed: no conversions");
        return WS_ERR_TIMEOUT;
    }
    self->offset_counts = sum / (double)ok;
    ESP_LOGI(TAG, "tare offset=%.0f counts (%d samples)", self->offset_counts, ok);
    return WS_OK;
}

static ws_err_t hw_grams(weight_sensor_t *self, double *grams)
{
    int32_t counts = 0;
    ws_err_t err = hw_read_counts(self, &counts);
    if (err != WS_OK) {
        return err;
    }
    return weight_sensor_counts_to_grams(self, counts, grams);
}

static const weight_sensor_ops_t s_hw_ops = {
    .name = "hx711-hw",
    .read_counts = hw_read_counts,
    .tare = hw_tare,
    .grams = hw_grams,
    .data_ready = hw_data_ready,
};

ws_err_t hx711_hw_init(weight_sensor_t *sensor, int dout_gpio, int sck_gpio)
{
    if (sensor == NULL) {
        return WS_ERR_INVALID_ARG;
    }
    s_impl.dout_gpio = dout_gpio;
    s_impl.sck_gpio = sck_gpio;

    gpio_config_t in_cfg = {
        .pin_bit_mask = 1ULL << dout_gpio,
        .mode = GPIO_MODE_INPUT,
        /* Pull-up so a missing/unpowered HX711 reads "not ready" (high)
         * instead of floating low and producing garbage. */
        .pull_up_en = GPIO_PULLUP_ONLY,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&in_cfg);
    if (err != ESP_OK) {
        return WS_ERR_IO;
    }

    gpio_config_t out_cfg = {
        .pin_bit_mask = 1ULL << sck_gpio,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&out_cfg);
    if (err != ESP_OK) {
        return WS_ERR_IO;
    }
    gpio_set_level(sck_gpio, 0); /* idle low: power-down when high */

    sensor->ops = &s_hw_ops;
    sensor->impl = &s_impl;
    sensor->offset_counts = 0.0;
    sensor->counts_per_g = HX711_HW_DEFAULT_COUNTS_PER_G;
    sensor->reads = 0;
    sensor->errors = 0;

    ESP_LOGI(TAG, "init dout=%d sck=%d counts_per_g=%.1f (PROVISIONAL)", dout_gpio, sck_gpio,
             sensor->counts_per_g);
    return WS_OK;
}

ws_err_t hx711_hw_set_scale(weight_sensor_t *sensor, double counts_per_g)
{
    if (sensor == NULL || counts_per_g <= 0.0) {
        return WS_ERR_INVALID_ARG;
    }
    sensor->counts_per_g = counts_per_g;
    return WS_OK;
}
