import paho.mqtt.client as mqtt
import time
import json

BROKER = "localhost"
PORT = 1883
USER = "admin"
PASS = "admin"

def simulate():
    client = mqtt.Client()
    client.username_pw_set(USER, PASS)
    
    try:
        client.connect(BROKER, PORT, 60)
        print(f"Connected to MQTT Broker at {BROKER}:{PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Mock Data
    barcode = "SIMULATED-SCAN-001"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    # 1. Publish Raw (User requested topic)
    client.publish("scanner-01", barcode)
    print(f"[Sim] Published raw to 'scanner-01': {barcode}")

    # 2. Publish JSON (Frontend topic)
    payload = {
        "barcode": barcode,
        "node_id": "scanner-01",
        "timestamp": timestamp
    }
    json_payload = json.dumps(payload)
    client.publish("scanner/scanner-01/scan", json_payload)
    print(f"[Sim] Published JSON to 'scanner/scanner-01/scan': {json_payload}")

    client.disconnect()

if __name__ == "__main__":
    simulate()
