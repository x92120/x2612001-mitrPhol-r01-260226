import serial
import serial.tools.list_ports
import time

def list_available_ports():
    print("--- Available Serial Ports ---")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Port: {port.device} - {port.description}")
    return ports

def test_baud_rates(port_path):
    baud_rates = [4800, 9600, 19200, 38400, 57600, 115200]
    print(f"\n--- Testing Baud Rates on {port_path} ---")
    
    for baud in baud_rates:
        print(f"Testing {baud} bps...", end=" ", flush=True)
        try:
            with serial.Serial(port_path, baud, timeout=2) as ser:
                # Read a bit of data to see if it looks like something readable
                data = ser.read(100)
                if data:
                    print(f" [SUCCESS] Data received: {data.hex(' ')}")
                    try:
                        print(f" Formatted: {data.decode('ascii', errors='replace').strip()}")
                    except:
                        pass
                else:
                    print(" [TIMEOUT] No data received.")
        except Exception as e:
            print(f" [ERROR] {e}")

def main():
    ports = list_available_ports()
    if not ports:
        print("No serial ports found!")
        return

    # Check for usbserial ports specifically
    usb_ports = [p.device for p in ports if "usbserial" in p.device]
    
    if not usb_ports:
        print("No USB serial devices detected.")
        return

    print(f"\nFound {len(usb_ports)} USB serial devices.")
    
    for port in usb_ports:
        test_baud_rates(port)

    print("\nSelect a port to monitor (e.g., /dev/cu.usbserial-FTARKJMG0):")
    # In a real script we would take input, but for this utility we just scan.

if __name__ == "__main__":
    main()
