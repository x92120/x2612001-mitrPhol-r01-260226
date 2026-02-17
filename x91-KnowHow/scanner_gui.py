import tkinter as tk
from tkinter import ttk
import serial
import threading
import time
import glob

class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Scanner Interface Tester")
        self.root.geometry("600x400")
        self.root.configure(bg="#f0f0f0")

        # UI Styling
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 12), background="#f0f0f0")
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), background="#f0f0f0")

        # Main Container
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Keyboard Emulator Section
        ttk.Label(main_frame, text="Keyboard Emulator Input (Wedge)", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.kb_label = ttk.Label(main_frame, text="Waiting for scan...", font=("Helvetica", 18, "bold"), foreground="#555", wraplength=550)
        self.kb_label.pack(anchor=tk.W, pady=(10, 30))

        # Hidden entry to capture keyboard input
        self.kb_entry = ttk.Entry(main_frame, width=1)
        self.kb_entry.pack(pady=0, padx=0) 
        self.kb_entry.bind("<Return>", self.on_kb_scan)
        self.kb_entry.focus_set()

        # 2. USB-Serial Section
        ttk.Label(main_frame, text="USB-Serial Interface (CDC-ACM)", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.serial_label = ttk.Label(main_frame, text="Searching for scanner...", font=("Helvetica", 18, "bold"), foreground="#555", wraplength=550)
        self.serial_label.pack(anchor=tk.W, pady=(10, 5))
        
        ttk.Label(main_frame, text="Raw Hex Data:", font=("Helvetica", 10, "italic")).pack(anchor=tk.W)
        self.hex_label = ttk.Label(main_frame, text="N/A", foreground="#888", font=("Courier", 9))
        self.hex_label.pack(anchor=tk.W, pady=(0, 5))

        self.serial_status = ttk.Label(main_frame, text="Status: Disconnected", foreground="red")
        self.serial_status.pack(anchor=tk.W, pady=(0, 20))

        # 3. Footer / Instructions
        instructions = ttk.Label(main_frame, text="Note: Click inside this window to ensure keyboard focus.", font=("Helvetica", 9, "italic"))
        instructions.pack(side=tk.BOTTOM, pady=10)

        # Serial Thread Setup
        self.stop_thread = False
        self.serial_thread = threading.Thread(target=self.serial_listener, daemon=True)
        self.serial_thread.start()

        # Periodic Focus Keep-alive
        self.root.after(1000, self.keep_focus)

    def keep_focus(self):
        """Ensure the hidden entry keeps focus for keyboard wedge mode."""
        if self.root.focus_get() != self.kb_entry:
            # Only refocus if user isn't clicking elsewhere specifically
            pass 
        self.root.after(1000, self.keep_focus)

    def on_kb_scan(self, event):
        """Handle data from keyboard wedge."""
        data = self.kb_entry.get().strip()
        if data:
            # Reset the other interface labels
            self.serial_label.config(text="Waiting for scan...", foreground="#555")
            self.hex_label.config(text="N/A")
            
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            self.kb_label.config(text=f"[{ts.split()[1]}] {data}", foreground="green")
            print(f"[{ts}] [KEYBOARD] Scan: {data}")
        self.kb_entry.delete(0, tk.END)

    def serial_listener(self):
        """Listen for data on USB serial ports."""
        while not self.stop_thread:
            ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
            if not ports:
                self.update_serial_status("No serial ports found", "red")
                time.sleep(2)
                continue

            port = ports[0] # Take the first one for this demo
            self.update_serial_status(f"Connecting to {port}...", "blue")
            
            try:
                with serial.Serial(port, 9600, timeout=1) as ser:
                    self.update_serial_status(f"Connected to {port}", "green")
                    while not self.stop_thread:
                        raw_data = ser.readline()
                        if raw_data:
                            # Log raw for debugging
                            hex_str = raw_data.hex(' ')
                            
                            try:
                                # Try multiple decodings
                                payload = raw_data.decode('utf-8', errors='replace').strip()
                                
                                # Apply parsing logic from existing scanner_read.py if needed
                                clean_payload = "".join(c for c in payload if c.isprintable())
                                
                                self.root.after(0, lambda p=clean_payload, h=hex_str: self.update_scan_data(p, h))
                            except Exception as decode_err:
                                print(f"[SERIAL] Decode error: {decode_err}")
                        time.sleep(0.01)
            except Exception as e:
                self.update_serial_status(f"Error: {str(e)}", "red")
                time.sleep(2)

    def update_scan_data(self, payload, hex_str):
        # Reset the other interface labels
        self.kb_label.config(text="Waiting for scan...", foreground="#555")
        
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.serial_label.config(text=f"[{ts.split()[1]}] {payload}", foreground="green")
        self.hex_label.config(text=hex_str)
        print(f"[{ts}] [SERIAL] Scan: {payload} | Raw: {hex_str}")

    def update_serial_status(self, text, color):
        self.root.after(0, lambda: self.serial_status.config(text=f"Status: {text}", foreground=color))

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    
    # Ensure window is on top initially
    root.lift()
    root.attributes("-topmost", True)
    root.after_idle(root.attributes, "-topmost", False)
    
    root.mainloop()
