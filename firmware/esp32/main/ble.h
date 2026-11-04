/* ble.h — BLE GATT transport (NimBLE, P1). */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "hydration.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool initialised;
    bool connected;
    uint16_t mtu;
    hydration_tracker_t *tracker; /* for writable goal */
    uint16_t weight_g;
    uint16_t today_ml;
    uint16_t goal_ml;
    uint32_t epoch;       /* Unix time set by the app (0xFF06) */
    bool epoch_valid;     /* new value pending for app_main */
} ble_t;

esp_err_t ble_init(ble_t *ble);
bool ble_is_connected(const ble_t *ble);
void ble_set_tracker(ble_t *ble, hydration_tracker_t *tr);
void ble_update(ble_t *ble, uint16_t weight_g, uint16_t today_ml, uint16_t goal_ml);
esp_err_t ble_notify_progress(ble_t *ble, uint16_t today_ml, uint16_t goal_ml);

#ifdef __cplusplus
}
#endif
