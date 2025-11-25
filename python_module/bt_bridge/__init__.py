"""BT Bridge - Python module for Bluetooth communication

This module provides clients for communicating via Bluetooth in both
transceiver mode (ESP32 UART bridge) and bleak mode (direct HM-10 BLE).

Example Usage:
    Transceiver Mode (UART via ESP32):
        >>> from bt_bridge import TransceiverClient
        >>> client = TransceiverClient(port='COM3')
        >>> if client.connect():
        ...     client.send_message("Hello!")
        ...     client.disconnect()

    Bleak Mode (Direct BLE to HM-10):
        >>> from bt_bridge import BleakClient
        >>> client = BleakClient(device_name='HMSoft')
        >>> if await client.connect():
        ...     await client.send_message("Hello!")
        ...     await client.disconnect()
"""

from .transceiver import TransceiverClient
from .bleak_client import BleakClient
from .common import strip_ansi_codes, extract_message_from_log, is_message_fragment

__version__ = '0.1.0'
__all__ = [
    'TransceiverClient',
    'BleakClient',
    'strip_ansi_codes',
    'extract_message_from_log',
    'is_message_fragment',
]
