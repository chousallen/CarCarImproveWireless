/**
 * @file bleak.c
 * @brief Bleak mode - BLE GATT Server for computer connection
 */

#include <string.h>
#include "ble_bridge_internal.h"

/* GATT Server definitions */
#define GATTS_SERVICE_UUID   0xFF00
#define GATTS_CHAR_UUID      0xFF01
#define GATTS_NUM_HANDLE     4

#define GATTS_CHAR_VAL_LEN_MAX 500
#define PREPARE_BUF_MAX_SIZE   1024

/* GATT Server state */
static esp_gatt_char_prop_t char_property = ESP_GATT_CHAR_PROP_BIT_READ | ESP_GATT_CHAR_PROP_BIT_WRITE | ESP_GATT_CHAR_PROP_BIT_NOTIFY;

/* Attribute handles */
static uint16_t gatts_char_handle = 0;

/* Forward declarations */
static void gatts_profile_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if, esp_ble_gatts_cb_param_t *param);
static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);
static void hm10_data_received(const uint8_t *data, size_t len);

/* GATT Server profile */
struct gatts_profile_inst {
    esp_gatts_cb_t gatts_cb;
    uint16_t gatts_if;
    uint16_t app_id;
    uint16_t conn_id;
    uint16_t service_handle;
    esp_gatt_srvc_id_t service_id;
    uint16_t char_handle;
    esp_bt_uuid_t char_uuid;
    esp_gatt_perm_t perm;
    esp_gatt_char_prop_t property;
    uint16_t descr_handle;
    esp_bt_uuid_t descr_uuid;
};

#define PROFILE_APP_ID 0

static struct gatts_profile_inst gl_gatts_profile = {
    .gatts_cb = gatts_profile_event_handler,
    .gatts_if = ESP_GATT_IF_NONE,
};

/* Advertising data */
static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = true,
    .min_interval = 0x0006,
    .max_interval = 0x0010,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = 0,
    .p_service_uuid = NULL,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20,
    .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

static void gatts_profile_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if, esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT Server registered");

        /* Set device name */
        esp_ble_gap_set_device_name(g_bridge_state.config.bleak.esp32_device_name);

        /* Configure advertising data */
        esp_ble_gap_config_adv_data(&adv_data);

        /* Create service */
        esp_gatt_srvc_id_t service_id = {
            .is_primary = true,
            .id.inst_id = 0x00,
            .id.uuid.len = ESP_UUID_LEN_16,
            .id.uuid.uuid.uuid16 = g_bridge_state.config.bleak.esp32_service_uuid,
        };
        esp_ble_gatts_create_service(gatts_if, &service_id, GATTS_NUM_HANDLE);
        break;

    case ESP_GATTS_CREATE_EVT:
        ESP_LOGI(TAG, "Service created, handle=%d", param->create.service_handle);
        g_bridge_state.mode.bleak.gatts_service_handle = param->create.service_handle;

        /* Start service */
        esp_ble_gatts_start_service(param->create.service_handle);

        /* Add characteristic */
        esp_bt_uuid_t char_uuid;
        char_uuid.len = ESP_UUID_LEN_16;
        char_uuid.uuid.uuid16 = g_bridge_state.config.bleak.esp32_char_uuid;

        esp_ble_gatts_add_char(param->create.service_handle, &char_uuid,
                              ESP_GATT_PERM_READ | ESP_GATT_PERM_WRITE,
                              char_property,
                              NULL, NULL);
        break;

    case ESP_GATTS_ADD_CHAR_EVT:
        ESP_LOGI(TAG, "Characteristic added, handle=%d", param->add_char.attr_handle);
        g_bridge_state.mode.bleak.gatts_char_handle = param->add_char.attr_handle;
        gatts_char_handle = param->add_char.attr_handle;
        break;

    case ESP_GATTS_CONNECT_EVT:
        ESP_LOGI(TAG, "Client connected, conn_id=%d", param->connect.conn_id);
        g_bridge_state.mode.bleak.gatts_conn_id = param->connect.conn_id;
        g_bridge_state.mode.bleak.client_connected = true;

        /* Update connection parameters */
        esp_ble_conn_update_params_t conn_params = {0};
        memcpy(conn_params.bda, param->connect.remote_bda, sizeof(esp_bd_addr_t));
        conn_params.latency = 0;
        conn_params.max_int = 0x20;
        conn_params.min_int = 0x10;
        conn_params.timeout = 400;
        esp_ble_gap_update_conn_params(&conn_params);
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        ESP_LOGI(TAG, "Client disconnected, reason=%d", param->disconnect.reason);
        g_bridge_state.mode.bleak.client_connected = false;

        /* Restart advertising */
        esp_ble_gap_start_advertising(&adv_params);
        break;

    case ESP_GATTS_WRITE_EVT:
        if (!param->write.is_prep) {
            ESP_LOGI(TAG, "GATT write, handle=%d, len=%d", param->write.handle, param->write.len);

            if (param->write.handle == g_bridge_state.mode.bleak.gatts_char_handle) {
                /* Data received from computer - forward to HM-10 */
                if (ble_bridge_is_hm10_connected()) {
                    ESP_LOGI(TAG_BT_COM, "%.*s", param->write.len, param->write.value);
                    ble_bridge_send_to_hm10(param->write.value, param->write.len);
                } else {
                    ESP_LOGW(TAG, "HM-10 not connected, cannot forward data");
                }
            }

            /* Send response if needed */
            if (param->write.need_rsp) {
                esp_ble_gatts_send_response(gatts_if, param->write.conn_id,
                                           param->write.trans_id, ESP_GATT_OK, NULL);
            }
        }
        break;

    case ESP_GATTS_READ_EVT:
        ESP_LOGI(TAG, "GATT read, handle=%d", param->read.handle);
        esp_gatt_rsp_t rsp;
        memset(&rsp, 0, sizeof(esp_gatt_rsp_t));
        rsp.attr_value.handle = param->read.handle;
        rsp.attr_value.len = 0;
        esp_ble_gatts_send_response(gatts_if, param->read.conn_id,
                                   param->read.trans_id, ESP_GATT_OK, &rsp);
        break;

    case ESP_GATTS_MTU_EVT:
        ESP_LOGI(TAG, "MTU exchange, conn_id=%d, mtu=%d", param->mtu.conn_id, param->mtu.mtu);
        break;

    default:
        break;
    }
}

static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;

    case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
        if (param->adv_start_cmpl.status != ESP_BT_STATUS_SUCCESS) {
            ESP_LOGE(TAG, "Advertising start failed");
        } else {
            ESP_LOGI(TAG, "Advertising started - waiting for client connection");
        }
        break;

    case ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT:
        if (param->adv_stop_cmpl.status != ESP_BT_STATUS_SUCCESS) {
            ESP_LOGE(TAG, "Advertising stop failed");
        } else {
            ESP_LOGI(TAG, "Advertising stopped");
        }
        break;

    case ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT:
        ESP_LOGI(TAG, "Connection params updated: status=%d, min_int=%d, max_int=%d, latency=%d, timeout=%d",
                param->update_conn_params.status,
                param->update_conn_params.min_int,
                param->update_conn_params.max_int,
                param->update_conn_params.latency,
                param->update_conn_params.timeout);
        break;

    default:
        break;
    }
}

static void gatts_event_handler(esp_gatts_cb_event_t event, esp_gatt_if_t gatts_if, esp_ble_gatts_cb_param_t *param)
{
    /* Handle registration */
    if (event == ESP_GATTS_REG_EVT) {
        if (param->reg.status == ESP_GATT_OK) {
            gl_gatts_profile.gatts_if = gatts_if;
            g_bridge_state.mode.bleak.gatts_if = gatts_if;
        } else {
            ESP_LOGE(TAG, "GATT Server registration failed, app_id=%04x, status=%d",
                    param->reg.app_id, param->reg.status);
            return;
        }
    }

    /* Route to profile handler */
    if (gatts_if == ESP_GATT_IF_NONE || gatts_if == gl_gatts_profile.gatts_if) {
        if (gl_gatts_profile.gatts_cb) {
            gl_gatts_profile.gatts_cb(event, gatts_if, param);
        }
    }
}

static void hm10_data_received(const uint8_t *data, size_t len)
{
    /* Log received data */
    ESP_LOGE(TAG_BT_COM, "%.*s", len, data);

    /* Forward to connected Bleak client */
    if (g_bridge_state.mode.bleak.client_connected) {
        bleak_send_to_client(data, len);
    } else {
        ESP_LOGW(TAG, "No Bleak client connected, data not forwarded");
    }
}

esp_err_t bleak_init(const ble_bridge_config_t *config)
{
    esp_err_t ret;

    /* Register GAP callback */
    ret = esp_ble_gap_register_callback(gap_event_handler);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GAP register callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Register GATT Server callback */
    ret = esp_ble_gatts_register_callback(gatts_event_handler);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GATTS register callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Register GATT Server application */
    ret = esp_ble_gatts_app_register(PROFILE_APP_ID);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GATTS app register failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Register callback for HM-10 data */
    ble_bridge_register_recv_callback(hm10_data_received);

    ESP_LOGI(TAG, "Bleak mode initialized");
    ESP_LOGI(TAG, "ESP32 will advertise as: %s", config->bleak.esp32_device_name);

    return ESP_OK;
}

esp_err_t bleak_deinit(void)
{
    ESP_LOGI(TAG, "Bleak mode deinitialized");
    return ESP_OK;
}

esp_err_t bleak_send_to_client(const uint8_t *data, size_t len)
{
    if (!g_bridge_state.mode.bleak.client_connected) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t ret = esp_ble_gatts_send_indicate(
        g_bridge_state.mode.bleak.gatts_if,
        g_bridge_state.mode.bleak.gatts_conn_id,
        g_bridge_state.mode.bleak.gatts_char_handle,
        len,
        (uint8_t *)data,
        false);  /* Don't need confirmation (use notify instead of indicate) */

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Send to client failed: %s", esp_err_to_name(ret));
    }

    return ret;
}

bool bleak_is_client_connected(void)
{
    return g_bridge_state.mode.bleak.client_connected;
}
