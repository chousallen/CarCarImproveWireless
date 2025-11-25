/**
 * @file ble_bridge_internal.h
 * @brief Internal definitions for BLE Bridge module
 *
 * This header is for internal use within the component only.
 */

#ifndef BLE_BRIDGE_INTERNAL_H
#define BLE_BRIDGE_INTERNAL_H

#include "ble_bridge.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_gap_ble_api.h"
#include "esp_gattc_api.h"
#include "esp_gatts_api.h"
#include "esp_gatt_defs.h"
#include "esp_bt_main.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Logging tags */
#define TAG "BLE_BRIDGE"
#define TAG_BT_COM "bt_com"

/* Bridge state structure */
typedef struct {
    ble_bridge_config_t config;
    bool initialized;
    bool hm10_connected;
    ble_bridge_recv_cb_t recv_callback;

    /* GATT Client state (HM-10 connection) */
    struct {
        uint16_t gattc_if;
        uint16_t conn_id;
        uint16_t char_handle;
        uint16_t service_start_handle;
        uint16_t service_end_handle;
        esp_bd_addr_t remote_bda;
    } gattc;

    /* Mode-specific state */
    union {
        struct {
            /* Transceiver mode state */
            uint8_t *uart_buffer;
            TaskHandle_t uart_task_handle;
        } transceiver;

        struct {
            /* Bleak mode state */
            uint16_t gatts_if;
            uint16_t gatts_conn_id;
            uint16_t gatts_char_handle;
            uint16_t gatts_service_handle;
            bool client_connected;
        } bleak;
    } mode;
} ble_bridge_state_t;

/* Global state - defined in ble_bridge.c */
extern ble_bridge_state_t g_bridge_state;

/* Internal functions - GATT Client (ble_gattc.c) */
esp_err_t ble_gattc_init(const ble_bridge_config_t *config);
esp_err_t ble_gattc_send_data(const uint8_t *data, size_t len);
bool ble_gattc_is_connected(void);

/* Internal functions - Transceiver mode (transceiver.c) */
esp_err_t transceiver_init(const ble_bridge_config_t *config);
esp_err_t transceiver_deinit(void);

/* Internal functions - Bleak mode (bleak.c) */
esp_err_t bleak_init(const ble_bridge_config_t *config);
esp_err_t bleak_deinit(void);
esp_err_t bleak_send_to_client(const uint8_t *data, size_t len);
bool bleak_is_client_connected(void);

/* Utility functions */
static inline void ble_bridge_log_hex(const char *tag, const uint8_t *data, size_t len) {
    esp_log_buffer_hex(tag, data, len);
}

#ifdef __cplusplus
}
#endif

#endif // BLE_BRIDGE_INTERNAL_H
