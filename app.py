import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="MT-25 Intelligence Dashboard", layout="wide")

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
body { background-color: #0e1117; }
.block-container { padding-top: 2rem; }
h1, h2, h3 { color: white; }

.kpi-card {
    background: linear-gradient(145deg, #1c1f26, #111318);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    text-align: center;
}
.kpi-title { font-size: 14px; color: #9aa4b2; }
.kpi-value { font-size: 28px; font-weight: bold; color: white; }

.section { margin-top: 30px; }
.good { color: #22c55e; }
.bad { color: #ef4444; }
.neutral { color: #facc15; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# TITLE
# -----------------------------
st.title("🏍️ MT-25 Intelligence Dashboard")

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

# Rolling efficiency (trend)
df["rolling_consumption"] = df["consumption"].rolling(3).mean()

# KPIs
avg_consumption = df["consumption"].mean()
avg_cost_km = df["cost_per_km"].mean()
total_spent = df["cost_rm"].sum()

best = df.loc[df["consumption"].idxmin()]
worst = df.loc[df["consumption"].idxmax()]

# -----------------------------
# PREDICTIONS
# -----------------------------
tank_capacity = 11  # MT-25 approx

avg_range = tank_capacity / (avg_consumption / 100)

latest_trip = df.iloc[-1]["trip_km"]

remaining_range = avg_range - latest_trip

# Price simulation
current_price = df.iloc[-1]["price_per_l"]
future_price = 3.87  # your scenario

monthly_liters = df["liters"].mean() * 4
future_monthly_cost = monthly_liters * future_price

# -----------------------------
# KPI DISPLAY
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Avg Consumption</div>
<div class="kpi-value">{avg_consumption:.2f}</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Cost / KM</div>
<div class="kpi-value">RM {avg_cost_km:.3f}</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Tank Range</div>
<div class="kpi-value">{avg_range:.0f} km</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Total Spent</div>
<div class="kpi-value">RM {total_spent:.0f}</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# INSIGHTS
# -----------------------------
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("🧠 Smart Insights")

if avg_consumption < 4:
    st.markdown("✅ Excellent efficiency — your riding is very smooth.")
elif avg_consumption < 5:
    st.markdown("⚖️ Good efficiency — slight improvement possible.")
else:
    st.markdown("⚠️ High consumption — aggressive riding or traffic impact.")

st.markdown(f"""
- 🥇 Best ride: **{best['consumption']:.2f} L/100km**
- 🔻 Worst ride: **{worst['consumption']:.2f} L/100km**
- ⛽ Estimated remaining range: **{remaining_range:.0f} km**
""")

# -----------------------------
# PRICE IMPACT
# -----------------------------
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("💸 Fuel Price Impact")

st.markdown(f"""
If fuel reaches **RM {future_price}/L**:

- Monthly cost → **RM {future_monthly_cost:.0f}**
- Increase vs today → **+{((future_price/current_price)-1)*100:.0f}%**
""")

# -----------------------------
# CHARTS
# -----------------------------
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.subheader("📈 Consumption Trend")
st.line_chart(df.set_index("date")[["consumption", "rolling_consumption"]])

st.subheader("💸 Cost per KM")
st.line_chart(df.set_index("date")["cost_per_km"])

st.subheader("⛽ Fuel Usage")
st.area_chart(df.set_index("date")["liters"])

# -----------------------------
# RAW DATA
# -----------------------------
with st.expander("📄 Data"):
    st.dataframe(df, use_container_width=True)import streamlit as st
import pandas as pd

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="MT-25 Dashboard", layout="wide")

# -----------------------------
# CUSTOM CSS
# -----------------------------
st.markdown("""
<style>
body { background-color: #0e1117; }

.block-container { padding-top: 2rem; }

h1, h2, h3 { color: white; }

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

.section { margin-top: 30px; }

hr { border: 1px solid #1f2937; }
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
# RAW DATA
# -----------------------------
with st.expander("📄 View Raw Data"):
    st.dataframe(df, use_container_width=True)
