import serial
import paho.mqtt.client as mqtt
import time
import threading
import glob
import re

# Configuration
BROKER = "localhost"
MQTT_USER = "admin"
MQTT_PASS = "admin"
BAUD = 9600

# Find all matching USB serial ports
PORTS = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/cu.usbserial*")

def port_reader(port, mqtt_client):
    print(f"[Scanner-Reader] Starting listener for {port}")
    while True:
        try:
            with serial.Serial(port, BAUD, timeout=1) as ser:
                print(f"[Scanner-Reader] Connected to {port}")
                while True:
                    line = ser.readline()
                    if line:
                        try:
                            payload = line.decode('ascii', errors='replace').strip()
                            # Clean payload
                            payload = "".join(c for c in payload if c.isprintable())
                            
                            if len(payload) > 3 and not (payload.startswith('A') or payload.startswith('B') or payload.startswith('C')):
                                # Attempt to extract barcode from noisy data
                                match = re.search(r'>>CODE128:[^:]+:[^:]+:([^:]+)', payload)
                                if match:
                                    payload = match.group(1).strip()
                                else:
                                    # Strip non-alphanumeric at start
                                    payload = re.sub(r'^[^a-zA-Z0-9>]+', '', payload)
                                
                                if payload:
                                    # Topic 1: Raw
                                    mqtt_client.publish("scanner-01", payload)
                                    # Topic 2: JSON
                                    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
                                    json_payload = f'{{"barcode": "{payload}", "node_id": "scanner-01", "timestamp": "{ts}"}}'
                                    mqtt_client.publish("scanner/scanner-01/scan", json_payload)
                                    print(f"[Scanner] Scanned: {payload}")
                        except Exception as e:
                            print(f"[Scanner] Parse error: {e}")
                    time.sleep(0.01)
        except Exception as e:
            print(f"[Scanner-Reader] Connection lost on {port}: {e}. Retrying in 5s...")
            time.sleep(5)

def main():
    if not PORTS:
        print("No serial ports found for Scanner.")
        return

    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_start()
        print("Scanner-Reader: Connected to MQTT")
    except Exception as e:
        print(f"Scanner-Reader: Failed to connect to MQTT: {e}")
        return

    for port in PORTS:
        threading.Thread(target=port_reader, args=(port, client), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()

if __name__ == "__main__":
    main()
