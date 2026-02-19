# Barcode Scanner Transmission Mode Analysis

I have investigated the barcode scanner connected to the system and determined its current mode of data transmission.

## Findings Summary

The barcode scanner is currently operating in **USB-Serial (CDC-ACM)** mode. 

While the hardware itself is a composite device (supporting both HID Keyboard and Serial), the system has been specifically configured to use the serial interface for data transmission.

### Technical Details

| Attribute | Value |
|-----------|-------|
| **Device ID** | `1d6f:0003` |
| **Active Driver** | `cdc_acm` |
| **Device Node** | `/dev/ttyACM0` (or similar) |
| **Configured Mode** | Serial (with HID disabled via UDEV) |

### Evidence

1. **Composite Device Identification**: `lsusb -t` shows the device at Bus 001, Port 002 (ID `1d6f:0003`) has multiple interfaces, including both `usbhid` and `cdc_acm`.
2. **Forced Serial Mode**: A custom UDEV rule [99-disable-scanner-hid.rules](file:///home/xmitrphol-ubuntu2404/xApp/x90-Doc/99-disable-scanner-hid.rules) is present, which explicitly disables the HID (Keyboard) interface for this device ID:
   ```bash
   SUBSYSTEM=="usb", ATTR{bInterfaceClass}=="03", ATTRS{idVendor}=="1d6f", ATTRS{idProduct}=="0003", ATTR{authorized}="0"
   ```
3. **Data Consumption**: The application script [scanner_read.py](file:///home/xmitrphol-ubuntu2404/xApp/x09-LocalMqtt/x01-EquipmentRead/scanner_read.py) is designed to listen for data on serial ports (`/dev/ttyACM*`), confirming that scanned barcodes are transmitted as serial data rather than keystrokes.

## Conclusion
The scanner is not acting as a "Keyboard Wedge" but is instead transmitting data via a **USB-Serial** connection to the local MQTT bridge.
