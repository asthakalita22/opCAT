import streamlit as st
from data.dummy import (get_latest_telemetry, get_operator, get_weather,
                        get_safety_statuses, get_safety_status,
                        get_alerts, get_active_alerts)

# ---------- Load data ----------
tel = get_latest_telemetry()
op = get_operator()
weather = get_weather()
statuses = get_safety_statuses()
overall = get_safety_status()
alerts_today = get_alerts()
active_alerts = get_active_alerts()

LABEL = {"safe": "SAFE", "warning": "CAUTION", "critical": "CRITICAL"}
ICON = {"safe": "🟢", "warning": "⚠️", "critical": "🔴"}

# ---------- Details, read from telemetry ----------
seatbelt_detail = "Fastened" if tel["seatbelt_fastened"] else "Not fastened"

prox = tel["proximity"]
if prox is None:
    proximity_detail = "No one nearby"
else:
    proximity_detail = f'Nearest {prox["object"]} {prox["distance_m"]:.0f} m, {prox["direction"]}'

if tel["engine_on"] and tel["machine_state"] == "idle":
    idle_detail = "Engine on, machine idle"
else:
    idle_detail = f'Machine working ({tel["machine_state"]})'

weather_detail = f'{weather["condition"]}, {weather["temp_c"]}°C'

hours, mins = divmod(op["operating_minutes"], 60)
hours_detail = f"{hours}h {mins:02d}m today"

cards = [
    ("Seatbelt", statuses["seatbelt"], seatbelt_detail),
    ("Proximity", statuses["proximity"], proximity_detail),
    ("Idling", statuses["idle"], idle_detail),
    ("Weather", statuses["weather"], weather_detail),
    ("Operating hours", statuses["overwork"], hours_detail),
]

# ---------- Alert counts ----------
counts = {
    "Active": len(active_alerts),
    "Critical": sum(a["severity"] == "critical" for a in alerts_today),
    "Warning": sum(a["severity"] == "warning" for a in alerts_today),
    "Info": sum(a["severity"] == "info" for a in alerts_today),
}

# ================= Page =================
st.subheader("Safety status")

# Overall banner
banner = (
    f'<div class="status-banner status-{overall}">'
    f'{ICON[overall]} {LABEL[overall]}'
    '</div>'
)
st.markdown(banner, unsafe_allow_html=True)

# Alert counter
counter = '<div class="counter-row">'
for name, n in counts.items():
    counter += f'<div class="counter {name.lower()}"><b>{n}</b><span>{name}</span></div>'
counter += '</div>'
st.markdown(counter, unsafe_allow_html=True)

# Safety cards
for title, status, detail in cards:
    card = (
        f'<div class="safety-card {status}">'
        f'<div><div class="t">{title}</div><div class="d">{detail}</div></div>'
        f'<div class="s {status}">{LABEL[status]}</div>'
        '</div>'
    )
    st.markdown(card, unsafe_allow_html=True)

st.page_link("pages/05_Incidents.py", label="View incident history", icon="📋")