import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="MT-25 Elite Dashboard", layout="wide")

# -----------------------------
# GOOGLE SHEETS CONNECTION
# -----------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtOfkiFAYIV9uubiLi8RAmMSj5mKDBxY9iEeOCGXjN5p7TVjPbmGOdSA-pIpDeC1ajS-y0yVDwAJ1m/pub?gid=1859833030&single=true&output=csv"

def connect_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df

df = load_data()

# -----------------------------
# INPUT FORM (🔥 NEW)
# -----------------------------
st.markdown("## ➕ Add Refuel Entry")

with st.form("fuel_form", clear_on_submit=True):

    col1, col2 = st.columns(2)

    with col1:
        date = st.date_input("Date", datetime.today())
        trip_km = st.number_input("Trip KM", min_value=0.0, step=1.0)
        liters = st.number_input("Liters", min_value=0.0, step=0.01)

    with col2:
        cost = st.number_input("Cost (RM)", min_value=0.0, step=0.01)
        price = st.number_input("Price per Liter", min_value=0.0, step=0.01)
        full_tank = st.selectbox("Full Tank", ["yes", "partial"])

    submitted = st.form_submit_button("🚀 Add Entry")

    if submitted:
        try:
            client = connect_gsheet()
            sheet = client.open_by_url(
                "https://docs.google.com/spreadsheets/d/1PLACEHOLDER/edit"
            ).sheet1

            new_row = [
                str(date),
                trip_km,
                liters,
                cost,
                price,
                full_tank
            ]

            sheet.append_row(new_row)

            st.success("✅ Entry added successfully!")

            st.cache_data.clear()

        except Exception as e:
            st.error(f"Error: {e}")

# -----------------------------
# CALCULATIONS
# -----------------------------
df["consumption"] = (df["liters"] / df["trip_km"]) * 100
df["cost_per_km"] = df["cost_rm"] / df["trip_km"]

avg_consumption = df["consumption"].mean()
avg_cost_km = df["cost_per_km"].mean()
total_spent = df["cost_rm"].sum()

# -----------------------------
# KPI
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Consumption", f"{avg_consumption:.2f} L/100km")
col2.metric("Cost/km", f"RM {avg_cost_km:.3f}")
col3.metric("Total Spent", f"RM {total_spent:.2f}")

# -----------------------------
# CHARTS
# -----------------------------
st.subheader("📈 Consumption")
st.line_chart(df.set_index("date")["consumption"])

st.subheader("💸 Cost per KM")
st.line_chart(df.set_index("date")["cost_per_km"])

st.subheader("⛽ Fuel")
st.area_chart(df.set_index("date")["liters"])

# -----------------------------
# DATA
# -----------------------------
with st.expander("Data"):
    st.dataframe(df)
