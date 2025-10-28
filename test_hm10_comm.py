#!/usr/bin/env python3
"""
Bluetooth Device Finder using Bleak (BLE)
Scans for nearby Bluetooth Low Energy devices and finds a device by name
"""

import asyncio
from bleak import BleakScanner

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
    
    print(f"\nFound {len(devices)} device(s)")
    print("-" * 50)
    
    device_address = None
    
    # Search for the target device
    for device in devices:
        name = device.name if device.name else "Unknown"
        print(f"Device: {name}")
        print(f"Address: {device.address}")
        print()
        
        if device.name and device.name == target_name:
            device_address = device.address
    
    return device_address

async def main():
    """Main async function"""
    # Find the device
    device_address = await find_bluetooth_device(DEVICE_NAME)
    
    print("=" * 50)
    if device_address:
        print(f"✓ Device '{DEVICE_NAME}' found!")
        print(f"Address: {device_address}")
    else:
        print(f"✗ Device '{DEVICE_NAME}' not found")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
