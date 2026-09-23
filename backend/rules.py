"""
Hour 3-5 deliverable (Person A) --- Safety rules engine.

Evaluates one telemetry reading at a time against config/thresholds.yaml
and returns the list of rules currently being violated. This module is
STATELESS from the caller's point of view (call evaluate(t) once per
telemetry tick) but keeps its own per-machine timers internally, because
seatbelt / idle / overwork are duration rules, not instant ones.

backend.alerts turns these results into full Alert objects (ids,
active/resolved tracking, DB writes, auto-incidents) -- this file only
answers "is anything wrong right now, and why".

Rules implemented:
    seatbelt         moving + seated + unbuckled, sustained          (Hour 3-5)
    idling           engine on + zero speed + low hydraulic load     (Hour 3-5)
    unsafe_behavior  overspeed (instant) + harsh braking (instant)   (Hour 3-5)
    overwork         continuous operating time over threshold        (Hour 3-5)
    proximity        zone/risk from backend.proximity, using the     (Hour 5-7)
                     distance/direction already in the telemetry
                     contract plus machine_state -- no state kept
                     here, re-evaluated fresh every tick
"""

from pathlib import Path

import yaml

from backend import proximity
from backend.schemas import Telemetry

_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.yaml"

with open(_THRESHOLDS_PATH) as f:
    THRESHOLDS = yaml.safe_load(f)

# Per-machine timers, e.g.
#   {"CAT-EXC-01": {"seatbelt_violation_since": datetime|None, ...}}
# Reset to None the instant the underlying condition clears.
_state: dict[str, dict] = {}


def _machine_state(machine_id: str) -> dict:
    return _state.setdefault(machine_id, {
        "seatbelt_violation_since": None,
        "idle_since": None,
        "overwork_since": None,
        "last_speed_kmh": None,
    })


def evaluate(t: Telemetry) -> list[dict]:
    """Returns every rule currently violated by this telemetry reading.

    Each item: {"category": str, "severity": "info"|"warning"|"critical",
                "message": str, "speak": bool}

    A category missing from the returned list means that rule is NOT
    currently violated -- backend.alerts uses that to auto-resolve.
    """
    ms = _machine_state(t.machine_id)
    now = t.timestamp

    results: list[dict] = []
    results += _check_seatbelt(t, ms, now)
    results += _check_idle(t, ms, now)
    results += _check_overspeed(t)
    results += _check_harsh_brake(t, ms)
    results += _check_overwork(t, ms, now)
    results += _check_proximity(t)

    ms["last_speed_kmh"] = t.speed_kmh
    return results


def _check_seatbelt(t: Telemetry, ms: dict, now) -> list[dict]:
    """moving + seated + unbuckled"""
    violating = t.engine_on and t.speed_kmh > 0 and t.operator_seated and not t.seatbelt_fastened

    if not violating:
        ms["seatbelt_violation_since"] = None
        return []

    if ms["seatbelt_violation_since"] is None:
        ms["seatbelt_violation_since"] = now
    duration_s = (now - ms["seatbelt_violation_since"]).total_seconds()

    cfg = THRESHOLDS["seatbelt"]
    if duration_s >= cfg["critical_seconds"]:
        return [{
            "category": "seatbelt", "severity": "critical",
            "message": "Seatbelt not fastened while machine is moving. Stop and buckle up.",
            "speak": True,
        }]
    if duration_s >= cfg["warning_seconds"]:
        return [{
            "category": "seatbelt", "severity": "warning",
            "message": "Seatbelt not fastened while machine is moving.",
            "speak": False,
        }]
    return []


def _check_idle(t: Telemetry, ms: dict, now) -> list[dict]:
    """engine on + zero speed + low hydraulic load, sustained"""
    cfg = THRESHOLDS["idle"]
    violating = (
        t.engine_on
        and t.speed_kmh == 0
        and t.hydraulic_load_pct < cfg["hydraulic_load_pct"]
    )

    if not violating:
        ms["idle_since"] = None
        return []

    if ms["idle_since"] is None:
        ms["idle_since"] = now
    duration_min = (now - ms["idle_since"]).total_seconds() / 60

    if duration_min >= cfg["duration_minutes"]:
        return [{
            "category": "idling", "severity": "info",
            "message": f"Engine idling for {int(duration_min)} minutes. Consider switching off.",
            "speak": False,
        }]
    return []


def _check_overspeed(t: Telemetry) -> list[dict]:
    """speed > site limit"""
    limit = THRESHOLDS["unsafe"]["site_speed_limit_kmh"]
    if t.speed_kmh > limit:
        return [{
            "category": "unsafe_behavior", "severity": "warning",
            "message": f"Speed {t.speed_kmh:.1f} km/h exceeds site limit of {limit} km/h.",
            "speak": False,
        }]
    return []


def _check_harsh_brake(t: Telemetry, ms: dict) -> list[dict]:
    """rapid speed drop between two consecutive ticks"""
    last = ms["last_speed_kmh"]
    limit = THRESHOLDS["unsafe"]["harsh_braking_delta_kmh"]

    if last is not None and (last - t.speed_kmh) >= limit:
        return [{
            "category": "unsafe_behavior", "severity": "warning",
            "message": f"Harsh braking detected: speed dropped {last - t.speed_kmh:.1f} km/h in one second.",
            "speak": False,
        }]
    return []


def _check_overwork(t: Telemetry, ms: dict, now) -> list[dict]:
    """continuous operating duration > threshold"""
    if not t.engine_on:
        ms["overwork_since"] = None
        return []

    if ms["overwork_since"] is None:
        ms["overwork_since"] = now
    continuous_hours = (now - ms["overwork_since"]).total_seconds() / 3600

    # NOTE: thresholds.yaml also has a shorter `heat_continuous_hours`
    # limit for hot weather. Wire that up once the weather service lands
    # (Hour 15-17) -- using the standard threshold for every condition
    # until then, per the plan's "simplify weather" fallback.
    limit = THRESHOLDS["overwork"]["standard_continuous_hours"]
    if continuous_hours >= limit:
        return [{
            "category": "overwork", "severity": "warning",
            "message": f"Continuous operating time has passed {limit}h. Recommend a break.",
            "speak": False,
        }]
    return []


def _check_proximity(t: Telemetry) -> list[dict]:
    """Zone/risk classification for the nearest tracked person. Instant,
    not duration-based -- a red-zone reading is dangerous the moment it
    happens, no need to wait for it to persist."""
    prox = t.proximity
    if prox is None:
        return []

    result = proximity.evaluate(
        prox.distance_m, prox.direction, t.machine_state,
        prox.relative_velocity_mps,
    )
    zone = result["zone"]
    if zone == "green":
        return []

    severity = "critical" if zone == "red" else "warning"
    if zone == "red" and prox.direction == "rear":
        message = "Person behind you. Stop immediately."
    else:
        message = f"Person {prox.direction} of machine, {prox.distance_m:.1f} m away ({zone.upper()} zone)."

    return [{
        "category": "proximity", "severity": severity, "message": message,
        "speak": zone == "red",
        "zone": zone, "risk_score": result["risk_score"],
    }]
