from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import serial
import threading
import time
import glob

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Shared state
current_config = {
    'baud': 9600,
    'port': None,
    'clean_mode': True
}

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Barcode Scanner Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { max-width: 800px; width: 100%; }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 30px; }
        .card { background: #1e293b; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #334155; }
        .label { color: #94a3b8; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }
        .data { font-size: 2rem; font-weight: bold; word-break: break-all; min-height: 2.5rem; }
        .serial { color: #34d399; }
        .keyboard { color: #fbbf24; }
        .status { font-size: 0.875rem; margin-top: 10px; display: flex; align-items: center; }
        .dot { height: 8px; width: 8px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .online { background: #10b981; }
        .offline { background: #ef4444; }
        .hex { font-family: 'Courier New', Courier, monospace; color: #64748b; font-size: 1rem; margin-top: 15px; border-top: 1px solid #334155; padding-top: 10px; }
        .controls { margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
        select, button { background: #334155; color: white; border: 1px solid #475569; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
        button:hover { background: #475569; }
        .active-btn { background: #38bdf8; color: #0f172a; border-color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Scanner Live Dashboard</h1>
        
        <div class="card">
            <div class="label">USB-Serial Input (CDC-ACM)</div>
            <div id="serial-data" class="data serial">Waiting for scan...</div>
            <div id="serial-hex" class="hex">Raw Hex: N/A</div>
            
            <div class="controls">
                <select id="baud-rate" onchange="updateBaud()">
                    <option value="9600">9600 Baud</option>
                    <option value="19200">19200 Baud</option>
                    <option value="38400">38400 Baud</option>
                    <option value="57600">57600 Baud</option>
                    <option value="115200">115200 Baud</option>
                </select>
                <button id="clean-btn" class="active-btn" onclick="toggleClean()">Clean Mode: ON</button>
            </div>

            <div class="status" style="margin-top: 25px;">
                <span id="serial-dot" class="dot offline"></span>
                <span id="serial-status">Status: Disconnected</span>
            </div>
        </div>

        <div class="card">
            <div class="label">Keyboard Emulator (Wedge)</div>
            <div id="keyboard-data" class="data keyboard">Waiting for scan...</div>
            <p style="color: #64748b; font-size: 0.8rem; margin-top: 10px;">Ensure this browser tab is focused/clicked to capture keyboard input.</p>
        </div>
    </div>

    <script>
        const socket = io();
        let kbBuffer = "";
        let cleanMode = true;

        function updateBaud() {
            const baud = document.getElementById('baud-rate').value;
            socket.emit('set_baud', {baud: parseInt(baud)});
        }

        function toggleClean() {
            cleanMode = !cleanMode;
            socket.emit('toggle_clean', {enabled: cleanMode});
            const btn = document.getElementById('clean-btn');
            btn.innerText = "Clean Mode: " + (cleanMode ? "ON" : "OFF");
            btn.className = cleanMode ? "active-btn" : "";
        }

        socket.on('serial_scan', function(msg) {
            document.getElementById('serial-data').innerText = msg.payload;
            document.getElementById('serial-hex').innerText = "Raw Hex: " + msg.hex;
            document.getElementById('keyboard-data').innerText = "Waiting for scan...";
        });

        socket.on('serial_status', function(msg) {
            document.getElementById('serial-status').innerText = "Status: " + msg.text;
            document.getElementById('serial-dot').className = "dot " + (msg.online ? "online" : "offline");
        });

        window.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                if (kbBuffer) {
                    document.getElementById('keyboard-data').innerText = kbBuffer;
                    document.getElementById('serial-data').innerText = "Waiting for scan...";
                    kbBuffer = "";
                }
            } else if (e.key.length === 1) {
                kbBuffer += e.key;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('set_baud')
def handle_set_baud(data):
    global current_config
    current_config['baud'] = data['baud']
    print(f"Baud rate changed to: {data['baud']}")

@socketio.on('toggle_clean')
def handle_toggle_clean(data):
    global current_config
    current_config['clean_mode'] = data['enabled']
    print(f"Clean mode: {data['enabled']}")

def serial_thread_func():
    global current_config
    while True:
        ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
        if not ports:
            socketio.emit('serial_status', {'text': 'No ports found', 'online': False})
            time.sleep(2)
            continue

        port = ports[0]
        try:
            baud = current_config['baud']
            with serial.Serial(port, baud, timeout=1) as ser:
                socketio.emit('serial_status', {'text': f'Connected to {port} @ {baud}', 'online': True})
                while True:
                    if current_config['baud'] != baud:
                        break # Re-trigger connection with new baud

                    raw_data = ser.readline()
                    if raw_data:
                        hex_str = raw_data.hex(' ')
                        try:
                            payload = raw_data.decode('utf-8', errors='replace').strip()
                            
                            if current_config['clean_mode']:
                                # 1. Extract alphanumeric data that looks like a code
                                # If the data is "oUo<340dc3>sl:90>CE24H07.13.;6.,206582;99,14Nl,"
                                # We try to find the actual code.
                                # Let's strip the common "header" parts if they exist
                                if '>' in payload:
                                    parts = payload.split('>')
                                    payload = parts[-1] if parts[-1] else parts[-2]
                                
                                # 2. Filter for only common barcode characters (Alphanumeric and simple punctuation)
                                # This helps if the "real data" is buried in noise.
                                payload = "".join(c for c in payload if c.isalnum() or c in ".-_")
                                
                            socketio.emit('serial_scan', {'payload': payload, 'hex': hex_str})
                            print(f"[WEB] Serial Scan: {payload} | Raw: {hex_str}")
                        except Exception as e:
                            print(f"[WEB] Error: {e}")
                    time.sleep(0.01)
        except Exception as e:
            socketio.emit('serial_status', {'text': f'Error: {str(e)}', 'online': False})
            time.sleep(2)

if __name__ == '__main__':
    t = threading.Thread(target=serial_thread_func, daemon=True)
    t.start()
    socketio.run(app, host='0.0.0.0', port=5000)
