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
        lat REAL, lon REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT, machine_id TEXT, operator_id TEXT,
        type TEXT, severity TEXT, message TEXT, timestamp TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT, machine_id TEXT, operator_id TEXT,
        type TEXT, severity TEXT, description TEXT, timestamp TEXT, resolved INTEGER
    )""")
    conn.commit()
    conn.close()

init_db()