# TA Guide

For the TAs who run the course and keep the wireless link working. It explains what each device and module does, how to set a system up from nothing, and how to fix the usual problems. Building the firmware and the code internals are in [DEV_GUIDE.md](DEV_GUIDE.md). Students get [beginner_guide.md](beginner_guide.md).

Terms used here are in the [glossary](#9-glossary) at the end.

## 1. Two ways to reach the car

The car carries an HM-10 BLE module wired to the Arduino Mega's Serial3 at 9600 baud. The PC can reach it by one of two paths. Both carry raw text in both directions; the car code cannot tell which path is in use.

| Path | On the PC | Extra hardware | Why use it |
|---|---|---|---|
| **ESP32 bridge** | `chat_hm10/hm10_esp32` (Python, pyserial) | An ESP32 board flashed with `esp32-hm10/`, plugged in by USB | The PC's own Bluetooth does not matter. The ESP32 appears as a plain serial port on every operating system. |
| **Direct BLE** | `chat_hm10/hm10_bleak` (Python, bleak) | None. Needs a PC with BLE (Bluetooth 4.0 or newer). | No extra board. Depends on the PC's Bluetooth adapter and driver. |

The HM-10 accepts one connection at a time, so a car is reachable by either one ESP32 or one PC, not both.

## 2. The parts

| Part | What it does | Where | Reference |
|---|---|---|---|
| **HM-10 module** (on the car) | BLE radio with a UART. Bytes written to it over BLE come out of its TX pin; bytes on its RX pin go out over BLE in packets of at most 20 bytes. The course's modules sit on a black 6-pin base board with a 5 V regulator and level shifters. | Hardware | `resource/DS-HM10.pdf` |
| **`init_hm10.ino`** (Arduino sketch) | One-time setup of a new HM-10: finds its baud rate, factory-resets it, sets its name, turns on connect/disconnect notices (`AT+NOTI1`), prints its MAC address, leaves it at 9600 baud. Then relays text between the Serial Monitor and the module, which makes the Mega a test partner for chat. | `init_hm10/` | The sketch itself |
| **ESP32 bridge firmware** | Turns an ESP32 into a USB-serial-to-BLE bridge. Scans for the HM-10 by name, connects, and forwards bytes both ways. Four `AT+` commands configure it (section 5). Remembers the target name in flash. | `esp32-hm10/` | `esp32-hm10/README.md` |
| **`hm10_esp32`** (Python module) | Talks to the ESP32 over the serial port: sends the bridge commands, filters the ESP32's log output down to the HM-10 data. | `chat_hm10/hm10_esp32/` | `chat_hm10/hm10_esp32/README.md` |
| **`hm10_bleak`** (Python module) | Talks to the HM-10 from the PC's own Bluetooth using the `bleak` library. Cuts outgoing text into 20-byte pieces. | `chat_hm10/hm10_bleak/` | `chat_hm10/hm10_bleak/README.md` |
| **`chat_hm10-esp32.py`**, **`chat_hm10-bleak.py`** | Example chat programs, one per path. What students run first and copy from. | `chat_hm10/` | `beginner_guide.md` |

## 3. How data flows

```
┌──────────┐  USB serial  ┌──────────┐     BLE      ┌──────────┐  UART 9600  ┌──────────┐
│    PC    │ ◄──────────► │  ESP32   │ ◄──────────► │  HM-10   │ ◄─────────► │   Mega   │
│ (Python) │              │ (bridge) │              │ (on car) │             │  (car)   │
└──────────┘              └──────────┘              └──────────┘             └──────────┘
      ▲                                                   ▲
      └──────── BLE, direct from the PC's own Bluetooth ──┘
```

**ESP32 bridge path, PC to car:**

1. The PC writes text to the ESP32's USB serial port at 115200 baud.
2. The firmware reads the port in pieces of at most 10 bytes, once every 25 ms. A piece that is one of the four bridge commands is handled by the ESP32 itself. Everything else is data.
3. Each data piece is written over BLE to the HM-10's characteristic `0xFFE1`. The HM-10 sends it out of its UART to the Mega.

**ESP32 bridge path, car to PC:**

4. Whatever the Mega prints to Serial3, the HM-10 sends to the ESP32 as BLE notifications of at most 20 bytes each.
5. The firmware prints each notification on the USB serial port as a log line: `I (12345) bt_com: <payload>`. Replies to bridge commands (`OK+...`) use the same tag.
6. The Python module reads the port, keeps only the records tagged `bt_com:`, and hands the payloads to the caller. Every other line (boot messages, scan progress) is dropped.

**Direct path:** `HM10BleakClient` scans for up to 10 s for a device whose name (or MAC address) matches, connects, and subscribes to `0xFFE1` notifications. `send()` splits text into 20-byte pieces 20 ms apart. `listen()` returns everything received since the last call.

**Message boundaries:** there are none. Both paths are byte streams cut into packets of at most 20 bytes. A long message can arrive in two `listen()` calls, and two short messages can arrive in one. `chat_hm10-bleak.py` adds `\n` to each message; `chat_hm10-esp32.py` does not. If a course exercise needs message boundaries, tell the students which end marker to use on both sides.

## 4. Set up from scratch

### 4.1 Python environment (both paths)

```bash
conda env create -f environment.yml    # Python 3.12 + pyserial + bleak, env name "carcar"
conda activate carcar
# or, in any Python 3.12: pip install pyserial bleak
```

Scripts must be run from the `chat_hm10/` folder so that `import hm10_esp32` and `import hm10_bleak` resolve.

### 4.2 A new HM-10

1. **Check the board's voltage first.** The course's board (blue HM-10 on a black 6-pin base board) has a 3.3 V regulator and level shifters on TX and RX: power it from the Mega's 5 V pin and wire TX/RX straight to the Mega. A bare HM-10 module is rated 2.5–3.3 V and its RX takes 3.3 V logic: use the Mega's 3.3 V pin and a voltage divider on the Mega's TX3.
2. Wire it to an Arduino Mega: VCC → 5 V (course board) or 3.3 V (bare), GND → GND, HM-10 TX → RX3 (pin 15), HM-10 RX → TX3 (pin 14).
3. In `init_hm10/init_hm10.ino`, set `CUSTOM_NAME` (12 characters at most) and upload.
4. Open the Serial Monitor at 115200. The sketch tries each baud rate until the module answers `OK`, factory-resets it, sets the name, enables `AT+NOTI1`, prints the MAC address, and restarts the module. After this the module runs at 9600 baud, which is also what the car code must use.
5. The sketch then relays text between the Serial Monitor and the HM-10, so the Mega can be the car end of a chat test. Note that opening the Mega's serial port restarts the Mega, so the sketch runs again: it factory-resets the HM-10 and drops any Bluetooth link.

**Buying more boards:** check for level shifters on TX/RX. Listings often say only "with base board", and many base boards have a regulator but no shifter. Ask the seller, or test one board on arrival: put 5 V on VCC with the other pins open. TX and RX near VCC (about 4.3 V on the course's board) means a level shifter; about 3.3 V means none, so add a divider on TX3.

### 4.3 An ESP32 bridge

A TA flashes each ESP32 once; building and flashing is in [DEV_GUIDE.md](DEV_GUIDE.md#2-build-and-flash-the-firmware). After that:

1. Plug it in. The ESP32 boards use a CH340 USB-to-serial chip. Windows and macOS may need its driver (the student guide links the installation slides). It appears as `COM<n>` on Windows, `/dev/ttyUSB<n>` on Linux, `/dev/tty.usbserial-...` on macOS.
2. Tell it which HM-10 to look for. Either run `chat_hm10-esp32.py` with `EXPECTED_NAME` set (the script sets the name and restarts the ESP32 when the saved name differs), or send `AT+NAME<name>` yourself (section 6).
3. The ESP32 scans in rounds of 30 s until it finds a device advertising that name, connects, and reconnects on its own after a dropped link. Its serial output (115200 baud) shows the progress.

### 4.4 Chat test

```bash
cd chat_hm10
python chat_hm10-esp32.py     # edit PORT and EXPECTED_NAME at the top first
python chat_hm10-bleak.py     # edit target_name in main() first
```

With the init sketch still on the Mega, the Serial Monitor is the car end. `chat_hm10-esp32.py` checks the bridge's saved target name, sets it and resets the ESP32 if it differs, waits for the link, and then checks `AT+STATUS?` before the chat starts.

## 5. ESP32 bridge commands

Send these over the ESP32's USB serial port with **no line ending**. The ESP32 handles them itself and does not forward them to the HM-10.

| Command | Reply (as a `bt_com:` log line) | Effect | Python wrapper |
|---|---|---|---|
| `AT+NAME<name>` | `OK+SET<name>` | Saves the target HM-10 name in flash (NVS). Applies after `AT+RESET`. | `set_hm10_name(name)` |
| `AT+NAME?` | `OK+NAME<name>` | Reports the saved target name. | `get_hm10_name()` |
| `AT+STATUS?` | `OK+CONN` or `OK+UNCONN` | `OK+CONN` means the link is ready for data (HM-10 found, connected, notifications enabled). Data sent before that is dropped. | `get_status()` |
| `AT+RESET` | `OK+RESET` | Reboots the ESP32. It scans again for the saved name. | `reset()` |

Everything else written to the port is data for the car. Data that starts with `AT+NAME` is taken as a command, so do not start a message with `AT`.

To send a command by hand, use a terminal that sends the whole line at once with no line ending: the Arduino IDE Serial Monitor at 115200 baud with "No line ending" selected, or a few lines of Python with pyserial. Terminals that send each keystroke as you type it (`idf.py monitor`, `screen`, PuTTY) do not work: the firmware reads the port in 10 ms slices, so each character arrives as a separate piece of data (from code reading).

## 6. Changing the target name

The ESP32 keeps the target name in NVS (its flash key-value store), so it survives power cycles and even reflashing.

- **From Python:** `bridge.set_hm10_name("NewName")` then `bridge.reset()`, then `bridge.close()` and open a new `HM10ESP32Bridge`. `reset()` returns once the ESP32 reports the link ready again (about 6 s, at most 15 s). This is what `chat_hm10-esp32.py` does when `EXPECTED_NAME` differs.
- **From a terminal:** `AT+NAMENewName`, check with `AT+NAME?`, apply with `AT+RESET`.
- **The default in the firmware** (`sallen_hm10` in `main.c`) is only used by a board that has no saved name. Changing it does nothing on a board that already has one; run `idf.py erase-flash` first.

## 7. Troubleshooting

| Symptom | Check | Fix |
|---|---|---|
| ESP32 never connects; `AT+STATUS?` says `OK+UNCONN`; log repeats `Scan complete, <name> not found, scanning again` every 30 s | Is the HM-10 powered and advertising? Use the nRF Connect phone app to see it. Does `AT+NAME?` match the HM-10's name exactly (case matters)? Is another PC or ESP32 already connected to it? Is it within about 10 m? | Fix the name or power, or disconnect the other client. The ESP32 keeps scanning on its own. |
| `chat_hm10-esp32.py` prints `ESP32 is DISCONNECTED` | Same as above. The script does not wait for the scan. | Run it again after the ESP32's next scan round. |
| `chat_hm10-esp32.py` prints `Failed to set name` | Rare; the reply arrived split across two reads. | Run it again. |
| The ESP32 log says `HM-10 link not ready, dropped N bytes` | Data was sent before `AT+STATUS?` answered `OK+CONN`. | Wait for `OK+CONN` first; `reset()` and the chat script already do. |
| `Access is denied` (Windows) or `could not open port` | Another program holds the port: Arduino Serial Monitor, `idf.py monitor`, an old Python process. Windows ports are exclusive. | Close it. In your own code, call `close()` before opening the same port again. |
| No serial port for the ESP32 | CH340 driver missing, or a power-only USB cable. | Install the driver; try another cable. |
| Arduino sketch reports no HM-10 | Supply voltage (5 V for the course board, 3.3 V bare), TX/RX swapped, module held by a BLE connection (the sketch sends `AT` to force a disconnect, but a bad power supply still loses). | Rewire; power cycle the module. |
| Text arrives in pieces or two messages arrive joined | Normal: packets are at most 20 bytes and `listen()` returns whatever arrived. | Agree on an end marker (section 3). |
| `bleak` cannot find the device | Bluetooth off; name wrong; an ESP32 is already connected to the HM-10; on Linux, BlueZ not running. | Unplug the ESP32 or turn it off. |
| The car receives `OK+CONN` / `OK+LOST` | Normal: the init sketch enables `AT+NOTI1`. On the bench these notices twice arrived corrupted (`OK+CON\x00`); ordinary data never was. | Car code should ignore anything starting with `OK+`, without exact matching. |
| The link drops and comes back when a serial port is opened or closed | Seen once on reopening the ESP32's port; not investigated. | Wait a few seconds; the ESP32 reconnects. |
| Data garbled | Car side not at 9600 baud; non-UTF-8 bytes (the Python side decodes UTF-8 and drops invalid bytes). | Fix the baud rate; send text. |

## 8. Limits students will hit

- **20-byte packets, no framing.** See section 3. Agree on an end marker.
- **Speed.** The ESP32 path sends at most 10 bytes every 25 ms, about 400 bytes/s at best (estimated from the code, not measured). The direct path sends 20 bytes every 20 ms.
- **`listen()` drops car messages that start with `OK+`** on the ESP32 path, because bridge replies look like that. Tell students not to start a message with `OK+` or `AT`.
- **The bridge helpers discard data.** On the ESP32 path, `get_hm10_name()`, `get_status()`, `set_hm10_name()` and `reset()` throw away any car data that arrives while they wait for their reply. Call them before the chat, not during it.
- **One connection per HM-10.** An ESP32 that is still powered keeps the HM-10 busy, so the direct path cannot connect.
- **Names are at most 12 characters** (HM-10 limit). The bridge cuts an `AT+NAME` command at 25 characters and sends the rest to the car as data.

## 9. Glossary

- **BLE**: Bluetooth Low Energy. The low-power Bluetooth variant the HM-10 uses. Not compatible with HC-05 (Bluetooth Classic) devices.
- **GATT, service, characteristic**: how BLE devices expose data. A device has services (here `0xFFE0`) that contain characteristics (here `0xFFE1`). Writing to `0xFFE1` sends bytes to the HM-10's UART.
- **Notification**: a BLE message the HM-10 pushes to the connected client without being asked. This is how car-to-PC data arrives.
- **MTU**: Maximum Transmission Unit, the largest BLE packet. For the HM-10 it is 23 bytes, which leaves 20 bytes of data per packet.
- **AT command**: a short text command starting with `AT`. The HM-10 has its own set (datasheet). The ESP32 bridge has the four in section 5.
- **NVS**: Non-Volatile Storage, a small key-value store in the ESP32's flash. The bridge keeps the target HM-10 name here.
- **ESP-IDF**: Espressif IoT Development Framework, the official SDK and build tool (`idf.py`) for the ESP32. Only needed to build the firmware.
- **CH340**: the USB-to-serial chip on the ESP32 boards. Some PCs need a driver for it.
- **Serial port / COM port**: how the PC sees the ESP32's USB link: `COM3` on Windows, `/dev/ttyUSB0` on Linux, `/dev/tty.usbserial-...` on macOS. Also used for the Mega.
- **bleak**: a Python BLE library that runs on Windows, macOS and Linux. Used by the direct path.
- **pyserial**: the Python serial-port library. Used by the ESP32 path.
