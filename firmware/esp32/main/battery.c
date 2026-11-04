/* battery.c — ADC1 oneshot + curve-fitting calibration.
 *
 * QEMU note: IDF registers an unconditional ADC self-calibration constructor
 * when esp_adc is linked. QEMU 9.2 has no SAR ADC model, so that constructor
 * spins forever in adc_oneshot_ll_get_event(). For QEMU smoke tests only we
 * compile a stub battery path (CONFIG_SMARTCOASTER_BATTERY_STUB) that never
 * references esp_adc. The flashed firmware always uses the real ADC path.
 */
#include "battery.h"

#ifdef SMARTCOASTER_BATTERY_STUB

#include "esp_log.h"

esp_err_t battery_init(battery_t *bat, int adc_gpio, float divider)
{
    (void)adc_gpio;
    bat->ready = true;
    bat->divider = divider;
    bat->raw = 0;
    bat->millivolts = 3900;
    ESP_LOGW("battery", "STUB battery path (QEMU build) — no ADC");
    return ESP_OK;
}

esp_err_t battery_read(battery_t *bat)
{
    bat->millivolts = 3900;
    return ESP_OK;
}

int battery_percent(int millivolts)
{
    if (millivolts >= 4150) {
        return 100;
    }
    if (millivolts <= 3300) {
        return 0;
    }
    return (millivolts - 3300) * 100 / (4150 - 3300);
}

#else /* !SMARTCOASTER_BATTERY_STUB */

#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"

static const char *TAG = "battery";

static adc_oneshot_unit_handle_t s_unit;
static adc_cali_handle_t s_cali;
static adc_channel_t s_channel;

/* GPIO1 on ESP32-S3 = ADC1 channel 0. */
static bool gpio_to_adc1_channel(int gpio, adc_channel_t *out)
{
    if (gpio == 1) {
        *out = ADC_CHANNEL_0;
        return true;
    }
    if (gpio == 2) {
        *out = ADC_CHANNEL_1;
        return true;
    }
    if (gpio == 3) {
        *out = ADC_CHANNEL_2;
        return true;
    }
    if (gpio == 4) {
        *out = ADC_CHANNEL_3;
        return true;
    }
    return false;
}

esp_err_t battery_init(battery_t *bat, int adc_gpio, float divider)
{
    bat->ready = false;
    bat->divider = divider > 0.0f ? divider : 1.0f;
    bat->raw = 0;
    bat->millivolts = 0;

    if (!gpio_to_adc1_channel(adc_gpio, &s_channel)) {
        ESP_LOGE(TAG, "gpio %d is not an ADC1 channel on this board map", adc_gpio);
        return ESP_ERR_INVALID_ARG;
    }

    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    esp_err_t err = adc_oneshot_new_unit(&unit_cfg, &s_unit);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "adc unit init failed: %s", esp_err_to_name(err));
        return err;
    }

    adc_oneshot_chan_cfg_t chan_cfg = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    err = adc_oneshot_config_channel(s_unit, s_channel, &chan_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "adc channel config failed: %s", esp_err_to_name(err));
        return err;
    }

    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .chan = s_channel,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_cali) != ESP_OK) {
        ESP_LOGW(TAG, "ADC calibration unavailable, using linear approximation");
        s_cali = NULL;
    }

    bat->ready = true;
    ESP_LOGI(TAG, "init adc_gpio=%d divider=%.2f (PROVISIONAL)", adc_gpio, bat->divider);
    return ESP_OK;
}

esp_err_t battery_read(battery_t *bat)
{
    int raw = 0;
    int mv = 0;

    if (!bat->ready) {
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t err = adc_oneshot_read(s_unit, s_channel, &raw);
    if (err != ESP_OK) {
        return err;
    }
    bat->raw = raw;

    if (s_cali != NULL) {
        if (adc_cali_raw_to_voltage(s_cali, raw, &mv) != ESP_OK) {
            mv = 0;
        }
    } else {
        /* 12 dB atten: ~0..3100 mV over 0..4095 counts. */
        mv = (raw * 3100) / 4095;
    }
    if (mv <= 0) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    bat->millivolts = (int)((float)mv * bat->divider + 0.5f);
    return ESP_OK;
}

int battery_percent(int millivolts)
{
    /* Coarse LiPo curve; refine after bench measurement. */
    if (millivolts >= 4150) {
        return 100;
    }
    if (millivolts <= 3300) {
        return 0;
    }
    return (millivolts - 3300) * 100 / (4150 - 3300);
}

#endif /* SMARTCOASTER_BATTERY_STUB */
