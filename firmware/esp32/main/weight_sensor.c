/* weight_sensor.c — error-name helper (the rest of the HAL is header-inline). */
#include "weight_sensor.h"

const char *ws_err_name(ws_err_t err)
{
    switch (err) {
    case WS_OK:
        return "OK";
    case WS_ERR_INVALID_ARG:
        return "INVALID_ARG";
    case WS_ERR_INVALID_STATE:
        return "INVALID_STATE";
    case WS_ERR_TIMEOUT:
        return "TIMEOUT";
    case WS_ERR_NOT_READY:
        return "NOT_READY";
    case WS_ERR_IO:
        return "IO";
    default:
        return "?";
    }
}
