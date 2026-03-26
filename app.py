import streamlit as st
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
