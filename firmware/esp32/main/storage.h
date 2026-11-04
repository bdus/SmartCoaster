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

#ifdef __cplusplus
}
#endif
