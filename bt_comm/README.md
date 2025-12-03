# bt_comm - Bluetooth Communication Bridge

A Python module that acts as a bridge from PC to HM-10 Bluetooth modules. Supports two connection modes:
1. **Direct Bluetooth** via Bleak (BLE)
2. **ESP32 USB VCP Bridge** for serial communication

## Features

- Direct Bluetooth LE connection to HM-10 modules using Bleak
- ESP32 USB VCP bridge support for indirect connection
- AT command support for ESP32 configuration
- Interactive chat mode for real-time communication
- Automatic device discovery and connection status checking

## Installation

### Method 1: Direct pip installation

Install in editable mode (recommended for development):
```bash
cd /path/to/bt_comm
pip install -e .
```

Or install directly:
```bash
cd /path/to/bt_comm
pip install .
```

### Method 2: Using uv

With [uv](https://github.com/astral-sh/uv) (fast Python package installer):
```bash
cd /path/to/bt_comm
uv pip install -e .
```

Or using uv to manage the project:
```bash
cd /path/to/bt_comm
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Method 3: Using Poetry

With [Poetry](https://python-poetry.org/):
```bash
cd /path/to/bt_comm
poetry install
```

To run commands with Poetry:
```bash
poetry run bt_comm -n my_hm10_device
# or
poetry shell  # activates virtual environment
bt_comm -n my_hm10_device
```

### Method 4: Using Miniconda

With [Miniconda](https://docs.conda.io/en/latest/miniconda.html):

**Using environment.yml (recommended):**
```bash
cd /path/to/bt_comm
conda env create -f environment.yml
conda activate bt_comm
pip install -e .
```

**Manual installation:**
```bash
# Create a new conda environment
conda create -n bt_comm python=3.12
conda activate bt_comm

# Install the package
cd /path/to/bt_comm
pip install -e .
```

Or install dependencies separately:
```bash
conda create -n bt_comm python=3.12
conda activate bt_comm
conda install -c conda-forge bleak
pip install pyserial
cd /path/to/bt_comm
pip install -e . --no-deps
```

## Usage

### Direct Bluetooth Mode (via Bleak)

Connect directly to HM-10 via your PC's Bluetooth:

```bash
python -m bt_comm -n my_hm10_device
```

### ESP32 Bridge Mode

Connect to HM-10 via ESP32 USB VCP bridge without changing target device:

```bash
python -m bt_comm -p /dev/ttyUSB0
```

Connect via ESP32 and set the target HM-10 device name:

```bash
python -m bt_comm -p /dev/ttyUSB0 -n my_hm10_device
```

On Windows:
```bash
python -m bt_comm -p COM3 -n my_hm10_device
```

## Command Line Arguments

- `-p, --port`: ESP32 VCP port (e.g., `/dev/ttyUSB0`, `COM3`). If not specified, uses Bleak for direct connection.
- `-n, --name`: HM-10 device name. Required for Bleak mode. Optional for ESP32 mode (sets target device if provided).

At least one argument is required.

## ESP32 Bridge Protocol

The ESP32 bridge uses the following AT commands:

- `AT+NAME<device_name>` - Set the target HM-10 device name
- `AT+RESET` - Reset the ESP32 (automatically sent after setting device name)
- `AT+STATUS?` - Check connection status
  - Returns `OK+CONN` if connected to HM-10
  - Returns `OK+UNCONN` if not connected
- Any message without `AT` prefix is forwarded to HM-10

**Baudrate:** 115200

## Interactive Chat Mode

Once connected, you can send messages to the HM-10 device:

- Type your message and press Enter to send
- Received messages are displayed with `<<` prefix
- Type `exit` or press Ctrl+C to quit

## Module Structure

```
bt_comm/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── bleak_interface.py   # Bleak (direct Bluetooth) interface
└── esp32_interface.py   # ESP32 USB VCP bridge interface
```

## Requirements

- Python 3.7+ (including Python 3.12)
- bleak >= 0.21.0 (for Bluetooth LE communication)
- pyserial >= 3.5 (for ESP32 USB serial communication)

## Examples

### Example 1: Direct Connection
```bash
# Scan and connect to HM-10 device named "sallen_hm10"
python -m bt_comm -n sallen_hm10
```

### Example 2: ESP32 Bridge (Existing Configuration)
```bash
# Connect via ESP32 on /dev/ttyUSB0 using previously set device name
python -m bt_comm -p /dev/ttyUSB0
```

### Example 3: ESP32 Bridge (New Configuration)
```bash
# Connect via ESP32 and configure it to connect to "my_hm10"
python -m bt_comm -p /dev/ttyUSB0 -n my_hm10
```

## License

Open source - feel free to use and modify.
