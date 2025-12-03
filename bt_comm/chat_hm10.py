#!/usr/bin/env python3
"""
Bluetooth Device Finder using Bleak (BLE)
Scans for nearby Bluetooth Low Energy devices and finds a device by name
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient

# Specify the device name to search for
DEVICE_NAME = "sallen_hm10"  # Change this to your target device name

async def find_bluetooth_device(target_name):
    """
    Search for a Bluetooth device by name and return its address.
    
    Args:
        target_name (str): The name of the Bluetooth device to find
        
    Returns:
        str: The MAC address of the device if found, None otherwise
    """
    print(f"Scanning for Bluetooth LE devices...")
    print(f"Looking for device: '{target_name}'")
    print("-" * 50)
    
    # Discover nearby Bluetooth devices
    devices = await BleakScanner.discover(timeout=10.0)
    
    device_address = None
    
    # Search for the target device
    for device in devices:
        if device.name and device.name == target_name:
            device_address = device.address
            break
    
    return device_address

async def list_services(address):
    """
    Connect to a BLE device and list its services and characteristics.
    
    Args:
        address (str): The MAC address of the device
    """
    print(f"\nConnecting to device at {address}...")
    
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        print("\n" + "=" * 70)
        print("SERVICES AND CHARACTERISTICS")
        print("=" * 70)
        
        for service in client.services:
            print(f"\nService: {service.uuid}")
            print(f"  Description: {service.description}")
            
            for char in service.characteristics:
                properties = ", ".join(char.properties)
                print(f"  Characteristic: {char.uuid}")
                print(f"    Description: {char.description}")
                print(f"    Properties: {properties}")
                
                # List descriptors if any
                for descriptor in char.descriptors:
                    print(f"      Descriptor: {descriptor.uuid}")
        
        print("\n" + "=" * 70)

async def interactive_communication(address):
    """
    Interactive bidirectional communication with HM-10 BLE module.
    Allows reading notifications and writing data to the characteristic.
    
    Args:
        address (str): The MAC address of the device
    """
    # UUIDs for the service and characteristic
    SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
    CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
    
    def notification_handler(sender, data):
        """Handle incoming notifications"""
        try:
            decoded = data.decode('utf-8', errors='replace')
            print(f"\n<< Received: {decoded}")
            print(f"   (Hex: {data.hex()})")
        except Exception as e:
            print(f"\n<< Received (raw): {data.hex()}")
        print(">> ", end='', flush=True)
    
    print(f"\nConnecting to device at {address}...")
    
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        
        # Subscribe to notifications
        print(f"Subscribing to notifications on characteristic {CHAR_UUID}...")
        await client.start_notify(CHAR_UUID, notification_handler)
        print("✓ Subscribed to notifications\n")
        
        print("=" * 70)
        print("INTERACTIVE COMMUNICATION MODE")
        print("=" * 70)
        print("Type your message and press Enter to send")
        print("Press Ctrl+C or type 'exit' to quit")
        print("=" * 70)
        
        try:
            loop = asyncio.get_event_loop()
            
            while True:
                # Read user input in a non-blocking way
                print(">> ", end='', flush=True)
                
                # Use run_in_executor to read input without blocking
                user_input = await loop.run_in_executor(None, sys.stdin.readline)
                user_input = user_input.strip()
                
                if user_input.lower() == 'exit':
                    print("\nExiting...")
                    break
                
                if user_input:
                    # Send the message
                    data_to_send = user_input.encode('utf-8')
                    await client.write_gatt_char(CHAR_UUID, data_to_send)
                    print(f"   Sent: {user_input} (Hex: {data_to_send.hex()})")
                    
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            await client.stop_notify(CHAR_UUID)
            print("✓ Disconnected from device")

async def main():
    """Main async function"""
    # Find the device
    device_address = await find_bluetooth_device(DEVICE_NAME)
    
    print("=" * 50)
    if device_address:
        print(f"✓ Device '{DEVICE_NAME}' found!")
        print(f"Address: {device_address}")
        print("=" * 50)
        
        # List services
        await list_services(device_address)
        
        # Start interactive communication
        await interactive_communication(device_address)
    else:
        print(f"✗ Device '{DEVICE_NAME}' not found")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
