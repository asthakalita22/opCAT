from datetime import datetime
from pathlib import Path

import streamlit as st
from data.dummy import get_active_alerts

st.set_page_config(page_title="CAT Operator Assistant", page_icon="🚜")

# ---------------- Styling ----------------
css = Path("ui/styles.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ---------------- Pages ----------------
today = st.Page("pages/01_Today.py", title="Today", icon="🏠", default=True)
safety = st.Page("pages/02_Safety.py", title="Safety", icon="🛡️")
training = st.Page("pages/03_Training.py", title="Training", icon="📚")
ask = st.Page("pages/04_Ask_CAT.py", title="Ask CAT", icon="🤖")
incidents = st.Page("pages/05_Incidents.py", title="Incidents", icon="📋")
shift = st.Page("pages/06_Shift_Analytics.py", title="My Shift", icon="📊")
simulator = st.Page("pages/07_Simulator.py", title="Simulator", icon="🎛️")

nav = st.navigation([today, safety, training, ask, incidents, shift, simulator],
                    position="hidden")

# ---------------- Alerts (shown on every page) ----------------
active = get_active_alerts()

# ---------------- Auto-refresh ----------------
# Remember which alerts were active when this screen was drawn.
st.session_state.shown_alert_ids = sorted(a["alert_id"] for a in active)
st.session_state.setdefault("ticks", 0)


@st.fragment(run_every=2)
def watch_for_changes():
    """Every 2 s, check the backend. Redraw the whole screen only if something changed."""
    st.session_state.ticks += 1
    now_ids = sorted(a["alert_id"] for a in get_active_alerts())
    alerts_changed = now_ids != st.session_state.shown_alert_ids
    telemetry_due = st.session_state.ticks % 5 == 0      # every 10 s
    if alerts_changed or telemetry_due:
        st.rerun()


watch_for_changes()

# Critical pop-up
if "acknowledged" not in st.session_state:
    st.session_state.acknowledged = {}      # {alert_id: time acknowledged}


@st.dialog("🔴 CRITICAL ALERT", dismissible=False)
def critical_popup(alert):
    st.markdown(f'<div class="crit-msg">{alert["message"]}</div>', unsafe_allow_html=True)
    st.caption(f'At {alert["timestamp"][11:16]} · Stop and check your surroundings.')
    if st.button("I understand", type="primary", width="stretch"):
        st.session_state.acknowledged[alert["alert_id"]] = datetime.now().strftime("%H:%M")
        st.rerun()


pending = [a for a in active
           if a["severity"] == "critical" and a["alert_id"] not in st.session_state.acknowledged]
if pending:
    critical_popup(max(pending, key=lambda a: a["timestamp"]))

# Alert banner
ALERT_ICON = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}
if active:
    latest = max(active, key=lambda a: a["timestamp"])   # newest alert
    time_str = latest["timestamp"][11:16]                 # "11:45"
    banner = (
        f'<div class="alert-banner {latest["severity"]}">'
        f'<div class="a-head">{ALERT_ICON[latest["severity"]]} '
        f'{latest["severity"].upper()} · {time_str}</div>'
        f'<div class="a-msg">{latest["message"]}</div>'
        '</div>'
    )
    st.markdown(banner, unsafe_allow_html=True)

# ---------------- Run the selected page ----------------
nav.run()

# ---------------- Bottom tab bar ----------------
with st.container(key="bottom_nav"):
    cols = st.columns(5)
    n_active = len(active)
    for col, page in zip(cols, [today, safety, training, ask, shift]):
        label = page.title
        if page is safety and n_active > 0:
            label = f"{page.title} ({n_active})"
        col.page_link(page, label=label, icon=page.icon)