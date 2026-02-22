from hm10_esp32 import ESP32HM10Bridge
import time
import sys
import threading

TARGET_PORT = '/dev/ttyUSB2'
EXPECTED_NAME = 'HM10_Mega'

def background_listener(bridge):
    """Continuously monitors for incoming messages from HM-10."""
    while True:
        message_block = bridge.listen()
        if message_block:
            # \r clears the "You: " prompt line temporarily to print the message
            print(f"\r[HM10]: {message_block}")
            print("You: ", end="", flush=True)
        time.sleep(0.1)

def main():
    bridge = ESP32HM10Bridge(port=TARGET_PORT)
    
    # 1. Verify Name
    current_name = bridge.get_hm10_name()
    if current_name != EXPECTED_NAME:
        print(f"❌ Name mismatch. Expected {EXPECTED_NAME}, got {repr(current_name)}")
        sys.exit(1)
    
    # 2. Check Connection (Exit if disconnected)
    status = bridge.get_status()
    if status != "CONNECTED":
        print(f"⚠️ Status is {status}. HM-10 must be connected before starting chat.")
        sys.exit(0)

    print(f"✅ Ready! Connected to {EXPECTED_NAME}")
    print("--- Start Chatting (Type 'exit' to quit) ---")

    # 3. Start the listener thread
    listener_thread = threading.Thread(target=background_listener, args=(bridge,), daemon=True)
    listener_thread.start()

    # 4. Main Loop for Sending
    try:
        while True:
            # We use flush to keep the prompt visible
            user_msg = input("You: ")
            
            if user_msg.lower() in ['exit', 'quit']:
                break
            
            if user_msg:
                bridge.send(user_msg)
    except KeyboardInterrupt:
        pass
    
    print("\nChat ended.")

if __name__ == "__main__":
    main()