import streamlit as st
from data.dummy import (get_latest_telemetry, get_operator, get_weather,
                        get_safety_statuses, get_safety_status)

tel = get_latest_telemetry()
op = get_operator()
weather = get_weather()
statuses = get_safety_statuses()
overall = get_safety_status()

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

# ---------- Page ----------
st.subheader("Safety status")

banner = (
    f'<div class="status-banner status-{overall}">'
    f'{ICON[overall]} {LABEL[overall]}'
    '</div>'
)
st.markdown(banner, unsafe_allow_html=True)

for title, status, detail in cards:
    card = (
        f'<div class="safety-card {status}">'
        f'<div><div class="t">{title}</div><div class="d">{detail}</div></div>'
        f'<div class="s {status}">{LABEL[status]}</div>'
        '</div>'
    )
    st.markdown(card, unsafe_allow_html=True)