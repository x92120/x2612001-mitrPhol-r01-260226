import serial
import time
import threading

def monitor_port(port, baud):
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            print(f"Started monitoring {port} at {baud}")
            while True:
                line = ser.readline()
                if line:
                    print(f"[{port}] RAW: {line.hex(' ')} | TEXT: {line.decode('ascii', errors='replace').strip()}")
    except Exception as e:
        # print(f"[{port}] Off: {e}")
        pass

ports = [
    "/dev/cu.usbserial-FTARKJMG0",
    "/dev/cu.usbserial-FTARKJMG1",
    "/dev/cu.usbserial-FTARKJMG2",
    "/dev/cu.usbserial-FTARKJMG3"
]

bauds = [9600, 115200] # Most common for these devices

threads = []
for p in ports:
    for b in bauds:
        t = threading.Thread(target=monitor_port, args=(p, b), daemon=True)
        t.start()
        threads.append(t)

print("Monitoring all FTARKJMG ports... (9600 & 115200)")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
