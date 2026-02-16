import serial
import time
import threading

def monitor_port(port, baud):
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            print(f"Monitoring {port} @ {baud}...")
            while True:
                # Send trigger 0x05 (ENQ) to see if scale responds
                ser.write(b'\x05')
                time.sleep(0.1)
                line = ser.read_until(b'\x03')
                if line:
                    print(f"\n[DATA FOUND] {port}: {line.hex(' ')} | {line.decode('ascii', errors='replace').strip()}")
                time.sleep(0.5)
    except Exception as e:
        # print(f"Error {port}: {e}")
        pass

ports = [
    "/dev/cu.usbserial-FTARKJMG0",
    "/dev/cu.usbserial-FTARKJMG1",
    "/dev/cu.usbserial-FTARKJMG2",
    "/dev/cu.usbserial-FTARKJMG3"
]

for p in ports:
    threading.Thread(target=monitor_port, args=(p, 9600), daemon=True).start()

print("Scanning for Scale 1 (ENQ scan at 9600)...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
