/* halo.c — LEDC PWM halo driver. */
#include "halo.h"

#include <math.h>

#include "driver/ledc.h"
#include "esp_log.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static const char *TAG = "halo";

#define HALO_LEDC_MODE LEDC_LOW_SPEED_MODE
#define HALO_LEDC_TIMER LEDC_TIMER_0
#define HALO_LEDC_RES LEDC_TIMER_10_BIT
#define HALO_LEDC_FREQ_HZ 5000

static const ledc_channel_t s_channels[3] = {
    LEDC_CHANNEL_0, /* R */
    LEDC_CHANNEL_1, /* G */
    LEDC_CHANNEL_2, /* B */
};

esp_err_t halo_init(int r_gpio, int g_gpio, int b_gpio)
{
    const int gpios[3] = {r_gpio, g_gpio, b_gpio};

    ledc_timer_config_t timer = {
        .speed_mode = HALO_LEDC_MODE,
        .duty_resolution = HALO_LEDC_RES,
        .timer_num = HALO_LEDC_TIMER,
        .freq_hz = HALO_LEDC_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t err = ledc_timer_config(&timer);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ledc timer config failed: %s", esp_err_to_name(err));
        return err;
    }

    for (int i = 0; i < 3; i++) {
        ledc_channel_config_t ch = {
            .gpio_num = gpios[i],
            .speed_mode = HALO_LEDC_MODE,
            .channel = s_channels[i],
            .intr_type = LEDC_INTR_DISABLE,
            .timer_sel = HALO_LEDC_TIMER,
            .duty = 0,
            .hpoint = 0,
        };
        err = ledc_channel_config(&ch);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "ledc channel %d (gpio %d) failed: %s", i, gpios[i],
                     esp_err_to_name(err));
            return err;
        }
    }
    ESP_LOGI(TAG, "init R=%d G=%d B=%d @ %d Hz", r_gpio, g_gpio, b_gpio, HALO_LEDC_FREQ_HZ);
    return ESP_OK;
}

static void set_channel(ledc_channel_t ch, uint8_t value)
{
    /* 8-bit -> 10-bit duty. */
    uint32_t duty = ((uint32_t)value * 1023u) / 255u;
    ledc_set_duty(HALO_LEDC_MODE, ch, duty);
    ledc_update_duty(HALO_LEDC_MODE, ch);
}

void halo_set(uint8_t r, uint8_t g, uint8_t b)
{
    set_channel(s_channels[0], r);
    set_channel(s_channels[1], g);
    set_channel(s_channels[2], b);
}

void halo_set_rgb(halo_rgb_t c)
{
    halo_set(c.r, c.g, c.b);
}

void halo_off(void)
{
    halo_set(0, 0, 0);
}

uint8_t halo_breath_level(float phase)
{
    /* 0 -> 0, 0.5 -> 255, 1 -> 0. */
    float v = (1.0f - cosf(2.0f * (float)M_PI * phase)) * 0.5f;
    if (v < 0.0f) {
        v = 0.0f;
    }
    if (v > 1.0f) {
        v = 1.0f;
    }
    return (uint8_t)(v * 255.0f + 0.5f);
}

halo_rgb_t halo_color_behind(void)
{
    halo_rgb_t c = {255, 140, 0}; /* amber */
    return c;
}

halo_rgb_t halo_color_normal(void)
{
    halo_rgb_t c = {0, 80, 255}; /* blue */
    return c;
}

halo_rgb_t halo_color_goal(void)
{
    halo_rgb_t c = {0, 255, 60}; /* green */
    return c;
}
