"""
Hour 5-7 deliverable (Person A) --- Proximity zone classification.

Pure functions: given what's already in the telemetry contract
(distance_m, direction, machine_state) plus optional relative velocity,
decide which zone the nearest person is in (green/yellow/red) and how
risky that is right now (0-100). No state is kept here -- this is
re-evaluated fresh every tick, unlike the duration-based rules in
backend.rules.

Machine-state-aware geometry: the danger radius is not a plain circle.
A digging/swinging machine has a wider hazard arc where the arm/bucket
can reach in front and to the sides; a reversing machine has an
enlarged blind-spot radius behind it. Multipliers below are applied to
the base yellow/red radii from config/thresholds.yaml.
"""

from pathlib import Path

import yaml

_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml"
with open(_THRESHOLDS_PATH) as f:
    _CFG = yaml.safe_load(f)["proximity"]

BASE_YELLOW_M = _CFG["yellow_radius_m"]
BASE_RED_M = _CFG["red_radius_m"]

# {machine_state: {direction: multiplier}}. >1 = zone starts further out
# (more cautious) for a person on that side while the machine is in that
# state. Missing state/direction combos default to 1.0 (base radius).
_STATE_DIRECTION_MULTIPLIERS = {
    "digging":   {"front": 1.5, "left": 1.3, "right": 1.3, "rear": 1.0},
    "swinging":  {"front": 1.4, "left": 1.5, "right": 1.5, "rear": 1.0},
    "reversing": {"rear": 1.8, "front": 1.0, "left": 1.1, "right": 1.1},
    "traveling": {"front": 1.2, "rear": 1.2, "left": 1.0, "right": 1.0},
    "idle":      {"front": 1.0, "rear": 1.0, "left": 1.0, "right": 1.0},
}


def _effective_radii(direction: str, machine_state: str) -> tuple[float, float]:
    multipliers = _STATE_DIRECTION_MULTIPLIERS.get(machine_state, _STATE_DIRECTION_MULTIPLIERS["idle"])
    m = multipliers.get(direction, 1.0)
    return BASE_YELLOW_M * m, BASE_RED_M * m


def classify_zone(distance_m: float, direction: str, machine_state: str) -> str:
    """Returns 'green' | 'yellow' | 'red'."""
    yellow_r, red_r = _effective_radii(direction, machine_state)
    if distance_m <= red_r:
        return "red"
    if distance_m <= yellow_r:
        return "yellow"
    return "green"


def risk_score(distance_m: float, direction: str, machine_state: str,
               relative_velocity_mps: float | None = None) -> int:
    """0-100. The zone sets the base band; closing/opening speed nudges
    the score within that band (approaching = riskier, retreating = safer).
    """
    zone = classify_zone(distance_m, direction, machine_state)
    base = {"green": 10, "yellow": 50, "red": 85}[zone]

    adjustment = 0.0
    if relative_velocity_mps is not None:
        if relative_velocity_mps < 0:          # approaching
            adjustment = min(15.0, abs(relative_velocity_mps) * 5)
        elif relative_velocity_mps > 0:        # retreating
            adjustment = -min(10.0, relative_velocity_mps * 3)

    return int(max(0, min(100, base + adjustment)))


def evaluate(distance_m: float, direction: str, machine_state: str,
             relative_velocity_mps: float | None = None) -> dict:
    """Convenience wrapper: one call gives backend.rules and
    GET /proximity/current everything they need."""
    return {
        "zone": classify_zone(distance_m, direction, machine_state),
        "risk_score": risk_score(distance_m, direction, machine_state, relative_velocity_mps),
    }
