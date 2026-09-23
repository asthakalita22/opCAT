"""
Hour 5-7 deliverable (Person A) --- Proximity system, worker side.

Tracks one worker in machine-relative coordinates (meters). The machine
sits at the origin (0,0) facing "front" = +y. Distance and sector
("front"/"rear"/"left"/"right") and closing/opening velocity are all
DERIVED from x/y so there is a single source of truth.

Three drive modes:
    random   - default gentle wander, stays outside the danger zones
               (same organic feel as the Hour 1-3 version)
    scripted - deterministic canned approach path, for a repeatable
               demo beat ("worker walks in from behind")
    manual   - held wherever set_position()/set_distance() last put it
               -- this is what a judge dragging the worker icon on
               Person B's proximity map should call every frame

backend.proximity turns (distance, direction, machine_state) into a
zone + risk score; this module only owns where the worker physically is.
"""

import math
import random

DIRECTIONS = ("front", "rear", "left", "right")

# Rest of the simulator treats one step()/build_telemetry() call as one
# simulated second (see simulator.py's operating_hours/fuel updates), not
# measured wall-clock time -- so velocity here uses the same fixed-dt
# assumption rather than time.monotonic(). That keeps it correct no
# matter how fast/slow the caller actually invokes step() (e.g. a tight
# test loop, or a future non-1Hz control page), instead of only being
# correct when called exactly once per real second.
_TICK_SECONDS = 1.0

_ANGLE_UNIT = {"front": (0.0, 1.0), "rear": (0.0, -1.0), "left": (-1.0, 0.0), "right": (1.0, 0.0)}

state = {
    "x": 0.0,
    "y": 25.0,                     # start 25m out in front, clear of both zones
    "mode": "random",
    "distance_m": 25.0,
    "direction": "front",
    "relative_velocity_mps": 0.0,  # negative = approaching, positive = retreating
}

_last_distance = state["distance_m"]

# Where a "scripted" walk is currently headed. start_scripted_approach()
# arms it; step() moves state["x"]/["y"] toward it each tick.
_scripted_target = (0.0, 0.0)
_SCRIPTED_SPEED_MPS = 1.2   # roughly walking pace


def _sector(x: float, y: float) -> str:
    if abs(y) >= abs(x):
        return "front" if y >= 0 else "rear"
    return "right" if x >= 0 else "left"


def _recompute_derived():
    """Refresh distance/direction/relative_velocity from state['x'/'y'].
    Assumes one call == one simulated second (_TICK_SECONDS), matching
    the rest of the simulator's fixed-tick model."""
    global _last_distance
    x, y = state["x"], state["y"]
    distance = math.hypot(x, y)
    state["relative_velocity_mps"] = (distance - _last_distance) / _TICK_SECONDS
    state["distance_m"] = distance
    state["direction"] = _sector(x, y)
    _last_distance = distance


def set_mode(mode: str):
    if mode not in ("random", "scripted", "manual"):
        raise ValueError("mode must be one of random, scripted, manual")
    state["mode"] = mode


def set_position(x: float, y: float):
    """Manual override in machine-relative meters -- call this every time
    a judge drags the worker marker on the proximity map. Switches to
    'manual' mode so the random walk / scripted path don't fight the drag.
    """
    state["mode"] = "manual"
    state["x"], state["y"] = x, y
    _recompute_derived()
    return dict(state)


def set_distance(distance_m: float, direction: str = None):
    """Back-compat helper (same signature as the Hour 1-3 version): place
    the worker at a given distance in a given sector."""
    direction = direction if direction in DIRECTIONS else state["direction"]
    ux, uy = _ANGLE_UNIT[direction]
    return set_position(ux * distance_m, uy * distance_m)


def start_scripted_approach(from_direction: str = "rear", start_distance_m: float = 25.0):
    """Arms the canned demo path: worker starts `start_distance_m` out on
    `from_direction` and walks steadily in toward the machine each step()
    call until it reaches the center. Matches the judge demo beat in the
    plan: 'Judge drags worker toward machine -> SAFE -> CAUTION -> CRITICAL'
    but as a hands-off scripted fallback if dragging isn't wired up yet.
    """
    global _scripted_target
    if from_direction not in DIRECTIONS:
        raise ValueError(f"from_direction must be one of {DIRECTIONS}")
    ux, uy = _ANGLE_UNIT[from_direction]
    state["mode"] = "scripted"
    state["x"], state["y"] = ux * start_distance_m, uy * start_distance_m
    _scripted_target = (0.0, 0.0)
    _recompute_derived()


def step():
    """Advance the worker by one simulated second per the current mode,
    then return the fresh derived state (distance_m, direction,
    relative_velocity_mps, x, y)."""
    if state["mode"] == "random":
        state["x"] += random.uniform(-0.8, 0.8)
        state["y"] += random.uniform(-0.8, 0.8)
        # gentle pull back toward a safe standoff so an unattended demo
        # doesn't wander into the danger zone on its own
        distance = math.hypot(state["x"], state["y"])
        if distance < 15:
            state["x"] *= 1.05
            state["y"] *= 1.05

    elif state["mode"] == "scripted":
        tx, ty = _scripted_target
        dx, dy = tx - state["x"], ty - state["y"]
        remaining = math.hypot(dx, dy)
        if remaining > 0.5:
            step_len = min(_SCRIPTED_SPEED_MPS, remaining)
            state["x"] += dx / remaining * step_len
            state["y"] += dy / remaining * step_len
        # else: arrived -- hold position so the demo sits in the red zone

    # "manual" mode: do nothing here; position only changes via set_position()

    _recompute_derived()
    return dict(state)
