"""Bleak mode client for HM-10 BLE module"""

import asyncio
from bleak import BleakClient, BleakScanner


# Default HM-10 BLE configuration
DEFAULT_DEVICE_NAME = "HMSoft"
DEFAULT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"


class BleakClient:
    """BLE client for HM-10 module (Bleak Mode)

    This client communicates directly with HM-10 via Bluetooth Low Energy (BLE).
    The HM-10 forwards messages to/from Arduino via UART.

    Data Flow:
        Computer (this client) <--BLE--> HM-10 <--UART--> Arduino

    Example:
        >>> client = BleakClient(device_name='HMSoft')
        >>> if await client.connect():
        ...     await client.send_message("Hello Arduino!")
        ...     await client.disconnect()
    """

    def __init__(self, device_name=DEFAULT_DEVICE_NAME,
                 service_uuid=DEFAULT_SERVICE_UUID,
                 char_uuid=DEFAULT_CHAR_UUID):
        """
        Initialize the Bleak mode client.

        Args:
            device_name: HM-10 BLE device name to search for (default: "HMSoft")
            service_uuid: GATT service UUID (128-bit, default: 0xFFE0)
            char_uuid: GATT characteristic UUID (128-bit, default: 0xFFE1)
        """
        self.device_name = device_name
        self.service_uuid = service_uuid
        self.char_uuid = char_uuid
        self.device = None
        self.client = None

    async def scan_for_device(self, timeout=10.0):
        """Scan for the HM-10 BLE device

        Args:
            timeout: Scan timeout in seconds

        Returns:
            BLEDevice object if found, None otherwise
        """
        print(f"[INFO] Scanning for device: {self.device_name}...")
        print(f"[INFO] Timeout: {timeout} seconds")

        try:
            device = await BleakScanner.find_device_by_name(
                self.device_name,
                timeout=timeout
            )

            if device:
                print(f"[SUCCESS] Found device: {device.name}")
                print(f"[INFO] Address: {device.address}")
                print(f"[INFO] RSSI: {device.rssi} dBm")
                return device
            else:
                print(f"[ERROR] Device '{self.device_name}' not found")
                print("[INFO] Make sure:")
                print("  1. HM-10 module is powered on")
                print("  2. HM-10 is not connected to another device")
                print("  3. HM-10 is advertising")
                print("  4. Device name matches exactly (default: 'HMSoft')")
                return None

        except Exception as e:
            print(f"[ERROR] Scan failed: {e}")
            return None

    async def connect(self, timeout=10.0):
        """Connect to the HM-10 BLE device

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected, False otherwise
        """
        self.device = await self.scan_for_device(timeout)
        if not self.device:
            return False

        print(f"\n[INFO] Connecting to {self.device.name}...")

        try:
            self.client = BleakClient(self.device)
            await self.client.connect()

            if self.client.is_connected:
                print(f"[SUCCESS] Connected to {self.device.name}")
                print(f"[INFO] Service UUID: {self.service_uuid}")
                print(f"[INFO] Characteristic UUID: {self.char_uuid}\n")
                return True
            else:
                print("[ERROR] Connection failed")
                return False

        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the HM-10"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("\n[INFO] Disconnected from HM-10")

    def is_connected(self):
        """Check if connected to HM-10

        Returns:
            True if connected, False otherwise
        """
        return self.client and self.client.is_connected

    async def send_message(self, message):
        """Send a message to the HM-10 (forwarded to Arduino via UART)

        Args:
            message: String message to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected():
            print("[ERROR] Not connected")
            return False

        try:
            if not message.endswith('\n'):
                message += '\n'

            data = message.encode('utf-8')
            await self.client.write_gatt_char(self.char_uuid, data)
            return True

        except Exception as e:
            print(f"[ERROR] Failed to send: {e}")
            return False

    async def interactive_chat(self):
        """Run interactive chat mode"""
        print("=" * 60)
        print("  HM-10 BLE Client - Bleak Mode")
        print("=" * 60)
        print("  Computer (BLE) <-> HM-10 <-> Arduino")
        print("=" * 60)
        print()
        print("Type your messages and press Enter to send.")
        print("Type 'exit' to quit.")
        print()
        print("-" * 60)
        print()

        def notification_handler(sender, data):
            """Handle incoming notifications from HM-10"""
            try:
                message = data.decode('utf-8').strip()
                print(f"<< {message}")
            except Exception as e:
                print(f"[ERROR] Failed to decode message: {e}")

        try:
            await self.client.start_notify(self.char_uuid, notification_handler)
            print("[INFO] Listening for messages from Arduino...")
            print()
        except Exception as e:
            print(f"[ERROR] Failed to start notifications: {e}")
            return

        try:
            while True:
                message = await asyncio.get_event_loop().run_in_executor(
                    None, input, ">> "
                )

                if message.lower() in ['exit', 'quit', 'q']:
                    print("[INFO] Exiting...")
                    break

                if message:
                    if not await self.send_message(message):
                        print("[ERROR] Failed to send message")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
        except EOFError:
            print("\n[INFO] EOF received")
        finally:
            try:
                await self.client.stop_notify(self.char_uuid)
            except Exception:
                pass
