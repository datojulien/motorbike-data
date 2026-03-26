from datetime import date, timedelta
import math

import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="MT-25 Blackline",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PUBLIC_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQtOfkiFAYIV9uubiLi8RAmMSj5mKDBxY9iEeOCGXjN5p7TVjPbmGOdSA-pIpDeC1ajS-y0yVDwAJ1m/"
    "pub?gid=1859833030&single=true&output=csv"
)

EDIT_SHEET_URL = st.secrets["google_sheet_edit_url"] if "google_sheet_edit_url" in st.secrets else ""
WORKSHEET_NAME = st.secrets["worksheet_name"] if "worksheet_name" in st.secrets else "Sheet1"

# =========================================================
# STYLE
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --bg0: #07111f;
        --bg1: #0b1728;
        --bg2: #0f2237;
        --panel: rgba(11, 20, 35, 0.70);
        --panel-2: rgba(18, 29, 47, 0.78);
        --stroke: rgba(255,255,255,0.09);
        --text: #f8fafc;
        --muted: #94a3b8;
        --teal: #5eead4;
        --cyan: #67e8f9;
        --blue: #60a5fa;
        --amber: #fbbf24;
        --rose: #fb7185;
        --green: #34d399;
        --shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
    }

    .stApp {
        background:
            radial-gradient(900px 500px at 10% -5%, rgba(56,189,248,0.18), transparent 45%),
            radial-gradient(900px 600px at 100% 0%, rgba(16,185,129,0.12), transparent 35%),
            radial-gradient(700px 450px at 50% 100%, rgba(96,165,250,0.08), transparent 35%),
            linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 45%, var(--bg2) 100%);
        color: var(--text);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.2rem;
        max-width: 1380px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .hero {
        position: relative;
        overflow: hidden;
        border: 1px solid var(--stroke);
        background:
            linear-gradient(135deg, rgba(13,25,43,0.90) 0%, rgba(8,17,31,0.78) 100%);
        border-radius: 28px;
        box-shadow: var(--shadow);
        padding: 1.4rem 1.5rem 1.35rem 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(18px);
    }

    .hero::before {
        content: "";
        position: absolute;
        inset: -40% auto auto 60%;
        width: 360px;
        height: 360px;
        background: radial-gradient(circle, rgba(103,232,249,0.14), transparent 58%);
        pointer-events: none;
    }

    .eyebrow {
        color: var(--cyan);
        font-size: 0.80rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .hero-title {
        font-size: clamp(2rem, 3vw, 3rem);
        line-height: 1.02;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin: 0;
        color: var(--text);
    }

    .hero-sub {
        color: #cbd5e1;
        margin-top: 0.5rem;
        font-size: 1rem;
        max-width: 900px;
    }

    .pillbar {
        margin-top: 0.9rem;
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.42rem 0.74rem;
        border-radius: 999px;
        border: 1px solid var(--stroke);
        background: rgba(255,255,255,0.05);
        color: var(--text);
        font-size: 0.82rem;
        font-weight: 600;
    }

    .pill.good { background: rgba(52,211,153,0.14); color: #86efac; }
    .pill.warn { background: rgba(251,191,36,0.12); color: #fde68a; }
    .pill.info { background: rgba(96,165,250,0.14); color: #bfdbfe; }

    .metric-card, .insight-card, .section-shell {
        border: 1px solid var(--stroke);
        background: var(--panel);
        border-radius: 24px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(14px);
    }

    .metric-card {
        padding: 1rem 1rem 0.95rem 1rem;
        min-height: 132px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.84rem;
        margin-bottom: 0.4rem;
        letter-spacing: 0.02em;
    }

    .metric-value {
        color: var(--text);
        font-size: 2rem;
        line-height: 1.0;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.45rem;
    }

    .metric-sub {
        color: #cbd5e1;
        font-size: 0.86rem;
    }

    .insight-card {
        padding: 1rem 1rem 0.95rem 1rem;
        min-height: 138px;
    }

    .insight-title {
        color: var(--text);
        font-size: 0.96rem;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }

    .insight-body {
        color: #dbeafe;
        font-size: 0.92rem;
        line-height: 1.45;
    }

    .micro-note {
        color: var(--muted);
        font-size: 0.83rem;
    }

    .section-kicker {
        color: var(--cyan);
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }

    .section-title {
        color: var(--text);
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.3rem;
    }

    .section-body {
        color: #cbd5e1;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
        background: rgba(255,255,255,0.04) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input {
        color: white !important;
    }

    div[data-testid="stSegmentedControl"] {
        background: rgba(255,255,255,0.04);
        border-radius: 14px;
        padding: 0.25rem;
        border: 1px solid rgba(255,255,255,0.06);
    }

    div[data-testid="stPopover"] > div button,
    div[data-testid="stButton"] > button,
    div[data-testid="baseButton-secondary"] {
        border-radius: 14px !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
    }

    .footer-note {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def _card_metric(label: str, value: str, sub: str = "") -> None:
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


def _card_insight(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">{title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _norm_full_tank(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"yes", "y", "true", "1", "full"}


@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        return None

    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def append_refuel_entry(
    entry_date: date,
    trip_km: float,
    liters: float,
    cost_rm: float,
    price_per_l: float,
    full_tank: str,
) -> None:
    client = get_gsheet_client()
    if client is None:
        raise RuntimeError("Google Sheets write mode is not configured.")

    if not EDIT_SHEET_URL:
        raise RuntimeError("Missing 'google_sheet_edit_url' in Streamlit secrets.")

    workbook = client.open_by_url(EDIT_SHEET_URL)
    try:
        worksheet = workbook.worksheet(WORKSHEET_NAME)
    except Exception:
        worksheet = workbook.sheet1

    worksheet.append_row(
        [
            entry_date.isoformat(),
            round(float(trip_km), 1),
            round(float(liters), 3),
            round(float(cost_rm), 2),
            round(float(price_per_l), 2),
            full_tank,
        ],
        value_input_option="USER_ENTERED",
    )


@st.cache_data(ttl=180)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower()

    required = {"date", "trip_km", "liters", "cost_rm", "price_per_l", "full_tank"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["trip_km", "liters", "cost_rm", "price_per_l"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["full_tank_flag"] = df["full_tank"].map(_norm_full_tank)
    df["full_tank_label"] = np.where(df["full_tank_flag"], "Full", "Partial")

    df = (
        df.dropna(subset=["date", "trip_km", "liters", "cost_rm", "price_per_l"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    df["consumption_l_100"] = (df["liters"] / df["trip_km"]) * 100
    df["cost_per_km"] = df["cost_rm"] / df["trip_km"]
    df["km_per_l"] = df["trip_km"] / df["liters"]

    df["days_since_prev"] = df["date"].diff().dt.days
    df["daily_km"] = df["trip_km"] / df["days_since_prev"].replace(0, np.nan)

    df["year"] = df["date"].dt.year.astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    df["rolling_consumption"] = df["consumption_l_100"].rolling(3, min_periods=1).mean()
    df["rolling_cost_km"] = df["cost_per_km"].rolling(3, min_periods=1).mean()

    # Stable score: 100 is very efficient, 55 is heavy
    score = 100 - ((df["consumption_l_100"] - 3.6) * 22)
    df["efficiency_score"] = score.clip(55, 100)

    q1 = df["consumption_l_100"].quantile(0.25)
    q3 = df["consumption_l_100"].quantile(0.75)
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    df["is_anomaly"] = (df["consumption_l_100"] < low) | (df["consumption_l_100"] > high)

    return df


def apply_window(df: pd.DataFrame, window: str) -> pd.DataFrame:
    if window == "Last 3":
        return df.tail(3).copy()
    if window == "Last 6":
        return df.tail(6).copy()
    if window == "YTD":
        latest_year = df["date"].max().year
        return df[df["date"].dt.year == latest_year].copy()
    return df.copy()


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


def predict_refill(df: pd.DataFrame, tank_capacity_l: float) -> dict:
    avg_cons = df["consumption_l_100"].tail(min(4, len(df))).mean()
    latest_trip = float(df.iloc[-1]["trip_km"])

    if pd.isna(avg_cons) or avg_cons <= 0:
        return {"range_km": np.nan, "remaining_km": np.nan, "days_left": np.nan, "date": None}

    est_range = tank_capacity_l / avg_cons * 100
    remaining_km = max(est_range - latest_trip, 0)

    pace = df["daily_km"].dropna().tail(5).mean()
    if pd.isna(pace) or pace <= 0:
        return {"range_km": est_range, "remaining_km": remaining_km, "days_left": np.nan, "date": None}

    days_left = remaining_km / pace
    next_date = df.iloc[-1]["date"] + timedelta(days=float(days_left))
    return {"range_km": est_range, "remaining_km": remaining_km, "days_left": days_left, "date": next_date}


def classify_efficiency(avg_cons: float) -> tuple[str, str]:
    if avg_cons <= 4.1:
        return "Excellent", "good"
    if avg_cons <= 4.8:
        return "Balanced", "info"
    return "Heavy", "warn"


def make_plotly_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        margin=dict(l=12, r=12, t=12, b=12),
        height=height,
        legend_title="",
        font=dict(color="#e5eefc"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)")
    return fig


def generate_tips(df: pd.DataFrame, latest_price: float) -> list[str]:
    tips = []
    latest = df.iloc[-1]
    avg_cons = df["consumption_l_100"].mean()

    if latest["consumption_l_100"] > avg_cons * 1.08:
        tips.append("Latest tank was less efficient than your norm. That usually points to traffic, more stop-start riding, or a heavier throttle hand.")
    else:
        tips.append("Latest tank is sitting nicely inside your normal efficiency band. Riding style looks consistent.")

    if latest_price >= 3.5:
        tips.append("Fuel price is now the main enemy. The easiest savings are combining errands and avoiding short low-value rides.")
    else:
        tips.append("Fuel price is not yet at panic level. Riding efficiency still has meaningful influence on total cost.")

    if (df["is_anomaly"]).sum() > 0:
        tips.append("There is at least one unusual tank in the data. Not a crisis — just worth reading as a special case rather than a trend.")
    else:
        tips.append("No major anomalies detected. Your log is coherent enough for the forecasts to be fairly trustworthy.")

    return tips[:3]


# =========================================================
# LOAD DATA
# =========================================================
df_all = load_data(PUBLIC_CSV_URL)

# =========================================================
# COMMAND DECK
# =========================================================
deck1, deck2, deck3, deck4 = st.columns([2.6, 1.2, 1.0, 1.0])

with deck1:
    window = st.segmented_control(
        "Window",
        options=["All", "Last 6", "Last 3", "YTD"],
        default="All",
        label_visibility="collapsed",
        width="stretch",
    )

with deck2:
    years = ["All"] + sorted(df_all["year"].unique().tolist())
    selected_year = st.selectbox("Year", years, index=0, label_visibility="collapsed")

with deck3:
    include_partial = st.toggle("Include partial", value=True)

with deck4:
    tank_capacity = st.slider("Tank", 10.0, 14.0, 11.0, 0.1, label_visibility="collapsed")

# Add refuel action
action1, action2, action3 = st.columns([1.15, 1.0, 5.0])

with action1:
    with st.popover("➕ Add refuel", use_container_width=True):
        st.markdown("### New entry")
        st.caption("Writes directly to your Google Sheet.")

        new_date = st.date_input("Date", value=date.today(), key="new_date")
        new_trip_km = st.number_input("Trip km", min_value=0.0, step=1.0, format="%.1f", key="new_trip_km")
        new_liters = st.number_input("Liters", min_value=0.0, step=0.001, format="%.3f", key="new_liters")
        new_cost = st.number_input("Cost (RM)", min_value=0.0, step=0.01, format="%.2f", key="new_cost")

        auto_price = round(new_cost / new_liters, 2) if new_liters > 0 else 0.0
        manual_price = st.number_input(
            "Price/L",
            min_value=0.0,
            step=0.01,
            value=float(auto_price),
            format="%.2f",
            key="new_price",
        )

        new_full = st.selectbox("Refill type", ["yes", "partial"], key="new_full")

        write_ready = ("gcp_service_account" in st.secrets) and bool(EDIT_SHEET_URL)
        if not write_ready:
            st.info("Read-only mode. Add `google_sheet_edit_url` and `gcp_service_account` in Streamlit secrets to enable writing.")

        if st.button("Save entry", use_container_width=True, disabled=not write_ready):
            if new_trip_km <= 0 or new_liters <= 0 or new_cost <= 0:
                st.error("Trip km, liters, and cost must all be above zero.")
            else:
                try:
                    append_refuel_entry(
                        entry_date=new_date,
                        trip_km=new_trip_km,
                        liters=new_liters,
                        cost_rm=new_cost,
                        price_per_l=manual_price,
                        full_tank=new_full,
                    )
                    st.cache_data.clear()
                    st.success("Entry saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save entry: {exc}")

with action2:
    if st.button("↻ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with action3:
    st.caption("Blackline mode: clean telemetry, forecasting, and live Google Sheets logging.")

# =========================================================
# FILTER DATA
# =========================================================
df = apply_window(df_all, window)

if selected_year != "All":
    df = df[df["year"] == selected_year].copy()

if not include_partial:
    df = df[df["full_tank_flag"]].copy()

if df.empty:
    st.error("No rows match the current filters.")
    st.stop()

monthly = build_monthly(df)
latest = df.iloc[-1]
best = df.loc[df["consumption_l_100"].idxmin()]
worst = df.loc[df["consumption_l_100"].idxmax()]
pred = predict_refill(df, tank_capacity)

avg_cons = df["consumption_l_100"].mean()
avg_cost_km = df["cost_per_km"].mean()
avg_km_l = df["km_per_l"].mean()
eff_score = df["efficiency_score"].mean()
latest_price = float(latest["price_per_l"])
status_label, status_class = classify_efficiency(avg_cons)

total_spent = df["cost_rm"].sum()
total_distance = df["trip_km"].sum()
total_liters = df["liters"].sum()

days_span = max((df["date"].max() - df["date"].min()).days, 1)
monthly_spend_est = (total_spent / days_span) * 30.44
liters_per_month_est = (total_liters / days_span) * 30.44
future_price = 3.87
future_monthly_cost = liters_per_month_est * future_price

tips = generate_tips(df, latest_price)

# =========================================================
# HERO
# =========================================================
st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">Motorbike Intelligence Console</div>
        <h1 class="hero-title">MT-25 Blackline</h1>
        <div class="hero-sub">
            Live fuel telemetry, trend reading, refill forecasting, and clean ride economics —
            all fed from your Google Sheet, not a dead CSV.
        </div>
        <div class="pillbar">
            <span class="pill {status_class}">Efficiency: {status_label}</span>
            <span class="pill info">Latest fuel: RM {latest_price:.2f}/L</span>
            <span class="pill">Entries: {len(df)}</span>
            <span class="pill">Average: {avg_cons:.2f} L/100km</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# TABS
# =========================================================
tab_overview, tab_trends, tab_costs, tab_logbook = st.tabs(
    ["Overview", "Trends", "Costs", "Logbook"]
)

# =========================================================
# OVERVIEW
# =========================================================
with tab_overview:
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        _card_metric("Average consumption", f"{avg_cons:.2f} L/100km", f"{avg_km_l:.2f} km/L")
    with m2:
        _card_metric("Average cost per km", f"RM {avg_cost_km:.3f}", f"Latest: RM {latest['cost_per_km']:.3f}/km")
    with m3:
        _card_metric("Estimated tank range", f"{pred['range_km']:.0f} km", f"Remaining now: {pred['remaining_km']:.0f} km")
    with m4:
        _card_metric("Estimated monthly spend", f"RM {monthly_spend_est:.0f}", f"What RM 3.87/L does: RM {future_monthly_cost:.0f}")
    with m5:
        next_refill_text = pred["date"].strftime("%d %b %Y") if pred["date"] is not None else "Need more pace data"
        next_refill_sub = f"In {pred['days_left']:.1f} days" if pd.notna(pred["days_left"]) else "Forecast still tentative"
        _card_metric("Predicted next refill", next_refill_text, next_refill_sub)

    c1, c2 = st.columns([1.35, 0.9])

    with c1:
        st.markdown('<div class="section-kicker">Core telemetry</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Consumption curve</div>', unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["consumption_l_100"],
                mode="lines+markers",
                name="Actual",
                line=dict(width=3),
                marker=dict(size=8),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["rolling_consumption"],
                mode="lines",
                name="3-tank rolling",
                line=dict(width=2, dash="dot"),
            )
        )
        fig = make_plotly_layout(fig, height=370)
        fig.update_yaxes(title="L/100km")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-kicker">Score</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Efficiency gauge</div>', unsafe_allow_html=True)

        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=eff_score,
                number={"suffix": "/100", "font": {"size": 34}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#5eead4"},
                    "bgcolor": "rgba(255,255,255,0.04)",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 60], "color": "rgba(251,113,133,0.22)"},
                        {"range": [60, 80], "color": "rgba(251,191,36,0.18)"},
                        {"range": [80, 100], "color": "rgba(52,211,153,0.20)"},
                    ],
                },
                title={"text": "Ride economy", "font": {"size": 18}},
            )
        )
        gauge = make_plotly_layout(gauge, height=370)
        st.plotly_chart(gauge, use_container_width=True)

    i1, i2, i3 = st.columns(3)
    with i1:
        _card_insight(
            "Latest tank verdict",
            f"Your latest tank came in at <b>{latest['consumption_l_100']:.2f} L/100km</b>, "
            f"versus an app average of <b>{avg_cons:.2f}</b>. "
            f"That is <b>{((latest['consumption_l_100'] / avg_cons) - 1) * 100:+.1f}%</b> versus your norm.",
        )
    with i2:
        refill_sentence = (
            f"Likely refill around <b>{pred['date'].strftime('%d %b %Y')}</b>, with about "
            f"<b>{pred['remaining_km']:.0f} km</b> left."
            if pred["date"] is not None
            else "Not enough stable pace data yet to pin a confident refill date."
        )
        _card_insight("Refill forecast", refill_sentence)
    with i3:
        anomaly_count = int(df["is_anomaly"].sum())
        _card_insight(
            "Anomaly watch",
            "No major anomalies detected. Your entries look coherent."
            if anomaly_count == 0
            else f"{anomaly_count} tank(s) sit outside your usual pattern. Read them as special cases, not the baseline.",
        )

    st.markdown('<div class="section-kicker">Advisor</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Useful tips</div>', unsafe_allow_html=True)
    tip_cols = st.columns(3)
    for idx, tip in enumerate(tips):
        with tip_cols[idx]:
            _card_insight(f"Tip {idx + 1}", tip)

# =========================================================
# TRENDS
# =========================================================
with tab_trends:
    t1, t2 = st.columns(2)

    with t1:
        st.markdown('<div class="section-kicker">Shape</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Trip length vs consumption</div>', unsafe_allow_html=True)

        scatter = px.scatter(
            df,
            x="trip_km",
            y="consumption_l_100",
            size="liters",
            color="is_anomaly",
            hover_data=["date", "cost_rm", "price_per_l", "full_tank_label"],
            opacity=0.9,
        )
        scatter = make_plotly_layout(scatter, height=380)
        scatter.update_layout(showlegend=False)
        scatter.update_xaxes(title="Trip km")
        scatter.update_yaxes(title="L/100km")
        st.plotly_chart(scatter, use_container_width=True)

    with t2:
        st.markdown('<div class="section-kicker">Performance</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Efficiency score timeline</div>', unsafe_allow_html=True)

        score_fig = px.area(
            df,
            x="date",
            y="efficiency_score",
        )
        score_fig = make_plotly_layout(score_fig, height=380)
        score_fig.update_yaxes(title="Score / 100", range=[50, 100])
        st.plotly_chart(score_fig, use_container_width=True)

    top_col, bottom_col = st.columns(2)
    with top_col:
        st.markdown('<div class="section-title">Top 5 most efficient tanks</div>', unsafe_allow_html=True)
        top5 = df.sort_values("consumption_l_100", ascending=True)[
            ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
        ].head(5).copy()
        top5["date"] = top5["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(top5, use_container_width=True, hide_index=True)

    with bottom_col:
        st.markdown('<div class="section-title">5 heaviest tanks</div>', unsafe_allow_html=True)
        bottom5 = df.sort_values("consumption_l_100", ascending=False)[
            ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
        ].head(5).copy()
        bottom5["date"] = bottom5["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(bottom5, use_container_width=True, hide_index=True)

# =========================================================
# COSTS
# =========================================================
with tab_costs:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-kicker">Pressure</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Monthly spending</div>', unsafe_allow_html=True)

        monthly_bar = px.bar(
            monthly,
            x="month",
            y="cost_rm",
            text_auto=".2f",
        )
        monthly_bar = make_plotly_layout(monthly_bar, height=380)
        monthly_bar.update_xaxes(title="")
        monthly_bar.update_yaxes(title="RM")
        st.plotly_chart(monthly_bar, use_container_width=True)

    with c2:
        st.markdown('<div class="section-kicker">Simulation</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Fuel price shock curve</div>', unsafe_allow_html=True)

        simulator = pd.DataFrame({"price_rm_l": np.round(np.linspace(2.0, 5.0, 13), 2)})
        simulator["monthly_cost_rm"] = simulator["price_rm_l"] * liters_per_month_est

        sim_fig = px.line(
            simulator,
            x="price_rm_l",
            y="monthly_cost_rm",
            markers=True,
        )
        sim_fig.add_vline(x=future_price, line_dash="dash")
        sim_fig = make_plotly_layout(sim_fig, height=380)
        sim_fig.update_xaxes(title="Fuel price (RM/L)")
        sim_fig.update_yaxes(title="Estimated monthly cost (RM)")
        st.plotly_chart(sim_fig, use_container_width=True)

    i1, i2, i3 = st.columns(3)
    with i1:
        _card_insight(
            "Current spend pace",
            f"Based on the tracked period, you are burning about <b>RM {monthly_spend_est:.0f}/month</b>."
        )
    with i2:
        _card_insight(
            "At RM 3.87/L",
            f"Your monthly fuel bill would move to about <b>RM {future_monthly_cost:.0f}</b>."
        )
    with i3:
        delta = future_monthly_cost - monthly_spend_est
        _card_insight(
            "Difference",
            f"That is a shift of about <b>{delta:+.0f} RM/month</b> from your current estimated pace."
        )

# =========================================================
# LOGBOOK
# =========================================================
with tab_logbook:
    st.markdown('<div class="section-kicker">Data</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Refuel logbook</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-body">This is the same data feeding the dashboard, with diagnostics added.</div>', unsafe_allow_html=True)

    display = df[
        [
            "date",
            "trip_km",
            "liters",
            "cost_rm",
            "price_per_l",
            "full_tank_label",
            "consumption_l_100",
            "cost_per_km",
            "km_per_l",
            "efficiency_score",
            "is_anomaly",
        ]
    ].copy()
    display["date"] = display["date"].dt.strftime("%Y-%m-%d")
    display.columns = [
        "date",
        "trip_km",
        "liters",
        "cost_rm",
        "price_per_l",
        "refill_type",
        "consumption_l_100",
        "cost_per_km",
        "km_per_l",
        "efficiency_score",
        "is_anomaly",
    ]

    st.dataframe(display, use_container_width=True, hide_index=True)

    csv_bytes = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered log as CSV",
        data=csv_bytes,
        file_name="mt25_filtered_log.csv",
        mime="text/csv",
        use_container_width=False,
    )

st.markdown(
    '<div class="footer-note">Write mode needs a real Google Sheet edit URL in secrets. '
    'The public published CSV keeps the dashboard read path simple and fast.</div>',
    unsafe_allow_html=True,
)
