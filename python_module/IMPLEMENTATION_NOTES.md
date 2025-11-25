# BT Bridge Python Module Implementation Notes

## Overview

This Python module provides two modes for communicating with Arduino via HM-10 BLE module:
- **Transceiver Mode**: Uses ESP32 as a USB-UART bridge to HM-10
- **Bleak Mode**: Direct BLE connection to HM-10 (no ESP32 required)

## Module Structure

```
bt_bridge/
├── __init__.py         # Package exports
├── transceiver.py      # TransceiverClient (ESP32 bridge mode)
├── bleak_client.py     # BleakClient (direct BLE mode)
└── common.py           # Shared utilities
```

## Key Implementation Details

### 1. Transceiver Mode (transceiver.py)

#### Architecture
```
Computer (Python) --USB/UART--> ESP32 --BLE--> HM-10 --UART--> Arduino
```

#### Port Auto-Detection

The `auto_detect_port()` method searches for ESP32 by:
1. Listing all serial ports using `serial.tools.list_ports.comports()`
2. Filtering by hardware description containing "USB" or "Serial"
3. Attempting to open each candidate port
4. Returning the first successfully opened port

```python
def auto_detect_port(self):
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'USB' in port.description or 'Serial' in port.description:
            try:
                ser = serial.Serial(port.device, self.baudrate, timeout=1)
                ser.close()
                return port.device
            except:
                continue
```

#### Message Filtering

ESP-IDF outputs ANSI color codes and log formatting. The module filters these:

1. **ANSI Code Stripping** (`common.strip_ansi_codes()`):
   - Removes terminal color escape sequences
   - Pattern: `\x1b\[[0-9;]*m`

2. **Log Format Parsing** (`common.extract_message_from_log()`):
   - Detects ESP-IDF log format: `X (timestamp) [TAG]: message`
   - Extracts only the `bt_com` tagged messages (actual BLE data)
   - Filters out system logs

3. **Fragment Detection** (`common.is_message_fragment()`):
   - Checks if line starts with log level prefix (I, E, W, D, V)
   - Returns True if it's a continuation of previous message

#### Background Reading Thread

Uses Python threading to continuously read serial data:

```python
self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
```

The daemon thread:
- Runs `_read_loop()` continuously
- Reads lines from serial port
- Filters and prints received messages
- Automatically stops when main thread exits

#### Synchronization

Uses `threading.Lock()` to prevent concurrent access to serial port:

```python
with self.lock:
    self.serial.write(data)
```

This prevents write collisions between main thread (sending) and read thread.

### 2. Bleak Mode (bleak_client.py)

#### Architecture
```
Computer (Python) --BLE--> HM-10 --UART--> Arduino
```

#### HM-10 GATT Configuration

Default UUIDs for HM-10:
```python
DEFAULT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
```

These are 128-bit representations of:
- Service: `0xFFE0`
- Characteristic: `0xFFE1`

#### Device Scanning

Uses `BleakScanner.find_device_by_name()`:

```python
device = await BleakScanner.find_device_by_name(
    self.device_name,
    timeout=timeout
)
```

Returns `BLEDevice` object with:
- `device.name` - Advertised device name
- `device.address` - MAC address
- `device.rssi` - Signal strength (dBm)

#### Connection Flow

1. Scan for device by name
2. Create `BleakClient` with device address
3. Call `await client.connect()`
4. Verify connection with `client.is_connected`

#### Notification Handling

Registers a callback for incoming BLE notifications:

```python
def notification_handler(sender, data):
    message = data.decode('utf-8').strip()
    print(f"<< {message}")

await self.client.start_notify(self.char_uuid, notification_handler)
```

The handler:
- Receives raw bytes from characteristic
- Decodes as UTF-8
- Prints with `<<` prefix to indicate incoming message

#### Async I/O for User Input

Since Bleak is async, user input needs special handling:

```python
message = await asyncio.get_event_loop().run_in_executor(
    None, input, ">> "
)
```

This runs the blocking `input()` in a thread pool executor, allowing async operations to continue.

#### Message Transmission

Encodes string to bytes and writes to GATT characteristic:

```python
data = message.encode('utf-8')
await self.client.write_gatt_char(self.char_uuid, data)
```

Automatically appends newline if not present (for Arduino Serial.readStringUntil()).

### 3. Shared Utilities (common.py)

#### strip_ansi_codes(text)
Removes ANSI terminal color codes from ESP-IDF output.

**Pattern**: `\x1b\[[0-9;]*m`

**Example**:
```
Input:  "\x1b[0;32mI (123) [TAG]: Hello\x1b[0m"
Output: "I (123) [TAG]: Hello"
```

#### extract_message_from_log(line)
Parses ESP-IDF log format and extracts BLE communication messages.

**Format**: `LEVEL (timestamp) [TAG]: message`

**Returns**: Message content if TAG is `bt_com`, else None

**Example**:
```python
extract_message_from_log("E (456) [bt_com]: Hello")  # Returns "Hello"
extract_message_from_log("I (789) [GATTC]: Connected")  # Returns None
```

#### is_message_fragment(line)
Checks if line is a log fragment without timestamp.

**Returns**: True if line doesn't start with log level (I, E, W, D, V)

## Installation and Usage

### Development Installation

```bash
cd python_module
pip install -e .
```

This creates an "editable install" where changes to source files are immediately available.

### Import Patterns

```python
# Import specific classes
from bt_bridge import TransceiverClient, BleakClient

# Import utilities
from bt_bridge import strip_ansi_codes, extract_message_from_log
```

## Message Length Limitations and MTU

### BLE Packet Size Constraints

The system has several buffer size limitations that affect message transmission:

| Component | Buffer/MTU Size | Description |
|-----------|----------------|-------------|
| **HM-10 BLE Packet** | **20 bytes** | Hard limit per BLE packet |
| **Default BLE ATT MTU** | 23 bytes (20 usable) | 3-byte overhead for ATT header |
| **ESP32 MTU Request** | 500 bytes | Requested, but limited by HM-10 |
| **ESP32 UART Buffer** | 1024 bytes | Can receive long messages |
| **Arduino Serial Buffer** | ~64 bytes | Typical default |

### Critical Bottleneck: HM-10 20-Byte Limit

The HM-10 module splits messages longer than 20 bytes into multiple BLE notifications. Each arrives separately at the ESP32.

**Example fragmentation:**
```
Message: "Hello Arduino! How are you doing?" (35 bytes)

Packet 1: "Arduino: Hello Ardui" (20 bytes)
Packet 2: "no! How are you doi" (20 bytes)
Packet 3: "ng?" (4 bytes)
```

### Message Reassembly in TransceiverClient

The `reader_loop()` implements automatic fragment reassembly:

1. **Buffering**: Messages starting with "Arduino:" begin a new buffer
2. **Continuation**: Subsequent packets (without "Arduino:" prefix) are appended
3. **Timeout**: After 50ms of no new data, the buffer is flushed and displayed
4. **New message**: When a new "Arduino:" message arrives, the previous buffer is flushed

**Key parameters:**
- Fragment timeout: 50ms (line 220 in transceiver.py)
- Duplicate detection: Uses `seen_responses` set
- Buffer size limit: 200 bytes (configurable in `is_message_fragment()`)

### Recommended Message Lengths

| Length Range | Behavior | Reliability |
|-------------|----------|-------------|
| **≤ 20 bytes** | Single packet | ✅ Highest (no fragmentation) |
| **21-150 bytes** | 2-8 packets, auto-reassembled | ⚠️ Good (minor 50ms latency) |
| **> 150 bytes** | Many packets | ⚠️ Higher risk of issues |

**Best practices:**
- Keep messages under 20 bytes for maximum reliability
- Messages up to 150 bytes work well with buffering
- Avoid messages over 200 bytes

## Dependencies

### pySerial (≥3.5)
Used for UART communication in Transceiver mode.

Key functions:
- `serial.Serial()` - Open serial port
- `serial.tools.list_ports.comports()` - List available ports
- `Serial.read()` / `Serial.write()` - I/O operations

### Bleak (≥0.21.0)
Bluetooth Low Energy platform-agnostic client library.

Key classes:
- `BleakScanner` - Scan for BLE devices
- `BleakClient` - Connect and communicate with BLE devices

Platform support:
- Windows: Uses Windows BLE API
- Linux: Uses BlueZ
- macOS: Uses CoreBluetooth

## Error Handling

### Transceiver Mode

**Port detection failure**:
- Prints available ports for user reference
- Suggests manual port specification

**Connection loss**:
- Read thread detects `serial.SerialException`
- Prints error and stops reading

### Bleak Mode

**Device not found**:
- Provides checklist of common issues
- Suggests using BLE scanner app

**Connection timeout**:
- Returns False from `connect()`
- Provides timeout value for debugging

**Bluetooth unavailable**:
- Bleak raises exception
- Suggests platform-specific fixes

## Threading Model

### Transceiver Mode
- **Main thread**: User input, message sending
- **Read thread**: Background serial reading (daemon)
- **Lock**: Prevents concurrent serial port access

### Bleak Mode
- **Event loop**: Async I/O for BLE operations
- **Thread pool**: Blocking input() calls
- All BLE operations are async/await

## Protocol Assumptions

### Message Format
- Text messages (UTF-8 encoded)
- Newline-terminated (`\n`)
- Arduino uses `Serial.readStringUntil('\n')`

### MTU Size
- Default BLE MTU: 23 bytes (20 bytes payload)
- Long messages may be split by BLE stack
- Transceiver mode has no practical limit (UART buffer)

## Customization Points

### Transceiver Mode
1. **Port detection**: Modify `auto_detect_port()` logic
2. **Baudrate**: Change `baudrate` parameter (default: 115200)
3. **Message filtering**: Adjust `extract_message_from_log()` TAG filter
4. **Timeout**: Modify `serial.Serial(timeout=...)`

### Bleak Mode
1. **Device name**: Change `device_name` parameter
2. **UUIDs**: Override `service_uuid` and `char_uuid`
3. **Scan timeout**: Adjust `scan_for_device(timeout=...)`
4. **Notification handler**: Customize message processing

## Testing

### Unit Testing (Manual)

**Transceiver Mode**:
```bash
python examples/transceiver_example.py
```

**Bleak Mode**:
```bash
python examples/bleak_example.py
```

### Hardware Requirements

**Minimum**:
- HM-10 BLE module
- Arduino with serial echo sketch
- USB cable for HM-10 power

**Transceiver Mode**:
- ESP32 with BLE bridge firmware
- USB cable for ESP32

**Bleak Mode**:
- Computer with Bluetooth 4.0+ (BLE)

## Common Issues and Solutions

### Issue: Import error after installation
**Solution**: Verify installation with `pip list | grep bt-bridge`

### Issue: Port access denied (Linux)
**Solution**: Add user to dialout group:
```bash
sudo usermod -a -G dialout $USER
```

### Issue: Bleak device not found
**Solution**:
1. Check HM-10 is powered and advertising
2. Verify device name with BLE scanner app
3. Ensure HM-10 not connected to another device

### Issue: Messages not received
**Solution**:
1. Check Arduino is running and echoing
2. Verify HM-10 UART connections (TX/RX crossed)
3. Check newline termination in messages

## Performance Considerations

### Transceiver Mode
- Thread overhead: ~1-2 MB memory
- Polling interval: 20ms (in ESP32 UART read)
- Latency: ~50-100ms (UART + BLE round trip)

### Bleak Mode
- BLE scan: 1-10 seconds (depends on advertising interval)
- Connection: 1-3 seconds
- Notification latency: 10-50ms
- Throughput: Limited by BLE MTU and connection interval

## Future Enhancements

Potential improvements:
1. **Binary mode**: Support non-text data transmission
2. **Reconnection**: Auto-reconnect on connection loss
3. **Multiple devices**: Connect to multiple HM-10s simultaneously
4. **Logging**: Add Python logging module support
5. **Configuration**: Support config file for common settings
