"""
Hour 1-3 deliverable (Person A).

Simulates one CAT machine + operator and POSTs telemetry to the FastAPI
backend once per second, matching the frozen telemetry contract in
config/telemetry_contract.json.

Run this in its own terminal WHILE uvicorn is running:
    python -m simulator.simulator
"""

import time
import random
from datetime import datetime, timezone

import requests

from simulator import worker_motion

BACKEND_URL = "http://127.0.0.1:8000/telemetry"

MACHINE_ID = "CAT-EXC-01"
MACHINE_MODEL = "CAT 320 Excavator"
OPERATOR_ID = "OP-017"

# Base GPS point (site origin) - small jitter simulates the machine moving
# around a fixed worksite rather than travelling long distances.
BASE_LAT = 12.9700
BASE_LON = 79.1300

# Mutable simulator state. A future Streamlit "Simulator" control page
# (07_Simulator.py, per the repo structure) can import this module and
# write to `state` directly to drive live demo scenarios.
state = {
    "engine_on": True,
    "speed_kmh": 0.0,
    "seatbelt_fastened": True,
    "operator_seated": True,
    "hydraulic_load_pct": 20.0,
    "fuel_level_pct": 100.0,
    "operating_hours": 0.0,
    "machine_state": "idle",
}


def toggle_engine(on: bool):
    state["engine_on"] = on


def set_speed(kmh: float):
    state["speed_kmh"] = max(0.0, kmh)


def set_seatbelt(fastened: bool):
    state["seatbelt_fastened"] = fastened


def set_seated(seated: bool):
    state["operator_seated"] = seated


def set_hydraulic_load(pct: float):
    state["hydraulic_load_pct"] = min(100.0, max(0.0, pct))

VALID_STATES = ("idle", "traveling", "reversing", "swinging", "digging")


def set_machine_state(machine_state: str):
    """What the machine is doing right now. Drives the proximity zone shape."""
    if machine_state not in VALID_STATES:
        raise ValueError(f"machine_state must be one of {VALID_STATES}")
    state["machine_state"] = machine_state

def harsh_brake():
    """One-off event: sudden speed drop, used later for the harsh-braking rule."""
    state["speed_kmh"] = max(0.0, state["speed_kmh"] - 8.0)


def _tick_autonomous_values():
    """Advance the values that should drift on their own each second."""
    if state["engine_on"]:
        # gentle random walk on speed and hydraulic load so the dashboard
        # feels "alive" even with no manual control yet
        state["speed_kmh"] = max(0.0, state["speed_kmh"] + random.uniform(-1.5, 1.5))
        state["speed_kmh"] = min(state["speed_kmh"], 15.0)  # spec range: 0-15 km/h

        state["hydraulic_load_pct"] += random.uniform(-5, 5)
        state["hydraulic_load_pct"] = min(100.0, max(0.0, state["hydraulic_load_pct"]))

        # fuel burns down while engine is on
        state["fuel_level_pct"] = max(0.0, state["fuel_level_pct"] - 0.01)

        # operating hours accumulate (in hours; +1 second each tick)
        state["operating_hours"] += 1 / 3600
    else:
        state["speed_kmh"] = 0.0
        state["hydraulic_load_pct"] = 0.0
        state["machine_state"] = "idle"


def build_telemetry():
    _tick_autonomous_values()
    worker = worker_motion.step()

    gps_lat = BASE_LAT + random.uniform(-0.0005, 0.0005)
    gps_lon = BASE_LON + random.uniform(-0.0005, 0.0005)

    return {
        "type": "telemetry",
        "timestamp": datetime.now().astimezone().isoformat(),
        "machine_id": MACHINE_ID,
        "machine_model": MACHINE_MODEL,
        "operator_id": OPERATOR_ID,
        "engine_on": state["engine_on"],
        "speed_kmh": round(state["speed_kmh"], 2),
        "seatbelt_fastened": state["seatbelt_fastened"],
        "operator_seated": state["operator_seated"],
        "hydraulic_load_pct": round(state["hydraulic_load_pct"], 1),
        "fuel_level_pct": round(state["fuel_level_pct"], 2),
        "operating_hours": round(state["operating_hours"], 4),
        "machine_state": state["machine_state"],
        "gps": {"lat": gps_lat, "lon": gps_lon},
        "proximity": {
            "object": "person",
            "distance_m": round(worker["distance_m"], 2),
            "direction": worker["direction"],
        },
    }


def run():
    print(f"Simulator started for {MACHINE_ID}. Posting to {BACKEND_URL} every 1s.")
    print("Press Ctrl+C to stop.\n")
    while True:
        payload = build_telemetry()
        try:
            resp = requests.post(BACKEND_URL, json=payload, timeout=2)
            print(f"[{payload['timestamp']}] sent -> {resp.status_code}  "
                  f"speed={payload['speed_kmh']}  seatbelt={payload['seatbelt_fastened']}  "
                  f"proximity={payload['proximity']['distance_m']}m")
        except requests.exceptions.ConnectionError:
            print("Could not reach backend - is uvicorn running on port 8000?")
        time.sleep(1)


if __name__ == "__main__":
    run()
