import serial
import time

def read_from_scanner(port, baud_rate=9600):
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        print(f"Connected to {port} at {baud_rate} baud.")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"Scanned: {line}")
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Error accessing serial port: {e}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    scanner_port = '/dev/ttyACM0'  # Update this if your port is different
    read_from_scanner(scanner_port)
