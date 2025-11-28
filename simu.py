import time
import random
import json
import threading
import socket

import PySimpleGUI as sg

# ----------------- Config -----------------
UPDATE_INTERVAL = 100
SPEED_CHANGE_INTERVAL = 3.0
BACKGROUND_COLOR = "#FFD1DC"
FONT_COLOR = "black"

TCP_HOST = "127.0.0.1"
TCP_PORT = 5000

sg.set_options(font=("Arial", 12))

# Shared data for socket server (like working script)
latest_data = {
    "speed": 0.0,
    "distance": 0.0,
    "system_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "mode": "Day",
    "ignition": "OFF",
    "unit": "km/h"
}
data_lock = threading.Lock()


class Simulator:
    def __init__(self):
        self.ignition = False
        # Use same case as working script: "Day"/"Night"
        self.mode = "Day"
        self.current_speed = 0.0
        self.start_speed = 0.0
        self.target_speed = 0.0
        self.last_change = time.time()
        self.last_tick = time.time()
        self.trip_distance = 0.0
        self.trip_time = 0.0
        self.unit = "km/h"

    def toggle_ignition(self, value: bool):
        self.ignition = value
        now = time.time()
        if value:
            self.start_speed = self.current_speed
            self.target_speed = random.uniform(0, 999)
            self.last_change = now
        else:
            self.start_speed = self.current_speed
            self.target_speed = 0.0
            self.last_change = now

    def update(self):
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        elapsed = now - self.last_change
        if elapsed >= SPEED_CHANGE_INTERVAL:
            self.current_speed = self.target_speed
            if self.ignition:
                self.start_speed = self.current_speed
                self.target_speed = random.uniform(0, 999)
                self.last_change = now
        else:
            t = elapsed / SPEED_CHANGE_INTERVAL
            self.current_speed = self.start_speed + (self.target_speed - self.start_speed) * t

        if not self.ignition:
            self.current_speed = max(0.0, self.current_speed)

        if self.ignition:
            self.trip_time += dt
            self.trip_distance += self.current_speed * (dt / 3600.0)

        speed_display = self.current_speed if self.unit == "km/h" else self.current_speed * 0.621371

        h = int(self.trip_time // 3600)
        m = int((self.trip_time % 3600) // 60)
        s = int(self.trip_time % 60)

        return {
            "time": time.strftime("%H:%M:%S"),
            "speed": round(speed_display, 1),
            "distance": round(self.trip_distance, 3),
            "trip_time": f"{h:02d}:{m:02d}:{s:02d}",
        }


sim = Simulator()


def txt(content, w=16):
    return sg.Text(
        content,
        size=(w, 1),
        justification="center",
        background_color=BACKGROUND_COLOR,
        text_color=FONT_COLOR,
    )


table_layout = [
    [txt("Sl No", 6), txt("Signal ID", 16), txt("Value", 16)],
    [
        txt("1", 6),
        txt("Ignition", 16),
        sg.Checkbox(
            "ON",
            key="ignition",
            enable_events=True,
            background_color=BACKGROUND_COLOR,
            text_color=FONT_COLOR,
        ),
    ],
    [
        txt("2", 6),
        txt("Mode", 16),
        sg.Column(
            [
                [
                    sg.Radio(
                        "Day",
                        "mode",
                        key="day",
                        default=True,
                        enable_events=True,
                        background_color=BACKGROUND_COLOR,
                        text_color=FONT_COLOR,
                    ),
                    sg.Radio(
                        "Night",
                        "mode",
                        key="night",
                        enable_events=True,
                        background_color=BACKGROUND_COLOR,
                        text_color=FONT_COLOR,
                    ),
                ]
            ],
            background_color=BACKGROUND_COLOR,
        ),
    ],
    [
        txt("3", 6),
        txt("Unit", 16),
        sg.Column(
            [
                [
                    sg.Radio(
                        "km/h",
                        "unit",
                        key="kmh",
                        default=True,
                        enable_events=True,
                        background_color=BACKGROUND_COLOR,
                        text_color=FONT_COLOR,
                    ),
                    sg.Radio(
                        "mph",
                        "unit",
                        key="mph",
                        enable_events=True,
                        background_color=BACKGROUND_COLOR,
                        text_color=FONT_COLOR,
                    ),
                ]
            ],
            background_color=BACKGROUND_COLOR,
        ),
    ],
]

layout = [
    [
        sg.Text(
            "Signal Simulator",
            font=("Arial", 16, "bold"),
            background_color=BACKGROUND_COLOR,
            text_color=FONT_COLOR,
        )
    ],
    [sg.Frame("", table_layout, border_width=1, relief="solid", background_color=BACKGROUND_COLOR)],
    [sg.Text("Time: --:--:--", key="clock", background_color=BACKGROUND_COLOR, text_color=FONT_COLOR)],
    [sg.Text("Speed: 0.0 km/h", key="speed", background_color=BACKGROUND_COLOR, text_color=FONT_COLOR)],
    [
        sg.Text(
            "Trip Distance: 0.000 km",
            key="distance",
            background_color=BACKGROUND_COLOR,
            text_color=FONT_COLOR,
        )
    ],
    [
        sg.Text(
            "Trip Time: 00:00:00",
            key="trip_time",
            background_color=BACKGROUND_COLOR,
            text_color=FONT_COLOR,
        )
    ],
    [sg.Text("", background_color=BACKGROUND_COLOR)],
    [
        sg.Text("", expand_x=True, background_color=BACKGROUND_COLOR),
        sg.Button("Exit", button_color=("white", "#333333")),
    ],
]

window = sg.Window(
    "Simulator",
    layout,
    finalize=True,
    background_color=BACKGROUND_COLOR,
    resizable=False,
    size=(520, 380),
)


# ---------- TCP Server (same idea as working script) ----------
def start_socket_server():
    print(f"Starting TCP server on {TCP_HOST}:{TCP_PORT} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((TCP_HOST, TCP_PORT))
        except Exception as e:
            print(f"Failed to bind {TCP_HOST}:{TCP_PORT} -> {e}")
            return
        s.listen(1)
        print(f"Simulator TCP server listening on {TCP_HOST}:{TCP_PORT}")

        while True:
            try:
                conn, addr = s.accept()
                print("Client connected:", addr)
                with conn:
                    while True:
                        # Get latest data safely
                        with data_lock:
                            payload = json.dumps(latest_data) + "\n"
                        try:
                            conn.sendall(payload.encode())
                        except BrokenPipeError:
                            print("Client disconnected")
                            break
                        time.sleep(1)
            except Exception as e:
                print("Socket server error:", e)
                time.sleep(1)


# Start TCP server in background
threading.Thread(target=start_socket_server, daemon=True).start()


# ----------------- Main Event Loop -----------------
while True:
    event, values = window.read(timeout=UPDATE_INTERVAL)
    if event in (sg.WINDOW_CLOSED, "Exit"):
        break

    if event == "ignition":
        sim.toggle_ignition(values["ignition"])

    if event in ("day", "night"):
        # keep internal mode in "Day"/"Night" form
        sim.mode = "Day" if values["day"] else "Night"

    if event in ("kmh", "mph"):
        sim.unit = "km/h" if values["kmh"] else "mph"

    state = sim.update()

    # ---- Update GUI ----
    window["clock"].update(f"Time: {state['time']}")
    window["speed"].update(f"Speed: {state['speed']} {sim.unit}")
    window["distance"].update(f"Trip Distance: {state['distance']} km")
    window["trip_time"].update(f"Trip Time: {state['trip_time']}")

    # ---- Update shared JSON for service app ----
    with data_lock:
        # Use same field names as working script
        latest_data["speed"] = float(state["speed"])   # already in chosen unit; change to sim.current_speed if needed
        latest_data["distance"] = float(state["distance"])
        latest_data["system_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        latest_data["mode"] = sim.mode
        latest_data["ignition"] = "ON" if sim.ignition else "OFF"
        latest_data["unit"] = sim.unit

window.close()