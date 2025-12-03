"""
Main entry point for bt_comm module
Provides CLI for communicating with HM-10 via Bleak or ESP32
"""

import argparse
import asyncio
import sys
from .bleak_interface import BleakInterface
from .esp32_interface import ESP32Interface
from .chat import chat_esp32, chat_bleak


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Bluetooth communication bridge to HM-10',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct Bluetooth connection via Bleak
  python -m bt_comm -n my_hm10_device
  
  # Via ESP32 USB VCP bridge without changing target device
  python -m bt_comm -p /dev/ttyUSB0
  
  # Via ESP32 USB VCP bridge and set target HM-10 device
  python -m bt_comm -p /dev/ttyUSB0 -n my_hm10_device
        """
    )
    
    parser.add_argument(
        '-p', '--port',
        type=str,
        help='ESP32 VCP port (e.g., /dev/ttyUSB0, COM3). If not specified, uses Bleak for direct connection.'
    )
    
    parser.add_argument(
        '-n', '--name',
        type=str,
        help='HM-10 device name. Required for Bleak mode. Optional for ESP32 mode (sets target device if provided).'
    )
    
    args = parser.parse_args()
    
    # Validation: at least one argument is required
    if not args.port and not args.name:
        parser.error("At least one argument is required: -p (port) or -n (name)")
    
    # Validation: Bleak mode requires device name
    if not args.port and not args.name:
        parser.error("Device name (-n) is required when not using ESP32 bridge")
    
    return args


def main_bleak(device_name):
    """
    Main function for Bleak interface (direct Bluetooth)
    
    Args:
        device_name (str): The name of the HM-10 device
    """
    print("=" * 60)
    print("BT_COMM - Direct Bluetooth Mode (Bleak)")
    print("=" * 60)
    
    interface = BleakInterface(device_name)
    
    async def run():
        try:
            # Find and connect to device
            if not await interface.connect():
                return 1
            
            # Start chat mode
            await chat_bleak(interface)
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return 1
        finally:
            # Cleanup
            await interface.disconnect()
        
        return 0
    
    return asyncio.run(run())


def main_esp32(port, device_name=None):
    """
    Main function for ESP32 interface (USB VCP bridge)
    
    Args:
        port (str): The serial port for ESP32
        device_name (str, optional): The name of the HM-10 device to set as target
    """
    print("=" * 60)
    print("BT_COMM - ESP32 USB VCP Bridge Mode")
    print("=" * 60)
    
    interface = ESP32Interface(port)
    
    try:
        # Connect to ESP32
        if not interface.connect():
            return 1
        
        # Set target device if name provided
        if device_name:
            if not interface.set_target_device(device_name):
                print("⚠ Warning: Failed to set target device name")
        
        # Start chat mode
        chat_esp32(interface)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    finally:
        # Cleanup
        interface.disconnect()
    
    return 0


def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        if args.port:
            # ESP32 mode
            return main_esp32(args.port, args.name)
        else:
            # Bleak mode
            return main_bleak(args.name)
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
        return 0


if __name__ == "__main__":
    sys.exit(main())
