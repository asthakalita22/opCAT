"""
Tracks a single worker's simulated distance from the machine.
Kept separate from simulator.py so the proximity logic (built out fully
in Hour 5-7) has its own home from the start.
"""

import random

# Starting state: worker safely far away
state = {
    "distance_m": 25.0,
    "direction": "rear",
}

DIRECTIONS = ["front", "rear", "left", "right"]


def step():
    """Advance the worker's position by one simulated second.
    Default behaviour: gentle random walk, worker mostly stays clear.
    Hour 5-7 will add drag-on-map control that overrides this directly
    by writing to `state`.
    """
    drift = random.uniform(-1.0, 1.0)
    state["distance_m"] = max(0.5, state["distance_m"] + drift)
    if random.random() < 0.05:  # occasionally change side
        state["direction"] = random.choice(DIRECTIONS)
    return dict(state)


def set_distance(distance_m: float, direction: str = None):
    """Manual override, e.g. from a future Streamlit control slider."""
    state["distance_m"] = distance_m
    if direction:
        state["direction"] = direction
    return dict(state)
