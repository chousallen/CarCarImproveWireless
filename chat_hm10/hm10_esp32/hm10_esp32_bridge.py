import serial
import time
import re

class HM10ESP32Bridge:
    def __init__(self, port, rx_timeout=0.1):
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=rx_timeout)
        # ESP-IDF log record: ESC[0;32mI (<ms>) bt_com: <payload>ESC[0m\r\n
        # The payload may itself contain newlines, so the record ends at the
        # colour-reset code, not at the first line break.
        self.record_start = re.compile(rb'\x1b\[[0-9;]*m[A-Z] \(\d+\) bt_com: ')
        self.record_end = b'\x1b[0m\r\n'
        # Bytes read from the port that do not yet form a complete record
        self._rx_buf = b''
        time.sleep(1)

    def _read_bt_com_payloads(self):
        """Returns the payloads of all complete 'bt_com' records received so far."""
        if self.ser.in_waiting:
            self._rx_buf += self.ser.read_all()
        payloads = []
        while True:
            start = self.record_start.search(self._rx_buf)
            if not start:
                # Keep a record start that is still arriving; drop other output
                esc = self._rx_buf.rfind(b'\x1b')
                self._rx_buf = self._rx_buf[esc:] if esc >= 0 else b''
                break
            end = self._rx_buf.find(self.record_end, start.end())
            if end < 0:
                self._rx_buf = self._rx_buf[start.start():]
                break
            payload = self._rx_buf[start.end():end]
            # The ESP32 sends each '\n' in the payload as '\r\n'; undo that
            payload = payload.replace(b'\r\n', b'\n')
            payloads.append(payload.decode('utf-8', errors='ignore'))
            self._rx_buf = self._rx_buf[end + len(self.record_end):]
        return payloads

    def set_hm10_name(self, name, timeout=2.0):
        """
        Sends AT+NAME<name> and verifies OK+SET<name> reply.
        Returns True on success, False on timeout/failure.
        """
        command = f"AT+NAME{name}"
        self.ser.write(command.encode('utf-8'))
        
        # Poll for the specific OK+SET response
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            for entry in self._read_bt_com_payloads():
                if f"OK+SET{name}" in entry:
                    return True
            time.sleep(0.01)
        return False

    def get_hm10_name(self, timeout=2.0):
        """Queries the device name currently in NVS."""
        self.ser.write(b"AT+NAME?")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            for entry in self._read_bt_com_payloads():
                if "OK+NAME" in entry:
                    return entry.replace("OK+NAME", "").strip()
            time.sleep(0.01)
        return None

    def get_status(self, timeout=2.0):
        """Checks connection status via AT+STATUS?."""
        self.ser.write(b"AT+STATUS?")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            for entry in self._read_bt_com_payloads():
                if "OK+CONN" in entry: return "CONNECTED"
                if "OK+UNCONN" in entry: return "DISCONNECTED"
            time.sleep(0.01)
        return "TIMEOUT"

    def reset(self):
        """Triggers AT+RESET and returns True if OK+RESET is received."""
        self.ser.write(b"AT+RESET")
        start_time = time.time()
        while (time.time() - start_time) < 10.0:
            for entry in self._read_bt_com_payloads():
                if "OK+RESET" in entry:
                    time.sleep(6) # Wait for ESP32 to reboot and connect to HM-10
                    return True
            time.sleep(0.01)
        return False

    def listen(self):
        """Returns concatenated data from BLE (ignores AT replies)."""
        logs = self._read_bt_com_payloads()
        data_parts = [l for l in logs if not l.startswith("OK+")]
        return "".join(data_parts)

    def send(self, text):
        """Sends data to be forwarded to HM-10 via GATT."""
        self.ser.write(text.encode('utf-8'))

    def close(self):
        """Explicitly close the serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def __del__(self):
        """Ensure serial port is closed when object is destroyed."""
        self.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures port is closed."""
        self.close()
        return False