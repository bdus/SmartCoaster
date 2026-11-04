/* ble.c — deliberate stub, see ble.h. */
#include "ble.h"

#include "esp_log.h"

static const char *TAG = "ble";

esp_err_t ble_init(ble_t *ble)
{
    ble->initialised = false;
    ble->connected = false;
    ble->mtu = 0;
    ESP_LOGW(TAG, "BLE is stubbed in this milestone (no GATT service)");
    return ESP_ERR_NOT_SUPPORTED;
}

bool ble_is_connected(const ble_t *ble)
{
    return ble != NULL && ble->connected;
}

esp_err_t ble_notify_progress(ble_t *ble, uint16_t today_ml, uint16_t goal_ml)
{
    (void)ble;
    (void)today_ml;
    (void)goal_ml;
    return ESP_ERR_NOT_SUPPORTED;
}
