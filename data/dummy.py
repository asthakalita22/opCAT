# Data layer for the app.
# Every function tries the FastAPI backend first. If the backend is down,
# it falls back to the dummy data below, so the app never shows an error.
import calendar
import random
from datetime import date

import requests

API_URL = "http://127.0.0.1:8000"

# Where the latest data came from: "live" (backend) or "demo" (dummy data)
DATA_SOURCE = {"telemetry": "demo", "alerts": "demo"}


def _from_backend(path, name, fallback):
    """Try the backend. If it's down or errors, use the dummy data instead."""
    try:
        r = requests.get(f"{API_URL}{path}", timeout=1)
        r.raise_for_status()
        DATA_SOURCE[name] = "live"
        return r.json()
    except Exception:
        DATA_SOURCE[name] = "demo"
        return fallback()


# Task types + planned minutes from the sample task table in the problem statement
TASK_TYPES = [
    ("Excavation", 60),
    ("Trenching", 45),
    ("Material Loading", 30),
    ("Grading", 35),
    ("Demolition", 90),
]


# ======================= Tasks (dummy for now) =======================

def get_today_tasks():
    return [
        {"task_id": "T002", "task_type": "Trenching", "zone": "Zone B",
         "weather": "Rainy", "estimated_min": 45, "ai_eta_min": None, "progress_pct": 0},
        {"task_id": "T003", "task_type": "Material Loading", "zone": "Zone A",
         "weather": "Cloudy", "estimated_min": 30, "ai_eta_min": None, "progress_pct": 0},
        {"task_id": "T004", "task_type": "Grading", "zone": "Zone C",
         "weather": "Sunny", "estimated_min": 35, "ai_eta_min": None, "progress_pct": 0},
    ]


def get_month_tasks(year, month):
    """Returns {date: [tasks]} for every day in the month."""
    rng = random.Random(f"{year}-{month}")      # same schedule every time you run
    days_in_month = calendar.monthrange(year, month)[1]
    schedule = {}
    for d in range(1, days_in_month + 1):
        day = date(year, month, d)
        if day == date.today():
            schedule[day] = get_today_tasks()   # keep today consistent with the big card
        elif day.weekday() == 6:
            schedule[day] = []                  # Sundays off
        else:
            picks = rng.sample(TASK_TYPES, rng.randint(1, 3))
            schedule[day] = [
                {"task_type": t, "zone": f"Zone {rng.choice('ABC')}", "estimated_min": m}
                for t, m in picks
            ]
    return schedule


# ======================= Telemetry (LIVE from backend) =======================

def get_latest_telemetry():
    return _from_backend("/telemetry/latest", "telemetry", _dummy_telemetry)


def _dummy_telemetry():
    # Exact shape of the agreed telemetry contract
    return {
        "type": "telemetry",
        "timestamp": "2026-09-23T09:14:02",
        "machine_id": "CAT-EXC-01",
        "machine_model": "CAT 320 Excavator",
        "operator_id": "OP-017",
        "machine_state": "digging",
        "engine_on": True,
        "speed_kmh": 0.0,
        "seatbelt_fastened": True,
        "operator_seated": True,
        "hydraulic_load_pct": 35,
        "fuel_level_pct": 72.4,
        "operating_hours": 3.27,
        "gps": {"lat": 12.97, "lon": 79.13},
        "proximity": {"object": "person", "distance_m": 14.0, "direction": "rear"},
    }


# ======================= Operator, weather, safety (dummy for now) =======================

def get_operator():
    return {"operator_id": "OP-017", "name": "Ravi", "operating_minutes": 196}


def get_weather():
    return {"condition": "Rain", "temp_c": 27}


# Which Safety card each alert category belongs to
CARD_FOR_CATEGORY = {
    "seatbelt": "seatbelt",
    "proximity": "proximity",
    "idling": "idle",
    "weather": "weather",
    "overwork": "overwork",
}
LEVEL = {"info": "safe", "warning": "warning", "critical": "critical"}
ORDER = ["safe", "warning", "critical"]


def get_safety_statuses():
    """Each Safety card's status = the worst ACTIVE alert in its category."""
    statuses = {card: "safe" for card in CARD_FOR_CATEGORY.values()}
    for a in get_active_alerts():
        card = CARD_FOR_CATEGORY.get(a["category"])
        if card:
            level = LEVEL[a["severity"]]
            if ORDER.index(level) > ORDER.index(statuses[card]):
                statuses[card] = level
    return statuses


def get_safety_status():
    """Overall status = the worst of all active alerts (including ones without a card)."""
    levels = ["safe"] + [LEVEL[a["severity"]] for a in get_active_alerts()]
    return max(levels, key=ORDER.index)


# ======================= Alerts (LIVE from backend) =======================

def get_alerts():
    return _from_backend("/alerts", "alerts", _dummy_alerts)


def get_active_alerts():
    return _from_backend("/alerts?active=true", "alerts",
                         lambda: [a for a in _dummy_alerts() if a["active"]])


def _dummy_alerts():
    """Today's alerts, in the agreed alert format (oldest first)."""
    today = date.today().isoformat()
    return [
        {"type": "alert", "alert_id": "A-0001", "timestamp": f"{today}T09:02:10",
         "category": "seatbelt", "severity": "warning",
         "message": "Seatbelt not fastened while machine is moving.",
         "speak": False, "machine_id": "CAT-EXC-01", "active": False},
        {"type": "alert", "alert_id": "A-0002", "timestamp": f"{today}T09:15:40",
         "category": "proximity", "severity": "critical",
         "message": "Person in danger zone behind the machine.",
         "speak": True, "machine_id": "CAT-EXC-01", "active": False},
        {"type": "alert", "alert_id": "A-0003", "timestamp": f"{today}T10:30:05",
         "category": "idling", "severity": "info",
         "message": "Engine idling for 12 minutes. Consider switching off.",
         "speak": False, "machine_id": "CAT-EXC-01", "active": False},
        {"type": "alert", "alert_id": "A-0004", "timestamp": f"{today}T11:45:00",
         "category": "weather", "severity": "warning",
         "message": "Rain: ground may be soft. Reduce speed near edges.",
         "speak": False, "machine_id": "CAT-EXC-01", "active": True},
    ]