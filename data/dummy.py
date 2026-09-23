# ALL fake data lives here. Later, swap these for calls to the FastAPI backend.
import calendar
import random
from datetime import date

# Task types + planned minutes from the sample task table in the problem statement
TASK_TYPES = [
    ("Excavation", 60),
    ("Trenching", 45),
    ("Material Loading", 30),
    ("Grading", 35),
    ("Demolition", 90),
]


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


def get_latest_telemetry():
    # Exact shape of the agreed telemetry contract
    return {
        "type": "telemetry",
        "timestamp": "2026-09-23T09:14:02",
        "machine_id": "CAT-320-01",
        "machine_model": "CAT 320",
        "operator_id": "OP-017",
        "machine_state": "digging",
        "engine_on": True,
        "speed_kmh": 0.0,
        "seatbelt_fastened": True,
        "operator_seated": True,
        "hydraulic_load_pct": 35,
        "fuel_level_pct": 72.4,
        "gps": {"lat": 12.97, "lon": 79.13},
        "proximity": {"object": "person", "distance_m": 14.0, "direction": "rear"},
    }


def get_operator():
    return {"operator_id": "OP-017", "name": "Ravi", "operating_minutes": 196}


def get_weather():
    return {"condition": "Rain", "temp_c": 27}


def get_safety_statuses():
    # One status per safety check: "safe" | "warning" | "critical"
    # Person A's rules engine decides these later.
    return {
        "seatbelt": "safe",
        "proximity": "safe",
        "idle": "safe",
        "weather": "warning",
        "overwork": "safe",
    }


def get_safety_status():
    """Overall status = the worst of the individual checks."""
    order = ["safe", "warning", "critical"]
    return max(get_safety_statuses().values(), key=order.index)