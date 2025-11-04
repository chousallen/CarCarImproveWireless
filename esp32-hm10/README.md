| Supported Targets | ESP32 | ESP32-C2 | ESP32-C3 | ESP32-C5 | ESP32-C6 | ESP32-C61 | ESP32-H2 | ESP32-H21 | ESP32-H4 | ESP32-P4 | ESP32-S2 | ESP32-S3 | Linux |
| ----------------- | ----- | -------- | -------- | -------- | -------- | --------- | -------- | --------- | -------- | -------- | -------- | -------- | ----- |

# ESP32 BLE GATT Client for HM-10

This project implements a BLE GATT Client that connects to an HM-10 module and interacts with its characteristics.

## Target Device Information

- **Device Name**: `sallen_hm10`
- **Service UUID**: `0000FFE0-0000-1000-8000-00805F9B34FB`
- **Characteristic UUID**: `0000FFE1-0000-1000-8000-00805F9B34FB`

## Features

This application will:
1. Scan for the HM-10 device by name
2. Connect to the device when found
3. Discover the service and characteristic
4. Register for notifications from the characteristic
5. Read the characteristic value
6. Write data to the characteristic ("Hello from ESP32!")
7. Receive and display notifications

## Configuration

Before building, you need to enable Bluetooth in the SDK configuration:

```bash
idf.py menuconfig
```

Navigate to:
- **Component config → Bluetooth → Bluedroid Options**
  - Enable `Bluedroid - Bluetooth driver stack`
  - Enable `BLE GATT Client module`

## Building and Flashing

```bash
# Configure the project (select your target if needed)
idf.py set-target esp32

# Build the project
idf.py build

# Flash to ESP32 and open monitor
idf.py flash monitor
```

## Expected Output

When running, you should see:
1. BLE initialization messages
2. Scan start notification
3. Device discovery: "Found target device: sallen_hm10"
4. Connection establishment
5. Service and characteristic discovery
6. Notification registration
7. Read operation results
8. Write operation confirmation
9. Incoming notifications (if the HM-10 sends any)

## Code Structure

- **GAP Callback**: Handles scanning and device discovery
- **GATT Client Callback**: Handles connection, service discovery, and data operations
- **Profile System**: Uses a profile-based architecture for managing GATT connections

## Project folder contents

The project contains one source file in C language [hello_world_main.c](main/hello_world_main.c). The file is located in folder [main](main).

ESP-IDF projects are built using CMake. The project build configuration is contained in `CMakeLists.txt` files that provide set of directives and instructions describing the project's source files and targets (executable, library, or both).

```
├── CMakeLists.txt
├── pytest_hello_world.py      Python script used for automated testing
├── main
│   ├── CMakeLists.txt
│   └── hello_world_main.c
└── README.md                  This is the file you are currently reading
```

For more information on structure and contents of ESP-IDF projects, please refer to Section [Build System](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/build-system.html) of the ESP-IDF Programming Guide.

## Customization

You can modify the following in `hello_world_main.c`:
- `DEVICE_NAME`: Change the target device name
- `REMOTE_SERVICE_UUID`: Change the service UUID (16-bit)
- `REMOTE_NOTIFY_CHAR_UUID`: Change the characteristic UUID (16-bit)
- Write data in the `ESP_GATTC_READ_CHAR_EVT` case

## Troubleshooting

* Program upload failure
    * Hardware connection is not correct: run `idf.py -p PORT monitor`, and reboot your board to see if there are any output logs.
    * The baud rate for downloading is too high: lower your baud rate in the `menuconfig` menu, and try again.

* Device not found
    * Ensure the HM-10 is powered on and advertising
    * Check the device name matches exactly

* Connection failed
    * Check that the device is not already connected to another device
    * Verify the Bluetooth range is adequate

* Build errors
    * Make sure Bluetooth is enabled in menuconfig
    * Ensure all required components are included

## References

- [ESP-IDF GATT Client API Documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/bluetooth/esp_gattc.html)
- [ESP-IDF BLE Examples](https://github.com/espressif/esp-idf/tree/master/examples/bluetooth/bluedroid/ble)

## Technical support and feedback

Please use the following feedback channels:

* For technical queries, go to the [esp32.com](https://esp32.com/) forum
* For a feature request or bug report, create a [GitHub issue](https://github.com/espressif/esp-idf/issues)

We will get back to you as soon as possible.
