import asyncio
import sys
from hm10_bleak import HM10BleakClient

async def receive_task(hm10):
    """Background task that constantly checks the buffer and prints."""
    while True:
        incoming = hm10.listen()
        if incoming:
            # \r clears the "You: " line temporarily for a clean print
            print(f"\r[HM10]: {incoming}")
            print("You: ", end="", flush=True)
        await asyncio.sleep(0.1) # Check buffer every 100ms

async def send_task(hm10):
    """Task that waits for user input and sends it."""
    loop = asyncio.get_running_loop()
    print("--- Chat Started. Type 'exit' to quit. ---")
    print("You: ", end="", flush=True)
    
    while True:
        # This still blocks THIS task, but NOT the receive_task
        user_msg = await loop.run_in_executor(None, sys.stdin.readline)
        user_msg = user_msg.strip()

        if user_msg.lower() in ['exit', 'quit']:
            return # Exit the task
        
        if user_msg:
            # Many Arduino sketches require a newline to process strings
            await hm10.send(user_msg + "\n")
            print("You: ", end="", flush=True)

async def main():
    hm10 = HM10BleakClient(target_name="sallenHM10")
    
    if not await hm10.connect():
        return

    try:
        # Run both tasks concurrently
        # When send_task returns (on 'exit'), the program moves to finally
        await asyncio.gather(
            receive_task(hm10),
            send_task(hm10),
            return_exceptions=True
        )
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        await hm10.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass