# 💡 Smart RGB LED Controller System

A complete hardware and software solution to control standard (non-addressable) **Common Anode RGB LED strips over the internet**. The system uses an **ESP32-S3 Super Mini** microcontroller for hardware control and a modern **Python desktop application** for user interaction, communicating seamlessly via the **MQTT protocol**.

---

## ✨ Features

- **Asynchronous Architecture** — The ESP32 firmware is entirely non-blocking. It uses `millis()` instead of `delay()`, ensuring the system is always responsive to incoming MQTT messages, even during complex, long-running LED animations.
- **Persistent Memory (EEPROM)** — The ESP32 saves the latest configuration (mode, speed, active colors) to non-volatile memory. Upon powering up, the device instantly resumes its last known state without waiting for a Wi-Fi or MQTT connection.
- **Advanced Animation Engine** — Supports multiple dynamic lighting modes: **Solid**, **Breathe**, **Crossfade**, and **Strobe**.
- **Sequence Builder** — The Python application allows users to build an animation sequence of up to **10 custom colors** for Crossfade and Strobe modes.
- **Professional Python GUI** — Built with `customtkinter`, featuring a dark-themed interface, live color preview, master brightness control, HEX color input, and integration with the native OS color picker.

---

## 🛒 Hardware Requirements

| Component | Quantity |
|---|---|
| ESP32-S3 Super Mini | 1x |
| 12V RGB LED Strip (Common Anode) | 1x |
| 12V DC Power Supply (e.g., 60W LED Transformer) | 1x |
| LM2596 Step-Down Buck Converter | 1x |
| 2N2222 NPN Transistors (TO-92) | 3x |
| Resistors (330Ω or 470Ω) | 3x |
| Breadboard and Jumper Wires | — |

---

## 🔌 Circuit Wiring Guide

### Power Management

1. Connect the **12V Power Supply** to the `IN+` and `IN-` of the LM2596.
2. > ⚠️ **CRITICAL:** Adjust the LM2596 potentiometer until the output voltage is **exactly 5.0V** before connecting the ESP32.
3. Connect the LM2596 `OUT+` (5V) to the **ESP32 5V pin**.
4. **Common Ground:** Connect the Power Supply GND, LM2596 `OUT-`, and ESP32 GND together.

### LED Strip Power

- Connect the **+12V wire** of the RGB LED strip directly to the 12V positive terminal of the power supply.

### Transistor Switching (Low-Side)

| Transistor Pin | Connection |
|---|---|
| **Emitter** | Common Ground (all 3 transistors) |
| **Base** | ESP32 GPIO via 330Ω resistor — GPIO 8 (Red), GPIO 10 (Green), GPIO 12 (Blue) |
| **Collector** | Respective R, G, B wires of the LED strip |

---

## ⚙️ Software Setup

### ESP32 Firmware

#### Prerequisites

- [Arduino IDE](https://www.arduino.cc/en/software) with ESP32 board definitions installed.
- Install the following libraries via the **Arduino Library Manager**:
  - `PubSubClient` by Nick O'Leary
  - `ArduinoJson` by Benoit Blanchon (Version 7.x)

#### Configuration

Before uploading, open the `.cpp` file and modify these variables:

```cpp
const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_topic = "yourname/room/led_control"; // Must match the Python script
```

Then upload the sketch to your **ESP32-S3 Super Mini**.

---

### Python Desktop Application

#### Prerequisites

- Python 3 installed on your computer.
- Install dependencies:

```bash
pip install customtkinter paho-mqtt
```

#### Configuration

Open `app.py` and verify the MQTT settings at the top of the file:

```python
MQTT_BROKER = "broker.hivemq.com"   # Default public broker
MQTT_TOPIC  = "yourname/room/led_control"  # Must match the ESP32 firmware
```

#### Run the Application

```bash
python app.py
```

---

## 🖥️ How to Use the Application

Once the Python application is running and shows a successful MQTT connection, you can control the LED strip using the following features:

### 1. Master Controls

| Control | Description |
|---|---|
| **Animation Mode** | Choose between Solid, Breathe, Crossfade, or Strobe |
| **Speed** | Delay in milliseconds between animation steps — lower = faster |
| **Master Brightness** | Scales brightness from 0–100% without altering RGB ratios |

### 2. Color Engine

Define colors using three synchronized methods:

- 🎚️ **RGB Sliders / Textboxes** — Drag sliders or type precise 0–255 values.
- 🔢 **HEX Input** — Paste a hex color code (e.g., `#FF5733`) and press Enter.
- 🎨 **OS Palette** — Click **"Open OS Palette"** to use your system's native color picker.

> The **Live Color Preview** box instantly displays the final color, accounting for the current Master Brightness setting.

### 3. Managing the Animation Sequence

| Mode | Behavior |
|---|---|
| **Solid / Breathe** | No sequence needed. Set a color and click **PUBLISH TO ESP32**. |
| **Crossfade / Strobe** | Requires multiple colors. Build a list using the steps below. |

**Building a Crossfade / Strobe sequence:**

1. Select a color using the Color Engine.
2. Click **"Add to Anim. List"**.
3. Repeat for additional colors (up to **10 colors**).
4. Click **PUBLISH TO ESP32** — the hardware will cycle through your sequence.
5. Click **"Clear List"** to start over.

---

## 📡 MQTT Communication

The system uses a public MQTT broker (`broker.hivemq.com`) by default. Both the ESP32 firmware and the Python app must be configured with the **exact same topic string** for communication to work.

> For production or private use, consider switching to a self-hosted broker such as [Mosquitto](https://mosquitto.org/).

---

## 📄 License

This project is open-source. Feel free to modify and distribute it for personal or educational use.
