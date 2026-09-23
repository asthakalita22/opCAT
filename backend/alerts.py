"""
Hour 3-5 deliverable (Person A) --- Alert manager.

Turns backend.rules results into real Alert objects:
    - assigns alert_id / timestamp / machine_id / operator_id
    - keeps ONE active alert per (machine_id, category) so a seatbelt
      violation doesn't spam a new alert every second it stays unbuckled
    - auto-resolves an alert the instant its rule stops firing
    - escalates in place (e.g. seatbelt warning -> critical) instead of
      opening a second alert
    - writes every new/escalated alert to SQLite
    - automatically opens an Incident the moment an alert reaches
      "critical" (the "Incident is logged automatically" step of the
      SENSE -> UNDERSTAND -> ACT -> LEARN loop in the plan)

Person B's Streamlit pages currently read data.dummy.get_active_alerts()
/ get_alerts(). Once wired to the backend, they should instead poll:
    GET /alerts/active   -> alerts.get_active_alerts()
    GET /alerts/today     -> alerts.get_todays_alerts()
which return data in the exact same shape as data.dummy's fake versions.
"""

import uuid

from backend.database import insert_alert, insert_incident
from backend.schemas import Telemetry
from backend import rules

# Active alert per (machine_id, category). Removed the moment it resolves.
_active: dict[tuple[str, str], dict] = {}

# Every alert raised today, oldest first. In-memory history is enough for
# a single-shift hackathon demo; SQLite has the durable copy.
_alert_log: list[dict] = []


def process(t: Telemetry) -> list[dict]:
    """Call once per telemetry tick (from POST /telemetry).

    Runs the rules engine, updates the active-alert set (raising,
    escalating, or resolving alerts as needed), and returns the alerts
    that are active for this machine AFTER this tick.
    """
    results = rules.evaluate(t)
    firing_categories = {r["category"] for r in results}

    # Resolve alerts whose rule stopped firing this tick.
    for key in [k for k in _active if k[0] == t.machine_id and k[1] not in firing_categories]:
        _active[key]["active"] = False
        del _active[key]

    # Raise new alerts / escalate existing ones for rules firing now.
    for r in results:
        key = (t.machine_id, r["category"])
        existing = _active.get(key)

        if existing is None:
            alert = _build_alert(t, r)
            _active[key] = alert
            _alert_log.append(alert)
            insert_alert(alert)
            if alert["severity"] == "critical":
                _open_incident(t, alert)

        elif existing["severity"] != r["severity"]:
            existing["severity"] = r["severity"]
            existing["message"] = r["message"]
            existing["speak"] = r["speak"]
            existing["zone"] = r.get("zone")
            existing["risk_score"] = r.get("risk_score")
            insert_alert(existing)
            if existing["severity"] == "critical":
                _open_incident(t, existing)

    return get_active_alerts(t.machine_id)


def _build_alert(t: Telemetry, r: dict) -> dict:
    return {
        "type": "alert",
        "alert_id": f"A-{uuid.uuid4().hex[:8]}",
        "timestamp": t.timestamp.isoformat(),
        "category": r["category"],
        "severity": r["severity"],
        "message": r["message"],
        "speak": r["speak"],
        "machine_id": t.machine_id,
        "operator_id": t.operator_id,
        "active": True,
        # Only populated for category="proximity" (Hour 5-7); None
        # elsewhere. Lets Person B's map color/size the marker without
        # a second API call.
        "zone": r.get("zone"),
        "risk_score": r.get("risk_score"),
    }


def _open_incident(t: Telemetry, alert: dict) -> None:
    incident = {
        "incident_id": f"I-{uuid.uuid4().hex[:8]}",
        "machine_id": t.machine_id,
        "operator_id": t.operator_id,
        "type": alert["category"],
        "severity": alert["severity"],
        "description": alert["message"],
        "timestamp": t.timestamp.isoformat(),
        "resolved": False,
    }
    insert_incident(incident)


def get_active_alerts(machine_id: str | None = None) -> list[dict]:
    """Alerts that are still happening right now."""
    values = list(_active.values())
    if machine_id:
        values = [a for a in values if a["machine_id"] == machine_id]
    return sorted(values, key=lambda a: a["timestamp"])


def get_todays_alerts(machine_id: str | None = None) -> list[dict]:
    """Every alert raised this run (active or resolved), oldest first."""
    values = _alert_log
    if machine_id:
        values = [a for a in values if a["machine_id"] == machine_id]
    return sorted(values, key=lambda a: a["timestamp"])
