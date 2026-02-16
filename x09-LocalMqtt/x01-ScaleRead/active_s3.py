
import serial
import time
import threading

def monitor_port(port, baud):
    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            time.sleep(0.5)
            ser.reset_input_buffer()
            # Send ENQ but expecting address C (Scale 3?)
            ser.write(b'\x05')
            time.sleep(0.5)
            
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                # Ignore S1 and S2 if they respond
                decoded = data.decode('ascii', errors='replace').strip()
                if "A0" in decoded:
                    print(f"Skipping S1 on {port}")
                elif "B0" in decoded:
                    print(f"Skipping S2 on {port}")
                else:
                    print(f"[NEW DEVICE?] {port}: {data.hex(' ')} | {decoded}")
                
            ser.reset_input_buffer()
    except Exception:
        pass

ports = [
    "/dev/cu.usbserial-FTARKJMG0",
    "/dev/cu.usbserial-FTARKJMG1",
    "/dev/cu.usbserial-FTARKJMG2",
    "/dev/cu.usbserial-FTARKJMG3"
]

print("Probing specifically for NEW devices...")
for p in ports:
    threading.Thread(target=monitor_port, args=(p, 9600), daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("End")
