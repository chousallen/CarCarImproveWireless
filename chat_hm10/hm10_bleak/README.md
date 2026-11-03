# HM-10 Bleak Client

This module provides a robust, asynchronous GATT client designed to interface directly with **HM-10 (CC2541)** Bluetooth modules. It streamlines the connection process by abstracting the BLE scanning, MTU management, and data packetization into a simple `listen`/`send` interface.

---

## Key Features

* **16-bit UUID Support**: Uses simplified short-form UUIDs (`ffe0`/`ffe1`) with automatic 128-bit expansion.
* **Automatic Chunking**: Transparently splits messages longer than **20 bytes** to respect the BLE 4.0 MTU limit.
* **Serial-Style Buffering**: Includes an internal RX buffer so you can poll for data using a synchronous `listen()` call.
* **Filtering**: Connects to the first device whose name and/or MAC address matches the ones given.

---

## Installation

```bash
pip install bleak
```

Or use the shared conda environment (`environment.yml` in the repo root), see [TA_GUIDE.md, section 4.1](../../TA_GUIDE.md#41-python-environment-both-paths). Run your script from `chat_hm10/` so `import hm10_bleak` resolves.

---

## API Reference

### `HM10BleakClient(target_name=None, target_address=None)`

Initializes the client.

* **target_name**: String (e.g., `"HM10_Mega"`).
* **target_address**: MAC address (e.g., `"88:C2:55:03:BC:D7"`).

### `await connect()`

Scans for the device using the provided name/address. Upon finding the device, it establishes a GATT connection and automatically starts listening to the `0xFFE1` characteristic.

* **Returns**: `True` if connected and notifications are enabled.

### `listen()`

**Synchronous.** Returns all data accumulated in the internal buffer since the last call and clears the buffer.

* **Returns**: `String` (UTF-8 decoded).

### `await send(message)`

Encodes the message and writes it to the HM-10.

* **MTU Management**: Automatically slices data into 20-byte chunks.
* **Flow Control**: Includes a 20ms delay between chunks to prevent UART buffer overflows on the receiving Arduino.

### `await disconnect()`

Stops notifications and closes the BLE connection.

---

## Communication Logic

The module is designed for **Asynchronous Concurrency**. Because `Bleak` is push-based (notifications), the module populates an internal `_rx_buffer` in the background. The user script can then "pull" that data at its own pace.

---

## Example

The complete chat program is [`chat_hm10-bleak.py`](../chat_hm10-bleak.py): a receiver task that polls `listen()` runs next to a sender task that reads the keyboard, so typing does not block receiving. The minimum is:

```python
import asyncio
from hm10_bleak import HM10BleakClient

async def main():
    hm10 = HM10BleakClient(target_name="HM10_Mega")
    if await hm10.connect():
        await hm10.send("Hello HM-10!\n")
        await asyncio.sleep(0.5)
        print(hm10.listen())          # whatever the HM-10 sent since the last call
        await hm10.disconnect()

asyncio.run(main())
```
