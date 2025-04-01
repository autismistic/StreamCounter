import tkinter as tk
from tkinter import ttk, colorchooser, font, filedialog, messagebox
from PIL import Image, ImageTk
import json
import os
import sys
from pynput import keyboard
import threading
import webbrowser

class StreamCounter:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Counter")
        self.root.geometry("800x700")  # Adjusted height for combined viewer

        # Determine the base path for saving settings
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Define settings_file before using it
        self.settings_file = os.path.join(self.base_path, "stream_counter_settings.json")

        # Promotional Text at the Top
        promo_frame = ttk.Frame(root)
        promo_frame.pack(side="top", fill="x", pady=5)
        promo_label = ttk.Label(promo_frame, text="Created by Autismistic", font=("Arial", 10))
        promo_label.pack()
        link_label = ttk.Label(promo_frame, text="http://autismistic.com", font=("Arial", 10), foreground="blue", cursor="hand2")
        link_label.pack()
        link_label.bind("<Button-1>", lambda e: webbrowser.open("http://autismistic.com"))

        # Main frame to hold both counters and the copy button
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=False)

        # Left Counter (Original "Deaths")
        self.left_counter_frame = ttk.LabelFrame(main_frame, text="Counter 1", padding="10")
        self.left_counter_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Copy Settings Button (in the middle, vertically centered)
        copy_frame = ttk.Frame(main_frame)
        copy_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        copy_button = ttk.Button(copy_frame, text="Copy Settings -->", command=self.copy_settings)
        copy_button.pack(expand=True)

        # Right Counter ("Deaths Today")
        self.right_counter_frame = ttk.LabelFrame(main_frame, text="Counter 2 (Deaths Today)", padding="10")
        self.right_counter_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Configure grid weights to make counters expand equally
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0, minsize=100)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Variables for Left Counter (Original)
        self.left_label_text = tk.StringVar(value="Deaths:")
        self.left_count = tk.IntVar(value=0)
        self.left_bg_color = tk.StringVar(value="#ffffff")
        self.left_font_color = tk.StringVar(value="#000000")
        self.left_font_size = tk.IntVar(value=12)
        self.left_font_family = tk.StringVar(value="Arial")
        self.left_bg_image = None
        self.left_bg_photo = None
        self.left_bg_image_path = tk.StringVar(value="")

        # Variables for Right Counter (Deaths Today)
        self.right_label_text = tk.StringVar(value="Deaths Today:")
        self.right_count = tk.IntVar(value=0)
        self.right_font_color = tk.StringVar(value="#000000")
        self.right_font_size = tk.IntVar(value=12)
        self.right_font_family = tk.StringVar(value="Arial")
        self.right_include_in_viewer = tk.BooleanVar(value=True)  # Checkbox variable

        # Variable for viewer label spacing
        self.viewer_spacing = tk.IntVar(value=10)  # Default spacing of 10 pixels

        # Hotkey variables (default values)
        self.hotkeys = {
            "left_increment": {"ctrl": True, "shift": True, "key": keyboard.Key.f1},
            "left_decrement": {"ctrl": True, "shift": True, "key": keyboard.Key.f2},
            "left_reset": {"ctrl": True, "shift": True, "key": keyboard.Key.f3},
            "right_increment": {"ctrl": True, "shift": True, "key": keyboard.Key.f4},
            "right_decrement": {"ctrl": True, "shift": True, "key": keyboard.Key.f5},
            "right_reset": {"ctrl": True, "shift": True, "key": keyboard.Key.f6},
        }
        self.hotkey_labels = {}  # To store labels displaying current hotkeys
        self.recording_hotkey = None  # To track which hotkey is being recorded

        # Load settings from file
        self.load_settings()

        # Setup Left Counter
        self.setup_counter(self.left_counter_frame, "left")
        # Setup Right Counter
        self.setup_counter(self.right_counter_frame, "right")

        # Combined Display Frame (at the bottom)
        self.display_frame = ttk.LabelFrame(root, text="Viewer", padding="10")
        self.display_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Spacing Control Frame
        spacing_frame = ttk.Frame(self.display_frame)
        spacing_frame.pack(fill="x", pady=2)
        ttk.Label(spacing_frame, text="Label Spacing:").pack(side="left")
        ttk.Spinbox(spacing_frame, from_=0, to=100, textvariable=self.viewer_spacing,
                    command=self.update_display).pack(side="left", padx=5)

        # Canvas for combined display
        self.display_canvas = tk.Canvas(self.display_frame, highlightthickness=0)
        self.display_canvas.pack(fill="both", expand=True)

        # Frame inside canvas to hold labels
        self.label_frame = tk.Frame(self.display_canvas, bg=self.left_bg_color.get())
        self.label_frame_id = self.display_canvas.create_window(0, 0, window=self.label_frame, anchor="center")

        # Labels for text (inside the frame)
        self.left_display_label = tk.Label(self.label_frame, 
                                          text=f"{self.left_label_text.get()} {self.left_count.get()}",
                                          font=(self.left_font_family.get(), self.left_font_size.get()),
                                          fg=self.left_font_color.get(),
                                          bg=self.left_bg_color.get())
        self.left_display_label.pack(pady=self.viewer_spacing.get())

        self.right_display_label = tk.Label(self.label_frame, 
                                           text=f"{self.right_label_text.get()} {self.right_count.get()}",
                                           font=(self.right_font_family.get(), self.right_font_size.get()),
                                           fg=self.right_font_color.get(),
                                           bg=self.left_bg_color.get())
        self.right_display_label.pack(pady=self.viewer_spacing.get())

        # Bind canvas resize to update the background image and center the label frame
        self.display_canvas.bind("<Configure>", lambda e: self.update_display())

        # Initial update
        self.update_display()

        # Start global hotkey listener
        self.start_hotkey_listener()

        # Bind closing event to save settings
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_counter(self, frame, side):
        # Variables specific to this counter
        label_text = self.left_label_text if side == "left" else self.right_label_text
        count = self.left_count if side == "left" else self.right_count
        font_color = self.left_font_color if side == "left" else self.right_font_color
        font_size = self.left_font_size if side == "left" else self.right_font_size
        font_family = self.left_font_family if side == "left" else self.right_font_family

        # Checkbox for Right Counter (only for side="right")
        if side == "right":
            checkbox_frame = ttk.Frame(frame)
            checkbox_frame.pack(fill="x", pady=2)
            ttk.Checkbutton(checkbox_frame, text="Include in Viewer?", 
                           variable=self.right_include_in_viewer, 
                           command=self.update_display).pack(side="left")

        # Top Frame - Input Boxes
        top_frame = ttk.Frame(frame, padding="10")
        top_frame.pack(fill="x")

        label_entry = ttk.Entry(top_frame, textvariable=label_text)
        label_entry.pack(side="left", padx=5)
        label_entry.bind("<KeyRelease>", lambda e: self.update_display())

        count_entry = ttk.Entry(top_frame, textvariable=count, width=10)
        count_entry.pack(side="left", padx=5)
        count_entry.bind("<Return>", lambda e: self.update_count_from_entry(side))

        # Button Frame
        button_frame = ttk.Frame(frame, padding="10")
        button_frame.pack(fill="x")

        # +1 Button and Hotkey Setter
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack(side="top", fill="x", pady=2)
        ttk.Button(btn_frame, text="+1", command=lambda: self.increment(side)).pack(side="left")
        set_hotkey_btn = ttk.Button(btn_frame, text="Set Hotkey", command=lambda: self.start_recording_hotkey(f"{side}_increment"))
        set_hotkey_btn.pack(side="left", padx=5)
        hotkey_label = ttk.Label(btn_frame, text=self.format_hotkey(f"{side}_increment"), font=("Arial", 8))
        hotkey_label.pack(side="left", padx=5)
        self.hotkey_labels[f"{side}_increment"] = hotkey_label

        # -1 Button and Hotkey Setter
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack(side="top", fill="x", pady=2)
        ttk.Button(btn_frame, text="-1", command=lambda: self.decrement(side)).pack(side="left")
        set_hotkey_btn = ttk.Button(btn_frame, text="Set Hotkey", command=lambda: self.start_recording_hotkey(f"{side}_decrement"))
        set_hotkey_btn.pack(side="left", padx=5)
        hotkey_label = ttk.Label(btn_frame, text=self.format_hotkey(f"{side}_decrement"), font=("Arial", 8))
        hotkey_label.pack(side="left", padx=5)
        self.hotkey_labels[f"{side}_decrement"] = hotkey_label

        # Reset Button and Hotkey Setter
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack(side="top", fill="x", pady=2)
        ttk.Button(btn_frame, text="0", command=lambda: self.reset(side)).pack(side="left")
        set_hotkey_btn = ttk.Button(btn_frame, text="Set Hotkey", command=lambda: self.start_recording_hotkey(f"{side}_reset"))
        set_hotkey_btn.pack(side="left", padx=5)
        hotkey_label = ttk.Label(btn_frame, text=self.format_hotkey(f"{side}_reset"), font=("Arial", 8))
        hotkey_label.pack(side="left", padx=5)
        self.hotkey_labels[f"{side}_reset"] = hotkey_label

        # Settings Frame
        settings_frame = ttk.LabelFrame(frame, text="Display Settings", padding="10")
        settings_frame.pack(fill="x", pady=5)

        # Background Options (only for Counter 1)
        if side == "left":
            # Background Color
            ttk.Button(settings_frame, text="Background Color", 
                      command=lambda: self.choose_bg_color()).pack(fill="x", pady=2)

            # Background Image
            ttk.Button(settings_frame, text="Background Image", 
                      command=lambda: self.choose_bg_image()).pack(fill="x", pady=2)

            # Remove Background Image
            remove_bg_button = ttk.Button(settings_frame, text="Remove Background", 
                                         command=lambda: self.remove_bg_image())
            remove_bg_button.pack(fill="x", pady=2)
            self.left_remove_bg_button = remove_bg_button
            self.update_remove_bg_button_state()

        # Font Color
        ttk.Button(settings_frame, text="Font Color", 
                  command=lambda: self.choose_font_color(side)).pack(fill="x", pady=2)

        # Font Selection
        font_frame = ttk.Frame(settings_frame)
        font_frame.pack(fill="x", pady=2)
        ttk.Label(font_frame, text="Font:").pack(side="left")
        font_combo = ttk.Combobox(font_frame, textvariable=font_family)
        fonts = sorted(list(font.families()))
        font_combo['values'] = fonts
        font_combo.pack(side="left", fill="x", expand=True)
        font_combo.bind("<<ComboboxSelected>>", lambda e: self.update_display())

        # Font Size
        size_frame = ttk.Frame(settings_frame)
        size_frame.pack(fill="x", pady=2)
        ttk.Label(size_frame, text="Size:").pack(side="left")
        ttk.Spinbox(size_frame, from_=8, to=72, textvariable=font_size,
                   command=lambda: self.update_display()).pack(side="left")

    def start_hotkey_listener(self):
        self.current_keys = set()

        def on_press(key):
            try:
                self.current_keys.add(key)
                for action, hotkey in self.hotkeys.items():
                    required_ctrl = hotkey.get("ctrl", False)
                    required_shift = hotkey.get("shift", False)
                    required_alt = hotkey.get("alt", False)
                    required_key = hotkey["key"]

                    ctrl_pressed = any(k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r] for k in self.current_keys)
                    shift_pressed = any(k in [keyboard.Key.shift_l, keyboard.Key.shift_r] for k in self.current_keys)
                    alt_pressed = any(k in [keyboard.Key.alt_l, keyboard.Key.alt_r] for k in self.current_keys)
                    key_pressed = required_key in self.current_keys

                    if (ctrl_pressed == required_ctrl and
                        shift_pressed == required_shift and
                        alt_pressed == required_alt and
                        key_pressed):
                        side = "left" if "left" in action else "right"
                        if "increment" in action:
                            self.root.after(0, lambda: self.increment(side))
                        elif "decrement" in action:
                            self.root.after(0, lambda: self.decrement(side))
                        elif "reset" in action:
                            self.root.after(0, lambda: self.reset(side))
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key in self.current_keys:
                    self.current_keys.remove(key)
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener_thread = threading.Thread(target=listener.start, daemon=True)
        listener_thread.start()

    def start_recording_hotkey(self, action):
        if self.recording_hotkey:
            messagebox.showwarning("Warning", "Already recording a hotkey. Please finish or press Esc to cancel.")
            return

        self.recording_hotkey = action
        self.current_keys = set()
        self.hotkey_labels[action].configure(text="Press keys (Esc to cancel)...")

        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.hotkey_labels[action].configure(text=self.format_hotkey(action))
                    self.recording_hotkey = None
                    return False
                self.current_keys.add(key)
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key in self.current_keys:
                    self.current_keys.remove(key)
                if not self.current_keys and key != keyboard.Key.esc:
                    ctrl_pressed = any(k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r] for k in self.current_keys)
                    shift_pressed = any(k in [keyboard.Key.shift_l, keyboard.Key.shift_r] for k in self.current_keys)
                    alt_pressed = any(k in [keyboard.Key.alt_l, keyboard.Key.alt_r] for k in self.current_keys)
                    main_key = key

                    if not hasattr(main_key, 'char') and main_key not in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                                                                         keyboard.Key.shift_l, keyboard.Key.shift_r,
                                                                         keyboard.Key.alt_l, keyboard.Key.alt_r]:
                        new_hotkey = {
                            "ctrl": ctrl_pressed,
                            "shift": shift_pressed,
                            "alt": alt_pressed,
                            "key": main_key
                        }
                        for other_action, other_hotkey in self.hotkeys.items():
                            if other_action != action and other_hotkey == new_hotkey:
                                messagebox.showwarning("Warning", "This hotkey is already in use by another action.")
                                self.hotkey_labels[action].configure(text=self.format_hotkey(action))
                                self.recording_hotkey = None
                                return False

                        self.hotkeys[action] = new_hotkey
                        self.hotkey_labels[action].configure(text=self.format_hotkey(action))
                        self.recording_hotkey = None
                        return False
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

    def format_hotkey(self, action):
        hotkey = self.hotkeys[action]
        modifiers = []
        if hotkey.get("ctrl", False):
            modifiers.append("Ctrl")
        if hotkey.get("shift", False):
            modifiers.append("Shift")
        if hotkey.get("alt", False):
            modifiers.append("Alt")
        key_name = str(hotkey["key"]).replace("Key.", "")
        if modifiers:
            return f"{' + '.join(modifiers)} + {key_name}"
        return key_name

    def update_display(self):
        # Update text for both counters
        self.left_display_label.configure(
            text=f"{self.left_label_text.get()} {self.left_count.get()}",
            font=(self.left_font_family.get(), self.left_font_size.get()),
            fg=self.left_font_color.get(),
            bg=self.left_bg_color.get()
        )

        self.right_display_label.configure(
            text=f"{self.right_label_text.get()} {self.right_count.get()}",
            font=(self.right_font_family.get(), self.right_font_size.get()),
            fg=self.right_font_color.get(),
            bg=self.left_bg_color.get()
        )

        # Repack labels with updated spacing
        self.left_display_label.pack_forget()
        self.right_display_label.pack_forget()
        self.left_display_label.pack(pady=self.viewer_spacing.get())
        if self.right_include_in_viewer.get():
            self.right_display_label.pack(pady=self.viewer_spacing.get())

        # Update canvas background
        self.display_canvas.configure(bg=self.left_bg_color.get())
        self.label_frame.configure(bg=self.left_bg_color.get())

        # Update background image if exists
        if self.left_bg_image:
            canvas_width = self.display_canvas.winfo_width()
            canvas_height = self.display_canvas.winfo_height()
            if canvas_width <= 0 or canvas_height <= 0:
                canvas_width, canvas_height = 200, 100
            image = self.left_bg_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            self.left_bg_photo = ImageTk.PhotoImage(image)
            if hasattr(self, 'bg_image_id'):
                self.display_canvas.delete(self.bg_image_id)
            self.bg_image_id = self.display_canvas.create_image(0, 0, image=self.left_bg_photo, anchor="nw")
            # Ensure the label frame is on top of the background image
            self.display_canvas.tag_raise(self.label_frame_id)

        # Center the label frame in the canvas
        canvas_width = self.display_canvas.winfo_width()
        canvas_height = self.display_canvas.winfo_height()
        self.display_canvas.coords(self.label_frame_id, canvas_width / 2, canvas_height / 2)

    def increment(self, side):
        count = self.left_count if side == "left" else self.right_count
        count.set(count.get() + 1)
        self.update_display()

    def decrement(self, side):
        count = self.left_count if side == "left" else self.right_count
        count.set(max(0, count.get() - 1))
        self.update_display()

    def reset(self, side):
        count = self.left_count if side == "left" else self.right_count
        count.set(0)
        self.update_display()

    def update_count_from_entry(self, side):
        count = self.left_count if side == "left" else self.right_count
        count_entry = self.left_counter_frame.winfo_children()[1].winfo_children()[1] if side == "left" else self.right_counter_frame.winfo_children()[1].winfo_children()[1]
        try:
            value = int(count_entry.get())
            count.set(max(0, value))
            self.update_display()
        except ValueError:
            count_entry.delete(0, tk.END)
            count_entry.insert(0, count.get())

    def choose_bg_color(self):
        color = colorchooser.askcolor(title="Choose Background Color")[1]
        if color:
            self.left_bg_color.set(color)
            self.left_bg_image = None
            self.left_bg_photo = None
            self.left_bg_image_path.set("")
            if hasattr(self, 'bg_image_id'):
                self.display_canvas.delete(self.bg_image_id)
                delattr(self, 'bg_image_id')
            self.update_display()
            self.update_remove_bg_button_state()

    def choose_bg_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.left_bg_image = Image.open(file_path)
            self.left_bg_image_path.set(file_path)
            self.update_display()
            self.update_remove_bg_button_state()

    def remove_bg_image(self):
        self.left_bg_image = None
        self.left_bg_photo = None
        self.left_bg_image_path.set("")
        if hasattr(self, 'bg_image_id'):
            self.display_canvas.delete(self.bg_image_id)
            delattr(self, 'bg_image_id')
        self.update_display()
        self.update_remove_bg_button_state()

    def update_remove_bg_button_state(self):
        if self.left_bg_image_path.get():
            self.left_remove_bg_button.configure(state="normal")
        else:
            self.left_remove_bg_button.configure(state="disabled")

    def choose_font_color(self, side):
        color = colorchooser.askcolor(title="Choose Font Color")[1]
        if color:
            if side == "left":
                self.left_font_color.set(color)
            else:
                self.right_font_color.set(color)
            self.update_display()

    def copy_settings(self):
        self.right_font_color.set(self.left_font_color.get())
        self.right_font_size.set(self.left_font_size.get())
        self.right_font_family.set(self.left_font_family.get())
        self.update_display()

    def save_settings(self):
        settings = {
            "left_label_text": self.left_label_text.get(),
            "left_count": self.left_count.get(),
            "left_bg_color": self.left_bg_color.get(),
            "left_font_color": self.left_font_color.get(),
            "left_font_size": self.left_font_size.get(),
            "left_font_family": self.left_font_family.get(),
            "left_bg_image_path": self.left_bg_image_path.get(),
            "right_label_text": self.right_label_text.get(),
            "right_count": self.right_count.get(),
            "right_font_color": self.right_font_color.get(),
            "right_font_size": self.right_font_size.get(),
            "right_font_family": self.right_font_family.get(),
            "right_include_in_viewer": self.right_include_in_viewer.get(),
            "viewer_spacing": self.viewer_spacing.get(),
            "hotkeys": {}
        }
        for action, hotkey in self.hotkeys.items():
            key_str = str(hotkey["key"])
            settings["hotkeys"][action] = {
                "ctrl": hotkey.get("ctrl", False),
                "shift": hotkey.get("shift", False),
                "alt": hotkey.get("alt", False),
                "key": key_str
            }
        with open(self.settings_file, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
                self.left_label_text.set(settings.get("left_label_text", "Deaths:"))
                self.left_count.set(settings.get("left_count", 0))
                self.left_bg_color.set(settings.get("left_bg_color", "#ffffff"))
                self.left_font_color.set(settings.get("left_font_color", "#000000"))
                self.left_font_size.set(settings.get("left_font_size", 12))
                self.left_font_family.set(settings.get("left_font_family", "Arial"))
                left_bg_image_path = settings.get("left_bg_image_path", "")
                self.left_bg_image_path.set(left_bg_image_path)
                if left_bg_image_path and os.path.exists(left_bg_image_path):
                    self.left_bg_image = Image.open(left_bg_image_path)

                self.right_label_text.set(settings.get("right_label_text", "Deaths Today:"))
                self.right_count.set(settings.get("right_count", 0))
                self.right_font_color.set(settings.get("right_font_color", "#000000"))
                self.right_font_size.set(settings.get("right_font_size", 12))
                self.right_font_family.set(settings.get("right_font_family", "Arial"))
                self.right_include_in_viewer.set(settings.get("right_include_in_viewer", True))
                self.viewer_spacing.set(settings.get("viewer_spacing", 10))

                if "hotkeys" in settings:
                    for action, hotkey in settings["hotkeys"].items():
                        key_str = hotkey["key"]
                        if "Key." in key_str:
                            key_str = key_str.replace("Key.", "")
                            key = getattr(keyboard.Key, key_str, None)
                        else:
                            key = key_str
                        self.hotkeys[action] = {
                            "ctrl": hotkey["ctrl"],
                            "shift": hotkey["shift"],
                            "alt": hotkey["alt"],
                            "key": key
                        }

    def on_closing(self):
        self.save_settings()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = StreamCounter(root)
    root.mainloop()

if __name__ == "__main__":
    main()