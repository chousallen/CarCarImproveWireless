# BLE Bridge Component

ESP-IDF component for bridging communication between a computer and Arduino via BLE (HM-10 module).

## Features

- **Two operating modes**:
  - **Transceiver Mode**: Computer (UART) ↔ ESP32 ↔ HM-10 ↔ Arduino
  - **Bleak Mode**: Computer (BLE) ↔ ESP32 ↔ HM-10 ↔ Arduino

- **Clean API**: Easy to integrate into any ESP32 project
- **Configurable**: Support for custom UUIDs, baud rates, etc.
- **Auto-reconnect**: Automatically reconnects to HM-10 if disconnected

## Usage

### Basic Example

```c
#include "ble_bridge.h"

void app_main(void) {
    // Get default configuration for transceiver mode
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = "HMSoft";  // Your HM-10 device name

    // Initialize bridge
    esp_err_t ret = ble_bridge_init(&config);
    if (ret != ESP_OK) {
        ESP_LOGE("APP", "Bridge init failed: %s", esp_err_to_name(ret));
        return;
    }

    ESP_LOGI("APP", "BLE Bridge initialized successfully");
}
```

### Transceiver Mode

```c
ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
config.hm10_device_name = "HMSoft";
config.transceiver.uart_baud_rate = 115200;
ble_bridge_init(&config);
```

### Bleak Mode

```c
ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_BLEAK);
config.hm10_device_name = "HMSoft";
config.bleak.esp32_device_name = "ESP32_Bridge";
ble_bridge_init(&config);
```

### Custom Receive Callback

```c
void my_recv_callback(const uint8_t *data, size_t len) {
    ESP_LOGI("APP", "Received from Arduino: %.*s", len, data);
    // Custom processing here
}

ble_bridge_register_recv_callback(my_recv_callback);
```

## API Reference

See [ble_bridge.h](include/ble_bridge.h) for complete API documentation.

## Dependencies

- ESP-IDF v4.4 or later
- Bluetooth (Bluedroid) enabled in menuconfig

## License

Same as the parent project.
