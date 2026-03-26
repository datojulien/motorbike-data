import math
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="MT-25 Elite Dashboard",
    page_icon="🏍️",
    layout="wide",
)

# -------------------------------------------------
# STYLING
# -------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(59,130,246,0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(16,185,129,0.08), transparent 25%),
            linear-gradient(180deg, #0b1020 0%, #0f172a 100%);
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
        letter-spacing: -0.02em;
    }

    .hero-card, .metric-card, .insight-card {
        background: rgba(15, 23, 42, 0.78);
        border: 1px solid rgba(148, 163, 184, 0.16);
        backdrop-filter: blur(10px);
        border-radius: 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.28);
    }

    .hero-card {
        padding: 1.4rem 1.5rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        padding: 1rem 1.1rem;
        min-height: 126px;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.05;
        margin-bottom: 0.35rem;
    }

    .metric-sub {
        color: #cbd5e1;
        font-size: 0.86rem;
    }

    .pill {
        display: inline-block;
        padding: 0.28rem 0.65rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 0.35rem;
        margin-top: 0.25rem;
    }

    .pill-good {
        background: rgba(16,185,129,0.16);
        color: #6ee7b7;
        border: 1px solid rgba(16,185,129,0.28);
    }

    .pill-warn {
        background: rgba(245,158,11,0.14);
        color: #fcd34d;
        border: 1px solid rgba(245,158,11,0.26);
    }

    .pill-bad {
        background: rgba(239,68,68,0.14);
        color: #fca5a5;
        border: 1px solid rgba(239,68,68,0.26);
    }

    .insight-card {
        padding: 1rem 1.05rem;
        margin-bottom: 0.9rem;
    }

    .small-muted {
        color: #94a3b8;
        font-size: 0.9rem;
    }

    div[data-testid="stMetric"] {
        background: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("mt25_fuel_log.csv")
    required = {"date", "trip_km", "liters", "cost_rm", "price_per_l", "full_tank"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["trip_km"] = pd.to_numeric(df["trip_km"], errors="coerce")
    df["liters"] = pd.to_numeric(df["liters"], errors="coerce")
    df["cost_rm"] = pd.to_numeric(df["cost_rm"], errors="coerce")
    df["price_per_l"] = pd.to_numeric(df["price_per_l"], errors="coerce")
    df["full_tank"] = (
        df["full_tank"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"yes": True, "true": True, "1": True, "partial": False, "no": False, "false": False, "0": False})
    )

    df = df.dropna(subset=["date", "trip_km", "liters", "cost_rm", "price_per_l"]).sort_values("date").reset_index(drop=True)

    df["consumption_l_100"] = (df["liters"] / df["trip_km"]) * 100
    df["cost_per_km"] = df["cost_rm"] / df["trip_km"]
    df["km_per_l"] = df["trip_km"] / df["liters"]
    df["days_since_prev"] = df["date"].diff().dt.days
    df["daily_km"] = df["trip_km"] / df["days_since_prev"].replace(0, np.nan)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["year"] = df["date"].dt.year.astype(str)

    df["rolling_consumption"] = df["consumption_l_100"].rolling(3, min_periods=1).mean()
    df["rolling_cost_km"] = df["cost_per_km"].rolling(3, min_periods=1).mean()

    # Efficiency score: lower L/100km = better
    min_c = df["consumption_l_100"].min()
    max_c = df["consumption_l_100"].max()
    if math.isclose(min_c, max_c):
        df["efficiency_score"] = 100.0
    else:
        df["efficiency_score"] = 100 - ((df["consumption_l_100"] - min_c) / (max_c - min_c) * 40)
        df["efficiency_score"] = df["efficiency_score"].clip(60, 100)

    # Anomaly flag using simple z-score
    mean_c = df["consumption_l_100"].mean()
    std_c = df["consumption_l_100"].std(ddof=0)
    if std_c == 0 or np.isnan(std_c):
        df["is_anomaly"] = False
    else:
        z = (df["consumption_l_100"] - mean_c) / std_c
        df["is_anomaly"] = z.abs() >= 1.5

    return df


def metric_card(label: str, value: str, sub: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def classify_consumption(v: float) -> tuple[str, str]:
    if v <= 4.1:
        return "Excellent", "pill-good"
    if v <= 4.6:
        return "Very good", "pill-good"
    if v <= 5.1:
        return "Good", "pill-warn"
    return "Heavy", "pill-bad"


def build_monthly(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        df.groupby("month", as_index=False)
        .agg(
            trip_km=("trip_km", "sum"),
            liters=("liters", "sum"),
            cost_rm=("cost_rm", "sum"),
            avg_consumption=("consumption_l_100", "mean"),
            avg_cost_per_km=("cost_per_km", "mean"),
            entries=("date", "count"),
        )
    )
    monthly["km_per_l"] = monthly["trip_km"] / monthly["liters"]
    return monthly


def predict_next_refill(df: pd.DataFrame, tank_capacity_l: float) -> dict:
    if len(df) == 0:
        return {"range_km": np.nan, "days_left": np.nan, "next_date": None}

    avg_consumption = df["consumption_l_100"].mean()
    avg_daily_km = df["daily_km"].dropna().tail(5).mean()

    if pd.isna(avg_consumption) or avg_consumption <= 0:
        return {"range_km": np.nan, "days_left": np.nan, "next_date": None}

    est_range = tank_capacity_l / avg_consumption * 100
    current_trip = df.iloc[-1]["trip_km"]
    remaining = max(est_range - current_trip, 0)

    if pd.isna(avg_daily_km) or avg_daily_km <= 0:
        days_left = np.nan
        next_date = None
    else:
        days_left = remaining / avg_daily_km
        next_date = df.iloc[-1]["date"] + timedelta(days=float(days_left))

    return {
        "range_km": est_range,
        "remaining_km": remaining,
        "days_left": days_left,
        "next_date": next_date,
    }


def tip_generator(row: pd.Series, avg_consumption: float, latest_price: float) -> list[str]:
    tips = []

    if row["consumption_l_100"] > avg_consumption * 1.08:
        tips.append("This latest tank was less efficient than your usual pattern. Likely suspects: heavier traffic, shorter trips, or more aggressive throttle.")
    else:
        tips.append("Your latest tank sits well within your normal efficiency range. Riding style looks steady.")

    if latest_price >= 3.5:
        tips.append("Fuel price is now doing more damage than riding style. The biggest savings may come from combining errands and avoiding low-value short rides.")

    if row["trip_km"] < 200:
        tips.append("Shorter intervals between refuels can make trends look noisier. A few more full cycles will sharpen the predictions.")

    if row["liters"] > 11.5:
        tips.append("That refill was unusually large. Good to flag in case the bike was especially low or the fill level varied more than usual.")

    if row["days_since_prev"] and row["days_since_prev"] <= 5:
        tips.append("You refueled again quite quickly. Usage pace is high; worth watching if this becomes a streak.")

    if not tips:
        tips.append("No obvious red flags. Your data looks tidy and consistent — the sort of thing that makes forecasting much more trustworthy.")

    return tips[:3]


# -------------------------------------------------
# LOAD
# -------------------------------------------------
df_all = load_data()

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.header("Filters")

years = ["All"] + sorted(df_all["year"].unique().tolist())
selected_year = st.sidebar.selectbox("Year", years, index=0)

months = ["All"] + sorted(df_all["month"].unique().tolist())
selected_month = st.sidebar.selectbox("Month", months, index=0)

tank_capacity = st.sidebar.slider("Estimated tank capacity (L)", 10.0, 16.0, 11.0, 0.1)
future_price = st.sidebar.slider("What-if fuel price (RM/L)", 2.00, 5.50, 3.87, 0.01)
show_partial = st.sidebar.toggle("Include partial fills", value=True)

df = df_all.copy()

if selected_year != "All":
    df = df[df["year"] == selected_year]

if selected_month != "All":
    df = df[df["month"] == selected_month]

if not show_partial:
    df = df[df["full_tank"] == True]  # noqa: E712

if df.empty:
    st.error("No data matches the current filters.")
    st.stop()

monthly = build_monthly(df)
latest = df.iloc[-1]
first = df.iloc[0]
pred = predict_next_refill(df, tank_capacity)

avg_consumption = df["consumption_l_100"].mean()
avg_cost_km = df["cost_per_km"].mean()
avg_km_per_l = df["km_per_l"].mean()
total_spent = df["cost_rm"].sum()
total_distance = df["trip_km"].sum()
total_liters = df["liters"].sum()
latest_price = df["price_per_l"].iloc[-1]
best = df.loc[df["consumption_l_100"].idxmin()]
worst = df.loc[df["consumption_l_100"].idxmax()]
efficiency_label, efficiency_class = classify_consumption(avg_consumption)

days_span = max((df["date"].max() - df["date"].min()).days, 1)
monthly_spend_est = total_spent / days_span * 30.44
monthly_distance_est = total_distance / days_span * 30.44
future_monthly_cost = total_liters / days_span * 30.44 * future_price
delta_future = future_monthly_cost - monthly_spend_est

tips = tip_generator(latest, avg_consumption, latest_price)

# -------------------------------------------------
# HERO
# -------------------------------------------------
st.markdown(
    f"""
    <div class="hero-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
            <div>
                <h1 style="margin:0;">🏍️ MT-25 Elite Dashboard</h1>
                <div class="small-muted">Premium fuel intelligence for your bike — trends, forecasts, anomalies, and cost control.</div>
            </div>
            <div>
                <span class="pill {efficiency_class}">{efficiency_label} efficiency</span>
                <span class="pill pill-warn">Latest fuel: RM {latest_price:.2f}/L</span>
                <span class="pill pill-good">{len(df)} logged refuels</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# TOP METRICS
# -------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    metric_card("Average consumption", f"{avg_consumption:.2f} L/100km", f"{avg_km_per_l:.2f} km/L")
with m2:
    metric_card("Average cost per km", f"RM {avg_cost_km:.3f}", f"Latest: RM {latest['cost_per_km']:.3f}/km")
with m3:
    metric_card("Estimated monthly spend", f"RM {monthly_spend_est:.0f}", f"Based on {days_span} tracked days")
with m4:
    metric_card("Estimated tank range", f"{pred['range_km']:.0f} km", f"Remaining now: {pred['remaining_km']:.0f} km")
with m5:
    next_refill_text = pred["next_date"].strftime("%d %b %Y") if pred["next_date"] is not None else "Need more data"
    metric_card("Predicted next refill", next_refill_text, f"In {pred['days_left']:.1f} days" if pd.notna(pred["days_left"]) else "Pace not stable enough")

# -------------------------------------------------
# SECOND ROW
# -------------------------------------------------
m6, m7, m8, m9 = st.columns(4)
with m6:
    metric_card("Total spent", f"RM {total_spent:.2f}", f"{total_liters:.2f} L bought")
with m7:
    metric_card("Total tracked distance", f"{total_distance:.1f} km", f"From {first['date'].date()} to {latest['date'].date()}")
with m8:
    metric_card("Best tank", f"{best['consumption_l_100']:.2f} L/100km", f"{best['date'].date()} • {best['trip_km']:.1f} km")
with m9:
    metric_card("Worst tank", f"{worst['consumption_l_100']:.2f} L/100km", f"{worst['date'].date()} • {worst['trip_km']:.1f} km")

# -------------------------------------------------
# CHARTS
# -------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Consumption trend")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["consumption_l_100"],
            mode="lines+markers",
            name="Actual",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["rolling_consumption"],
            mode="lines",
            name="3-tank rolling average",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="",
        yaxis_title="L/100km",
        legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Cost pressure")
    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=df["date"],
            y=df["cost_per_km"],
            name="Cost per km",
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["rolling_cost_km"],
            mode="lines+markers",
            name="Rolling average",
            yaxis="y2",
        )
    )
    fig2.update_layout(
        template="plotly_dark",
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="",
        yaxis=dict(title="RM/km"),
        yaxis2=dict(title="Rolling RM/km", overlaying="y", side="right"),
        legend_title="",
    )
    st.plotly_chart(fig2, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    st.subheader("Monthly spending")
    fig3 = px.bar(
        monthly,
        x="month",
        y="cost_rm",
        text_auto=".2f",
        template="plotly_dark",
    )
    fig3.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="RM")
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("Efficiency score")
    fig4 = px.area(
        df,
        x="date",
        y="efficiency_score",
        template="plotly_dark",
    )
    fig4.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="Score / 100")
    st.plotly_chart(fig4, use_container_width=True)

# -------------------------------------------------
# INSIGHTS + SIMULATOR
# -------------------------------------------------
left, right = st.columns([1.05, 0.95])

with left:
    st.subheader("Smart insights")

    anomaly_rows = df[df["is_anomaly"]].sort_values("date", ascending=False)

    st.markdown(
        f"""
        <div class="insight-card">
            <strong>Latest tank verdict</strong><br>
            Your latest recorded tank used <strong>{latest['consumption_l_100']:.2f} L/100km</strong>,
            compared with a dashboard average of <strong>{avg_consumption:.2f} L/100km</strong>.
            That puts it at <strong>{((latest['consumption_l_100']/avg_consumption)-1)*100:+.1f}%</strong> versus your normal pattern.
        </div>
        """,
        unsafe_allow_html=True,
    )

    refill_line = (
        f"Based on recent pace, next refill is likely around <strong>{pred['next_date'].strftime('%d %b %Y')}</strong> "
        f"with about <strong>{pred['remaining_km']:.0f} km</strong> of estimated range left."
        if pred["next_date"] is not None
        else "There is not yet enough stable day-to-day riding data to estimate a refill date confidently."
    )
    st.markdown(
        f"""
        <div class="insight-card">
            <strong>Refill forecast</strong><br>
            {refill_line}
        </div>
        """,
        unsafe_allow_html=True,
    )

    anomaly_text = (
        f"{len(anomaly_rows)} tank(s) look unusual enough to inspect. These do not mean something is wrong — just that they differ meaningfully from your average."
        if len(anomaly_rows) > 0
        else "No major anomalies detected. Your entries form a fairly coherent pattern, which is excellent for forecasting."
    )
    st.markdown(
        f"""
        <div class="insight-card">
            <strong>Anomaly watch</strong><br>
            {anomaly_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Useful tips**")
    for tip in tips:
        st.markdown(f"- {tip}")

with right:
    st.subheader("Fuel price simulator")

    pct_change = ((future_price / latest_price) - 1) * 100 if latest_price > 0 else np.nan

    st.markdown(
        f"""
        <div class="insight-card">
            <strong>If fuel rises to RM {future_price:.2f}/L</strong><br>
            Estimated monthly spend becomes <strong>RM {future_monthly_cost:.0f}</strong>,
            which is <strong>{delta_future:+.0f} RM/month</strong> versus your current estimated pace
            ({pct_change:+.1f}% on fuel price).
        </div>
        """,
        unsafe_allow_html=True,
    )

    simulator_df = pd.DataFrame(
        {
            "price_rm_l": np.round(np.linspace(2.0, 5.0, 13), 2),
        }
    )
    liters_per_month_est = total_liters / days_span * 30.44
    simulator_df["monthly_cost_rm"] = simulator_df["price_rm_l"] * liters_per_month_est

    fig5 = px.line(
        simulator_df,
        x="price_rm_l",
        y="monthly_cost_rm",
        markers=True,
        template="plotly_dark",
    )
    fig5.add_vline(x=future_price, line_dash="dash")
    fig5.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Fuel price (RM/L)",
        yaxis_title="Estimated monthly cost (RM)",
    )
    st.plotly_chart(fig5, use_container_width=True)

# -------------------------------------------------
# LEADERBOARD + MONTHLY TABLE
# -------------------------------------------------
l1, l2 = st.columns(2)

with l1:
    st.subheader("Top 5 most efficient tanks")
    top5 = df.sort_values("consumption_l_100", ascending=True)[
        ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
    ].head(5).copy()
    top5["date"] = top5["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(top5, use_container_width=True, hide_index=True)

with l2:
    st.subheader("5 heaviest tanks")
    bottom5 = df.sort_values("consumption_l_100", ascending=False)[
        ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
    ].head(5).copy()
    bottom5["date"] = bottom5["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(bottom5, use_container_width=True, hide_index=True)

st.subheader("Monthly breakdown")
monthly_display = monthly.copy()
st.dataframe(monthly_display, use_container_width=True, hide_index=True)

# -------------------------------------------------
# DATA EXPLORER
# -------------------------------------------------
with st.expander("Raw data and diagnostics"):
    diagnostic_cols = [
        "date",
        "trip_km",
        "liters",
        "cost_rm",
        "price_per_l",
        "full_tank",
        "consumption_l_100",
        "cost_per_km",
        "km_per_l",
        "days_since_prev",
        "daily_km",
        "efficiency_score",
        "is_anomaly",
    ]
    raw = df[diagnostic_cols].copy()
    raw["date"] = raw["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(raw, use_container_width=True, hide_index=True)
