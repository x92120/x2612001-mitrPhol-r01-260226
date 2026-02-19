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
PORTS = glob.glob("/dev/ttyUSB*")
if not PORTS:
    print("No serial ports discovered. Waiting...")
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
                                
                                # Dynamic Routing based on Prefix
                                if payload.startswith('A'):
                                    topic = "scale/scale-01"
                                    scale_id = "scale-01"
                                    weight_str = payload[1:].strip()
                                elif payload.startswith('B'):
                                    topic = "scale/scale-02"
                                    scale_id = "scale-02"
                                    weight_str = payload[1:].strip()
                                elif payload.startswith('C'):
                                    topic = "scale/scale-03"
                                    scale_id = "scale-03"
                                    weight_str = payload[1:].strip()
                                
                                if topic and weight_str:
                                    last_topic = topic
                                    last_scale_id = scale_id
                                    with heartbeat_lock:
                                        scale_heartbeats[scale_id] = time.time()
                                    
                                    try:
                                        if len(weight_str) >= 9:
                                            status_char = weight_str[0]
                                            sign_char = weight_str[1]
                                            data_str = weight_str[2:8]
                                            decimal_char = weight_str[8]
                                            
                                            raw_val = float(data_str)
                                            decimal_places = int(decimal_char)
                                            
                                            final_weight = raw_val / (10 ** decimal_places)
                                            if sign_char == '-':
                                                final_weight = -final_weight
                                                
                                            is_stable = (status_char == '0')
                                            json_payload = f'{{"weight": {final_weight}, "scale_id": "{scale_id}", "unit": "kg", "stable": {str(is_stable).lower()}}}'
                                            mqtt_client.publish(topic, json_payload)
                                            print(f"[{scale_id}] {final_weight} kg (Stable: {is_stable})")
                                    except ValueError as e:
                                        print(f"[{scale_id}] Parsing error: {e}")
                        else:
                            timeout_count += 1
                            if timeout_count >= MAX_TIMEOUTS:
                                if last_topic:
                                    err_payload = f'{{"weight": 0.0, "scale_id": "{last_scale_id}", "error_msg": "----"}}'
                                    mqtt_client.publish(last_topic, err_payload)
                                timeout_count = 0
                        time.sleep(0.02)
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
        print("Scale-Reader: Connected to MQTT")
    except Exception as e:
        print(f"Scale-Reader: Failed to connect to MQTT: {e}")
        return

    threading.Thread(target=scale_monitor, args=(client,), daemon=True).start()

    for port in PORTS:
        threading.Thread(target=port_reader, args=(port, client), daemon=True).start()

    print(f"Scale-Reader Monitoring: {', '.join(PORTS)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()

if __name__ == "__main__":
    main()
