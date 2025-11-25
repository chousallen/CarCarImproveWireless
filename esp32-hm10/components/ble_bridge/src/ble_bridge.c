/**
 * @file ble_bridge.c
 * @brief BLE Bridge Module - Main coordinator
 */

#include <string.h>
#include "ble_bridge_internal.h"
#include "nvs_flash.h"
#include "esp_gatt_common_api.h"

/* Global state */
ble_bridge_state_t g_bridge_state = {0};

ble_bridge_config_t ble_bridge_get_default_config(ble_bridge_mode_t mode)
{
    ble_bridge_config_t config = {
        .mode = mode,
        .hm10_device_name = "HMSoft",
        .hm10_service_uuid = 0xFFE0,
        .hm10_char_uuid = 0xFFE1,
    };

    if (mode == BLE_BRIDGE_MODE_TRANSCEIVER) {
        config.transceiver.uart_baud_rate = 115200;
        config.transceiver.uart_buf_size = 1024;
    } else {
        config.bleak.esp32_device_name = "ESP32_BLE_Bridge";
        config.bleak.esp32_service_uuid = 0xFF00;
        config.bleak.esp32_char_uuid = 0xFF01;
    }

    return config;
}

esp_err_t ble_bridge_init(const ble_bridge_config_t *config)
{
    if (!config) {
        ESP_LOGE(TAG, "Invalid config");
        return ESP_ERR_INVALID_ARG;
    }

    if (g_bridge_state.initialized) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing BLE Bridge - Mode: %s",
             config->mode == BLE_BRIDGE_MODE_TRANSCEIVER ? "Transceiver" : "Bleak");

    /* Store config */
    memcpy(&g_bridge_state.config, config, sizeof(ble_bridge_config_t));

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Release classic BT memory */
    ret = esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT mem release failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Initialize BT controller */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ret = esp_bt_controller_init(&bt_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Initialize Bluedroid */
    ret = esp_bluedroid_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bluedroid_enable();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Set MTU */
    esp_err_t local_mtu_ret = esp_ble_gatt_set_local_mtu(500);
    if (local_mtu_ret != ESP_OK) {
        ESP_LOGW(TAG, "Set MTU failed: %s", esp_err_to_name(local_mtu_ret));
    }

    /* Initialize mode-specific functionality */
    if (config->mode == BLE_BRIDGE_MODE_TRANSCEIVER) {
        ret = transceiver_init(config);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Transceiver init failed");
            goto cleanup;
        }
    } else {
        ret = bleak_init(config);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Bleak init failed");
            goto cleanup;
        }
    }

    /* Initialize GATT client (HM-10 connection) */
    ret = ble_gattc_init(config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "GATT client init failed");
        goto cleanup;
    }

    g_bridge_state.initialized = true;
    ESP_LOGI(TAG, "BLE Bridge initialized successfully");
    ESP_LOGI(TAG, "Will connect to HM-10: %s", config->hm10_device_name);

    return ESP_OK;

cleanup:
    ble_bridge_deinit();
    return ret;
}

esp_err_t ble_bridge_deinit(void)
{
    if (!g_bridge_state.initialized) {
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Deinitializing BLE Bridge");

    /* Deinit mode-specific */
    if (g_bridge_state.config.mode == BLE_BRIDGE_MODE_TRANSCEIVER) {
        transceiver_deinit();
    } else {
        bleak_deinit();
    }

    /* Deinit Bluetooth */
    esp_bluedroid_disable();
    esp_bluedroid_deinit();
    esp_bt_controller_disable();
    esp_bt_controller_deinit();

    memset(&g_bridge_state, 0, sizeof(g_bridge_state));

    ESP_LOGI(TAG, "BLE Bridge deinitialized");
    return ESP_OK;
}

esp_err_t ble_bridge_send_to_hm10(const uint8_t *data, size_t len)
{
    if (!g_bridge_state.initialized) {
        ESP_LOGE(TAG, "Not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    if (!g_bridge_state.hm10_connected) {
        ESP_LOGW(TAG, "HM-10 not connected");
        return ESP_ERR_INVALID_STATE;
    }

    ESP_LOGI(TAG_BT_COM, "%.*s", len, data);
    return ble_gattc_send_data(data, len);
}

esp_err_t ble_bridge_register_recv_callback(ble_bridge_recv_cb_t callback)
{
    g_bridge_state.recv_callback = callback;
    return ESP_OK;
}

bool ble_bridge_is_hm10_connected(void)
{
    return g_bridge_state.hm10_connected;
}

bool ble_bridge_is_client_connected(void)
{
    if (g_bridge_state.config.mode == BLE_BRIDGE_MODE_BLEAK) {
        return bleak_is_client_connected();
    }
    return false;
}
