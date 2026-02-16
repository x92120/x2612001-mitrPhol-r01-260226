import serial
import time
import threading

def monitor_port(port, baud):
    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            print(f"Monitoring {port} @ {baud}...")
            ser.reset_input_buffer()
            while True:
                # Based on S1/S2 being ENQ triggered, try ENQ first BUT...
                # Some scales are continuous output. We'll listen passively AND try trigger
                
                # Active Trigger (ENQ | 0x05)
                ser.write(b'\x05')
                time.sleep(0.1)
                
                # Try simple Readline which works for CR/LF terminated
                if ser.in_waiting:
                    line = ser.readline()
                    if line:
                         print(f"\n[DATA FOUND] {port}: {line.hex(' ')} | {line.decode('ascii', errors='replace').strip()}")
                
                time.sleep(0.5)
    except Exception as e:
        pass

ports = [
    "/dev/cu.usbserial-FTARKJMG0",
    "/dev/cu.usbserial-FTARKJMG1",
    "/dev/cu.usbserial-FTARKJMG2",
    "/dev/cu.usbserial-FTARKJMG3"
]

print("Scanning for Scale 3...")
for p in ports:
    threading.Thread(target=monitor_port, args=(p, 9600), daemon=True).start()
    # threading.Thread(target=monitor_port, args=(p, 115200), daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
