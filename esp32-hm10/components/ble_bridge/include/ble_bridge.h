/**
 * @file ble_bridge.h
 * @brief BLE Bridge Module - Public API
 *
 * This module provides a bridge between computer and Arduino via BLE.
 * Supports two modes:
 *   - Transceiver: Computer (UART) <-> ESP32 <-> HM-10 <-> Arduino
 *   - Bleak: Computer (BLE) <-> ESP32 <-> HM-10 <-> Arduino
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Bridge operating modes
 */
typedef enum {
    BLE_BRIDGE_MODE_TRANSCEIVER,  /**< UART to BLE bridge mode */
    BLE_BRIDGE_MODE_BLEAK,        /**< BLE Server to BLE Client bridge mode */
} ble_bridge_mode_t;

/**
 * @brief Bridge configuration structure
 */
typedef struct {
    ble_bridge_mode_t mode;           /**< Operating mode */
    const char *hm10_device_name;     /**< HM-10 BLE device name to connect to */
    uint16_t hm10_service_uuid;       /**< HM-10 service UUID (default: 0xFFE0) */
    uint16_t hm10_char_uuid;          /**< HM-10 characteristic UUID (default: 0xFFE1) */

    /* Transceiver mode specific */
    struct {
        uint32_t uart_baud_rate;      /**< UART baud rate (default: 115200) */
        uint16_t uart_buf_size;       /**< UART buffer size (default: 1024) */
    } transceiver;

    /* Bleak mode specific */
    struct {
        const char *esp32_device_name;  /**< ESP32 advertised name (default: "ESP32_BLE_Bridge") */
        uint16_t esp32_service_uuid;    /**< ESP32 service UUID (default: 0xFF00) */
        uint16_t esp32_char_uuid;       /**< ESP32 characteristic UUID (default: 0xFF01) */
    } bleak;
} ble_bridge_config_t;

/**
 * @brief Callback function type for receiving data from HM-10
 *
 * @param data Pointer to received data
 * @param len Length of received data
 */
typedef void (*ble_bridge_recv_cb_t)(const uint8_t *data, size_t len);

/**
 * @brief Get default configuration
 *
 * @param mode Operating mode
 * @return Default configuration for the specified mode
 */
ble_bridge_config_t ble_bridge_get_default_config(ble_bridge_mode_t mode);

/**
 * @brief Initialize BLE bridge module
 *
 * This function initializes the BLE stack, connects to HM-10, and sets up
 * the selected operating mode (UART or BLE server).
 *
 * @param config Pointer to configuration structure
 * @return
 *     - ESP_OK: Success
 *     - ESP_ERR_INVALID_ARG: Invalid configuration
 *     - ESP_FAIL: Initialization failed
 */
esp_err_t ble_bridge_init(const ble_bridge_config_t *config);

/**
 * @brief Deinitialize BLE bridge module
 *
 * @return ESP_OK on success
 */
esp_err_t ble_bridge_deinit(void);

/**
 * @brief Send data to HM-10
 *
 * This function sends data from computer to HM-10 (and then to Arduino).
 * In transceiver mode, this is called internally from UART task.
 * In bleak mode, this is called when BLE client writes data.
 *
 * @param data Pointer to data to send
 * @param len Length of data
 * @return
 *     - ESP_OK: Success
 *     - ESP_ERR_INVALID_STATE: Not connected to HM-10
 *     - ESP_FAIL: Send failed
 */
esp_err_t ble_bridge_send_to_hm10(const uint8_t *data, size_t len);

/**
 * @brief Register callback for receiving data from HM-10
 *
 * The callback will be invoked when data is received from HM-10.
 * This is useful for custom processing in application code.
 *
 * @param callback Callback function pointer
 * @return ESP_OK on success
 */
esp_err_t ble_bridge_register_recv_callback(ble_bridge_recv_cb_t callback);

/**
 * @brief Check if connected to HM-10
 *
 * @return true if connected, false otherwise
 */
bool ble_bridge_is_hm10_connected(void);

/**
 * @brief Check if client is connected (Bleak mode only)
 *
 * @return true if BLE client connected, false otherwise or if in transceiver mode
 */
bool ble_bridge_is_client_connected(void);

#ifdef __cplusplus
}
#endif

#endif // BLE_BRIDGE_H
