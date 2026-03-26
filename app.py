import streamlit as st
import pandas as pd

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="MT-25 Dashboard",
    layout="wide"
)

# -----------------------------
# CUSTOM CSS (THE MAGIC ✨)
# -----------------------------
st.markdown("""
<style>

body {
    background-color: #0e1117;
}

.block-container {
    padding-top: 2rem;
}

h1, h2, h3 {
    color: white;
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(145deg, #1c1f26, #111318);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    text-align: center;
}

.kpi-title {
    font-size: 14px;
    color: #9aa4b2;
}

.kpi-value {
    font-size: 28px;
    font-weight: bold;
    color: white;
}

/* Section spacing */
.section {
    margin-top: 30px;
}

/* Divider */
hr {
    border: 1px solid #1f2937;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# TITLE
# -----------------------------
st.title("🏍️ MT-25 Premium Dashboard")

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv("mt25_fuel_log.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date")

# -----------------------------
# CALCULATIONS
# -----------------------------
df["consumption"] = (df["liters"] / df["trip_km"]) * 100
df["cost_per_km"] = df["cost_rm"] / df["trip_km"]

# KPIs
avg_consumption = df["consumption"].mean()
avg_cost_km = df["cost_per_km"].mean()
total_spent = df["cost_rm"].sum()

# -----------------------------
# KPI DISPLAY
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Avg Consumption</div>
        <div class="kpi-value">{avg_consumption:.2f} L/100km</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Cost per KM</div>
        <div class="kpi-value">RM {avg_cost_km:.3f}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Total Spent</div>
        <div class="kpi-value">RM {total_spent:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# CHARTS
# -----------------------------
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("📈 Fuel Consumption Trend")

st.line_chart(df.set_index("date")["consumption"])

st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("💸 Cost per KM")

st.line_chart(df.set_index("date")["cost_per_km"])

st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("⛽ Fuel Volume per Ride")

st.area_chart(df.set_index("date")["liters"])

# -----------------------------
# RAW DATA (HIDDEN)
# -----------------------------
with st.expander("📄 View Raw Data"):
    st.dataframe(df, use_container_width=True)import streamlit as st
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
