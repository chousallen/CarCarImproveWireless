"""Hardware end-to-end test for the ESP32 HM-10 bridge.

Path under test: PC -> ESP32 (esp32-hm10 firmware) -> BLE -> HM-10 -> Arduino Mega -> PC, and back.
The Mega must run a plain Serial (115200) <-> Serial3 (HM-10) pass-through.
The ESP32 must already target the HM-10's name (AT+NAME<name>).

usage: python tests/hw_e2e.py [--esp /dev/ttyUSB0] [--mega /dev/ttyUSB1] [--name HM10_Mega]
Exit code 0 when every check passes.
"""
import argparse, os, re, subprocess, sys, tempfile, threading, time
import serial

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "chat_hm10"))
from hm10_esp32 import HM10ESP32Bridge  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--esp", default="/dev/ttyUSB0", help="ESP32 serial port")
ap.add_argument("--mega", default="/dev/ttyUSB1", help="Arduino Mega serial port")
ap.add_argument("--name", default="HM10_Mega", help="HM-10 name the ESP32 should target")
args = ap.parse_args()

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}", flush=True)

def wait_for(pred, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False

# ---- Mega side: collect everything it prints ----
mega = serial.Serial(args.mega, 115200, timeout=0.1)
mega_out = bytearray()
lock = threading.Lock()
stop = False
def mega_reader():
    while not stop:
        d = mega.read(4096)
        if d:
            with lock:
                mega_out.extend(d)
threading.Thread(target=mega_reader, daemon=True).start()
time.sleep(3)  # opening the port resets the Mega

def mega_text():
    with lock:
        return mega_out.decode(errors="replace")

def mega_clear():
    with lock:
        mega_out.clear()

def mega_has(msg):
    return msg in re.sub(r"\r?\n", "", mega_text())

# ---- ESP32 side: the same bridge class the chat script uses ----
br = HM10ESP32Bridge(port=args.esp)

def esp_to_mega(name, msg, timeout=6):
    mega_clear()
    br.send(msg)
    ok = wait_for(lambda: mega_has(msg), timeout)
    check(name, ok, "" if ok else f"mega saw: {mega_text()!r}")

def mega_to_esp(name, msg, timeout=6):
    br.listen()  # drain
    mega.write(msg.encode() + b"\n")
    acc = ""
    end = time.time() + timeout
    while time.time() < end and msg not in acc:
        acc += br.listen()
        time.sleep(0.05)
    check(name, msg in acc, "" if msg in acc else f"esp saw: {acc!r}")

t0 = time.time()
ok = wait_for(lambda: br.get_status(timeout=1.0) == "CONNECTED", 60)
check("T1  AT+STATUS? reports CONNECTED", ok, f"({time.time()-t0:.1f}s)")
if not ok:
    sys.exit(1)
check("T2  AT+NAME? returns target", br.get_hm10_name() == args.name)

esp_to_mega("T3  ESP->Mega short (5 B)", "ping1")
esp_to_mega("T4  ESP->Mega long (52 B, 6 BLE writes)", "The quick brown fox jumps over the lazy dog 0123456")
esp_to_mega("T5  ESP->Mega UTF-8 (12 B, split mid-char)", "你好世界")
mega_to_esp("T6  Mega->ESP short (5 B)", "pong1")
mega_to_esp("T7  Mega->ESP long (52 B, 3 notifies)", "Pack my box with five dozen liquor jugs 9876543210ab")
mega_to_esp("T8  Mega->ESP UTF-8 (12 B)", "早安台大")

mega_clear()
for i in range(10):
    br.send(f"b{i:02d};")
    time.sleep(0.05)
check("T9  ESP->Mega burst of 10", wait_for(lambda: all(mega_has(f"b{i:02d};") for i in range(10)), 8))

# After a reboot, data sent as soon as AT+STATUS? says CONNECTED must arrive.
for n in range(3):
    br.ser.write(b"AT+RESET")
    time.sleep(1.0)
    t0 = time.time()
    ok = wait_for(lambda: br.get_status(timeout=0.5) == "CONNECTED", 30)
    check(f"T10 reboot {n+1}: reconnects", ok, f"({time.time()-t0:.1f}s)")
    esp_to_mega(f"T11 reboot {n+1}: ESP->Mega right after CONNECTED", f"first-after-reset-{n}")
mega_to_esp("T12 Mega->ESP after reboots", "back-again")

# The bridge's reset() must return only once the link is usable (chat script relies on it).
ok = br.reset()
check("T12b bridge.reset() returns with link CONNECTED", ok and br.get_status() == "CONNECTED")
esp_to_mega("T12c ESP->Mega right after bridge.reset()", "after-bridge-reset")
br.close()

# ---- The real chat script, with PORT pointed at the ESP32 ----
src = open(os.path.join(REPO, "chat_hm10", "chat_hm10-esp32.py"), encoding="utf-8").read()
src = re.sub(r"^PORT = .*$", f"PORT = {args.esp!r}", src, count=1, flags=re.M)
src = re.sub(r"^EXPECTED_NAME = .*$", f"EXPECTED_NAME = {args.name!r}", src, count=1, flags=re.M)
with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
    f.write(src)
# UTF-8 everywhere: the chat script prints emoji, and Windows defaults to the locale code page.
env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "chat_hm10"), PYTHONUNBUFFERED="1",
           PYTHONIOENCODING="utf-8")
p = subprocess.Popen([sys.executable, f.name], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, env=env, text=True, encoding="utf-8")
chat_out = []
threading.Thread(target=lambda: [chat_out.append(l) for l in p.stdout], daemon=True).start()
ready = wait_for(lambda: any("Ready!" in l for l in chat_out), 15)
check("T13 chat script starts and reports Ready", ready, "" if ready else repr(chat_out))
mega_clear()
p.stdin.write("hi from chat script\n"); p.stdin.flush()
check("T14 chat script -> Mega", wait_for(lambda: mega_has("hi from chat script"), 6))
mega.write(b"reply to chat\n")
check("T15 Mega -> chat script", wait_for(lambda: any("[HM10]: reply to chat" in l for l in chat_out), 6))
p.stdin.write("exit\n"); p.stdin.flush()
try:
    p.wait(5)
    check("T16 chat script exits cleanly", p.returncode == 0 and any("Chat closed" in l for l in chat_out))
except subprocess.TimeoutExpired:
    p.kill()
    check("T16 chat script exits cleanly", False, "timeout")
os.unlink(f.name)

stop = True
time.sleep(0.2)
mega.close()
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
