/**
 * @file ble_gattc.c
 * @brief GATT Client implementation for HM-10 connection
 */

#include <string.h>
#include "ble_bridge_internal.h"

#define INVALID_HANDLE 0
#define PROFILE_APP_ID 0

/* GATT client profile structure */
struct gattc_profile_inst {
    esp_gattc_cb_t gattc_cb;
    uint16_t gattc_if;
    uint16_t app_id;
    uint16_t conn_id;
    uint16_t service_start_handle;
    uint16_t service_end_handle;
    uint16_t char_handle;
    esp_bd_addr_t remote_bda;
};

/* Forward declarations */
static void gattc_profile_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param);
static void esp_gap_cb(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);
static void esp_gattc_cb(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param);

/* Profile instance */
static struct gattc_profile_inst gl_profile = {
    .gattc_cb = gattc_profile_event_handler,
    .gattc_if = ESP_GATT_IF_NONE,
    .app_id = PROFILE_APP_ID,
};

/* Connection state */
static bool scanning = false;
static bool service_found = false;

/* Scan parameters */
static esp_ble_scan_params_t ble_scan_params = {
    .scan_type              = BLE_SCAN_TYPE_ACTIVE,
    .own_addr_type          = BLE_ADDR_TYPE_PUBLIC,
    .scan_filter_policy     = BLE_SCAN_FILTER_ALLOW_ALL,
    .scan_interval          = 0x50,
    .scan_window            = 0x30,
    .scan_duplicate         = BLE_SCAN_DUPLICATE_DISABLE
};

static void gattc_profile_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param)
{
    esp_ble_gattc_cb_param_t *p_data = (esp_ble_gattc_cb_param_t *)param;

    switch (event) {
    case ESP_GATTC_REG_EVT:
        ESP_LOGI(TAG, "GATT Client registered, starting scan");
        esp_ble_gap_set_scan_params(&ble_scan_params);
        break;

    case ESP_GATTC_CONNECT_EVT:
        ESP_LOGI(TAG, "Connected to HM-10, conn_id=%d", p_data->connect.conn_id);
        g_bridge_state.gattc.conn_id = p_data->connect.conn_id;
        memcpy(g_bridge_state.gattc.remote_bda, p_data->connect.remote_bda, sizeof(esp_bd_addr_t));

        /* Configure MTU */
        esp_err_t mtu_ret = esp_ble_gattc_send_mtu_req(gattc_if, p_data->connect.conn_id);
        if (mtu_ret != ESP_OK) {
            ESP_LOGE(TAG, "MTU request failed: %s", esp_err_to_name(mtu_ret));
        }
        break;

    case ESP_GATTC_OPEN_EVT:
        if (param->open.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Open failed, status=%d", p_data->open.status);
            g_bridge_state.hm10_connected = false;
            break;
        }
        ESP_LOGI(TAG, "Connection opened successfully");
        break;

    case ESP_GATTC_DIS_SRVC_CMPL_EVT:
        if (param->dis_srvc_cmpl.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Service discovery failed, status=%d", param->dis_srvc_cmpl.status);
            break;
        }
        ESP_LOGI(TAG, "Service discovery complete");
        esp_ble_gattc_search_service(gattc_if, param->cfg_mtu.conn_id, NULL);
        break;

    case ESP_GATTC_CFG_MTU_EVT:
        if (param->cfg_mtu.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "MTU config failed, status=%d", param->cfg_mtu.status);
        }
        ESP_LOGI(TAG, "MTU configured: %d", param->cfg_mtu.mtu);
        break;

    case ESP_GATTC_SEARCH_RES_EVT: {
        if (p_data->search_res.srvc_id.uuid.len == ESP_UUID_LEN_16 &&
            p_data->search_res.srvc_id.uuid.uuid.uuid16 == g_bridge_state.config.hm10_service_uuid) {
            ESP_LOGI(TAG, "Found HM-10 service (UUID=0x%04X)", g_bridge_state.config.hm10_service_uuid);
            service_found = true;
            g_bridge_state.gattc.service_start_handle = p_data->search_res.start_handle;
            g_bridge_state.gattc.service_end_handle = p_data->search_res.end_handle;
        }
        break;
    }

    case ESP_GATTC_SEARCH_CMPL_EVT:
        if (p_data->search_cmpl.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Search complete failed, status=%d", p_data->search_cmpl.status);
            break;
        }

        if (!service_found) {
            ESP_LOGE(TAG, "HM-10 service not found!");
            break;
        }

        /* Get characteristics */
        uint16_t count = 0;
        esp_gatt_status_t status = esp_ble_gattc_get_attr_count(
            gattc_if,
            p_data->search_cmpl.conn_id,
            ESP_GATT_DB_CHARACTERISTIC,
            g_bridge_state.gattc.service_start_handle,
            g_bridge_state.gattc.service_end_handle,
            INVALID_HANDLE,
            &count);

        if (status != ESP_GATT_OK || count == 0) {
            ESP_LOGE(TAG, "Failed to get characteristics");
            break;
        }

        esp_gattc_char_elem_t *char_elem_result = malloc(sizeof(esp_gattc_char_elem_t) * count);
        if (!char_elem_result) {
            ESP_LOGE(TAG, "Memory allocation failed");
            break;
        }

        status = esp_ble_gattc_get_all_char(
            gattc_if,
            p_data->search_cmpl.conn_id,
            g_bridge_state.gattc.service_start_handle,
            g_bridge_state.gattc.service_end_handle,
            char_elem_result,
            &count,
            0);

        if (status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Failed to get all characteristics");
            free(char_elem_result);
            break;
        }

        /* Find target characteristic */
        for (int i = 0; i < count; i++) {
            if (char_elem_result[i].uuid.len == ESP_UUID_LEN_16 &&
                char_elem_result[i].uuid.uuid.uuid16 == g_bridge_state.config.hm10_char_uuid) {
                ESP_LOGI(TAG, "Found HM-10 characteristic (UUID=0x%04X)", g_bridge_state.config.hm10_char_uuid);
                g_bridge_state.gattc.char_handle = char_elem_result[i].char_handle;

                /* Register for notifications */
                esp_ble_gattc_register_for_notify(gattc_if, g_bridge_state.gattc.remote_bda, char_elem_result[i].char_handle);
                break;
            }
        }
        free(char_elem_result);
        break;

    case ESP_GATTC_REG_FOR_NOTIFY_EVT: {
        if (p_data->reg_for_notify.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Register for notify failed, status=%d", p_data->reg_for_notify.status);
            break;
        }

        /* Get CCCD descriptor */
        uint16_t count = 0;
        esp_gatt_status_t ret_status = esp_ble_gattc_get_attr_count(
            gattc_if,
            g_bridge_state.gattc.conn_id,
            ESP_GATT_DB_DESCRIPTOR,
            g_bridge_state.gattc.service_start_handle,
            g_bridge_state.gattc.service_end_handle,
            g_bridge_state.gattc.char_handle,
            &count);

        if (ret_status != ESP_GATT_OK || count == 0) {
            ESP_LOGE(TAG, "Failed to get descriptors");
            break;
        }

        esp_gattc_descr_elem_t *descr_elem_result = malloc(sizeof(esp_gattc_descr_elem_t) * count);
        if (!descr_elem_result) {
            ESP_LOGE(TAG, "Memory allocation failed");
            break;
        }

        ret_status = esp_ble_gattc_get_all_descr(
            gattc_if,
            g_bridge_state.gattc.conn_id,
            g_bridge_state.gattc.char_handle,
            descr_elem_result,
            &count,
            0);

        if (ret_status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Failed to get all descriptors");
            free(descr_elem_result);
            break;
        }

        /* Write to CCCD to enable notifications */
        uint16_t notify_en = 1;
        for (int i = 0; i < count; ++i) {
            if (descr_elem_result[i].uuid.len == ESP_UUID_LEN_16 &&
                descr_elem_result[i].uuid.uuid.uuid16 == ESP_GATT_UUID_CHAR_CLIENT_CONFIG) {
                esp_ble_gattc_write_char_descr(
                    gattc_if,
                    g_bridge_state.gattc.conn_id,
                    descr_elem_result[i].handle,
                    sizeof(notify_en),
                    (uint8_t *)&notify_en,
                    ESP_GATT_WRITE_TYPE_RSP,
                    ESP_GATT_AUTH_REQ_NONE);
                break;
            }
        }
        free(descr_elem_result);
        break;
    }

    case ESP_GATTC_NOTIFY_EVT:
        /* Forward data to application callback or mode handler */
        if (g_bridge_state.recv_callback) {
            g_bridge_state.recv_callback(p_data->notify.value, p_data->notify.value_len);
        } else {
            /* Default: log received data */
            ESP_LOGE(TAG_BT_COM, "%.*s", p_data->notify.value_len, p_data->notify.value);
        }
        break;

    case ESP_GATTC_WRITE_CHAR_EVT:
        if (p_data->write.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Write characteristic failed, status=%d", p_data->write.status);
        }
        break;

    case ESP_GATTC_WRITE_DESCR_EVT:
        if (p_data->write.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Write descriptor failed, status=%d", p_data->write.status);
        } else {
            ESP_LOGI(TAG, "Notifications enabled - HM-10 connection ready");
            g_bridge_state.hm10_connected = true;
        }
        break;

    case ESP_GATTC_DISCONNECT_EVT:
        ESP_LOGI(TAG, "Disconnected from HM-10, reason=%d", p_data->disconnect.reason);
        g_bridge_state.hm10_connected = false;
        service_found = false;
        g_bridge_state.gattc.char_handle = INVALID_HANDLE;

        /* Restart scanning after delay */
        ESP_LOGI(TAG, "Restarting scan in 2 seconds...");
        vTaskDelay(2000 / portTICK_PERIOD_MS);
        esp_ble_gap_start_scanning(30);
        break;

    default:
        break;
    }
}

static void esp_gap_cb(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    uint8_t *adv_name = NULL;
    uint8_t adv_name_len = 0;

    switch (event) {
    case ESP_GAP_BLE_SCAN_PARAM_SET_COMPLETE_EVT:
        ESP_LOGI(TAG, "Scan parameters set");
        esp_ble_gap_start_scanning(30);
        break;

    case ESP_GAP_BLE_SCAN_START_COMPLETE_EVT:
        if (param->scan_start_cmpl.status != ESP_BT_STATUS_SUCCESS) {
            ESP_LOGE(TAG, "Scan start failed, status=%x", param->scan_start_cmpl.status);
            break;
        }
        scanning = true;
        ESP_LOGI(TAG, "Scanning for HM-10: %s", g_bridge_state.config.hm10_device_name);
        break;

    case ESP_GAP_BLE_SCAN_RESULT_EVT: {
        esp_ble_gap_cb_param_t *scan_result = (esp_ble_gap_cb_param_t *)param;

        if (scan_result->scan_rst.search_evt == ESP_GAP_SEARCH_INQ_RES_EVT) {
            /* Parse device name from advertisement */
            adv_name = esp_ble_resolve_adv_data(
                scan_result->scan_rst.ble_adv,
                ESP_BLE_AD_TYPE_NAME_CMPL,
                &adv_name_len);

            if (adv_name != NULL) {
                size_t target_name_len = strlen(g_bridge_state.config.hm10_device_name);
                if (target_name_len == adv_name_len &&
                    strncmp((char *)adv_name, g_bridge_state.config.hm10_device_name, adv_name_len) == 0) {

                    ESP_LOGI(TAG, "Found target HM-10: %s", g_bridge_state.config.hm10_device_name);
                    esp_log_buffer_hex(TAG, scan_result->scan_rst.bda, 6);

                    if (!g_bridge_state.hm10_connected) {
                        ESP_LOGI(TAG, "Connecting to HM-10...");
                        esp_ble_gap_stop_scanning();

                        memcpy(g_bridge_state.gattc.remote_bda, scan_result->scan_rst.bda, sizeof(esp_bd_addr_t));
                        esp_ble_gattc_open(
                            g_bridge_state.gattc.gattc_if,
                            g_bridge_state.gattc.remote_bda,
                            scan_result->scan_rst.ble_addr_type,
                            true);
                    }
                }
            }
        } else if (scan_result->scan_rst.search_evt == ESP_GAP_SEARCH_INQ_CMPL_EVT) {
            scanning = false;
        }
        break;
    }

    case ESP_GAP_BLE_SCAN_STOP_COMPLETE_EVT:
        if (param->scan_stop_cmpl.status != ESP_BT_STATUS_SUCCESS) {
            ESP_LOGE(TAG, "Scan stop failed, status=%x", param->scan_stop_cmpl.status);
        } else {
            scanning = false;
            ESP_LOGI(TAG, "Scan stopped");
        }
        break;

    default:
        break;
    }
}

static void esp_gattc_cb(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if, esp_ble_gattc_cb_param_t *param)
{
    /* Handle registration */
    if (event == ESP_GATTC_REG_EVT) {
        if (param->reg.status == ESP_GATT_OK) {
            gl_profile.gattc_if = gattc_if;
            g_bridge_state.gattc.gattc_if = gattc_if;
        } else {
            ESP_LOGE(TAG, "GATT client registration failed, app_id=%04x, status=%d",
                    param->reg.app_id, param->reg.status);
            return;
        }
    }

    /* Route to profile handler */
    if (gattc_if == ESP_GATT_IF_NONE || gattc_if == gl_profile.gattc_if) {
        if (gl_profile.gattc_cb) {
            gl_profile.gattc_cb(event, gattc_if, param);
        }
    }
}

esp_err_t ble_gattc_init(const ble_bridge_config_t *config)
{
    esp_err_t ret;

    /* Register GAP callback */
    ret = esp_ble_gap_register_callback(esp_gap_cb);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GAP register callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Register GATT client callback */
    ret = esp_ble_gattc_register_callback(esp_gattc_cb);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GATTC register callback failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Register GATT client application */
    ret = esp_ble_gattc_app_register(PROFILE_APP_ID);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GATTC app register failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "GATT Client initialized");
    return ESP_OK;
}

esp_err_t ble_gattc_send_data(const uint8_t *data, size_t len)
{
    if (!g_bridge_state.hm10_connected) {
        return ESP_ERR_INVALID_STATE;
    }

    if (g_bridge_state.gattc.char_handle == INVALID_HANDLE) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t ret = esp_ble_gattc_write_char(
        g_bridge_state.gattc.gattc_if,
        g_bridge_state.gattc.conn_id,
        g_bridge_state.gattc.char_handle,
        len,
        (uint8_t *)data,
        ESP_GATT_WRITE_TYPE_RSP,
        ESP_GATT_AUTH_REQ_NONE);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Write failed: %s", esp_err_to_name(ret));
    }

    return ret;
}

bool ble_gattc_is_connected(void)
{
    return g_bridge_state.hm10_connected;
}
