import serial
import paho.mqtt.client as mqtt
import time
import threading
import glob

# Configuration
BROKER = "localhost"
MQTT_USER = "admin"
MQTT_PASS = "admin"
BAUD = 9600

# Find all matching USB serial ports
PORTS = sorted(glob.glob("/dev/ttyUSB*"))
if not PORTS:
    print("[Scale-Reader] !!! No serial ports discovered. (/dev/ttyUSB*) !!!")
    time.sleep(5)
    PORTS = []

# Shared state for heartbeats
scale_heartbeats = {
    "scale-01": 0.0,
    "scale-02": 0.0,
    "scale-03": 0.0
}
heartbeat_lock = threading.Lock()

def scale_monitor(mqtt_client):
    """Monitors expected scales and reports errors if silent > 5s"""
    print("[Scale-Monitor] Starting Watchdog Monitor...")
    required_scales = ["scale-01", "scale-02", "scale-03"]
    startup_grace = time.time() + 5.0
    
    while True:
        if time.time() < startup_grace:
            time.sleep(1)
            continue
            
        current_time = time.time()
        for scale_id in required_scales:
            last_seen = 0.0
            with heartbeat_lock:
                last_seen = scale_heartbeats.get(scale_id, 0.0)
            
            if current_time - last_seen > 5.0:
                topic = f"scale/{scale_id}"
                err_payload = f'{{"weight": 0.0, "scale_id": "{scale_id}", "error_msg": "----", "detail": "Watchdog Timeout"}}'
                try:
                    mqtt_client.publish(topic, err_payload)
                except Exception as e:
                    print(f"Error publishing monitor alert: {e}")
        time.sleep(1.0)

def port_reader(port, mqtt_client):
    print(f"[Scale-Reader] Starting listener for {port}")
    last_topic = None
    last_scale_id = None
    timeout_count = 0
    MAX_TIMEOUTS = 5

    while True:
        try:
            with serial.Serial(port, BAUD, timeout=1) as ser:
                print(f"[Scale-Reader] Connected to {port}")
                while True:
                    try:
                        # Trigger ENQ to get data (Protocol requirement)
                        ser.write(b'\x05')
                        
                        # Read until ETX (0x03)
                        line = ser.read_until(b'\x03')
                        
                        if line:
                            timeout_count = 0
                            # Clean bytes (remove STX/ETX)
                            clean_bytes = line[1:-1] if line.startswith(b'\x02') and line.endswith(b'\x03') else line
                            payload = "".join(c for c in clean_bytes.decode('ascii', errors='replace') if c.isprintable() or c == '.')
                            
                            if payload:
                                topic = None
                                scale_id = "unknown"
                                weight_str = ""
                                
                                # Dynamic Routing & Parsing
                                if payload.startswith('A'):
                                    topic = "scale/scale-01"
                                    scale_id = "scale-01"
                                    weight_str = payload[1:].strip()
                                    try:
                                        if len(weight_str) >= 9:
                                            status_char = weight_str[0]
                                            sign_char = weight_str[1]
                                            data_str = weight_str[2:8]
                                            decimal_char = weight_str[8]
                                            
                                            raw_val = float(data_str)
                                            decimal_places = int(decimal_char)
                                            final_weight = raw_val / (10 ** decimal_places)
                                            if sign_char == '-': final_weight = -final_weight
                                            is_stable = (status_char == '0')
                                            
                                            # Extract unit from packet (usually at index 10)
                                            unit_part = "kg"
                                            if len(weight_str) >= 12:
                                                extracted_unit = weight_str[10:12].strip()
                                                if extracted_unit: unit_part = extracted_unit
                                            
                                            json_payload = f'{{"weight": {final_weight}, "scale_id": "{scale_id}", "unit": "{unit_part.lower()}", "stable": {str(is_stable).lower()}}}'
                                            mqtt_client.publish(topic, json_payload)
                                            print(f"[Echo] {scale_id} on {port}: {final_weight} {unit_part} (Stable: {is_stable})")
                                    except Exception as e:
                                        print(f"[{scale_id}] Parse Error: {e}")

                                elif "GS" in payload:
                                    # Handle Scale 2 Format: ST,GS   533.6,g
                                    topic = "scale/scale-02"
                                    scale_id = "scale-02"
                                    try:
                                        # Use regex-like approach to find the first GS and extract weight
                                        # Example payload: "ST,GS   533.6,g ST,GS..."
                                        import re
                                        # Find all patterns like ST,GS 123.4,g or US,GS 123.4,g
                                        match = re.search(r'(ST|US),GS\s*(-?[\d.]+)\s*,(g|kg)', payload)
                                        if match:
                                            status_part = match.group(1) # ST or US
                                            val_str = match.group(2)     # 533.6
                                            unit_part = match.group(3)   # g or kg
                                            
                                            final_weight = float(val_str)
                                            # Use the unit directly from the scale as requested
                                            is_stable = (status_part == 'ST')
                                            json_payload = f'{{"weight": {final_weight}, "scale_id": "{scale_id}", "unit": "{unit_part}", "stable": {str(is_stable).lower()}}}'
                                            mqtt_client.publish(topic, json_payload)
                                            print(f"[Echo] {scale_id} on {port}: {final_weight} {unit_part} (Stable: {is_stable})")
                                    except Exception as e:
                                        print(f"[{scale_id}] Parse Error: {e}")

                                elif payload.startswith('B'):
                                    topic = "scale/scale-02"
                                    scale_id = "scale-02"
                                    weight_str = payload[1:].strip()
                                    # (Use existing logic if B ever appears)
                                elif payload.startswith('C'):
                                    topic = "scale/scale-03"
                                    scale_id = "scale-03"
                                    weight_str = payload[1:].strip()
                                else:
                                    if len(payload) > 3:
                                        print(f"[Port:{port}] Unknown format: {payload[:20]}...")
                                
                                if topic:
                                    last_topic = topic
                                    last_scale_id = scale_id
                                    with heartbeat_lock:
                                        scale_heartbeats[scale_id] = time.time()
                        else:
                            timeout_count += 1
                            if timeout_count >= MAX_TIMEOUTS:
                                if last_topic:
                                    err_payload = f'{{"weight": 0.0, "scale_id": "{last_scale_id}", "error_msg": "----"}}'
                                    mqtt_client.publish(last_topic, err_payload)
                                timeout_count = 0
                        time.sleep(0.25)
                    except serial.SerialTimeoutException:
                        pass
        except Exception as e:
            print(f"[Scale-Reader] Connection lost on {port}: {e}. Retrying in 5s...")
            time.sleep(5)

def main():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_start()
        print("[Scale-Reader] Successfully Connected to RabbitMQ Broker")
    except Exception as e:
        print(f"[Scale-Reader] !!! Failed to connect to MQTT: {e} !!!")
        return

    threading.Thread(target=scale_monitor, args=(client,), daemon=True).start()

    for port in PORTS:
        t = threading.Thread(target=port_reader, args=(port, client), daemon=True)
        t.start()
        print(f"[Scale-Reader] Initializing thread for {port}")

    print(f"[Scale-Reader] Active Monitoring Ports: {', '.join(PORTS)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()

if __name__ == "__main__":
    main()
