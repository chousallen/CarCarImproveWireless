import asyncio
from bleak import BleakClient, BleakScanner

class HM10BleakClient:
    def __init__(self, target_name=None, target_address=None):
        self.target_name = target_name
        self.address = target_address
        self.client = None
        # Standard HM-10 UUIDs
        self.CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
        self._rx_buffer = ""

    async def connect(self):
        def device_filter(device, adv):
            name_match = (self.target_name is None) or (device.name == self.target_name)
            addr_match = (self.address is None) or (device.address.upper() == self.address.upper())
            return name_match and addr_match

        print(f"Scanning for {self.target_name or 'device'}...")
        device = await BleakScanner.find_device_by_filter(device_filter, timeout=10.0)

        if not device:
            print("❌ Device not found.")
            return False
        
        self.client = BleakClient(device)
        await self.client.connect()
        
        # Start notifications immediately upon connection
        await self.client.start_notify(self.CHAR_UUID, self._notification_handler)
        print(f"✅ Connected to {device.name}")
        return self.client.is_connected

    def _notification_handler(self, sender, data):
        """Pushes data into the internal buffer as it arrives."""
        self._rx_buffer += data.decode('utf-8', errors='ignore')

    def listen(self):
        """Returns and clears the accumulated buffer."""
        data = self._rx_buffer
        self._rx_buffer = ""
        return data

    async def send(self, message):
        """Writes data to HM-10. response=False is safer for CC2541/HM-10."""
        if self.client and self.client.is_connected:
            await self.client.write_gatt_char(
                self.CHAR_UUID, 
                message.encode('utf-8'), 
                # HM-10 often requires 'Write Without Response'
                response=False 
            )

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print("\nDisconnected.")