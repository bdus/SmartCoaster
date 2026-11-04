/* storage.h — NVS persistence for the daily state (P1). */
#pragma once

#include "esp_err.h"
#include "hydration.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t storage_init(void);
esp_err_t storage_load(hydration_tracker_t *tr);
esp_err_t storage_save(const hydration_tracker_t *tr);
esp_err_t storage_load_time(uint32_t *epoch, uint32_t *day);
esp_err_t storage_save_time(uint32_t epoch, uint32_t day);

#ifdef __cplusplus
}
#endif
