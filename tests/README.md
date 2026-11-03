# Hardware end-to-end test

`hw_e2e.py` checks the whole path on real boards:
PC → ESP32 (`esp32-hm10` firmware) → BLE → HM-10 → Arduino Mega → PC, and back.

## Setup
- ESP32 flashed with `esp32-hm10`, already targeting the HM-10's name (`AT+NAME<name>`).
- HM-10 on the Mega's Serial3. The Mega runs a plain pass-through:
  USB `Serial` at 115200 ↔ `Serial3`, no extra text printed.
- Both boards on USB. They are usually both CH340 adapters, so the `ttyUSB` numbers follow plug
  order. Find the ESP32 with `python -m esptool -p /dev/ttyUSBx chip-id`.

## Run
```bash
conda activate carcar
python tests/hw_e2e.py --esp /dev/ttyUSB0 --mega /dev/ttyUSB1 --name HM10_Mega
```
Takes about 2 minutes. Exit code 0 when every check passes.

On Windows: `python tests\hw_e2e.py --esp COM3 --mega COM4` (only `pyserial` is needed).

## What it checks
- `AT+STATUS?` and `AT+NAME?` replies.
- Both directions: short, long (several BLE packets), UTF-8, and a burst of 10 messages.
- Three ESP32 reboots: data sent the moment `AT+STATUS?` says `OK+CONN` must arrive (T11).
- `HM10ESP32Bridge.reset()` returns only when the link is usable (T12b, T12c).
- `chat_hm10/chat_hm10-esp32.py` itself: start, send, receive, `exit`.

T11 and T12b/T12c fail on firmware and bridge code from before branch
`fix/esp32-hm10-connect-race` (the old firmware reports `OK+CONN` before the link is ready).
