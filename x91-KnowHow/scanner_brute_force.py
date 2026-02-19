import serial
import time
import glob
import itertools

# Settings to cycle
BAUDS = [9600, 19200, 38400, 57600, 115200]
PARITIES = [serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD]
BYTESIZES = [serial.EIGHTBITS, serial.SEVENBITS]
STOPBITS = [serial.STOPBITS_ONE, serial.STOPBITS_TWO]

def test_configurations():
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    if not ports:
        print("Error: No serial ports found.")
        return

    port = ports[0]
    print(f"--- Starting Brute Force on {port} ---")
    print("For each setting, scan the barcode once.")
    print("If you see 'H620', that's our winner!\n")

    # Generate all combinations
    combinations = list(itertools.product(BAUDS, PARITIES, BYTESIZES, STOPBITS))
    
    for baud, parity, size, stop in combinations:
        parity_name = {serial.PARITY_NONE: 'N', serial.PARITY_EVEN: 'E', serial.PARITY_ODD: 'O'}[parity]
        config_str = f"{baud} {size}{parity_name}{stop}"
        
        print(f"\n[Setting] {config_str} - OPENING...")
        
        try:
            with serial.Serial(port, baud, bytesize=size, parity=parity, stopbits=stop, timeout=5) as ser:
                print(f"[Ready] Scan now (Waiting 5 seconds)...")
                raw_data = ser.read(100) # Read up to 100 bytes
                
                if raw_data:
                    hex_data = raw_data.hex(' ')
                    try:
                        text_data = raw_data.decode('utf-8', errors='replace').strip()
                        print(f" >> DATA (Text): {text_data}")
                    except:
                        print(" >> DATA (Text): [Undecodable]")
                    print(f" >> DATA (Hex) : {hex_data}")
                    
                    if "H620" in (text_data or ""):
                        print(f"\n✨ SUCCESS! Found correct setting: {config_str}")
                        return
                else:
                    print(" >> No data received.")
                    
        except Exception as e:
            print(f" >> Error: {e}")
        
        # small delay before next attempt
        time.sleep(0.5)

if __name__ == "__main__":
    test_configurations()
