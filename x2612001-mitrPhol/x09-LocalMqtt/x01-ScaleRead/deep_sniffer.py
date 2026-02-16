import serial
import time
import threading

def monitor_port(port, baud):
    try:
        # Use short timeout to cycle quickly
        with serial.Serial(port, baud, timeout=0.5) as ser:
            # Clear junk
            ser.read(100)
            while True:
                line = ser.readline()
                if line:
                    clean = line.decode('ascii', errors='replace').strip()
                    if any(c.isdigit() for c in clean): # Only print if it looks like there's a number
                        print(f"[{port} @ {baud}] RECEIVED: {clean}")
    except:
        pass

ports = ["/dev/cu.usbserial-FTARKJMG0", "/dev/cu.usbserial-FTARKJMG1", "/dev/cu.usbserial-FTARKJMG2", "/dev/cu.usbserial-FTARKJMG3"]
bauds = [2400, 4800, 9600, 19200, 38400, 115200]

print(f"Scanning {len(ports)*len(bauds)} combinations...")
for p in ports:
    for b in bauds:
        threading.Thread(target=monitor_port, args=(p, b), daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
