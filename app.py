import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="MT-25 Elite Dashboard", layout="wide")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
PUBLIC_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtOfkiFAYIV9uubiLi8RAmMSj5mKDBxY9iEeOCGXjN5p7TVjPbmGOdSA-pIpDeC1ajS-y0yVDwAJ1m/pub?gid=1859833030&single=true&output=csv"

EDIT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1PLACEHOLDER/edit"  # 🔁 replace this

# -------------------------------------------------
# STYLE (PREMIUM)
# -------------------------------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #0b1020, #0f172a);
}

.metric-card {
    background: rgba(15, 23, 42, 0.8);
    padding: 20px;
    border-radius: 18px;
    border: 1px solid rgba(148,163,184,0.2);
    text-align: center;
}

.metric-title {
    color: #94a3b8;
    font-size: 14px;
}

.metric-value {
    color: white;
    font-size: 26px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# GOOGLE CONNECTION
# -------------------------------------------------
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(PUBLIC_SHEET_URL)
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    df["consumption"] = (df["liters"] / df["trip_km"]) * 100
    df["cost_per_km"] = df["cost_rm"] / df["trip_km"]

    return df

df = load_data()

# -------------------------------------------------
# TITLE
# -------------------------------------------------
st.title("🏍️ MT-25 Elite Dashboard")

# -------------------------------------------------
# INPUT FORM (INTEGRATED)
# -------------------------------------------------
with st.expander("➕ Add Refuel Entry"):

    with st.form("form", clear_on_submit=True):

        col1, col2 = st.columns(2)

        with col1:
            date = st.date_input("Date", datetime.today())
            trip_km = st.number_input("Trip KM", step=1.0)
            liters = st.number_input("Liters", step=0.01)

        with col2:
            cost = st.number_input("Cost RM", step=0.01)
            price = st.number_input("Price per Liter", step=0.01)
            full = st.selectbox("Full Tank", ["yes", "partial"])

        submit = st.form_submit_button("Add Entry")

        if submit:
            try:
                client = connect_sheet()
                sheet = client.open_by_url(EDIT_SHEET_URL).sheet1

                sheet.append_row([
                    str(date),
                    trip_km,
                    liters,
                    cost,
                    price,
                    full
                ])

                st.success("✅ Entry added")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(e)

# -------------------------------------------------
# KPIs
# -------------------------------------------------
avg_cons = df["consumption"].mean()
avg_cost = df["cost_per_km"].mean()
total = df["cost_rm"].sum()

tank_capacity = 11
range_km = tank_capacity / (avg_cons / 100)

latest_trip = df.iloc[-1]["trip_km"]
remaining = range_km - latest_trip

col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"<div class='metric-card'><div class='metric-title'>Consumption</div><div class='metric-value'>{avg_cons:.2f}</div></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='metric-card'><div class='metric-title'>Cost/km</div><div class='metric-value'>RM {avg_cost:.3f}</div></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='metric-card'><div class='metric-title'>Range</div><div class='metric-value'>{range_km:.0f} km</div></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='metric-card'><div class='metric-title'>Total</div><div class='metric-value'>RM {total:.0f}</div></div>", unsafe_allow_html=True)

# -------------------------------------------------
# INSIGHTS
# -------------------------------------------------
st.subheader("🧠 Insights")

best = df.loc[df["consumption"].idxmin()]
worst = df.loc[df["consumption"].idxmax()]

st.markdown(f"""
- 🥇 Best: {best['consumption']:.2f} L/100km  
- 🔻 Worst: {worst['consumption']:.2f} L/100km  
- ⛽ Remaining range: {remaining:.0f} km  
""")

# -------------------------------------------------
# CHARTS
# -------------------------------------------------
st.subheader("📈 Consumption")
fig = px.line(df, x="date", y="consumption", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

st.subheader("💸 Cost per KM")
fig2 = px.line(df, x="date", y="cost_per_km", template="plotly_dark")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("⛽ Fuel")
fig3 = px.area(df, x="date", y="liters", template="plotly_dark")
st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------
# DATA
# -------------------------------------------------
with st.expander("📄 Data"):
    st.dataframe(df)
