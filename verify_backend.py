"""
End-to-end verification for the Hour 0-7 backend (Person A).
Run this WHILE uvicorn is running on port 8000.

Usage:
    python verify_backend.py

Checks, in order:
    1. /health responds
    2. POST /telemetry is accepted and returns active_alerts
    3. Seatbelt rule: warning at ~3s, critical at ~10s of violation
    4. Overspeed + harsh-brake rules fire
    5. Idling rule fires after sustained low-hydraulic zero-speed
    6. Proximity: walking a worker in from the rear of a reversing
       machine goes green -> yellow -> red, with a matching alert
    7. Alerts auto-resolve once the underlying condition clears
    8. Critical alerts auto-opened an Incident
    9. /alerts/today and /proximity/current respond correctly

Prints PASS/FAIL for each check and a final summary. Exits non-zero if
anything failed, so you can also use this in CI / a pre-demo sanity run.
"""

import sys
from datetime import datetime, timezone, timedelta

import requests

BASE = "http://127.0.0.1:8000"
MACHINE_ID = "CAT-VERIFY-01"
OPERATOR_ID = "OP-VERIFY"

results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, status))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    return condition


def send(t, **overrides):
    payload = {
        "type": "telemetry", "timestamp": t.isoformat(),
        "machine_id": MACHINE_ID, "machine_model": "CAT 320 Excavator",
        "operator_id": OPERATOR_ID, "engine_on": True, "speed_kmh": 0,
        "seatbelt_fastened": True, "operator_seated": True,
        "hydraulic_load_pct": 40, "fuel_level_pct": 80, "operating_hours": 0.0,
        "machine_state": "idle",
        "gps": {"lat": 12.97, "lon": 79.13},
        "proximity": {"object": "person", "distance_m": 30, "direction": "front",
                      "relative_velocity_mps": 0.0, "worker_x_m": 0.0, "worker_y_m": 30.0},
    }
    payload.update(overrides)
    r = requests.post(f"{BASE}/telemetry", json=payload, timeout=5)
    r.raise_for_status()
    return r.json()


def active_categories(resp):
    return {a["category"]: a["severity"] for a in resp["active_alerts"]}


def main():
    start = datetime.now(timezone.utc)

    # 1. health
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        check("Backend is reachable (/health)", r.status_code == 200, r.text)
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot reach the backend at", BASE)
        print("       Is uvicorn running? Try: uvicorn backend.main:app --reload --port 8000")
        sys.exit(1)

    # 2. basic telemetry accepted
    resp = send(start)
    check("POST /telemetry accepted", "active_alerts" in resp, str(resp))

    # 3. seatbelt escalation
    for i in range(1, 12):
        t = start + timedelta(seconds=i)
        resp = send(t, speed_kmh=6, seatbelt_fastened=False, machine_state="digging")
        if i == 4:
            cats = active_categories(resp)
            check("Seatbelt -> warning by ~4s unbuckled+moving",
                  cats.get("seatbelt") == "warning", cats)
        if i == 11:
            cats = active_categories(resp)
            check("Seatbelt -> critical by ~11s unbuckled+moving",
                  cats.get("seatbelt") == "critical", cats)

    # clear seatbelt violation
    t = start + timedelta(seconds=12)
    resp = send(t, speed_kmh=6, seatbelt_fastened=True, machine_state="digging")
    cats = active_categories(resp)
    check("Seatbelt alert auto-resolves once buckled", "seatbelt" not in cats, cats)

    # 4. overspeed + harsh brake
    t = start + timedelta(seconds=20)
    resp = send(t, speed_kmh=15, machine_state="traveling")
    cats = active_categories(resp)
    check("Overspeed rule fires above site limit", cats.get("unsafe_behavior") == "warning", cats)

    t = start + timedelta(seconds=21)
    resp = send(t, speed_kmh=3, machine_state="traveling")
    cats = active_categories(resp)
    check("Harsh-brake rule fires on sudden speed drop", cats.get("unsafe_behavior") == "warning", cats)

    # 5. idling
    t0 = start + timedelta(seconds=30)
    for m in (0, 5, 10, 11):
        t = t0 + timedelta(minutes=m)
        resp = send(t, speed_kmh=0, hydraulic_load_pct=2, machine_state="idle")
    cats = active_categories(resp)
    check("Idling rule fires after sustained low load", cats.get("idling") == "info", cats)

    # 6. proximity walk-in (rear, reversing -> enlarged blind spot)
    t0 = start + timedelta(minutes=20)
    zones_seen = []
    for i, dist in enumerate([25, 20, 15, 10, 6, 2]):
        t = t0 + timedelta(seconds=i)
        resp = send(t, speed_kmh=0, machine_state="reversing",
                    proximity={"object": "person", "distance_m": dist, "direction": "rear",
                               "relative_velocity_mps": -1.2,
                               "worker_x_m": 0.0, "worker_y_m": -dist})
        cats = active_categories(resp)
        zones_seen.append(cats.get("proximity"))
    check("Proximity escalates warning->critical as worker approaches",
          "warning" in zones_seen and zones_seen[-1] == "critical", zones_seen)

    # 7. proximity auto-resolves on retreat
    t = t0 + timedelta(seconds=10)
    resp = send(t, speed_kmh=0, machine_state="idle",
                proximity={"object": "person", "distance_m": 30, "direction": "front",
                           "relative_velocity_mps": 2.0, "worker_x_m": 0.0, "worker_y_m": 30.0})
    cats = active_categories(resp)
    check("Proximity alert auto-resolves once worker retreats", "proximity" not in cats, cats)

    # 8. incidents were auto-logged for the critical alerts above
    incidents = requests.get(f"{BASE}/incidents", params={"machine_id": MACHINE_ID}, timeout=5).json()
    types_logged = {i["type"] for i in incidents}
    check("Incident auto-logged for critical seatbelt alert", "seatbelt" in types_logged, types_logged)
    check("Incident auto-logged for critical proximity alert", "proximity" in types_logged, types_logged)

    # 9. read endpoints respond in the right shape
    today = requests.get(f"{BASE}/alerts/today", params={"machine_id": MACHINE_ID}, timeout=5).json()
    check("/alerts/today returns a non-empty list", isinstance(today, list) and len(today) > 0, today)

    prox = requests.get(f"{BASE}/proximity/current", params={"machine_id": MACHINE_ID}, timeout=5).json()
    check("/proximity/current returns zone + risk_score",
          "zone" in prox and "risk_score" in prox, prox)

    # summary
    print()
    passed = sum(1 for _, s in results if s == "PASS")
    total = len(results)
    print(f"{passed}/{total} checks passed")
    if passed != total:
        print("Failing checks:", [n for n, s in results if s == "FAIL"])
        sys.exit(1)
    print("Everything is working as intended.")


if __name__ == "__main__":
    main()