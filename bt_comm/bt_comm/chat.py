"""
Chat utilities for interactive communication
"""

import sys
import asyncio


def chat_esp32(interface):
    """
    Interactive chat mode with HM-10 via ESP32
    
    Args:
        interface: ESP32Interface instance (must be connected)
    """
    if not interface.serial or not interface.serial.is_open:
        print("✗ Not connected to ESP32")
        return
    
    # Check connection status
    print("Checking connection status...")
    status = interface.check_status()
    
    if status == "CONNECTED":
        print("✓ ESP32 is connected to HM-10")
    elif status == "DISCONNECTED":
        print("⚠ Warning: ESP32 is not connected to HM-10")
        print("  Make sure HM-10 is powered on and in range")
    else:
        print("⚠ Warning: Could not determine connection status")
    
    print("\n✓ Started chat mode")
    print("Type your message and press Enter to send")
    print("Press Ctrl+C or type 'exit' to quit")
    print("-" * 50)
    
    try:
        while True:
            # Check for incoming messages
            if interface.available():
                msg = interface.read(timeout=0.01)
                print(f"BT: {msg}")
            
            # Check if user has input ready (non-blocking check)
            import select
            if select.select([sys.stdin], [], [], 0.01)[0]:
                user_input = sys.stdin.readline().strip()
                
                if user_input.lower() == 'exit':
                    print("\nExiting chat mode...")
                    break
                
                if user_input:
                    if interface.send(user_input):
                        pass  # Success
                    else:
                        print("Failed to send message")
            
    except KeyboardInterrupt:
        print("\n\nExiting chat mode...")


async def chat_bleak(interface):
    """
    Interactive chat mode with HM-10 via Bleak
    
    Args:
        interface: BleakInterface instance (must be connected)
    """
    if not interface.client or not interface.client.is_connected:
        print("✗ Not connected to device")
        return
    
    # Start notifications
    await interface.start_notifications()
    
    print("✓ Started chat mode")
    print("Type your message and press Enter to send")
    print("Press Ctrl+C or type 'exit' to quit")
    print("-" * 50)
    
    try:
        loop = asyncio.get_event_loop()
        
        while True:
            # Check for incoming messages
            msg = interface.read()
            if msg:
                print(f"\n<< {msg}")
                print(">> ", end='', flush=True)
            
            print(">> ", end='', flush=True)
            
            # Read user input in a non-blocking way
            user_input = await loop.run_in_executor(None, sys.stdin.readline)
            user_input = user_input.strip()
            
            if user_input.lower() == 'exit':
                print("\nExiting chat mode...")
                break
            
            if user_input:
                if await interface.send(user_input):
                    pass  # Success (no output to keep chat clean)
                else:
                    print("Failed to send message")
            
            # Small delay to allow messages to accumulate
            await asyncio.sleep(0.01)
                    
    except KeyboardInterrupt:
        print("\n\nExiting chat mode...")
    finally:
        await interface.stop_notifications()
