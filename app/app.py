import json
import customtkinter as ctk
import paho.mqtt.client as mqtt
from tkinter.colorchooser import askcolor

# --- Configuration ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "cebeci/emre/led_control"

# UI Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SmartLEDController(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pro RGB LED Controller")
        self.geometry("750x700")
        self.resizable(False, False)

        # MQTT Client Setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # State Variables
        self.animation_palette = []
        self.current_r = 0
        self.current_g = 0
        self.current_b = 0
        self.is_updating_ui = False # Flag to prevent infinite recursive UI updates

        self.setup_ui()
        self.connect_mqtt()

    def setup_ui(self):
        # --- Header ---
        self.title_label = ctk.CTkLabel(self, text="RGB LED Control Panel", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Connecting to MQTT...", text_color="orange", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=0)

        # --- Main Layout ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # ================= LEFT PANEL (Mode & Speed) =================
        self.left_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", width=250)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Mode Selection
        ctk.CTkLabel(self.left_frame, text="Animation Mode", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        self.mode_var = ctk.StringVar(value="0")
        modes = [("Solid", "0"), ("Breathe", "1"), ("Crossfade", "2"), ("Strobe", "3")]
        for text, val in modes:
            ctk.CTkRadioButton(self.left_frame, text=text, variable=self.mode_var, value=val).pack(anchor="w", pady=5)

        # Speed Slider
        ctk.CTkLabel(self.left_frame, text="Speed (ms delay)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(20, 5))
        self.speed_slider = ctk.CTkSlider(self.left_frame, from_=5, to=300, number_of_steps=295, command=self.update_speed_label)
        self.speed_slider.set(20)
        self.speed_slider.pack(fill="x", pady=5)
        self.speed_label = ctk.CTkLabel(self.left_frame, text="20 ms")
        self.speed_label.pack(anchor="w")

        # Master Brightness Slider
        ctk.CTkLabel(self.left_frame, text="Master Brightness (%)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(20, 5))
        self.brightness_slider = ctk.CTkSlider(self.left_frame, from_=0, to=100, number_of_steps=100, command=self.on_brightness_change)
        self.brightness_slider.set(100)
        self.brightness_slider.pack(fill="x", pady=5)
        self.brightness_label = ctk.CTkLabel(self.left_frame, text="100 %")
        self.brightness_label.pack(anchor="w")

        # ================= RIGHT PANEL (Color Engine) =================
        self.right_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.right_frame, text="Color Engine", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))

        # Live Color Preview Box
        self.color_preview = ctk.CTkFrame(self.right_frame, height=60, fg_color="#000000", corner_radius=8)
        self.color_preview.pack(fill="x", pady=5)

        # Top Controls: Hex & OS Color Palette
        self.hex_palette_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.hex_palette_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.hex_palette_frame, text="HEX:").pack(side="left", padx=(0, 5))
        self.hex_entry = ctk.CTkEntry(self.hex_palette_frame, width=100)
        self.hex_entry.pack(side="left")
        self.hex_entry.bind("<Return>", self.on_hex_enter)
        self.hex_entry.bind("<FocusOut>", self.on_hex_enter)

        ctk.CTkButton(self.hex_palette_frame, text="🎨 Open OS Palette", command=self.open_color_palette, width=120).pack(side="right")

        # RGB Sliders and Textboxes (Grid Layout)
        self.rgb_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.rgb_frame.pack(fill="x", pady=10)

        self.r_slider, self.r_entry = self.create_color_row(self.rgb_frame, "R", "red", 0)
        self.g_slider, self.g_entry = self.create_color_row(self.rgb_frame, "G", "green", 1)
        self.b_slider, self.b_entry = self.create_color_row(self.rgb_frame, "B", "blue", 2)

        # Animation Palette Buttons
        self.btn_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", pady=15)
        
        ctk.CTkButton(self.btn_frame, text="Add to Anim. List", command=self.add_to_palette).pack(side="left", padx=5)
        ctk.CTkButton(self.btn_frame, text="Clear List", fg_color="#8B0000", hover_color="#5C0000", command=self.clear_palette).pack(side="right", padx=5)

        # Animation Palette Display
        ctk.CTkLabel(self.right_frame, text="Animation Sequence List (Max 10):", font=ctk.CTkFont(size=12, slant="italic")).pack(anchor="w")
        self.palette_label = ctk.CTkLabel(self.right_frame, text="List is empty.", text_color="gray", justify="left")
        self.palette_label.pack(anchor="w", pady=5)

        # ================= SEND BUTTON =================
        self.send_button = ctk.CTkButton(self, text="PUBLISH TO ESP32", height=45, font=ctk.CTkFont(size=16, weight="bold"), fg_color="#006400", hover_color="#004d00", command=self.send_payload)
        self.send_button.pack(fill="x", padx=40, pady=(0, 20))

        # Initialize Default State
        self.sync_all_colors(0, 0, 0, source="init")

    def create_color_row(self, parent, label_text, color, row_index):
        ctk.CTkLabel(parent, text=label_text, width=20).grid(row=row_index, column=0, padx=5, pady=5)
        
        slider = ctk.CTkSlider(parent, from_=0, to=255, number_of_steps=255, progress_color=color, command=lambda v: self.on_slider_change())
        slider.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        
        entry = ctk.CTkEntry(parent, width=50)
        entry.grid(row=row_index, column=2, padx=5, pady=5)
        entry.bind("<Return>", lambda e: self.on_entry_enter())
        entry.bind("<FocusOut>", lambda e: self.on_entry_enter())
        
        parent.columnconfigure(1, weight=1) # Make slider expand
        return slider, entry

    # --- Sync & Update Logic ---
    def sync_all_colors(self, r, g, b, source):
        if self.is_updating_ui: return
        self.is_updating_ui = True

        # Ensure bounds
        r, g, b = max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))
        self.current_r, self.current_g, self.current_b = r, g, b

        # Update Sliders
        if source != "slider":
            self.r_slider.set(r); self.g_slider.set(g); self.b_slider.set(b)

        # Update Textboxes
        if source != "entry":
            self.r_entry.delete(0, 'end'); self.r_entry.insert(0, str(r))
            self.g_entry.delete(0, 'end'); self.g_entry.insert(0, str(g))
            self.b_entry.delete(0, 'end'); self.b_entry.insert(0, str(b))

        # Update Hex Box
        if source != "hex":
            hex_val = f"#{r:02x}{g:02x}{b:02x}".upper()
            self.hex_entry.delete(0, 'end'); self.hex_entry.insert(0, hex_val)

        self.update_preview_box()
        self.is_updating_ui = False

    def update_preview_box(self):
        # Calculate final output color considering Master Brightness
        brightness = self.brightness_slider.get() / 100.0
        final_r = int(self.current_r * brightness)
        final_g = int(self.current_g * brightness)
        final_b = int(self.current_b * brightness)
        
        hex_color = f"#{final_r:02x}{final_g:02x}{final_b:02x}"
        self.color_preview.configure(fg_color=hex_color)

    # --- Event Handlers ---
    def on_slider_change(self):
        self.sync_all_colors(self.r_slider.get(), self.g_slider.get(), self.b_slider.get(), source="slider")

    def on_entry_enter(self):
        try:
            r = int(self.r_entry.get())
            g = int(self.g_entry.get())
            b = int(self.b_entry.get())
            self.sync_all_colors(r, g, b, source="entry")
        except ValueError:
            pass # Ignore invalid text input

    def on_hex_enter(self, event=None):
        hex_val = self.hex_entry.get().strip().lstrip('#')
        if len(hex_val) == 6:
            try:
                r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
                self.sync_all_colors(r, g, b, source="hex")
            except ValueError:
                pass

    def open_color_palette(self):
        # OS Native Color Chooser
        color_code = askcolor(title="Choose LED Color", color=f"#{self.current_r:02x}{self.current_g:02x}{self.current_b:02x}")
        if color_code[0] is not None:
            r, g, b = map(int, color_code[0])
            self.sync_all_colors(r, g, b, source="palette")

    def on_brightness_change(self, value):
        self.brightness_label.configure(text=f"{int(value)} %")
        self.update_preview_box()

    def update_speed_label(self, value):
        self.speed_label.configure(text=f"{int(value)} ms")

    # --- Animation Palette Management ---
    def add_to_palette(self):
        if len(self.animation_palette) >= 10:
            return 

        # Apply brightness to the saved palette color
        brightness = self.brightness_slider.get() / 100.0
        final_r = int(self.current_r * brightness)
        final_g = int(self.current_g * brightness)
        final_b = int(self.current_b * brightness)
        
        self.animation_palette.append([final_r, final_g, final_b])
        self.update_palette_ui()

    def clear_palette(self):
        self.animation_palette.clear()
        self.update_palette_ui()

    def update_palette_ui(self):
        if not self.animation_palette:
            self.palette_label.configure(text="List is empty.")
            return

        text = ""
        for i, color in enumerate(self.animation_palette):
            text += f"{i+1}. ➔ R: {color[0]:<4} G: {color[1]:<4} B: {color[2]:<4}\n"
        self.palette_label.configure(text=text)

    # --- MQTT Network ---
    def connect_mqtt(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start() 
        except Exception as e:
            self.status_label.configure(text=f"Connection Error: {e}", text_color="red")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.status_label.configure(text="🟢 MQTT Connected - Ready to transmit!", text_color="#00FF00")
        else:
            self.status_label.configure(text="🔴 MQTT Connection Refused!", text_color="red")

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.status_label.configure(text="🔴 MQTT Disconnected!", text_color="red")

    def send_payload(self):
        mode = int(self.mode_var.get())
        speed = int(self.speed_slider.get())
        
        # If animation list is empty, send the current scaled color
        colors_to_send = self.animation_palette
        if not colors_to_send:
            brightness = self.brightness_slider.get() / 100.0
            r = int(self.current_r * brightness)
            g = int(self.current_g * brightness)
            b = int(self.current_b * brightness)
            colors_to_send = [[r, g, b]]

        payload = {
            "mode": mode,
            "speed": speed,
            "colorCount": len(colors_to_send),
            "colors": colors_to_send
        }

        json_payload = json.dumps(payload)
        self.client.publish(MQTT_TOPIC, json_payload)
        print(f"Published Payload: {json_payload}")

if __name__ == "__main__":
    app = SmartLEDController()
    app.mainloop()