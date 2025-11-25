# CarCar Wireless Communication Module

Wireless communication solutions for Arduino-based car projects. This repository contains both ESP32 firmware and Python client libraries for communicating with HM-10 BLE modules.

## Components

### 1. ESP32 BLE Bridge Firmware ([esp32-hm10/](esp32-hm10/))

ESP-IDF firmware that enables ESP32 to act as a USB-to-BLE bridge, allowing computers without BLE support to communicate with HM-10 modules. This firmware is used for **Transceiver mode only**.

**Architecture:**
```
Computer --USB/UART--> ESP32 --BLE--> HM-10 --UART--> Arduino
```

**Features:**
- UART communication with computer via USB (115200 baud)
- BLE GATT client to connect to HM-10
- Automatic device discovery and connection
- Bidirectional message forwarding

See [esp32-hm10/IMPLEMETATION_NOTES.md](esp32-hm10/IMPLEMENTATION_NOTES.md) for details.

### 2. Python BT Bridge Module ([python_module/bt_bridge/](python_module/bt_bridge/))

Python library for communicating with Arduino via Bluetooth in two modes:

#### Transceiver Mode
Uses ESP32 as a UART bridge to HM-10:
```
Computer (Python) --USB--> ESP32 --BLE--> HM-10 --UART--> Arduino
```

#### Bleak Mode
Connects directly to HM-10 via BLE (no ESP32 required):
```
Computer (Python) --BLE--> HM-10 --UART--> Arduino
```

## Installation

### ESP32 Firmware

```bash
cd esp32-hm10
idf.py set-target esp32
idf.py build
idf.py flash
```

### Python Module

**Option 1: Install from source (development)**
```bash
cd python_module
pip install -e .
```

**Option 2: Install dependencies only**
```bash
cd python_module
pip install -r requirements.txt
```

## Quick Start

### Transceiver Mode (UART)

```python
from bt_bridge import TransceiverClient

# Create client (auto-detect port)
client = TransceiverClient()

# Connect
if client.connect():
    # Send message
    client.send_message("Hello Arduino!")

    # Interactive chat
    client.interactive_chat()

    # Disconnect
    client.disconnect()
```

### Bleak Mode (Direct BLE to HM-10)

```python
import asyncio
from bt_bridge import BleakClient

async def main():
    # Create client (connect directly to HM-10)
    client = BleakClient(device_name='HMSoft')

    # Connect
    if await client.connect():
        # Send message
        await client.send_message("Hello Arduino!")

        # Interactive chat
        await client.interactive_chat()

        # Disconnect
        await client.disconnect()

asyncio.run(main())
```

## Python API Reference

### TransceiverClient

```python
from bt_bridge import TransceiverClient

client = TransceiverClient(port=None, baudrate=115200)
```

**Methods:**
- `connect()` - Connect to ESP32
- `disconnect()` - Disconnect from ESP32
- `is_connected()` - Check connection status
- `send_message(message)` - Send message to device
- `read_message()` - Read message from device
- `interactive_chat()` - Start interactive chat session
- `list_ports()` - List available serial ports
- `auto_detect_port()` - Auto-detect ESP32 port

### BleakClient

```python
from bt_bridge import BleakClient

client = BleakClient(
    device_name='HMSoft',
    service_uuid='0000ffe0-0000-1000-8000-00805f9b34fb',
    char_uuid='0000ffe1-0000-1000-8000-00805f9b34fb'
)
```

**Methods:**
- `async connect(timeout=10.0)` - Connect to HM-10 via BLE
- `async disconnect()` - Disconnect from HM-10
- `is_connected()` - Check connection status
- `async send_message(message)` - Send message to Arduino
- `async interactive_chat()` - Start interactive chat session
- `async scan_for_device(timeout=10.0)` - Scan for HM-10 device

## Requirements

### Python
- Python 3.7+
- pySerial 3.5+ (for Transceiver mode)
- Bleak 0.21.0+ (for BLE mode)

### Hardware
- ESP32 development board (for Transceiver mode)
- HM-10 BLE module
- Arduino board (optional, for testing)
- Computer with BLE support (for Bleak mode)

### ESP32 Development
- ESP-IDF v5.0+
- USB cable for flashing and communication

## Examples and Demos

For complete working examples and sample code, see the [CarCarBluetoothDemo](https://github.com/samklin33/CarCarBluetoothDemo) repository.

The demo repository includes:
- Example scripts for both modes
- Arduino echo server sketch
- Standalone scripts for quick testing

## Project Structure

```
CarCarImproveWireless/
├── esp32-hm10/                 # ESP32 firmware (ESP-IDF)
│   ├── main/
│   │   └── main.c              # Main firmware code
│   ├── CMakeLists.txt
│   └── README.md
├── python_module/              # Python module
|   ├── bt_bridge/              # Python package
|   │   ├── __init__.py         # Package initialization
|   │   ├── transceiver.py      # TransceiverClient class
|   │   ├── bleak_client.py     # BleakClient class
|   │   └── common.py           # Shared utilities
|   ├── setup.py                # Package installation
|   └── requirements.txt        # Python dependencies
└── README.md                   # This file
```

## Troubleshooting

### Transceiver Mode

**Error: Could not auto-detect ESP32 port**
- List available ports: `python -m serial.tools.list_ports`
- Specify port manually: `TransceiverClient(port='COM3')`

**Error: Permission denied (Linux)**
- Add user to dialout group: `sudo usermod -a -G dialout $USER`
- Logout and login again

### Bleak Mode

**Error: Device not found**
- Check HM-10 module is powered on
- Verify HM-10 is not connected to another device
- Ensure HM-10 is advertising (visible)
- Check device name matches exactly (default: "HMSoft")

**Error: Bluetooth not available**
- Ensure computer has Bluetooth 4.0+ (BLE) support
- Windows: Enable Bluetooth in Settings
- Linux: `sudo systemctl start bluetooth`
- macOS: Enable Bluetooth in System Preferences

## Development

### Installing in Development Mode

```bash
cd python_module
pip install -e .
```

This allows you to edit the source code and see changes immediately without reinstalling.

### Building ESP32 Firmware

```bash
cd esp32-hm10
idf.py build
```