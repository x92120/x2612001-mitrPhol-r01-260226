import serial
import paho.mqtt.client as mqtt
import time
import threading
import re

# Configuration
BROKER = "localhost"
MQTT_USER = "admin"
MQTT_PASS = "admin"

import glob

# specific to Mac; update for Linux/Windows if needed
# Find all matching USB serial ports
# Find all matching USB serial ports
PORTS = glob.glob("/dev/cu.usbserial-FTARK*") + glob.glob("/dev/cu.usbserial-FTWK*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
if not PORTS:
    # Fallback/Default for testing if no devices found
    PORTS = ["/dev/cu.usbserial-FTARKJMG0", "/dev/cu.usbserial-FTARKJMG1", "/dev/cu.usbserial-FTARKJMG2"]

print(f"Discovered Ports: {PORTS}")

BAUD = 9600

# Shared state for heartbeats
scale_heartbeats = {
    "scale-01": 0.0,
    "scale-02": 0.0,
    "scale-03": 0.0
}
heartbeat_lock = threading.Lock()

def scale_monitor(mqtt_client):
    """Monitors expected scales and reports errors if silent > 5s"""
    print("[Monitor] Starting Scale Watchdog Monitor...")
    required_scales = ["scale-01", "scale-02", "scale-03"]
    
    # Initialize heartbeats to current time so we don't error immediately on startup?
    # No, user wants error if missed. But maybe give 5s grace at start.
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
            
            # If stale > 5s (or never seen which is 0), report error
            if current_time - last_seen > 5.0:
                # Construct missing payload
                # Note: topic structure is scale/scale-XX based on our previous logic
                topic = f"scale/{scale_id}"
                err_payload = f'{{"weight": 0.0, "scale_id": "{scale_id}", "error_msg": "----", "detail": "Watchdog Timeout"}}'
                try:
                    mqtt_client.publish(topic, err_payload)
                except Exception as e:
                    print(f"Error publishing monitor alert: {e}")
        
        time.sleep(1.0) # Check every 1s

def port_reader(port, mqtt_client):
    print(f"[Port-Reader] Starting listener for {port}")
    
    last_topic = None
    last_scale_id = None
    timeout_count = 0
    MAX_TIMEOUTS = 5  # 5 seconds without data triggers error (watchdog)

    while True:
        try:
            with serial.Serial(port, BAUD, timeout=1) as ser:
                print(f"[Port-Reader] Connected to {port}")
                timeout_count = 0 # Reset on connect
                
                while True:
                    try:
                        # Trigger ENQ to get data (Protocol requirement)
                        ser.write(b'\x05')
                        
                        # Read until ETX (0x03)
                        line = ser.read_until(b'\x03')
                        
                        if line:
                            timeout_count = 0 # Reset on data activity
                            
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
                                    # Remove prefix 'A' and whitespace to get weight
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
                                    
                                    # Update Heartbeat
                                    with heartbeat_lock:
                                        scale_heartbeats[scale_id] = time.time()
                                    
                                    try:
                                        # Manual Parsing Logic
                                        # Format: [Status][Sign][Data 6 chars][Decimal 1 char]
                                        # Example: '0+0003993' -> Status=0, Sign=+, Data=000399, Decimal=3
                                        
                                        if len(weight_str) >= 9:
                                            status_char = weight_str[0]
                                            sign_char = weight_str[1]
                                            data_str = weight_str[2:8]
                                            decimal_char = weight_str[8]
                                            
                                            # Parse numeric parts
                                            raw_val = float(data_str)
                                            decimal_places = int(decimal_char)
                                            
                                            # Apply sign and decimal
                                            final_weight = raw_val / (10 ** decimal_places)
                                            if sign_char == '-':
                                                final_weight = -final_weight
                                                
                                            is_stable = (status_char == '0')
                                            
                                            # Create JSON payload
                                            json_payload = f'{{"weight": {final_weight}, "scale_id": "{scale_id}", "unit": "kg", "stable": {str(is_stable).lower()}}}'
                                            
                                            mqtt_client.publish(topic, json_payload)
                                            print(f"[{scale_id}] RAW: '{weight_str}' -> PARSED: {final_weight} (Stable: {is_stable})")
                                        else:
                                            print(f"[{scale_id}] Incomplete data (len {len(weight_str)}): '{weight_str}'")
                                            
                                    except ValueError as e:
                                        print(f"[{scale_id}] Parsing error: {e}")
                                else:
                                    pass # Ignore unknown data
                        else:
                            # Timeout occurred (empty line read)
                            timeout_count += 1
                            if timeout_count >= MAX_TIMEOUTS:
                                if last_topic:
                                    print(f"[{last_scale_id}] No data for {timeout_count}s. Sending error status.")
                                    err_payload = f'{{"weight": 0.0, "scale_id": "{last_scale_id}", "error_msg": "----"}}'
                                    mqtt_client.publish(last_topic, err_payload)
                                else:
                                    print(f"[Unknown Scale on {port}] Connected but no data/ID received for {timeout_count}s.")
                                
                                timeout_count = 0 # Don't spam immediately, wait another cycle
                                
                        time.sleep(0.02) # Fast polling
                        
                    except serial.SerialTimeoutException:
                         # Handle explicit timeout exception if raised
                        pass

        except Exception as e:
            print(f"[Port-Reader] Connection lost on {port}: {e}. Retrying in 5s...")
            if last_topic:
                 err_payload = f'{{"weight": 0.0, "scale_id": "{last_scale_id}", "error_msg": "----"}}'
                 mqtt_client.publish(last_topic, err_payload)
            time.sleep(5)

def main():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_start()
        print("Connected to MQTT Broker - Dynamic Bridge Active")
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
        return


    # Start Watchdog Monitor
    monitor_thread = threading.Thread(target=scale_monitor, args=(client,), daemon=True)
    monitor_thread.start()

    threads = []
    for port in PORTS:
        thread = threading.Thread(target=port_reader, args=(port, client), daemon=True)
        thread.start()
        threads.append(thread)

    print(f"Monitoring ports: {', '.join(PORTS)}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping bridge...")
    finally:
        client.loop_stop()

if __name__ == "__main__":
    main()
