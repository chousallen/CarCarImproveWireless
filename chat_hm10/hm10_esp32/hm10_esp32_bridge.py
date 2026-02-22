import serial
import time
import re

class ESP32HM10Bridge:
    def __init__(self, port='/dev/ttyUSB2', baudrate=115200, timeout=0.1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.log_regex = re.compile(r'bt_com:\s*(.*)')
        self.ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
        time.sleep(1) 

    def _read_bt_com_payloads(self):
        if self.ser.in_waiting == 0:
            return []
        raw_data = self.ser.read_all().decode('utf-8', errors='ignore')
        lines = raw_data.splitlines()
        payloads = []
        for line in lines:
            match = self.log_regex.search(line)
            if match:
                clean_payload = self.ansi_regex.sub('', match.group(1)).strip()
                payloads.append(clean_payload)
        return payloads

    def get_status(self):
        self.ser.write(b"AT+STATUS?")
        start_time = time.time()
        while (time.time() - start_time) < 1.0:
            for entry in self._read_bt_com_payloads():
                if "OK+CONN" in entry: return "CONNECTED"
                if "OK+UNCONN" in entry: return "DISCONNECTED"
            time.sleep(0.1)
        return "TIMEOUT"

    def get_hm10_name(self):
        self.ser.write(b"AT+NAME?")
        start_time = time.time()
        while (time.time() - start_time) < 1.0:
            for entry in self._read_bt_com_payloads():
                if "OK+NAME" in entry:
                    return entry.replace("OK+NAME", "").strip()
            time.sleep(0.1)
        return None

    def listen(self):
        """Collects and joins all bt_com logs that aren't AT responses."""
        logs = self._read_bt_com_payloads()
        # Filter out the ESP32's own AT protocol feedback
        data_parts = [l for l in logs if not l.startswith("OK+")]
        
        if not data_parts:
            return ""
            
        # Join into a single string. 
        # If your HM-10 sends data in rapid bursts, this keeps them together.
        return "".join(data_parts)

    def send(self, text):
        """Sends text to the ESP32 (which forwards to HM-10)."""
        self.ser.write(text.encode('utf-8'))