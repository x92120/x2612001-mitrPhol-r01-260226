import serial
import serial.tools.list_ports
import time
import sys

def monitor_port(port_path, baud):
    print(f"\n--- Monitoring {port_path} at {baud} bps ---")
    print("Press Ctrl+C to stop.")
    try:
        with serial.Serial(port_path, baud, timeout=1) as ser:
            while True:
                line = ser.readline()
                if line:
                    try:
                        # Try to decode and strip common scale line endings
                        text = line.decode('ascii', errors='replace').strip()
                        print(f"[{time.strftime('%H:%M:%S')}] RAW: {line.hex(' ')} | TEXT: {text}")
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] RAW: {line.hex(' ')}")
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    # If no arguments, we monitor FTARKJMG0 @ 9600 as a default guess
    # but based on the previous scan, nothing showed "clean" weight data yet.
    # The user might need to check which device is actually the scale.
    
    port = "/dev/cu.usbserial-FTARKJMG0"
    baud = 9600
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        baud = int(sys.argv[2])
        
    monitor_port(port, baud)
