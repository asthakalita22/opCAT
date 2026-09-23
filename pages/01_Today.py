import calendar
from datetime import date

import streamlit as st
from data.dummy import (get_today_tasks, get_month_tasks, get_latest_telemetry,
                        get_operator, get_weather, get_safety_status)

# ---------------- Current machine ----------------
tel = get_latest_telemetry()
op = get_operator()

engine_class = "on" if tel["engine_on"] else "off"
engine_text = "Engine on" if tel["engine_on"] else "Engine off"

machine_bar = (
    '<div class="machine-bar">'
    '<div>'
    f'<div class="m-name">🚜 {tel["machine_model"]} · {tel["machine_id"]}</div>'
    f'<div class="m-sub">Operator: {op["name"]}</div>'
    '</div>'
    '<div class="m-right">'
    f'<div class="m-engine {engine_class}">● {engine_text}</div>'
    f'<div class="m-sub">{tel["machine_state"].capitalize()}</div>'
    '</div>'
    '</div>'
)
st.markdown(machine_bar, unsafe_allow_html=True)

# ---------------- Big task widget ----------------
tasks = get_today_tasks()
task = tasks[0]   # the next task

if task["ai_eta_min"] is None:
    ai_eta = "Not connected yet"
else:
    ai_eta = f'{task["ai_eta_min"]} min'

card = (
    '<div class="task-card">'
    '<div class="label">Your next task</div>'
    f'<div class="name">{task["task_type"]}</div>'
    f'<div class="zone">{task["zone"]} · {task["weather"]}</div>'
    '<div class="times">'
    f'<div><span>Planned</span><b>{task["estimated_min"]} min</b></div>'
    f'<div><span>AI estimate</span><b>{ai_eta}</b></div>'
    '</div>'
    '<div class="progress-track">'
    f'<div class="progress-fill" style="width:{task["progress_pct"]}%"></div>'
    '</div>'
    '</div>'
)
st.markdown(card, unsafe_allow_html=True)

st.button("Start task", type="primary", width="stretch")

# ---------------- Month calendar ----------------
today = date.today()
if "selected_day" not in st.session_state:
    st.session_state.selected_day = today


def pick_day(day):
    st.session_state.selected_day = day


with st.expander("📅 Month calendar"):
    schedule = get_month_tasks(today.year, today.month)
    st.markdown(f"**{today.strftime('%B %Y')}**")

    with st.container(key="calendar"):
        cols = st.columns(7)
        for col, name in zip(cols, ["M", "T", "W", "T", "F", "S", "S"]):
            col.markdown(f'<div class="cal-head">{name}</div>', unsafe_allow_html=True)

        for week in calendar.monthcalendar(today.year, today.month):
            cols = st.columns(7)
            for col, d in zip(cols, week):
                if d == 0:
                    continue          # empty box before day 1 / after the last day
                day = date(today.year, today.month, d)
                is_selected = day == st.session_state.selected_day
                col.button(
                    str(d),
                    key=f"day_{d}",
                    type="primary" if is_selected else "secondary",
                    on_click=pick_day,
                    args=(day,),
                    width="stretch",
                )

    chosen = st.session_state.selected_day
    day_tasks = schedule.get(chosen, [])
    st.markdown(f"**{chosen.strftime('%A, %d %B')}** · {len(day_tasks)} task(s)")
    if not day_tasks:
        st.caption("No tasks scheduled.")
    for t in day_tasks:
        st.markdown(
            f'<div class="tile" style="margin-bottom:0.4rem">'
            f'<b style="font-size:1.05rem">{t["task_type"]}</b>'
            f'<span>{t["zone"]} · {t["estimated_min"]} min</span></div>',
            unsafe_allow_html=True,
        )

# ---------------- Small widgets ----------------
tel = get_latest_telemetry()
op = get_operator()
weather = get_weather()
status = get_safety_status()

status_text = {"safe": "🟢 Safe", "warning": "⚠️ Caution", "critical": "🔴 Critical"}
hours, mins = divmod(op["operating_minutes"], 60)

tiles = (
    '<div class="tile-grid">'
    f'<div class="tile {status}"><span>Safety</span><b>{status_text[status]}</b></div>'
    f'<div class="tile"><span>Weather</span><b>{weather["condition"]}, {weather["temp_c"]}°C</b></div>'
    f'<div class="tile"><span>Operating today</span><b>{hours}h {mins:02d}m</b></div>'
    f'<div class="tile"><span>Fuel</span><b>{tel["fuel_level_pct"]:.0f}%</b></div>'
    '</div>'
)
st.markdown(tiles, unsafe_allow_html=True)