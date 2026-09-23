import sqlite3

DB_PATH = "cat_assistant.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT, operator_id TEXT, timestamp TEXT,
        engine_on INTEGER, speed_kmh REAL, seatbelt_fastened INTEGER,
        operator_seated INTEGER, hydraulic_load_pct REAL, fuel_level_pct REAL,
        operating_hours REAL, lat REAL, lon REAL,
        proximity_object TEXT, proximity_distance_m REAL, proximity_direction TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT, machine_id TEXT, operator_id TEXT,
        category TEXT, severity TEXT, message TEXT, speak INTEGER,
        timestamp TEXT, active INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT, machine_id TEXT, operator_id TEXT,
        type TEXT, severity TEXT, description TEXT, timestamp TEXT, resolved INTEGER
    )""")
    conn.commit()
    conn.close()


def insert_telemetry(t):
    """t is a backend.schemas.Telemetry instance."""
    conn = get_conn()
    c = conn.cursor()
    prox = t.proximity
    c.execute("""INSERT INTO telemetry (
        machine_id, operator_id, timestamp, engine_on, speed_kmh,
        seatbelt_fastened, operator_seated, hydraulic_load_pct, fuel_level_pct,
        operating_hours, lat, lon, proximity_object, proximity_distance_m, proximity_direction
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        t.machine_id, t.operator_id, t.timestamp.isoformat(), int(t.engine_on), t.speed_kmh,
        int(t.seatbelt_fastened), int(t.operator_seated), t.hydraulic_load_pct, t.fuel_level_pct,
        t.operating_hours, t.gps.lat, t.gps.lon,
        prox.object if prox else None, prox.distance_m if prox else None, prox.direction if prox else None
    ))
    conn.commit()
    conn.close()


def insert_alert(alert: dict):
    """alert is one of backend.alerts' plain dicts (see _build_alert)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO alerts (
        alert_id, machine_id, operator_id, category, severity, message,
        speak, timestamp, active
    ) VALUES (?,?,?,?,?,?,?,?,?)""", (
        alert["alert_id"], alert["machine_id"], alert["operator_id"],
        alert["category"], alert["severity"], alert["message"],
        int(alert["speak"]), alert["timestamp"], int(alert["active"]),
    ))
    conn.commit()
    conn.close()


def insert_incident(incident: dict):
    """incident is one of backend.alerts' plain dicts (see _open_incident)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO incidents (
        incident_id, machine_id, operator_id, type, severity, description,
        timestamp, resolved
    ) VALUES (?,?,?,?,?,?,?,?)""", (
        incident["incident_id"], incident["machine_id"], incident["operator_id"],
        incident["type"], incident["severity"], incident["description"],
        incident["timestamp"], int(incident["resolved"]),
    ))
    conn.commit()
    conn.close()


def get_incidents(machine_id: str | None = None) -> list[dict]:
    """Full incident history, newest first. Used by pages/05_Incidents.py
    and later by the Hour 9-11 training recommender."""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if machine_id:
        c.execute("SELECT * FROM incidents WHERE machine_id=? ORDER BY timestamp DESC", (machine_id,))
    else:
        c.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
