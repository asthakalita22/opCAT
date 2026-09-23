import streamlit as st
from data.dummy import get_alerts

ICON = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}

alerts = sorted(get_alerts(), key=lambda a: a["timestamp"], reverse=True)   # newest first
acknowledged = st.session_state.get("acknowledged", {})

st.subheader("Incident history")

choice = st.segmented_control(
    "Filter", ["All", "Critical", "Warning", "Info"],
    default="All", label_visibility="collapsed",
)
if choice and choice != "All":
    alerts = [a for a in alerts if a["severity"] == choice.lower()]

st.caption(f"{len(alerts)} incident(s) today")

if not alerts:
    st.info("No incidents for this filter.")

for a in alerts:
    status = "ACTIVE" if a["active"] else "RESOLVED"
    extra = a["category"].replace("_", " ").capitalize()
    if a["alert_id"] in acknowledged:
        extra += f' · Acknowledged {acknowledged[a["alert_id"]]}'

    row = (
        f'<div class="incident {a["severity"]}">'
        '<div class="i-top">'
        f'<span class="i-head">{ICON[a["severity"]]} {a["severity"].upper()} · {a["timestamp"][11:16]}</span>'
        f'<span class="i-status {status.lower()}">{status}</span>'
        '</div>'
        f'<div class="i-msg">{a["message"]}</div>'
        f'<div class="i-meta">{extra}</div>'
        '</div>'
    )
    st.markdown(row, unsafe_allow_html=True)