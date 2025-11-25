# BLE Bridge Component

A reusable ESP-IDF component for bridging BLE communication between a computer and HM-10 BLE module.

## Features

- **Two Operating Modes**: Transceiver (UART) and Bleak (BLE server)
- **Clean API**: Simple initialization and configuration
- **Auto-reconnect**: Automatically reconnects to HM-10 if disconnected
- **Modular Design**: Separated GATT client, transceiver, and bleak functionality
- **ESP-IDF Component**: Easy integration into any ESP-IDF project

## Architecture

```
Computer                ESP32                   HM-10           Endpoint Device
   |                      |                       |                 |
   |   (Mode-dependent)   |    (GATT Client)      |                 |
   |<-------------------->|<--------------------->|<--------------->|
                          |                       |
        Transceiver: UART | Bleak: BLE Server     |
```

**Transceiver Mode**: `Computer (UART) ↔ ESP32 ↔ HM-10 ↔ [Device]`
**Bleak Mode**: `Computer (BLE) ↔ ESP32 ↔ HM-10 ↔ [Device]`

> **Note**: Sample Python client code for testing both modes is available in [BT_demo](https://github.com/samklin33/CarCarBluetoothDemo.git).

---

## Quick Start

### Transceiver Mode (UART)

```c
#include "ble_bridge.h"

#define MODE_SELECT 0  // 0 for Transceiver, 1 for Bleak

void app_main(void)
{
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = "HMSoft";  // Your HM-10's name
    config.transceiver.uart_baud_rate = 115200;

    esp_err_t ret = ble_bridge_init(&config);
    if (ret != ESP_OK) {
        ESP_LOGE("APP", "Init failed: %s", esp_err_to_name(ret));
    }
}
```

### Bleak Mode (BLE Server)

```c
#include "ble_bridge.h"

#define MODE_SELECT 1  // 0 for Transceiver, 1 for Bleak

void app_main(void)
{
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_BLEAK);
    config.hm10_device_name = "HMSoft";
    config.bleak.esp32_device_name = "ESP32_Bridge";

    esp_err_t ret = ble_bridge_init(&config);
    if (ret != ESP_OK) {
        ESP_LOGE("APP", "Init failed: %s", esp_err_to_name(ret));
    }
}
```

---

## API Reference

### Initialization

```c
// Get default configuration
ble_bridge_config_t ble_bridge_get_default_config(ble_bridge_mode_t mode);

// Initialize bridge
esp_err_t ble_bridge_init(const ble_bridge_config_t *config);

// Deinitialize
esp_err_t ble_bridge_deinit(void);
```

### Communication

```c
// Send data to HM-10
esp_err_t ble_bridge_send_to_hm10(const uint8_t *data, size_t len);

// Register callback for data from HM-10
esp_err_t ble_bridge_register_recv_callback(ble_bridge_recv_cb_t callback);
```

### Status Check

```c
// Check HM-10 connection
bool ble_bridge_is_hm10_connected(void);

// Check client connection (Bleak mode only)
bool ble_bridge_is_client_connected(void);
```

---

## Configuration

### Configuration Structure

```c
typedef struct {
    ble_bridge_mode_t mode;           // BLE_BRIDGE_MODE_TRANSCEIVER or BLE_BRIDGE_MODE_BLEAK
    const char *hm10_device_name;     // HM-10 device name
    uint16_t hm10_service_uuid;       // Default: 0xFFE0
    uint16_t hm10_char_uuid;          // Default: 0xFFE1

    union {
        struct {
            uint32_t uart_baud_rate;  // Default: 115200
            size_t uart_buf_size;     // Default: 1024
        } transceiver;

        struct {
            const char *esp32_device_name;  // Default: "ESP32_BLE_Bridge"
            uint16_t esp32_service_uuid;    // Default: 0xFF00
            uint16_t esp32_char_uuid;       // Default: 0xFF01
        } bleak;
    };
} ble_bridge_config_t;
```

### Default Values

**Common:**
- HM-10 Device Name: `"HMSoft"`
- HM-10 Service UUID: `0xFFE0`
- HM-10 Characteristic UUID: `0xFFE1`

**Transceiver Mode:**
- UART Baud Rate: `115200`
- UART Buffer Size: `1024`

**Bleak Mode:**
- ESP32 Device Name: `"ESP32_BLE_Bridge"`
- ESP32 Service UUID: `0xFF00`
- ESP32 Characteristic UUID: `0xFF01`

---

## Mode Selection Pattern

The example in `main/main.c` demonstrates an easy mode switching pattern using preprocessor directives:

```c
/* ========== MODE SELECTION ========== */
#define MODE_SELECT 0  // 0 for Transceiver, 1 for Bleak

/* ========== CONFIGURATION ========== */
#define DEVICE_NAME                "HMSoft"
#define UART_BAUD_RATE             115200
#define ESP32_DEVICE_NAME          "ESP32_Bridge"

void app_main(void)
{
#if MODE_SELECT == 0
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = DEVICE_NAME;
    config.transceiver.uart_baud_rate = UART_BAUD_RATE;
#elif MODE_SELECT == 1
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_BLEAK);
    config.hm10_device_name = DEVICE_NAME;
    config.bleak.esp32_device_name = ESP32_DEVICE_NAME;
#endif

    ble_bridge_init(&config);
}
```

Simply change `MODE_SELECT` to switch between modes, then rebuild and flash.

---

## Troubleshooting

### HM-10 Not Found

- Verify device name matches exactly (use BLE scanner app)
- Check HM-10 is powered and advertising
- Ensure HM-10 is not connected to another device
- Reduce distance between ESP32 and HM-10

### Connection Drops

- Check HM-10 power supply (insufficient power causes drops)
- Update HM-10 firmware if available
- Check disconnect reason in ESP-IDF logs

### Build Errors

**Error**: `ble_bridge.h: No such file or directory`  
**Solution**: Add `REQUIRES ble_bridge` to `main/CMakeLists.txt`

**Error**: Bluetooth not enabled  
**Solution**: Create `sdkconfig.defaults` with Bluetooth configuration (see Integration section)

**Error**: `unknown type name 'bool'`  
**Solution**: Already fixed - `ble_bridge.h` includes `<stdbool.h>`

### UART Issues (Transceiver Mode)

- Verify baud rate matches your terminal (default: 115200)
- Check USB cable supports data transfer (not power-only)
- Ensure correct COM port selected
- Try different USB port or cable

### Bleak Mode Issues

- Verify ESP32 is advertising (check monitor logs)
- Check device name matches exactly
- Ensure Bluetooth 4.0+ (BLE) enabled on computer
- Reduce distance between computer and ESP32

---

## Component Structure

```
components/ble_bridge/
├── include/
│   └── ble_bridge.h              # Public API
├── src/
│   ├── ble_bridge.c              # Main coordinator
│   ├── ble_bridge_internal.h     # Internal definitions
│   ├── ble_gattc.c              # HM-10 GATT client
│   ├── transceiver.c            # UART mode implementation
│   └── bleak.c                   # BLE server mode implementation
├── CMakeLists.txt
└── README.md                     # Component overview
```

---

## Logging

Two logging tags are used:

- `ble_bridge` - System logs (connection status, errors, initialization)
- `bt_com` - Communication data (TX/RX messages)

**Filter logs:**
```bash
# Show only BLE communication data
idf.py monitor --print-filter bt_com

# Show everything except BLE data
idf.py monitor --print-filter "*:I" --print-filter "bt_com:N"
```

---

## Advanced Usage

### Custom Data Processing

```c
void my_handler(const uint8_t *data, size_t len) {
    ESP_LOGI("APP", "Received %d bytes from HM-10", len);
    // Custom processing here
}

void app_main(void) {
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = "HMSoft";
    ble_bridge_init(&config);
    ble_bridge_register_recv_callback(my_handler);
}
```

### Status Monitoring

```c
void status_task(void *arg) {
    while (1) {
        ESP_LOGI("STATUS", "HM-10: %s, Client: %s",
                 ble_bridge_is_hm10_connected() ? "Connected" : "Disconnected",
                 ble_bridge_is_client_connected() ? "Connected" : "Disconnected");
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

void app_main(void) {
    // Initialize bridge...
    xTaskCreate(status_task, "status", 2048, NULL, 5, NULL);
}
```

### Sending Data Programmatically

```c
void app_main(void) {
    ble_bridge_config_t config = ble_bridge_get_default_config(BLE_BRIDGE_MODE_TRANSCEIVER);
    config.hm10_device_name = "HMSoft";
    ble_bridge_init(&config);

    // Wait for connection
    while (!ble_bridge_is_hm10_connected()) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }

    // Send data
    const char *message = "Hello from ESP32\n";
    ble_bridge_send_to_hm10((uint8_t*)message, strlen(message));
}
```

---

## Implementation Notes

### GATT Client Connection Flow

1. Register GATT client → Start scanning for HM-10
2. Find HM-10 device → Connect
3. MTU negotiation → Service discovery
4. Find characteristic (0xFFE1) → Enable notifications
5. Ready for bidirectional communication

### UART Configuration (Transceiver Mode)

- Port: UART_NUM_0 (USB-Serial/VCP)
- Default: 115200 baud, 8N1, no flow control
- Continuous RX task forwards data to/from HM-10 via BLE
- TX queue for sending data from HM-10 to UART

### BLE Server (Bleak Mode)

- ESP32 advertises as GATT Server with custom service
- Service UUID: 0xFF00, Characteristic UUID: 0xFF01
- Supports Read, Write, and Notify operations
- Bidirectional data forwarding between BLE client and HM-10
- Simultaneous GATT Client (to HM-10) and GATT Server (to computer)

### Dual BLE Roles

The ESP32 operates in both BLE roles simultaneously:
- **GATT Client**: Connects to HM-10 module
- **GATT Server** (Bleak mode) or **UART Bridge** (Transceiver mode): Interface to computer

This dual-role operation is supported by ESP-IDF's Bluedroid stack.

---

## Dependencies

- **ESP-IDF**: v4.4 or later recommended
- **Bluetooth**: Bluedroid stack with BLE enabled
- **NVS**: Non-volatile storage partition
- **FreeRTOS**: Task scheduling (included in ESP-IDF)

---

## Related Repositories

- **Sample Clients**: [BT_demo](https://github.com/samklin33/CarCarBluetoothDemo.git)
- **Example Applications**: [BT_demo](https://github.com/samklin33/CarCarBluetoothDemo.git)
