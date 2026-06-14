import tkinter as tk
import psutil
import math
import subprocess
import threading
import random
import struct
from pynvml import *

class KimiDesktopHeart:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kimi Pulse")
        
        # Geometry sizing for the heart canvas
        self.width = 160
        self.height = 160
        
        # Configure frameless window staying always on top
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{self.width}x{self.height}+200+200")
        
        # True alpha transparency handling for Linux compositors
        self.root.config(bg="#000001")
        try:
            self.root.wm_attributes("-transparentcolor", "#000001")
        except tk.TclError:
            pass

        # Setup drawing canvas
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg="#000001", highlightthickness=0)
        self.canvas.pack()

        # Mouse dragging bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_window)
        
        # Right-click to exit cleanly
        self.canvas.bind("<Button-3>", self.exit_application)
        
        # Initialize NVIDIA Management Library (NVML)
        self.nvml_active = False
        try:
            nvmlInit()
            self.gpu_handle = nvmlDeviceGetHandleByIndex(0)
            self.nvml_active = True
        except Exception:
            print("NVIDIA NVML could not be initialized. Falling back to CPU only.")

        # Initial core metrics
        self.bpm = 60
        self.scale_factor = 1.0
        self.current_color = "#66fcf1"
        self.sample_rate = 16000 
        
        # Kickoff routines
        self.update_metrics()
        self.pulse_engine()
        
        self.root.mainloop()

    def start_drag(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def drag_window(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f"+{x}+{y}")

    def exit_application(self, event):
        if self.nvml_active:
            try:
                nvmlShutdown()
            except Exception:
                pass
        self.root.destroy()

    def generate_thump_bytes(self, pitch, duration, volume):
        num_samples = int(self.sample_rate * duration)
        audio_bytes = bytearray()
        
        for i in range(num_samples):
            t = i / self.sample_rate
            decay = math.exp(-15 * t)
            sample = math.sin(2 * math.pi * pitch * t) * decay * volume
            sample_val = int(max(-32768, min(32767, sample * 32767)))
            audio_bytes.extend(struct.pack('<h', sample_val))
            
        return bytes(audio_bytes)

    def play_sound_worker(self, is_dub=False):
        try:
            base_pitch = 50 + (self.bpm * 0.08)
            if is_dub:
                pcm_data = self.generate_thump_bytes(base_pitch * 1.12, 0.09, 0.35)
            else:
                pcm_data = self.generate_thump_bytes(base_pitch, 0.14, 0.40)
            
            proc = subprocess.Popen(
                ['aplay', '-t', 'raw', '-f', 'S16_LE', '-r', str(self.sample_rate), '-c', '1', '-q'],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            proc.communicate(input=pcm_data)
        except Exception:
            pass

    def trigger_sound(self, is_dub=False):
        threading.Thread(target=self.play_sound_worker, args=(is_dub,), daemon=True).start()

    def get_dynamic_color(self, load_percent):
        factor = load_percent / 100.0
        cyan = (102, 252, 241)
        amber = (245, 166, 35)
        crimson = (224, 36, 74)

        if factor < 0.5:
            t = factor * 2
            r = int(cyan[0] + t * (amber[0] - cyan[0]))
            g = int(cyan[1] + t * (amber[1] - cyan[1]))
            b = int(cyan[2] + t * (amber[2] - cyan[2]))
        else:
            t = (factor - 0.5) * 2
            r = int(amber[0] + t * (crimson[0] - amber[0]))
            g = int(amber[1] + t * (crimson[1] - amber[1]))
            b = int(amber[2] + t * (crimson[2] - amber[2]))
        return f"#{r:02x}{g:02x}{b:02x}"

    def draw_heart(self, color, scale):
        self.canvas.delete("heart")
        cx, cy = self.width // 2, self.height // 2 - 5
        
        points = [
            cx, cy + int(45 * scale),
            cx - int(45 * scale), cy + int(5 * scale),
            cx - int(55 * scale), cy - int(25 * scale),
            cx - int(30 * scale), cy - int(50 * scale),
            cx, cy - int(25 * scale),
            cx + int(30 * scale), cy - int(50 * scale),
            cx + int(55 * scale), cy - int(25 * scale),
            cx + int(45 * scale), cy + int(5 * scale),
        ]
        self.canvas.create_polygon(points, fill=color, outline=color, smooth=True, tags="heart")

    def update_metrics(self):
        # Sample local CPU usage
        cpu_load = psutil.cpu_percent(interval=None)
        
        # Sample eGPU usage if NVML initialized successfully
        gpu_load = 0
        if self.nvml_active:
            try:
                rates = nvmlDeviceGetUtilizationRates(self.gpu_handle)
                gpu_load = rates.gpu
            except Exception:
                pass

        # Evaluate the highest dominant stress factor on the system link
        dominant_load = max(cpu_load, gpu_load)
        
        self.current_color = self.get_dynamic_color(dominant_load)
        self.bpm = int(60 + (dominant_load / 100.0) * 80)
        
        self.root.after(1000, self.update_metrics) # Poll slightly quicker for responsive GPU spikes

    def pulse_engine(self):
        ms_per_beat = int((60.0 / self.bpm) * 1000)
        
        # 1. Lub Expansion
        self.scale_factor = 1.18
        self.draw_heart(self.current_color, self.scale_factor)
        self.trigger_sound(is_dub=False)
        
        self.root.after(90, lambda: self.reset_scale(1.0))
        
        # 2. Dub Expansion Sequence
        self.root.after(140, self.trigger_dub)
        
        # 3. Calculate next cycle with HRV Gaussian variance
        hrv_variance = int(random.gauss(0, 12))
        next_cycle = max(300, ms_per_beat + hrv_variance)
        
        self.root.after(next_cycle, self.pulse_engine)

    def trigger_dub(self):
        self.scale_factor = 1.08
        self.draw_heart(self.current_color, self.scale_factor)
        self.trigger_sound(is_dub=True)
        self.root.after(60, lambda: self.reset_scale(1.0))

    def reset_scale(self, target):
        self.scale_factor = target
        self.draw_heart(self.current_color, self.scale_factor)

if __name__ == "__main__":
    KimiDesktopHeart()
