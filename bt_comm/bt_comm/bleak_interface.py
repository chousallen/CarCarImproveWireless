"""
Bleak Interface for direct Bluetooth LE connection to HM-10
"""

import asyncio
from bleak import BleakScanner, BleakClient


class BleakInterface:
    """Interface for direct Bluetooth communication with HM-10 using Bleak"""
    
    # HM-10 default UUIDs
    SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
    CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
    
    def __init__(self, device_name):
        """
        Initialize the Bleak interface
        
        Args:
            device_name (str): The name of the HM-10 device to connect to
        """
        self.device_name = device_name
        self.client = None
        self.address = None
        self.message_buffer = []  # Buffer to store received messages
        self.notification_active = False
        
    async def find_device(self):
        """
        Search for the HM-10 device by name
        
        Returns:
            str: The MAC address of the device if found, None otherwise
        """
        print(f"Scanning for Bluetooth LE devices...")
        print(f"Looking for device: '{self.device_name}'")
        
        devices = await BleakScanner.discover(timeout=10.0)
        
        for device in devices:
            if device.name and device.name == self.device_name:
                self.address = device.address
                print(f"✓ Device '{self.device_name}' found at {self.address}")
                return self.address
        
        print(f"✗ Device '{self.device_name}' not found")
        return None
    
    async def connect(self):
        """
        Connect to the HM-10 device
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if not self.address:
            if not await self.find_device():
                return False
        
        print(f"Connecting to device at {self.address}...")
        self.client = BleakClient(self.address)
        await self.client.connect()
        
        if self.client.is_connected:
            print(f"✓ Connected to {self.device_name}")
            return True
        else:
            print("✗ Failed to connect")
            return False
    
    async def disconnect(self):
        """Disconnect from the HM-10 device"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("✓ Disconnected from device")
    
    async def send(self, data):
        """
        Send data to the HM-10 device
        
        Args:
            data (str): The data to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.client or not self.client.is_connected:
            print("✗ Not connected to device")
            return False
        
        try:
            data_bytes = data.encode('utf-8')
            await self.client.write_gatt_char(self.CHAR_UUID, data_bytes)
            return True
        except Exception as e:
            print(f"✗ Error sending data: {e}")
            return False
    
    def _notification_handler(self, sender, data):
        """Internal handler for incoming notifications"""
        try:
            decoded = data.decode('utf-8', errors='replace')
            self.message_buffer.append(decoded)
        except Exception:
            # Store hex representation for non-UTF8 data
            self.message_buffer.append(f"(raw): {data.hex()}")
    
    async def start_notifications(self):
        """Start receiving notifications from the HM-10 device"""
        if not self.client or not self.client.is_connected:
            print("✗ Not connected to device")
            return False
        
        if not self.notification_active:
            await self.client.start_notify(self.CHAR_UUID, self._notification_handler)
            self.notification_active = True
        return True
    
    async def stop_notifications(self):
        """Stop receiving notifications from the HM-10 device"""
        if self.client and self.client.is_connected and self.notification_active:
            await self.client.stop_notify(self.CHAR_UUID)
            self.notification_active = False
    
    def read(self):
        """
        Read all available messages from the buffer.
        
        Returns:
            str: The concatenated message, or None if no message available
        """
        if self.message_buffer:
            messages = ''.join(self.message_buffer)
            self.message_buffer.clear()
            return messages
        return None
