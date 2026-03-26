import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="MT-25 Elite", layout="wide")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PUBLIC_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtOfkiFAYIV9uubiLi8RAmMSj5mKDBxY9iEeOCGXjN5p7TVjPbmGOdSA-pIpDeC1ajS-y0yVDwAJ1m/pub?gid=1859833030&single=true&output=csv"
EDIT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PLACEHOLDER/edit"  # replace

# -------------------------------------------------
# STYLE (THIS IS THE MAGIC)
# -------------------------------------------------
st.markdown("""
<style>

.stApp {
    background:
        radial-gradient(circle at top left, rgba(59,130,246,0.15), transparent 30%),
        radial-gradient(circle at bottom right, rgba(16,185,129,0.10), transparent 30%),
        linear-gradient(180deg, #0b1020 0%, #0f172a 100%);
}

.block-container {
    padding-top: 1.5rem;
    max-width: 1300px;
}

.card {
    background: rgba(15,23,42,0.75);
    backdrop-filter: blur(12px);
    border-radius: 22px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.metric {
    font-size: 28px;
    font-weight: bold;
    color: white;
}

.label {
    color: #94a3b8;
    font-size: 14px;
}

.pill {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    margin-right: 6px;
    background: rgba(255,255,255,0.08);
}

.good { background: rgba(16,185,129,0.2); }
.warn { background: rgba(245,158,11,0.2); }

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# GOOGLE
# -------------------------------------------------
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

# -------------------------------------------------
# LOAD
# -------------------------------------------------
@st.cache_data(ttl=300)
def load():
    df = pd.read_csv(PUBLIC_SHEET_URL)
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["consumption"] = (df["liters"] / df["trip_km"]) * 100
    df["cost_km"] = df["cost_rm"] / df["trip_km"]

    return df

df = load()

# -------------------------------------------------
# HERO
# -------------------------------------------------
avg = df["consumption"].mean()
latest_price = df.iloc[-1]["price_per_l"]

st.markdown(f"""
<div class="card">
<h1>🏍️ MT-25 Elite</h1>
<span class="pill good">Efficiency {avg:.2f}</span>
<span class="pill warn">Fuel RM {latest_price:.2f}</span>
<span class="pill">{len(df)} entries</span>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# FORM (BLENDED)
# -------------------------------------------------
with st.expander("➕ Add Refuel"):

    with st.form("form", clear_on_submit=True):

        c1, c2 = st.columns(2)

        with c1:
            date = st.date_input("Date", datetime.today())
            km = st.number_input("Trip KM", step=1.0)
            liters = st.number_input("Liters", step=0.01)

        with c2:
            cost = st.number_input("Cost", step=0.01)
            price = st.number_input("Price/L", step=0.01)
            full = st.selectbox("Full Tank", ["yes", "partial"])

        submit = st.form_submit_button("Add")

        if submit:
            client = connect()
            sheet = client.open_by_url(EDIT_SHEET_URL).sheet1
            sheet.append_row([str(date), km, liters, cost, price, full])
            st.success("Added")
            st.cache_data.clear()
            st.rerun()

# -------------------------------------------------
# METRICS
# -------------------------------------------------
avg_cost = df["cost_km"].mean()
total = df["cost_rm"].sum()

tank = 11
range_km = tank / (avg / 100)

m1, m2, m3, m4 = st.columns(4)

m1.markdown(f"<div class='card'><div class='label'>Consumption</div><div class='metric'>{avg:.2f}</div></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='card'><div class='label'>Cost/km</div><div class='metric'>RM {avg_cost:.3f}</div></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='card'><div class='label'>Range</div><div class='metric'>{range_km:.0f} km</div></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='card'><div class='label'>Total</div><div class='metric'>RM {total:.0f}</div></div>", unsafe_allow_html=True)

# -------------------------------------------------
# CHARTS
# -------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    fig = px.line(df, x="date", y="consumption", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig2 = px.line(df, x="date", y="cost_km", template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

fig3 = px.area(df, x="date", y="liters", template="plotly_dark")
st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------
# INSIGHTS
# -------------------------------------------------
best = df.loc[df["consumption"].idxmin()]
worst = df.loc[df["consumption"].idxmax()]

st.markdown(f"""
<div class="card">
<h3>Insights</h3>
Best: {best['consumption']:.2f} L/100km  
Worst: {worst['consumption']:.2f} L/100km  
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# DATA
# -------------------------------------------------
with st.expander("Data"):
    st.dataframe(df)
