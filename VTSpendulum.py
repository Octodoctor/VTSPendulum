import pyvts
import time
import math
import asyncio
import tkinter as tk
from tkinter import scrolledtext, filedialog
from threading import Thread
import json
import os

# Plugin info for VTube Studio
plugin_info = {
    "plugin_name": "VTS Pendulum",
    "developer": "Octorizotto",
    "authentication_token_path": "./token.txt"
}

# Global variables
parameters = []
running = False

async def vts_loop():
    global parameters, running
    vts = pyvts.vts(plugin_info=plugin_info)
    await vts.connect()
    await vts.request_authenticate_token()
    await vts.request_authenticate()

    for param in parameters:
        await vts.request(vts.vts_request.requestCustomParameter(param["name"]))

    start_time = time.time()
    try:
        while running:
            elapsed_time = time.time() - start_time
            for param in parameters:
                frequency = float(param["slider"].get())
                oscillation = 0.5 + 0.5 * math.sin(2 * math.pi * frequency * elapsed_time)
                value = param["min_val"] + (param["max_val"] - param["min_val"]) * oscillation
                await vts.request(vts.vts_request.requestSetParameterValue(param["name"], value))

            await asyncio.sleep(1 / 60)

    except KeyboardInterrupt:
        print("Stopped by user")

    finally:
        await vts.close()

def update_parameters():
    global parameters
    parameters.clear()
    for frame in param_frames:
        name = frame["name_entry"].get()
        try:
            min_val = float(frame["min_entry"].get())
            max_val = float(frame["max_entry"].get())
        except ValueError:
            continue
        if name:
            parameters.append({
                "name": name,
                "frequency": float(frame["freq_slider"].get()),
                "min_val": min_val,
                "max_val": max_val,
                "slider": frame["freq_slider"]
            })

def save_settings():
    update_parameters()
    if not parameters:
        status_label.config(text="Error: No valid parameters to save")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Save Settings As"
    )
    if not file_path:
        return

    settings = []
    for param in parameters:
        settings.append({
            "name": param["name"],
            "min_val": param["min_val"],
            "max_val": param["max_val"],
            "frequency": param["frequency"]
        })
    with open(file_path, "w") as f:
        json.dump(settings, f)
    status_label.config(text=f"Saved to {os.path.basename(file_path)}")

def load_settings():
    global running
    if running:
        status_label.config(text="Error: Stop the plugin before loading new settings")
        return

    file_path = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="Load Settings"
    )
    if not file_path:
        return

    for frame in param_frames[:]:
        frame["frame"].destroy()
    param_frames.clear()
    parameters.clear()

    with open(file_path, "r") as f:
        settings = json.load(f)
    for setting in settings:
        add_parameter(setting["name"], setting["min_val"], setting["max_val"], setting["frequency"])
    status_label.config(text=f"Loaded from {os.path.basename(file_path)}")

def start_vts():
    global running
    update_parameters()
    if not parameters:
        status_label.config(text="Error: No valid parameters defined")
        return

    running = True
    status_label.config(text="Running... (Stop or close window)")
    start_button.config(state="disabled")
    stop_button.config(state="normal")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    Thread(target=lambda: loop.run_until_complete(vts_loop()), daemon=True).start()

def stop_vts():
    global running
    running = False
    status_label.config(text="Stopped (Start to resume)")
    start_button.config(state="normal")
    stop_button.config(state="disabled")

def add_parameter(name="", min_val=0.0, max_val=1.0, frequency=1.0):
    frame = tk.Frame(param_container, borderwidth=1, relief="groove", pady=2)
    frame.pack(fill=tk.X, padx=5, pady=2)

    tk.Label(frame, text="Name:").pack(side=tk.LEFT, padx=2)
    name_entry = tk.Entry(frame, width=15)
    name_entry.insert(0, name)
    name_entry.pack(side=tk.LEFT, padx=2)

    tk.Label(frame, text="Min:").pack(side=tk.LEFT, padx=2)
    min_entry = tk.Entry(frame, width=5)
    min_entry.insert(0, str(min_val))
    min_entry.pack(side=tk.LEFT, padx=2)

    tk.Label(frame, text="Max:").pack(side=tk.LEFT, padx=2)
    max_entry = tk.Entry(frame, width=5)
    max_entry.insert(0, str(max_val))
    max_entry.pack(side=tk.LEFT, padx=2)

    tk.Label(frame, text="Freq:").pack(side=tk.LEFT, padx=2)
    freq_slider = tk.Scale(frame, from_=0.1, to=5.0, resolution=0.1, orient=tk.HORIZONTAL, length=120)
    freq_slider.set(frequency)
    freq_slider.pack(side=tk.LEFT, padx=2)

    remove_button = tk.Button(frame, text="X", command=lambda f=frame: remove_parameter(f), width=2)
    remove_button.pack(side=tk.LEFT, padx=2)

    param_frames.append({
        "frame": frame,
        "name_entry": name_entry,
        "min_entry": min_entry,
        "max_entry": max_entry,
        "freq_slider": freq_slider
    })
    update_parameters()

def remove_parameter(frame):
    frame.destroy()
    param_frames[:] = [f for f in param_frames if f["frame"] != frame]
    update_parameters()
    if not param_frames:
        add_parameter()

# Create the UI
root = tk.Tk()
root.title("VTS Pendulum")
root.geometry("600x450")  # Wider window to fit buttons
root.configure(bg="#f0f0f0")  # Light gray background

# Top frame for controls
control_frame = tk.Frame(root, bg="#f0f0f0")
control_frame.pack(fill=tk.X, padx=10, pady=5)

add_button = tk.Button(control_frame, text="Add Parameter", command=add_parameter, bg="#4CAF50", fg="white")
add_button.pack(side=tk.LEFT, padx=5)

save_button = tk.Button(control_frame, text="Save Settings", command=save_settings, bg="#2196F3", fg="white")
save_button.pack(side=tk.LEFT, padx=5)

load_button = tk.Button(control_frame, text="Load Settings", command=load_settings, bg="#FFC107", fg="black")
load_button.pack(side=tk.LEFT, padx=5)

start_button = tk.Button(control_frame, text="Start", command=start_vts, bg="#FF5722", fg="white")
start_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(control_frame, text="Stop", command=stop_vts, state="disabled", bg="#F44336", fg="white")
stop_button.pack(side=tk.LEFT, padx=5)

# Parameter list frame with scrollbar
param_frame = tk.Frame(root, bg="#f0f0f0")
param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

canvas = tk.Canvas(param_frame, bg="#ffffff")
scrollbar = tk.Scrollbar(param_frame, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

param_container = tk.Frame(canvas, bg="#ffffff")
canvas.create_window((0, 0), window=param_container, anchor="nw")
param_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

param_frames = []

# Status bar
status_frame = tk.Frame(root, bg="#f0f0f0")
status_frame.pack(fill=tk.X, padx=10, pady=5)
status_label = tk.Label(status_frame, text="", bg="#f0f0f0", anchor="w")
status_label.pack(fill=tk.X)

# Start with one default parameter
add_parameter()

def on_closing():
    global running
    running = False
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()