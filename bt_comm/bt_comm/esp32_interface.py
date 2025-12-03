"""
ESP32 Interface for USB VCP bridge to HM-10
"""

import time
import serial
import re


class ESP32Interface:
    """Interface for communication with HM-10 via ESP32 USB VCP bridge"""
    
    def __init__(self, port, baudrate=115200):
        """
        Initialize the ESP32 interface
        
        Args:
            port (str): The serial port for ESP32 (e.g., /dev/ttyUSB0, COM3)
            baudrate (int): The baud rate for serial communication (default: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.bt_com_pattern = re.compile(r'I\s*\(\s*\d+\s*\)\s*bt_com:\s*(.*)$')
        self.read_buffer = ""  # Buffer for incomplete lines
        
    def connect(self):
        """
        Connect to the ESP32 via serial port
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            print(f"✓ Connected to ESP32 on {self.port}")
            self.connected = True
            
            # Give ESP32 a moment to initialize
            time.sleep(0.5)
            
            return True
        except Exception as e:
            print(f"✗ Failed to connect to ESP32: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the ESP32"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("✓ Disconnected from ESP32")
        
        self.connected = False
    
    def send_at_command(self, command, wait_response=True, timeout=2.0):
        """
        Send an AT command to the ESP32
        
        Args:
            command (str): The AT command to send (without newline)
            wait_response (bool): Whether to wait for a response
            timeout (float): Maximum time to wait for response
            
        Returns:
            str: The response message from ESP32, or None if no response
        """
        # Send the AT command
        if not self.send(command):
            return None
        
        if wait_response:
            # Read the response (filtered through bt_com)
            return self.read(timeout=timeout)
        
        return None
    
    def set_target_device(self, device_name):
        """
        Set the target HM-10 device name for ESP32 to connect to
        
        Args:
            device_name (str): The name of the HM-10 device
            
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"Setting target device to: {device_name}")
        
        # Send AT+NAME command
        response = self.send_at_command(f"AT+NAME{device_name}")
        
        # Check if the response is valid
        if not response or f"OK+SET{device_name}" not in response:
            print(f"✗ Failed to set target device name")
            return False
        
        # Reset ESP32 to apply changes
        print("Resetting ESP32...")
        self.send_at_command("AT+RESET")
        
        # Wait for ESP32 to reboot
        time.sleep(5)
        
        # Clear any buffered data after reset
        if self.serial and self.serial.is_open:
            self.serial.reset_input_buffer()
        
        print("✓ Target device set and ESP32 reset")
        return True
    
    def check_status(self):
        """
        Check if ESP32 is connected to HM-10
        
        Returns:
            str: "CONNECTED" if connected, "DISCONNECTED" if not, None on error
        """
        response = self.send_at_command("AT+STATUS?", timeout=1)
        
        if response:
            if "OK+CONN" in response:
                return "CONNECTED"
            elif "OK+UNCONN" in response:
                return "DISCONNECTED"
        else:
            return "UNKNOWN"
        
        return None
    
    def send(self, data):
        """
        Send data to HM-10 via ESP32
        
        Args:
            data (str): The data to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.serial or not self.serial.is_open:
            print("✗ Not connected to ESP32")
            return False
        
        try:
            # Data without AT prefix goes directly to HM-10
            self.serial.write(data.encode('utf-8'))
            self.serial.flush()
            return True
        except Exception as e:
            print(f"✗ Error sending data: {e}")
            return False
    
    def available(self):
        """
        Check if there is data available to read from the serial port.
        
        Returns:
            bool: True if data is available, False otherwise
        """
        if not self.serial or not self.serial.is_open:
            return False
        
        return self.serial.in_waiting > 0
    
    def read(self, timeout=0.1):
        """
        Read messages from ESP32, filtering for bt_com messages only.
        Reads all available data, filters lines starting with "I (*) bt_com: ",
        and concatenates the message parts.
        
        Args:
            timeout (float): Maximum time to wait for data in seconds (default: 0.1)
            
        Returns:
            str: The concatenated message from bt_com lines, or None if no message
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        start_time = time.time()
        message_parts = []
        
        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                # Read available data
                data = self.serial.read(self.serial.in_waiting)
                decoded = data.decode('utf-8', errors='replace')
                self.read_buffer += decoded
                
                # Process complete lines from buffer
                while '\n' in self.read_buffer:
                    line, self.read_buffer = self.read_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line:
                        # Check if line matches the bt_com pattern
                        match = self.bt_com_pattern.search(line)
                        if match:
                            # Extract the message part after "bt_com: "
                            message = match.group(1)
                            message_parts.append(message)
                
                # Reset timeout after receiving data
                start_time = time.time()
            else:
                time.sleep(0.01)
        
        # Return concatenated message if any parts were found
        if message_parts:
            return ''.join(message_parts)
        
        return None