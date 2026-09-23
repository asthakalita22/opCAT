from fastapi import FastAPI, HTTPException

from backend.database import init_db, insert_telemetry
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
    return {"status": "received", "machine_id": t.machine_id, "timestamp": t.timestamp}


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
