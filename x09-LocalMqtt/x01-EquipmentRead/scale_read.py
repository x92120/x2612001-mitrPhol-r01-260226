"""
scale_read.py — Parallel Scale Reader (3 × RS-232 → MQTT)
Each scale has its own dedicated serial port and thread.
Sampling rate: 0.5 seconds per read cycle.
"""
import serial
import paho.mqtt.client as mqtt
import time
import threading
import glob
import re
import json
import os

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USER", "admin")
MQTT_PASS = os.environ.get("MQTT_PASS", "admin")

BAUD = 9600
SAMPLING_INTERVAL = 0.5  # seconds between each scale read

# Port-to-Scale mapping:
#   Each scale is on its own RS-232 serial port.
#   Configure these based on your actual USB-to-Serial wiring.
#   Format: { "scale_id": { "port": "/dev/ttyUSBx", "label": "..." } }
#
#   If SCALE_PORT_MAP is empty, auto-discovery mode is used (legacy).
SCALE_PORT_MAP = {
    "scale-01": {
        "port": os.environ.get("SCALE_01_PORT", "/dev/ttyUSB0"),
        "label": "Scale 1 (10 Kg ± 0.01)",
        "protocol": "protocol_A",    # Prefix 'A' format
    },
    "scale-02": {
        "port": os.environ.get("SCALE_02_PORT", "/dev/ttyUSB1"),
        "label": "Scale 2 (30 Kg ± 0.02)",
        "protocol": "protocol_GS",   # ST,GS format
    },
    "scale-03": {
        "port": os.environ.get("SCALE_03_PORT", "/dev/ttyUSB2"),
        "label": "Scale 3 (150 Kg ± 0.5)",
        "protocol": "protocol_A",    # Prefix 'A' or 'C' format
    },
}

# ═══════════════════════════════════════════════════════════════════
# SHARED STATE
# ═══════════════════════════════════════════════════════════════════
scale_heartbeats = {sid: 0.0 for sid in SCALE_PORT_MAP}
last_payloads = {sid: {"weight": 0.0, "unit": "kg", "stable": True} for sid in SCALE_PORT_MAP}
heartbeat_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
# PARSE FUNCTIONS (per protocol type)
# ═══════════════════════════════════════════════════════════════════

def parse_protocol_A(payload: str) -> dict | None:
    """
    Protocol A: Binary-coded weight format
    First char = header (A/B/C), then:
      [0] status char ('0'=stable)
      [1] sign char ('+'/'-')
      [2:8] numeric data (6 digits)
      [8]  decimal places
      [10:12] unit (optional)
    """
    # Strip any header char (A, B, C, etc.)
    data = payload
    for prefix in ('A', 'B', 'C'):
        if data.startswith(prefix):
            data = data[1:]
            break

    data = data.strip()
    if len(data) < 9:
        return None

    try:
        status_char = data[0]
        sign_char = data[1]
        data_str = data[2:8]
        decimal_char = data[8]

        raw_val = float(data_str)
        decimal_places = int(decimal_char)
        final_weight = raw_val / (10 ** decimal_places)
        if sign_char == '-':
            final_weight = -final_weight
        is_stable = (status_char == '0')

        unit_part = "kg"
        if len(data) >= 12:
            extracted = data[10:12].strip()
            if extracted:
                unit_part = extracted.lower()

        return {
            "weight": final_weight,
            "unit": unit_part,
            "stable": is_stable,
        }
    except Exception:
        return None


def parse_protocol_GS(payload: str) -> dict | None:
    """
    Protocol GS: "ST,GS   533.6,g" or "US,GS   12.345,kg"
    """
    try:
        match = re.search(r'(ST|US),GS\s*(-?[\d.]+)\s*,(g|kg)', payload)
        if match:
            status_part = match.group(1)
            val_str = match.group(2)
            unit_part = match.group(3)
            return {
                "weight": float(val_str),
                "unit": unit_part.lower(),
                "stable": (status_part == 'ST'),
            }
    except Exception:
        pass
    return None


PARSERS = {
    "protocol_A": parse_protocol_A,
    "protocol_GS": parse_protocol_GS,
}


def try_all_parsers(payload: str) -> dict | None:
    """Try all parsers — used when protocol is unknown."""
    for parser in PARSERS.values():
        result = parser(payload)
        if result:
            return result
    return None


# ═══════════════════════════════════════════════════════════════════
# SCALE READER THREAD (one per scale)
# ═══════════════════════════════════════════════════════════════════

def scale_reader_thread(scale_id: str, config: dict, mqtt_client):
    """
    Dedicated reader for a single scale on its own RS-232 port.
    Reads at SAMPLING_INTERVAL (0.5s) and publishes to MQTT.
    """
    port = config["port"]
    label = config.get("label", scale_id)
    protocol = config.get("protocol", None)
    topic = f"scale/{scale_id}"

    parser_fn = PARSERS.get(protocol, try_all_parsers) if protocol else try_all_parsers

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 20  # 20 × 0.5s = 10 seconds of silence

    print(f"[{scale_id}] 🔌 Starting reader: {port} ({label}) protocol={protocol}")

    while True:
        try:
            with serial.Serial(port, BAUD, timeout=1) as ser:
                print(f"[{scale_id}] ✅ Connected to {port}")
                consecutive_errors = 0

                while True:
                    try:
                        # Send ENQ to trigger scale response
                        ser.write(b'\x05')

                        # Read until ETX (0x03)
                        line = ser.read_until(b'\x03')

                        if line:
                            # Clean bytes: remove STX (0x02) and ETX (0x03)
                            clean_bytes = line
                            if line.startswith(b'\x02') and line.endswith(b'\x03'):
                                clean_bytes = line[1:-1]
                            elif line.endswith(b'\x03'):
                                clean_bytes = line[:-1]

                            payload_str = "".join(
                                c for c in clean_bytes.decode('ascii', errors='replace')
                                if c.isprintable() or c == '.'
                            )

                            if payload_str:
                                result = parser_fn(payload_str)
                                if result:
                                    consecutive_errors = 0
                                    json_payload = json.dumps({
                                        "weight": result["weight"],
                                        "scale_id": scale_id,
                                        "unit": result["unit"],
                                        "stable": result["stable"],
                                    })
                                    mqtt_client.publish(topic, json_payload)

                                    with heartbeat_lock:
                                        last_payloads[scale_id] = result
                                        scale_heartbeats[scale_id] = time.time()

                                    print(f"[{scale_id}] {result['weight']} {result['unit']} (Stable: {result['stable']})")
                                else:
                                    consecutive_errors += 1
                                    if len(payload_str) > 3:
                                        print(f"[{scale_id}] ⚠ Unknown format: {payload_str[:30]}")
                        else:
                            # No data received (timeout)
                            consecutive_errors += 1

                        # If too many consecutive errors, publish error
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            with heartbeat_lock:
                                last = last_payloads.get(scale_id, {"weight": 0.0, "unit": "kg"})
                            err = json.dumps({
                                "weight": last["weight"],
                                "scale_id": scale_id,
                                "unit": last["unit"],
                                "error_msg": "error!!!",
                                "detail": "No valid data for extended period",
                            })
                            mqtt_client.publish(topic, err)
                            consecutive_errors = 0  # Reset so we don't spam

                    except serial.SerialTimeoutException:
                        pass

                    # ── Sampling interval ──
                    time.sleep(SAMPLING_INTERVAL)

        except Exception as e:
            print(f"[{scale_id}] ❌ Connection lost on {port}: {e}. Retrying in 3s...")
            # Publish error while disconnected
            with heartbeat_lock:
                last = last_payloads.get(scale_id, {"weight": 0.0, "unit": "kg"})
            err = json.dumps({
                "weight": last["weight"],
                "scale_id": scale_id,
                "unit": last["unit"],
                "error_msg": "error!!!",
                "detail": f"Connection lost: {e}",
            })
            try:
                mqtt_client.publish(f"scale/{scale_id}", err)
            except Exception:
                pass
            time.sleep(3)


# ═══════════════════════════════════════════════════════════════════
# WATCHDOG MONITOR
# ═══════════════════════════════════════════════════════════════════

def scale_monitor(mqtt_client):
    """Monitors all scales — publishes error if no data for > 5s."""
    print("[Monitor] 🐕 Starting Watchdog Monitor...")
    startup_grace = time.time() + 8.0

    while True:
        if time.time() < startup_grace:
            time.sleep(1)
            continue

        current_time = time.time()
        for scale_id in SCALE_PORT_MAP:
            with heartbeat_lock:
                last_seen = scale_heartbeats.get(scale_id, 0.0)

            if current_time - last_seen > 5.0:
                with heartbeat_lock:
                    last = last_payloads.get(scale_id, {"weight": 0.0, "unit": "kg"})
                err = json.dumps({
                    "weight": last["weight"],
                    "scale_id": scale_id,
                    "unit": last["unit"],
                    "error_msg": "error!!!",
                    "detail": "Watchdog: No heartbeat > 5s",
                })
                try:
                    mqtt_client.publish(f"scale/{scale_id}", err)
                except Exception:
                    pass

        time.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════
# LEGACY AUTO-DISCOVERY MODE (fallback)
# ═══════════════════════════════════════════════════════════════════

def legacy_port_reader(port, mqtt_client):
    """
    Legacy mode: auto-detect scale from payload prefix.
    Used only when SCALE_PORT_MAP is empty/overridden.
    """
    print(f"[Legacy] Starting listener for {port}")
    timeout_count = 0
    MAX_TIMEOUTS = 20
    last_scale_id = None
    last_topic = None

    while True:
        try:
            with serial.Serial(port, BAUD, timeout=1) as ser:
                while True:
                    try:
                        ser.write(b'\x05')
                        line = ser.read_until(b'\x03')
                        if line:
                            timeout_count = 0
                            clean_bytes = line[1:-1] if line.startswith(b'\x02') and line.endswith(b'\x03') else line
                            payload = "".join(c for c in clean_bytes.decode('ascii', errors='replace') if c.isprintable() or c == '.')

                            if payload:
                                scale_id = None
                                result = None
                                if payload.startswith('A'):
                                    scale_id = "scale-01"
                                    result = parse_protocol_A(payload)
                                elif "GS" in payload:
                                    scale_id = "scale-02"
                                    result = parse_protocol_GS(payload)
                                elif payload.startswith('C'):
                                    scale_id = "scale-03"
                                    result = parse_protocol_A(payload)

                                if scale_id and result:
                                    topic = f"scale/{scale_id}"
                                    last_topic = topic
                                    last_scale_id = scale_id
                                    mqtt_client.publish(topic, json.dumps({
                                        "weight": result["weight"],
                                        "scale_id": scale_id,
                                        "unit": result["unit"],
                                        "stable": result["stable"],
                                    }))
                                    with heartbeat_lock:
                                        last_payloads[scale_id] = result
                                        scale_heartbeats[scale_id] = time.time()
                                    print(f"[Legacy] {scale_id} on {port}: {result['weight']} {result['unit']}")
                        else:
                            timeout_count += 1
                            if timeout_count >= MAX_TIMEOUTS and last_topic and last_scale_id:
                                with heartbeat_lock:
                                    last = last_payloads.get(last_scale_id, {"weight": 0.0, "unit": "kg"})
                                mqtt_client.publish(last_topic, json.dumps({
                                    "weight": last["weight"],
                                    "scale_id": last_scale_id,
                                    "unit": last["unit"],
                                    "error_msg": "error!!!",
                                }))
                                timeout_count = 0
                        time.sleep(SAMPLING_INTERVAL)
                    except serial.SerialTimeoutException:
                        pass
        except Exception as e:
            print(f"[Legacy] Connection lost on {port}: {e}. Retrying in 5s...")
            time.sleep(5)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    # Connect MQTT
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    try:
        client.connect(BROKER, MQTT_PORT, 60)
        client.loop_start()
        print(f"[Scale-Reader] ✅ Connected to MQTT Broker ({BROKER}:{MQTT_PORT})")
    except Exception as e:
        print(f"[Scale-Reader] ❌ Failed to connect to MQTT: {e}")
        return

    # Start watchdog monitor
    threading.Thread(target=scale_monitor, args=(client,), daemon=True).start()

    # ── Check if explicit port map is usable ──
    use_explicit = True
    for sid, cfg in SCALE_PORT_MAP.items():
        port = cfg["port"]
        if not os.path.exists(port):
            print(f"[Scale-Reader] ⚠ Port {port} for {sid} not found — falling back to auto-discovery")
            use_explicit = False
            break

    if use_explicit:
        # ── PARALLEL MODE: One thread per scale ──
        print(f"[Scale-Reader] 🚀 Starting PARALLEL mode — {len(SCALE_PORT_MAP)} dedicated scale threads")
        print(f"[Scale-Reader] 📊 Sampling interval: {SAMPLING_INTERVAL}s")
        for scale_id, config in SCALE_PORT_MAP.items():
            t = threading.Thread(
                target=scale_reader_thread,
                args=(scale_id, config, client),
                daemon=True,
                name=f"reader-{scale_id}",
            )
            t.start()
            print(f"[Scale-Reader]   ├─ {scale_id}: {config['port']} ({config.get('label', '')})")
    else:
        # ── LEGACY MODE: Auto-discover ports ──
        ports = sorted(glob.glob("/dev/ttyUSB*"))
        if not ports:
            print("[Scale-Reader] ❌ No serial ports discovered. (/dev/ttyUSB*)")
            time.sleep(5)
        else:
            print(f"[Scale-Reader] 📡 Legacy auto-discovery mode — {len(ports)} ports")
            for port in ports:
                t = threading.Thread(target=legacy_port_reader, args=(port, client), daemon=True)
                t.start()
                print(f"[Scale-Reader]   ├─ {port}")

    # Keep main thread alive
    print("[Scale-Reader] ═══════════════════════════════════════════")
    print("[Scale-Reader] All scale readers active. Ctrl+C to stop.")
    print("[Scale-Reader] ═══════════════════════════════════════════")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Scale-Reader] Shutting down...")
    finally:
        client.loop_stop()


if __name__ == "__main__":
    main()
