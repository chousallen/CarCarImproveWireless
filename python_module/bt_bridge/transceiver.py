"""Transceiver mode client for ESP32 BLE Bridge"""

import sys
import time
import threading
import serial
import serial.tools.list_ports

from .common import strip_ansi_codes, extract_message_from_log


class TransceiverClient:
    """Serial communication client for ESP32 BLE Bridge (Transceiver Mode)

    This client communicates with ESP32 via USB/UART serial connection.
    The ESP32 forwards messages to/from the HM-10 module via BLE.

    Data Flow:
        Computer (this client) <--> ESP32 (UART) <--> HM-10 (BLE) <--> Device

    Example:
        >>> client = TransceiverClient(port='COM3', baudrate=115200)
        >>> if client.connect():
        ...     client.send_message("Hello Arduino!")
        ...     client.disconnect()
    """

    def __init__(self, port=None, baudrate=115200):
        """
        Initialize the transceiver client.

        Args:
            port: Serial port name (e.g., 'COM3', '/dev/ttyUSB0').
                 If None, will attempt auto-detection.
            baudrate: Baud rate (default: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.running = False
        self.reader_thread = None
        self.response_received = threading.Event()

    def list_ports(self):
        """List all available serial ports

        Returns:
            List of tuples: [(device, description), ...]
        """
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]

    def auto_detect_port(self):
        """Try to auto-detect ESP32 serial port

        Returns:
            Port device string if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()

        esp32_keywords = [
            'CP210', 'CH340', 'FTDI', 'USB Serial', 'UART',
        ]

        for port in ports:
            description = port.description.upper()
            for keyword in esp32_keywords:
                if keyword.upper() in description:
                    print(f"[INFO] Auto-detected ESP32 on: {port.device} ({port.description})")
                    return port.device

        return None

    def connect(self):
        """Connect to the ESP32

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.port is None:
                self.port = self.auto_detect_port()

                if self.port is None:
                    print("\n[ERROR] Could not auto-detect ESP32 port.")
                    print("\nAvailable ports:")
                    for device, desc in self.list_ports():
                        print(f"  {device}: {desc}")
                    print("\nPlease specify the port manually.")
                    return False

            print(f"[INFO] Connecting to {self.port} at {self.baudrate} baud...")

            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )

            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            print(f"[SUCCESS] Connected to ESP32 on {self.port}")
            print(f"[INFO] Baud rate: {self.baudrate}\n")

            return True

        except serial.SerialException as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the ESP32"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("\n[INFO] Disconnected from ESP32")

    def is_connected(self):
        """Check if connected to ESP32

        Returns:
            True if connected, False otherwise
        """
        return self.ser and self.ser.is_open

    def send_message(self, message):
        """Send a message to the ESP32 (forwarded to device via HM-10)

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

            self.ser.write(message.encode('utf-8'))
            self.ser.flush()
            return True

        except serial.SerialException as e:
            print(f"[ERROR] Failed to send: {e}")
            return False

    def read_message(self):
        """Read a message from the ESP32 (from device via HM-10)

        Returns:
            Received message string, or None if no data
        """
        if not self.is_connected():
            return None

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline()
                if line:
                    return line.decode('utf-8', errors='ignore').strip()
        except serial.SerialException as e:
            print(f"[ERROR] Failed to read: {e}")

        return None

    def reader_loop(self):
        """Background thread for reading incoming messages"""
        print("[INFO] Reader thread started")
        print("[INFO] Filtering ESP-IDF logs, colors, and duplicates...")

        seen_responses = set()
        message_buffer = ""  # Buffer for reassembling fragmented messages
        last_fragment_time = 0  # Timestamp of last fragment

        while self.running:
            message = self.read_message()

            if message:
                message = strip_ansi_codes(message)

                cleaned_message = extract_message_from_log(message)

                if cleaned_message and len(cleaned_message.strip()) > 0:
                    current_time = time.time()

                    # Reset buffer if too much time has passed (>100ms indicates new message)
                    if message_buffer and (current_time - last_fragment_time) > 0.1:
                        # Timeout - display what we have
                        if message_buffer not in seen_responses:
                            print(f"<< {message_buffer}")
                            seen_responses.add(message_buffer)
                        message_buffer = ""

                    # Check if this is start of a new Arduino response or continuation
                    if cleaned_message.startswith("Arduino:"):
                        # Start of new message - save any previous buffer first
                        if message_buffer and message_buffer not in seen_responses:
                            print(f"<< {message_buffer}")
                            seen_responses.add(message_buffer)

                        # Start new buffer
                        message_buffer = cleaned_message
                        last_fragment_time = current_time
                    elif message_buffer:
                        # Continuation of previous message (doesn't start with "Arduino:")
                        message_buffer += cleaned_message
                        last_fragment_time = current_time
                    else:
                        # Message doesn't start with "Arduino:" and no buffer
                        # Ignore non-Arduino messages
                        pass

            # Flush buffer if we haven't received data in a while
            if message_buffer and (time.time() - last_fragment_time) > 0.05:
                if message_buffer not in seen_responses:
                    print(f"<< {message_buffer}")
                    seen_responses.add(message_buffer)
                message_buffer = ""

            if len(seen_responses) > 50:
                seen_responses.clear()

            time.sleep(0.01)

    def start_reader(self):
        """Start the background reader thread"""
        self.running = True
        self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
        self.reader_thread.start()

    def stop_reader(self):
        """Stop the background reader thread"""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=1)

    def interactive_chat(self):
        """Run interactive chat mode"""
        print("=" * 60)
        print("  ESP32 BLE Bridge - Transceiver Mode")
        print("=" * 60)
        print("  Computer (UART) <-> ESP32 <-> HM-10 <-> Device")
        print("=" * 60)
        print()
        print("Type your messages and press Enter to send.")
        print("Type 'exit' to quit.")
        print()
        print("-" * 60)
        print()

        self.start_reader()

        try:
            while True:
                try:
                    message = input(">> ")
                    if len(message) > 150: 
                        print("[WARNING] Message too long (max 150 chars)")
                        continue
                except EOFError:
                    break

                if message.lower() in ['exit', 'quit', 'q']:
                    print("[INFO] Exiting...")
                    break

                if message:
                    self.response_received.clear()

                    if self.send_message(message):
                        self.response_received.wait(timeout=2.0)
                    else:
                        print("[ERROR] Failed to send message")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
        finally:
            self.stop_reader()
