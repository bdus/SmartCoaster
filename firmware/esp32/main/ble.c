/* ble.c — minimal NimBLE GATT service for the SmartCoaster (P1).
 *
 * Service 0xFF00:
 *   0xFF01 weight  u16  g     read + notify
 *   0xFF02 today   u16  ml    read + notify
 *   0xFF03 goal    u16  ml    read + write
 *   0xFF04 battery u8   %     read
 *   0xFF05 command u8         write (1 = reset day, 2 = tare)
 *
 * Values are cached in the characteristic `.arg`; the app calls ble_update()
 * once per second and on events.
 */
#include "ble.h"

#include <string.h>

#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble";
static ble_t *s_ble;
static uint8_t s_addr_type;
static uint16_t s_conn = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_h_weight, s_h_today, s_h_goal, s_h_batt, s_h_cmd;
static uint16_t s_weight, s_today, s_goal;
static uint8_t s_batt = 100;
static uint8_t s_cmd;
static bool s_adv;
static uint32_t s_epoch;
static uint16_t s_h_time;

static void advertise(void);

static int gap_cb(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            s_conn = event->connect.conn_handle;
            if (s_ble) s_ble->connected = true;
            s_ble->mtu = ble_att_mtu(s_conn);
            ESP_LOGI(TAG, "connected, mtu=%u", s_ble->mtu);
        } else {
            advertise();
        }
        return 0;
    case BLE_GAP_EVENT_DISCONNECT:
        s_conn = BLE_HS_CONN_HANDLE_NONE;
        s_adv = false;
        if (s_ble) s_ble->connected = false;
        return 0;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        s_adv = false;
        return 0;
    default:
        return 0;
    }
}

static void advertise(void)
{
    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    const char *name = ble_svc_gap_device_name();
    fields.name = (uint8_t *)name;
    fields.name_len = (uint8_t)strlen(name);
    fields.name_is_complete = 1;
    int rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "adv fields rc=%d", rc);
        return;
    }
    struct ble_gap_adv_params params = {0};
    params.conn_mode = BLE_GAP_CONN_MODE_UND;
    params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    rc = ble_gap_adv_start(s_addr_type, NULL, BLE_HS_FOREVER, &params, gap_cb, NULL);
    if (rc == 0 || rc == BLE_HS_EALREADY) {
        s_adv = true;
    } else {
        ESP_LOGE(TAG, "adv start rc=%d", rc);
    }
}

void ble_start_adv(void)
{
    if (s_ble && s_ble->connected) return;
    if (!s_adv) advertise();
}

void ble_stop_adv(void)
{
    if (s_adv) {
        ble_gap_adv_stop();
        s_adv = false;
        ESP_LOGI(TAG, "advertising stopped (idle)");
    }
}

bool ble_adv_active(void)
{
    return s_adv;
}

static int gatt_cb(uint16_t conn_handle, uint16_t attr_handle,
                   struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn_handle;
    (void)attr_handle;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        if (arg == &s_epoch) {
            return os_mbuf_append(ctxt->om, &s_epoch, sizeof s_epoch) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
        if (arg == &s_batt) {
            return os_mbuf_append(ctxt->om, &s_batt, sizeof s_batt) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
        uint16_t v = *(uint16_t *)arg;
        return os_mbuf_append(ctxt->om, &v, sizeof v) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        if (arg == &s_cmd) {
            uint8_t cmd = 0;
            if (os_mbuf_copydata(ctxt->om, 0, sizeof cmd, &cmd) != 0) {
                return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            }
            if (s_ble && s_ble->tracker) {
                if (cmd == 1) hydration_reset_day(s_ble->tracker, 0.0);
                if (cmd == 2 && s_ble->tracker) {
                    hydration_tare_cup(s_ble->tracker, s_ble->tracker->intake.last_stable);
                }
            }
            return 0;
        }
        if (arg == &s_epoch) {
            uint32_t v = 0;
            if (os_mbuf_copydata(ctxt->om, 0, sizeof v, &v) != 0) {
                return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            }
            s_epoch = v;
            if (s_ble) { s_ble->epoch = v; s_ble->epoch_valid = true; }
            return 0;
        }
        if (arg == &s_goal) {
            uint16_t v = 0;
            if (os_mbuf_copydata(ctxt->om, 0, sizeof v, &v) != 0) {
                return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            }
            s_goal = v;
            if (s_ble && s_ble->tracker) s_ble->tracker->cfg.goal_ml = (double)v;
            return 0;
        }
    }
    return BLE_ATT_ERR_UNLIKELY;
}

static const struct ble_gatt_chr_def s_chrs[] = {
    {.uuid = BLE_UUID16_DECLARE(0xFF01), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY, .val_handle = &s_h_weight,
     .arg = &s_weight},
    {.uuid = BLE_UUID16_DECLARE(0xFF02), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY, .val_handle = &s_h_today,
     .arg = &s_today},
    {.uuid = BLE_UUID16_DECLARE(0xFF03), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE, .val_handle = &s_h_goal,
     .arg = &s_goal},
    {.uuid = BLE_UUID16_DECLARE(0xFF04), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_READ, .val_handle = &s_h_batt, .arg = &s_batt},
    {.uuid = BLE_UUID16_DECLARE(0xFF05), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_WRITE, .val_handle = &s_h_cmd, .arg = &s_cmd},
    {.uuid = BLE_UUID16_DECLARE(0xFF06), .access_cb = gatt_cb,
     .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE, .val_handle = &s_h_time, .arg = &s_epoch},
    {0}
};

static const struct ble_gatt_svc_def s_svcs[] = {
    {.type = BLE_GATT_SVC_TYPE_PRIMARY, .uuid = BLE_UUID16_DECLARE(0xFF00),
     .characteristics = s_chrs},
    {0}
};

static void on_sync(void)
{
    ble_hs_util_ensure_addr(0);
    ble_hs_id_infer_auto(0, &s_addr_type);
    advertise();
}

static void on_reset(int reason)
{
    ESP_LOGW(TAG, "host reset, reason=%d", reason);
}

static void host_task(void *param)
{
    (void)param;
    nimble_port_run();
    nimble_port_freertos_deinit();
}

esp_err_t ble_init(ble_t *ble)
{
    s_ble = ble;
    ble->initialised = false;
    ble->connected = false;
    ble->mtu = 0;

    esp_err_t err = nimble_port_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nimble_port_init: %s", esp_err_to_name(err));
        return err;
    }
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.reset_cb = on_reset;
    ble_svc_gap_init();
    ble_svc_gatt_init();
    if (ble_gatts_count_cfg(s_svcs) != 0 || ble_gatts_add_svcs(s_svcs) != 0) {
        return ESP_FAIL;
    }
    ble_svc_gap_device_name_set("SmartCoaster");
    nimble_port_freertos_init(host_task);
    ble->initialised = true;
    ESP_LOGI(TAG, "GATT 0xFF00 ready (weight/today/goal/battery/cmd)");
    return ESP_OK;
}

bool ble_is_connected(const ble_t *ble)
{
    return ble != NULL && ble->connected;
}

void ble_set_tracker(ble_t *ble, hydration_tracker_t *tr)
{
    if (ble) ble->tracker = tr;
}

static void notify_u16(uint16_t handle, uint16_t v)
{
    if (s_conn == BLE_HS_CONN_HANDLE_NONE) return;
    struct os_mbuf *om = ble_hs_mbuf_from_flat(&v, sizeof v);
    if (om) {
        ble_gatts_notify_custom(s_conn, handle, om);
    }
}

void ble_update(ble_t *ble, uint16_t weight_g, uint16_t today_ml, uint16_t goal_ml,
                uint8_t battery_pct)
{
    (void)ble;
    s_batt = battery_pct > 100 ? 100 : battery_pct;
    if (s_weight != weight_g) {
        s_weight = weight_g;
        notify_u16(s_h_weight, s_weight);
    }
    if (s_today != today_ml) {
        s_today = today_ml;
        notify_u16(s_h_today, s_today);
    }
    s_goal = goal_ml;
}

esp_err_t ble_notify_progress(ble_t *ble, uint16_t today_ml, uint16_t goal_ml)
{
    (void)ble;
    s_goal = goal_ml;
    s_today = today_ml;
    notify_u16(s_h_today, s_today);
    return ESP_OK;
}
