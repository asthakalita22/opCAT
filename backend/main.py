from fastapi import FastAPI, HTTPException

from backend import alerts, proximity
from backend.database import get_incidents, init_db, insert_telemetry
from backend.schemas import Telemetry

app = FastAPI(title="CAT Smart Operator Assistant")

init_db()

# in-memory cache: latest telemetry per machine_id
# (fast reads for the Streamlit polling loop; SQLite still gets every row
# for history/analytics later)
latest_telemetry: dict[str, Telemetry] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telemetry")
def post_telemetry(t: Telemetry):
    latest_telemetry[t.machine_id] = t
    insert_telemetry(t)

    # Hour 3-5: run the safety rules engine on every reading. This raises,
    # escalates, or auto-resolves alerts (and opens incidents for anything
    # that reaches "critical") before we respond.
    active_alerts = alerts.process(t)

    return {
        "status": "received",
        "machine_id": t.machine_id,
        "timestamp": t.timestamp,
        "active_alerts": active_alerts,
    }


@app.get("/telemetry/latest")
def get_latest_telemetry(machine_id: str | None = None):
    if machine_id:
        if machine_id not in latest_telemetry:
            raise HTTPException(status_code=404, detail=f"No telemetry yet for {machine_id}")
        return latest_telemetry[machine_id]

    if not latest_telemetry:
        raise HTTPException(status_code=404, detail="No telemetry received yet")

    # no machine_id given -> return the single latest machine's reading
    # (fine for a 1-machine hackathon demo)
    last_machine = list(latest_telemetry.keys())[-1]
    return latest_telemetry[last_machine]


@app.get("/alerts/active")
def get_active_alerts(machine_id: str | None = None):
    """Alerts happening right now. Same shape as data.dummy.get_active_alerts()."""
    return alerts.get_active_alerts(machine_id)


@app.get("/alerts/today")
def get_todays_alerts(machine_id: str | None = None):
    """Every alert raised this run, oldest first. Same shape as data.dummy.get_alerts()."""
    return alerts.get_todays_alerts(machine_id)


@app.get("/incidents")
def get_incidents_endpoint(machine_id: str | None = None):
    """Full incident history, newest first (auto-logged by critical alerts)."""
    return get_incidents(machine_id)


@app.get("/proximity/current")
def get_proximity_current(machine_id: str | None = None):
    """Everything Person B's interactive proximity map needs to draw the
    worker marker, rings and risk color for the current reading."""
    if machine_id:
        t = latest_telemetry.get(machine_id)
    else:
        t = list(latest_telemetry.values())[-1] if latest_telemetry else None

    if t is None or t.proximity is None:
        raise HTTPException(status_code=404, detail="No proximity data yet")

    result = proximity.evaluate(
        t.proximity.distance_m, t.proximity.direction, t.machine_state,
        t.proximity.relative_velocity_mps,
    )
    return {
        "machine_id": t.machine_id,
        "machine_state": t.machine_state,
        "distance_m": t.proximity.distance_m,
        "direction": t.proximity.direction,
        "relative_velocity_mps": t.proximity.relative_velocity_mps,
        "worker_x_m": t.proximity.worker_x_m,
        "worker_y_m": t.proximity.worker_y_m,
        "zone": result["zone"],
        "risk_score": result["risk_score"],
    }
