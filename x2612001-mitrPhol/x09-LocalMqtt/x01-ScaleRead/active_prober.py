import serial
import time

ports = ["/dev/cu.usbserial-FTARKJMG0", "/dev/cu.usbserial-FTARKJMG1", "/dev/cu.usbserial-FTARKJMG2", "/dev/cu.usbserial-FTARKJMG3"]
bauds = [9600, 115200]
commands = [b'R\r\n', b'READ\r\n', b'\x05', b'W\r\n', b'P\r\n'] # Common trigger commands

print("Force-testing all ports...")
for p in ports:
    for b in bauds:
        try:
            with serial.Serial(p, b, timeout=1) as ser:
                for cmd in commands:
                    print(f"Testing {p} @ {b} with cmd {cmd.hex()}", end="\r")
                    ser.write(cmd)
                    time.sleep(0.5)
                    data = ser.read(100)
                    if data:
                        print(f"\n[FOUND DATA!] {p} @ {b}: {data.hex(' ')} | {data.decode('ascii', errors='replace')}")
        except:
            pass
print("\nScan complete.")
