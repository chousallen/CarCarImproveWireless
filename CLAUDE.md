# CarCarImprove Wireless

HM-10 BLE link between students' PCs and the CarCar cars (Arduino Mega). Two PC paths:
ESP32 bridge (`esp32-hm10/` + `chat_hm10/hm10_esp32`, pyserial) and direct BLE
(`chat_hm10/hm10_bleak`, bleak).

Read `DEV_GUIDE.md` before touching code: build and flash commands, internals, the
invariants (the `bt_com` log tag is the data channel, `CONFIG_LOG_COLORS` must stay on,
`OK+CONN` means the link is ready for data, NVS name beats the `main.c` default), and the
hardware end-to-end test. `TA_GUIDE.md` has the parts, setup and troubleshooting;
`beginner_guide.md` is what students read.
`HANDOVER.html` is the one-time handover note (status, test evidence, open work, branch state):
facts about how the system works belong in the guides, not there.

## Rules for this repo
- The only automated test needs real boards: `python tests/hw_e2e.py --esp <port> --mega <port>`
  (conda env `carcar`, about 2 min, 22 checks, exit 0 = pass; bench setup in `tests/README.md`).
  Run it after any change to the firmware or to `hm10_esp32_bridge.py`; verify the rest by hand.
- Firmware: ESP-IDF v6.1 (5.3+ also builds), zero warnings. Lasting settings go in
  `sdkconfig.defaults`, then regenerate the tracked `sdkconfig`.
- `beginner_guide.md` and `beginner_guide/` are linked from student material: do not move
  or rename them, and keep the identifiers shown in the screenshots (`CUSTOM_NAME`,
  `PORT`, `EXPECTED_NAME`).
- `.gitignore` has CRLF line endings on its older lines; match exactly when editing.
- Run the Python scripts from `chat_hm10/` so the package imports resolve.
- Keep each fact in one guide and link to it; do not copy build commands or the AT table
  into other files.

## This machine (ThinkPad) and the bench
- ESP-IDF v6.1 at `/media/sallen/SSD-Programs/esp/v6.1/esp-idf` (copied from sallenpi's clean
  v6.1 checkout; sallenpi's own tools are aarch64, do not copy them). v5.5.2 is still installed
  next to it. `IDF_TOOLS_PATH=/media/sallen/SSD-Programs/esp/.espressif`; shell alias `get_idf`
  sources `export.sh`. Build/flash: `get_idf; cd esp32-hm10; idf.py set-target esp32; idf.py build;
  idf.py -p /dev/ttyUSBx flash`.
- ESP32 and Mega are both CH340 adapters and take `/dev/ttyUSB0`/`1` in plug order. Identify the
  ESP32 with `python -m esptool -p /dev/ttyUSBx chip-id` (IDF python env) before flashing.
  `chat_hm10/chat_hm10-esp32.py` hard-codes `PORT = '/dev/ttyUSB1'`.
- `idf.py monitor` needs a TTY; from a non-interactive shell read the port with pyserial
  (115200, pulse RTS to reset).
- The bench Mega runs a plain pass-through (USB `Serial` 115200 ↔ `Serial3`), not `init_hm10.ino`:
  no banner, and opening its port does not reset the HM-10. Reconnect after `AT+RESET` takes
  about 6.3 s.
