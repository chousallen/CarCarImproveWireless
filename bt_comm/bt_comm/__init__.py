"""
bt_comm - Bluetooth Communication Bridge Module
Acts as a bridge from PC to HM-10 via Bleak or ESP32 USB VCP
"""

from .bleak_interface import BleakInterface
from .esp32_interface import ESP32Interface
from .chat import chat_esp32, chat_bleak

__version__ = "1.0.0"
__all__ = ["BleakInterface", "ESP32Interface", "chat_esp32", "chat_bleak"]
