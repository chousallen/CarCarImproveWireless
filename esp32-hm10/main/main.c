/**
 * BLE Bridge Example
 *
 * This example demonstrates using the ble_bridge component.
 *
 * To switch modes, simply change MODE_SELECT below:
 * - MODE_SELECT 0: Transceiver mode (UART bridge)
 *   Computer (UART) <-> ESP32 <-> HM-10 <-> Arduino
 *
 * - MODE_SELECT 1: Bleak mode (BLE server)
 *   Computer (BLE/Bleak) <-> ESP32 <-> HM-10 <-> Arduino
 */

#include "esp_log.h"
#include "ble_bridge.h"

#define MODE_SELECT                0               // 0 for Transceiver, 1 for Bleak
#define UART_BAUD_RATE             115200
#define UART_BUFFER_SIZE           1024
#define DEVICE_NAME                "HMSoft"        // Name of the HM-10 device
#define ESP32_DEVICE_NAME          "ESP32_Bridge"  // Name advertised to Bleak clients

static const char *TAG = "MAIN";

void app_main(void)
{
    ESP_LOGI(TAG, "Starting BLE Bridge Example");

#if MODE_SELECT == 0
    /* ===== TRANSCEIVER MODE ===== */
    ESP_LOGI(TAG, "Mode: Transceiver (UART Bridge)");

    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = DEVICE_NAME;
    config.transceiver.uart_baud_rate = UART_BAUD_RATE;
    config.transceiver.uart_buf_size = UART_BUFFER_SIZE;

#elif MODE_SELECT == 1
    /* ===== BLEAK MODE ===== */
    ESP_LOGI(TAG, "Mode: Bleak (BLE Server)");

    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_BLEAK);
    config.hm10_device_name = DEVICE_NAME;
    config.bleak.esp32_device_name = ESP32_DEVICE_NAME;

#else
    #error "Invalid MODE_SELECT value. Must be 0 (Transceiver) or 1 (Bleak)"
#endif

    /* Initialize BLE bridge */
    esp_err_t ret = ble_bridge_init(&config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BLE Bridge initialization failed: %s", esp_err_to_name(ret));
        return;
    }

    ESP_LOGI(TAG, "BLE Bridge initialized successfully");

#if MODE_SELECT == 0
    ESP_LOGI(TAG, "Ready to receive UART messages");
#elif MODE_SELECT == 1
    ESP_LOGI(TAG, "Ready to accept BLE connections from Bleak clients");
#endif
}
