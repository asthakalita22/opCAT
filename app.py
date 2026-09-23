import streamlit as st
from pathlib import Path

st.set_page_config(page_title="CAT Operator Assistant", page_icon="🚜")

css = Path("ui/styles.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

today = st.Page("pages/01_Today.py", title="Today", icon="🏠", default=True)
safety = st.Page("pages/02_Safety.py", title="Safety", icon="🛡️")
training = st.Page("pages/03_Training.py", title="Training", icon="📚")
ask = st.Page("pages/04_Ask_CAT.py", title="Ask CAT", icon="🤖")
incidents = st.Page("pages/05_Incidents.py", title="Incidents", icon="📋")
shift = st.Page("pages/06_Shift_Analytics.py", title="My Shift", icon="📊")
simulator = st.Page("pages/07_Simulator.py", title="Simulator", icon="🎛️")

nav = st.navigation([today, safety, training, ask, incidents, shift, simulator],
                    position="hidden")
nav.run()

# Bottom tab bar, like a phone app
with st.container(key="bottom_nav"):
    cols = st.columns(5)
    for col, page in zip(cols, [today, safety, training, ask, shift]):
        col.page_link(page, label=page.title, icon=page.icon)