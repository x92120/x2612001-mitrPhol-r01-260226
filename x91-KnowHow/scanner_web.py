from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import serial
import threading
import time
import glob

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- HTML Template (Embedded for simplicity) ---
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
        .instruction { text-align: center; color: #64748b; font-size: 0.875rem; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Scanner Live Dashboard</h1>
        
        <div class="card">
            <div class="label">USB-Serial Input (CDC-ACM)</div>
            <div id="serial-data" class="data serial">Waiting for scan...</div>
            <div id="serial-hex" class="hex">Raw Hex: N/A</div>
            <div class="status">
                <span id="serial-dot" class="dot offline"></span>
                <span id="serial-status">Status: Disconnected</span>
            </div>
        </div>

        <div class="card">
            <div class="label">Keyboard Emulator (Wedge)</div>
            <div id="keyboard-data" class="data keyboard">Waiting for scan...</div>
            <div class="instruction">Ensure this browser tab is focused to capture keyboard input.</div>
        </div>
    </div>

    <script>
        const socket = io();
        let kbBuffer = "";

        // Handle Serial Data from Server
        socket.on('serial_scan', function(msg) {
            document.getElementById('serial-data').innerText = msg.payload;
            document.getElementById('serial-hex').innerText = "Raw Hex: " + msg.hex;
            document.getElementById('keyboard-data').innerText = "Waiting for scan...";
        });

        socket.on('serial_status', function(msg) {
            document.getElementById('serial-status').innerText = "Status: " + msg.text;
            document.getElementById('serial-dot').className = "dot " + (msg.online ? "online" : "offline");
        });

        // Handle Keyboard Wedge (Client-side)
        window.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                if (kbBuffer) {
                    document.getElementById('keyboard-data').innerText = kbBuffer;
                    document.getElementById('serial-data').innerText = "Waiting for scan...";
                    document.getElementById('serial-hex').innerText = "Raw Hex: N/A";
                    console.log("Keyboard Scan:", kbBuffer);
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

def serial_thread_func():
    while True:
        ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
        if not ports:
            socketio.emit('serial_status', {'text': 'No ports found', 'online': False})
            time.sleep(2)
            continue

        port = ports[0]
        try:
            with serial.Serial(port, 9600, timeout=1) as ser:
                socketio.emit('serial_status', {'text': f'Connected to {port}', 'online': True})
                while True:
                    raw_data = ser.readline()
                    if raw_data:
                        hex_str = raw_data.hex(' ')
                        try:
                            payload = raw_data.decode('utf-8', errors='replace').strip()
                            clean_payload = "".join(c for c in payload if c.isprintable())
                            if clean_payload:
                                socketio.emit('serial_scan', {'payload': clean_payload, 'hex': hex_str})
                                print(f"[WEB] Serial Scan: {clean_payload}")
                        except Exception as e:
                            print(f"[WEB] Error: {e}")
                    time.sleep(0.01)
        except Exception as e:
            socketio.emit('serial_status', {'text': f'Error: {str(e)}', 'online': False})
            time.sleep(2)

if __name__ == '__main__':
    # Start serial listener in background
    t = threading.Thread(target=serial_thread_func, daemon=True)
    t.start()
    
    # Run Web Server
    print("Web Dashboard starting at http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
