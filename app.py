import streamlit as st
import pandas as pd

st.set_page_config(page_title="MT-25 Dashboard", layout="wide")

st.title("🏍️ MT-25 Fuel Dashboard")

# Load data
df = pd.read_csv("mt25_fuel_log.csv")

# Convert date
df["date"] = pd.to_datetime(df["date"])

# Sort
df = df.sort_values("date")

# Calculate distance between refuels
df["distance"] = df["odometer"].diff()

# Consumption (L/100km)
df["consumption"] = (df["liters"] / df["distance"]) * 100

# Cost per km
df["cost_per_km"] = df["cost"] / df["distance"]

# Monthly grouping
df["month"] = df["date"].dt.to_period("M")

monthly = df.groupby("month").agg({
    "cost": "sum",
    "liters": "sum",
    "distance": "sum"
}).reset_index()

# KPIs
col1, col2, col3 = st.columns(3)

col1.metric("Avg Consumption (L/100km)", f"{df['consumption'].mean():.2f}")
col2.metric("Avg Cost/km (RM)", f"{df['cost_per_km'].mean():.3f}")
col3.metric("Total Spent (RM)", f"{df['cost'].sum():.2f}")

st.divider()

# Charts
st.subheader("📈 Consumption Over Time")
st.line_chart(df.set_index("date")["consumption"])

st.subheader("💸 Monthly Spending")
st.bar_chart(monthly.set_index("month")["cost"])

st.subheader("⛽ Liters per Refuel")
st.line_chart(df.set_index("date")["liters"])

# Raw data
with st.expander("📄 Show Raw Data"):
    st.dataframe(df)
