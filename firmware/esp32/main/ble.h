/*
 * ble.h — BLE transport stub (milestone 1).
 *
 * The GATT service/characteristics from docs/design §6 are NOT implemented yet.
 * The stub keeps the app layer honest: callers must handle "BLE unavailable"
 * instead of assuming a phone is connected.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool initialised;
    bool connected;
    uint16_t mtu;
} ble_t;

esp_err_t ble_init(ble_t *ble);
bool ble_is_connected(const ble_t *ble);
/* Returns ESP_ERR_NOT_SUPPORTED until the GATT layer lands. */
esp_err_t ble_notify_progress(ble_t *ble, uint16_t today_ml, uint16_t goal_ml);

#ifdef __cplusplus
}
#endif
