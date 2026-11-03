# CarCarImprove Wireless

A Bluetooth Low Energy (BLE) link between a student's PC and a CarCar car (an Arduino Mega line-following car). The car carries an HM-10 BLE module wired to the Mega's Serial3. It replaces the HC-05 Bluetooth Classic modules, whose PC connections were unreliable.

The PC can reach the HM-10 in two ways:

```
┌──────────┐  USB serial  ┌──────────┐     BLE      ┌──────────┐  UART 9600  ┌──────────┐
│    PC    │ ◄──────────► │  ESP32   │ ◄──────────► │  HM-10   │ ◄─────────► │   Mega   │
│ (Python) │              │ (bridge) │              │ (on car) │             │  (car)   │
└──────────┘              └──────────┘              └──────────┘             └──────────┘
      ▲                                                   ▲
      └──────── BLE, direct from the PC's own Bluetooth ──┘
```

## Pick your guide

| You are | Read | What you need to know first |
|---|---|---|
| A **student** using the link in the course | [beginner_guide.md](beginner_guide.md) | How to upload an Arduino sketch and run a Python script. Nothing about the ESP32 or BLE. |
| A **TA** running the course | [TA_GUIDE.md](TA_GUIDE.md) | What each device and module does, how to set everything up from scratch, how to fix the usual problems. |
| A **developer** changing the code | [DEV_GUIDE.md](DEV_GUIDE.md) | Everything in the TA guide, plus building the firmware, the internals, and the rules that must not be broken. |

Taking the project over? Read [HANDOVER.html](HANDOVER.html) after the TA guide: where things stood on the handover date, the evidence behind the fixes, the open work, and the facts only the outgoing owner can fill in.

## Repository layout

```
CarCarImprove/
├── README.md                      # This file
├── beginner_guide.md              # Student guide
├── beginner_guide/                # Screenshots used by the student guide
├── TA_GUIDE.md                    # TA guide: parts, setup, troubleshooting
├── DEV_GUIDE.md                   # Developer guide: build, internals, invariants
├── CLAUDE.md                      # Notes for AI coding assistants
├── HANDOVER.html                  # Handover note: status, evidence, open work, facts to fill in
├── environment.yml                # Conda environment (Python 3.12, pyserial, bleak)
├── esp32-hm10/                    # ESP32 bridge firmware (ESP-IDF, C)
│   ├── main/main.c                # The whole firmware
│   ├── main/Kconfig.projbuild     # menuconfig options (not read by main.c)
│   ├── sdkconfig.defaults         # Lasting build settings (flash mode, log colours)
│   ├── sdkconfig                  # Generated from the defaults by ESP-IDF v6.1 (tracked)
│   ├── README.md                  # Firmware usage and how it works
│   └── IMPLEMENTATION_NOTES.md    # BLE client internals
├── chat_hm10/                     # Python side (run scripts from this folder)
│   ├── hm10_esp32/                # Module for the ESP32 path (pyserial) + README
│   ├── hm10_bleak/                # Module for the direct BLE path (bleak) + README
│   ├── chat_hm10-esp32.py         # Chat example, ESP32 path
│   └── chat_hm10-bleak.py         # Chat example, direct path
├── init_hm10/init_hm10.ino        # Arduino sketch that sets up a new HM-10
├── tests/hw_e2e.py                # Hardware end-to-end test (needs real boards) + README
└── resource/DS-HM10.pdf           # HM-10 datasheet (full AT command list)
```

## All documents

Guides, by audience:

- [beginner_guide.md](beginner_guide.md): students
- [TA_GUIDE.md](TA_GUIDE.md): TAs
- [DEV_GUIDE.md](DEV_GUIDE.md): developers
- [HANDOVER.html](HANDOVER.html): the next maintainers (one-time handover note)

Reference for one component each:

- [esp32-hm10/README.md](esp32-hm10/README.md): firmware usage, bridge commands, how it works, logging
- [esp32-hm10/IMPLEMENTATION_NOTES.md](esp32-hm10/IMPLEMENTATION_NOTES.md): the BLE client code, event by event
- [chat_hm10/hm10_esp32/README.md](chat_hm10/hm10_esp32/README.md): Python API for the ESP32 path
- [chat_hm10/hm10_bleak/README.md](chat_hm10/hm10_bleak/README.md): Python API for the direct path
- [tests/README.md](tests/README.md): how to run the hardware end-to-end test
- [resource/DS-HM10.pdf](resource/DS-HM10.pdf): HM-10 datasheet (official site: http://www.jnhuamao.cn/bluetooth.asp)
- [ESP-IDF programming guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/): the ESP32 build system and BLE API

## Contributing

Test every change on real boards: run the hardware end-to-end test in [tests/README.md](tests/README.md) for the ESP32 path, and test the rest by hand. There are no tests that run without hardware. Update the guide that describes what you changed. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/); see [DEV_GUIDE.md](DEV_GUIDE.md#9-git-conventions).
