/* storage.c — NVS persistence: today's intake, goal, cup tare (P1).
 *
 * The RTC/time source is not available on the coaster; `last_drink_t` is
 * intentionally not persisted (the reminder timer restarts after a reboot).
 * Day rollover is a BLE/app responsibility until a time source exists.
 */
#include "storage.h"

#include <math.h>

#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "storage";
static const char *NS = "coaster";

esp_err_t storage_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS needs erase (%s); erasing", esp_err_to_name(err));
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    return err;
}

esp_err_t storage_load(hydration_tracker_t *tr)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NS, NVS_READONLY, &h);
    if (err != ESP_OK) {
        ESP_LOGI(TAG, "no saved state (%s)", esp_err_to_name(err));
        return err;
    }
    uint32_t u = 0;
    if (nvs_get_u32(h, "today", &u) == ESP_OK) {
        tr->intake.today_ml = (double)u;
    }
    if (nvs_get_u32(h, "goal", &u) == ESP_OK) {
        tr->cfg.goal_ml = (double)u;
    }
    if (nvs_get_u32(h, "tare", &u) == ESP_OK) {
        tr->cfg.cup_tare_g = (double)u;
    }
    uint8_t mode = 0;
    if (nvs_get_u8(h, "mode", &mode) == ESP_OK) {
        tr->intake.mode = (hydration_mode_t)mode;
    }
    nvs_close(h);
    ESP_LOGI(TAG, "loaded today=%.0f ml goal=%.0f tare=%.0f g", tr->intake.today_ml,
             tr->cfg.goal_ml, tr->cfg.cup_tare_g);
    return ESP_OK;
}

esp_err_t storage_save(const hydration_tracker_t *tr)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NS, NVS_READWRITE, &h);
    if (err != ESP_OK) {
        return err;
    }
    nvs_set_u32(h, "today", (uint32_t)lround(tr->intake.today_ml));
    nvs_set_u32(h, "goal", (uint32_t)lround(tr->cfg.goal_ml));
    nvs_set_u32(h, "tare", (uint32_t)lround(tr->cfg.cup_tare_g));
    nvs_set_u8(h, "mode", (uint8_t)tr->intake.mode);
    err = nvs_commit(h);
    nvs_close(h);
    return err;
}
