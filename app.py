from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac
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
def pin_gate():
    if "app_pin" not in st.secrets:
        st.error("Missing `app_pin` in Streamlit secrets. Add it before deploying the app.")
        st.stop()

    expected_pin = str(st.secrets["app_pin"])
    st.session_state.setdefault("pin_status", "locked")
    st.session_state.setdefault("pin_buffer", "")

    def press_digit(digit: str):
        if len(st.session_state.pin_buffer) < 4:
            st.session_state.pin_buffer += digit

        if len(st.session_state.pin_buffer) == 4:
            check_pin()

    def clear_pin():
        st.session_state.pin_buffer = ""
        if st.session_state.pin_status == "incorrect":
            st.session_state.pin_status = "locked"

    def backspace():
        st.session_state.pin_buffer = st.session_state.pin_buffer[:-1]
        if st.session_state.pin_status == "incorrect":
            st.session_state.pin_status = "locked"

    def check_pin():
        entered = st.session_state.pin_buffer
        if len(entered) == 4 and hmac.compare_digest(entered, expected_pin):
            st.session_state.pin_status = "verified"
        else:
            st.session_state.pin_status = "incorrect"
        st.session_state.pin_buffer = ""

    def lock_page():
        st.session_state.pin_status = "locked"
        st.session_state.pin_buffer = ""

    if st.session_state.pin_status != "verified":
        st.markdown(
            """
            <style>
            .pin-shell {
                max-width: 360px;
                margin: 4rem auto 0 auto;
                padding: 1.5rem 1.2rem 1.2rem 1.2rem;
                border-radius: 28px;
                background: rgba(15, 23, 42, 0.72);
                border: 1px solid rgba(255,255,255,0.08);
                box-shadow: 0 20px 60px rgba(0,0,0,0.35);
                backdrop-filter: blur(14px);
                text-align: center;
            }
            .pin-title {
                font-size: 1.5rem;
                font-weight: 800;
                color: white;
                margin-bottom: 0.25rem;
            }
            .pin-sub {
                color: #94a3b8;
                font-size: 0.95rem;
                margin-bottom: 1rem;
            }
            .pin-dots {
                display: flex;
                justify-content: center;
                gap: 12px;
                margin: 0.8rem 0 1.2rem 0;
            }
            .pin-dot {
                width: 16px;
                height: 16px;
                border-radius: 999px;
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.08);
            }
            .pin-dot.filled {
                background: #67e8f9;
                box-shadow: 0 0 18px rgba(103,232,249,0.45);
            }
            div[data-testid="stButton"] > button {
                width: 100% !important;
                max-width: 78px !important;
                height: 72px !important;
                border-radius: 999px !important;
                font-size: 1.35rem !important;
                font-weight: 700 !important;
                margin: 0 auto !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                background: linear-gradient(180deg, rgba(30,41,59,0.95), rgba(15,23,42,0.98)) !important;
                color: white !important;
                box-shadow: 0 10px 28px rgba(0,0,0,0.22) !important;
            }
            div[data-testid="stButton"] > button:hover {
                border-color: rgba(103,232,249,0.35) !important;
                color: #67e8f9 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        entered_len = len(st.session_state.pin_buffer)
        dots = "".join(
            f'<div class="pin-dot {"filled" if i < entered_len else ""}"></div>'
            for i in range(4)
        )

        st.markdown(
            f"""
            <div class="pin-shell">
                <div class="pin-title">🔐 Enter PIN</div>
                <div class="pin-sub">4-digit access code</div>
                <div class="pin-dots">{dots}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.pin_status == "incorrect":
            st.error("Incorrect PIN")

        rows = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["C", "0", "⌫"],
        ]

        for row_index, row in enumerate(rows):
            left_pad, keypad, right_pad = st.columns([1.4, 1.1, 1.4], gap="small")
            with keypad:
                cols = st.columns(3, gap="small")
                for col, label in zip(cols, row):
                    with col:
                        key = f"pin_btn_{row_index}_{label}"
                        if label == "C":
                            st.button(label, key=key, on_click=clear_pin, use_container_width=True)
                        elif label == "⌫":
                            st.button(label, key=key, on_click=backspace, use_container_width=True)
                        else:
                            st.button(label, key=key, on_click=press_digit, args=(label,), use_container_width=True)

        st.stop()

    st.button("Lock page", on_click=lock_page, key="lock_page_btn")


pin_gate()

PUBLIC_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQtOfkiFAYIV9uubiLi8RAmMSj5mKDBxY9iEeOCGXjN5p7TVjPbmGOdSA-pIpDeC1ajS-y0yVDwAJ1m/"
    "pub?gid=1859833030&single=true&output=csv"
)
LOCAL_CSV_PATH = Path("mt25_fuel_log.csv")
APP_TIMEZONE = st.secrets["app_timezone"] if "app_timezone" in st.secrets else "Asia/Kuala_Lumpur"

EDIT_SHEET_URL = st.secrets["google_sheet_edit_url"] if "google_sheet_edit_url" in st.secrets else ""
WORKSHEET_NAME = st.secrets["worksheet_name"] if "worksheet_name" in st.secrets else "Sheet1"
MAINTENANCE_WORKSHEET_NAME = (
    st.secrets["maintenance_worksheet_name"] if "maintenance_worksheet_name" in st.secrets else "maintenance_log"
)

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
        --button-bg: linear-gradient(180deg, rgba(22, 36, 57, 0.96), rgba(11, 19, 34, 0.98));
        --button-bg-hover: linear-gradient(180deg, rgba(31, 48, 74, 0.98), rgba(14, 25, 42, 1));
        --button-bg-active: linear-gradient(180deg, rgba(54, 90, 132, 0.96), rgba(23, 41, 68, 1));
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

    .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 220px;
        gap: 1rem;
        align-items: center;
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

    .oil-signal-card {
        position: relative;
        z-index: 1;
        justify-self: end;
        width: 220px;
        padding: 1rem 1rem 0.9rem 1rem;
        border-radius: 22px;
        border: 1px solid rgba(255,255,255,0.08);
        background: linear-gradient(180deg, rgba(8, 15, 29, 0.92), rgba(10, 20, 36, 0.86));
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 20px 40px rgba(0,0,0,0.28);
    }

    .oil-signal-head {
        color: var(--muted);
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.65rem;
    }

    .oil-signal-layout {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .oil-signal-body {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }

    .oil-signal-label {
        color: var(--text);
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    .oil-signal-copy {
        color: #dbeafe;
        font-size: 0.84rem;
        line-height: 1.35;
    }

    .signal-stack {
        width: 54px;
        padding: 0.48rem 0.45rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(6,10,18,0.96), rgba(16,24,36,0.98));
        border: 1px solid rgba(255,255,255,0.08);
        display: flex;
        flex-direction: column;
        gap: 0.42rem;
        box-shadow: inset 0 1px 1px rgba(255,255,255,0.04);
    }

    .signal-dot {
        width: 100%;
        aspect-ratio: 1 / 1;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: inset 0 -8px 18px rgba(0,0,0,0.28);
    }

    .signal-dot.green.active {
        background: radial-gradient(circle at 35% 30%, #bbf7d0 0%, #4ade80 28%, #15803d 78%);
        box-shadow: 0 0 18px rgba(74, 222, 128, 0.35);
    }

    .signal-dot.orange.active {
        background: radial-gradient(circle at 35% 30%, #fde68a 0%, #f59e0b 26%, #b45309 78%);
        box-shadow: 0 0 18px rgba(245, 158, 11, 0.35);
    }

    .signal-dot.red.active {
        background: radial-gradient(circle at 35% 30%, #fecaca 0%, #ef4444 24%, #b91c1c 78%);
        box-shadow: 0 0 18px rgba(239, 68, 68, 0.35);
    }

    @media (max-width: 900px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .oil-signal-card {
            justify-self: stretch;
            width: auto;
        }
    }

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

    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stPopover"] button,
    button[kind="secondary"],
    button[kind="tertiary"] {
        background: var(--button-bg) !important;
        color: var(--text) !important;
        border: 1px solid rgba(148, 163, 184, 0.22) !important;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22) !important;
        transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease, color 0.18s ease;
    }

    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button,
    div[data-testid="stPopover"] button,
    button[kind="secondary"],
    button[kind="tertiary"] {
        border-radius: 14px !important;
    }

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover,
    div[data-testid="stPopover"] button:hover,
    button[kind="secondary"]:hover,
    button[kind="tertiary"]:hover {
        background: var(--button-bg-hover) !important;
        color: #ffffff !important;
        border-color: rgba(103, 232, 249, 0.38) !important;
        transform: translateY(-1px);
    }

    div[data-testid="stButton"] > button:focus-visible,
    div[data-testid="stDownloadButton"] > button:focus-visible,
    div[data-testid="stPopover"] button:focus-visible,
    button[kind="secondary"]:focus-visible,
    button[kind="tertiary"]:focus-visible {
        outline: 2px solid rgba(103, 232, 249, 0.75) !important;
        outline-offset: 2px !important;
    }

    div[data-testid="stButton"] > button:disabled,
    div[data-testid="stDownloadButton"] > button:disabled,
    div[data-testid="stPopover"] button:disabled,
    button[kind="secondary"]:disabled,
    button[kind="tertiary"]:disabled {
        color: rgba(226, 232, 240, 0.45) !important;
        background: linear-gradient(180deg, rgba(20, 27, 38, 0.85), rgba(12, 17, 28, 0.88)) !important;
        border-color: rgba(148, 163, 184, 0.10) !important;
        box-shadow: none !important;
        transform: none !important;
    }

    div[data-testid="stSegmentedControl"] button {
        color: #d6e2f0 !important;
        border-radius: 11px !important;
        min-height: 2.5rem;
    }

    div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
        background: var(--button-bg-active) !important;
        color: #ffffff !important;
        border: 1px solid rgba(103, 232, 249, 0.28) !important;
    }

    div[data-testid="stSegmentedControl"] button[aria-pressed="false"] {
        background: transparent !important;
        color: #cbd5e1 !important;
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


def _fmt_number(value: float, spec: str, fallback: str = "--") -> str:
    if pd.isna(value) or not np.isfinite(value):
        return fallback
    return format(float(value), spec)


def _now_local() -> datetime:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).replace(tzinfo=None)


def _secret_date(name: str, fallback: date) -> date:
    if name not in st.secrets:
        return fallback

    try:
        return pd.to_datetime(str(st.secrets[name])).date()
    except Exception:
        return fallback


def _secret_float(name: str, fallback: float) -> float:
    if name not in st.secrets:
        return fallback

    try:
        return float(st.secrets[name])
    except Exception:
        return fallback


def _secret_int(name: str, fallback: int) -> int:
    if name not in st.secrets:
        return fallback

    try:
        return int(st.secrets[name])
    except Exception:
        return fallback


def _norm_full_tank(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"yes", "y", "true", "1", "full"}


def _norm_service_type(value: object) -> str:
    return str(value).strip().lower().replace("-", " ").replace("_", " ")


def _is_oil_service(value: object) -> bool:
    text = _norm_service_type(value)
    return any(token in text for token in {"oil", "engine oil"})


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

    valid_numeric = (
        df["trip_km"].gt(0)
        & df["liters"].gt(0)
        & df["cost_rm"].gt(0)
        & df["price_per_l"].gt(0)
    )
    dropped_invalid_rows = int((~valid_numeric).sum())

    df["full_tank_flag"] = df["full_tank"].map(_norm_full_tank)
    df["full_tank_label"] = np.where(df["full_tank_flag"], "Full", "Partial")

    df = (
        df.dropna(subset=["date", "trip_km", "liters", "cost_rm", "price_per_l"])
        .loc[valid_numeric]
        .sort_values("date")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError("No valid rows remain after cleaning the fuel log.")

    df["measurement_ready"] = False
    df["measurement_trip_km"] = np.nan
    df["measurement_liters"] = np.nan
    df["measurement_cost_rm"] = np.nan
    df["days_since_prev_full"] = np.nan
    df["consumption_l_100"] = np.nan
    df["cost_per_km"] = np.nan
    df["km_per_l"] = np.nan
    df["daily_km"] = np.nan
    df["rolling_consumption"] = np.nan
    df["rolling_cost_km"] = np.nan
    df["efficiency_score"] = np.nan
    df["is_anomaly"] = False

    pending_trip_km = 0.0
    pending_liters = 0.0
    pending_cost_rm = 0.0
    last_full_date = None

    for idx, row in df.iterrows():
        pending_trip_km += float(row["trip_km"])
        pending_liters += float(row["liters"])
        pending_cost_rm += float(row["cost_rm"])

        if row["full_tank_flag"]:
            df.at[idx, "measurement_ready"] = True
            df.at[idx, "measurement_trip_km"] = pending_trip_km
            df.at[idx, "measurement_liters"] = pending_liters
            df.at[idx, "measurement_cost_rm"] = pending_cost_rm

            if last_full_date is not None:
                df.at[idx, "days_since_prev_full"] = (row["date"] - last_full_date).days

            pending_trip_km = 0.0
            pending_liters = 0.0
            pending_cost_rm = 0.0
            last_full_date = row["date"]

    measurement_mask = df["measurement_ready"]
    df.loc[measurement_mask, "consumption_l_100"] = (
        df.loc[measurement_mask, "measurement_liters"] / df.loc[measurement_mask, "measurement_trip_km"]
    ) * 100
    df.loc[measurement_mask, "cost_per_km"] = (
        df.loc[measurement_mask, "measurement_cost_rm"] / df.loc[measurement_mask, "measurement_trip_km"]
    )
    df.loc[measurement_mask, "km_per_l"] = (
        df.loc[measurement_mask, "measurement_trip_km"] / df.loc[measurement_mask, "measurement_liters"]
    )
    df.loc[measurement_mask, "daily_km"] = (
        df.loc[measurement_mask, "measurement_trip_km"]
        / df.loc[measurement_mask, "days_since_prev_full"].replace(0, np.nan)
    )

    df["year"] = df["date"].dt.year.astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    if measurement_mask.any():
        df.loc[measurement_mask, "rolling_consumption"] = (
            df.loc[measurement_mask, "consumption_l_100"].rolling(3, min_periods=1).mean().to_numpy()
        )
        df.loc[measurement_mask, "rolling_cost_km"] = (
            df.loc[measurement_mask, "cost_per_km"].rolling(3, min_periods=1).mean().to_numpy()
        )

        # Stable score: 100 is very efficient, 55 is heavy
        score = 100 - ((df.loc[measurement_mask, "consumption_l_100"] - 3.6) * 22)
        df.loc[measurement_mask, "efficiency_score"] = score.clip(55, 100).to_numpy()

        measured_consumption = df.loc[measurement_mask, "consumption_l_100"]
        q1 = measured_consumption.quantile(0.25)
        q3 = measured_consumption.quantile(0.75)
        iqr = q3 - q1
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        df.loc[measurement_mask, "is_anomaly"] = (
            (measured_consumption < low) | (measured_consumption > high)
        ).to_numpy()

    df.attrs["dropped_invalid_rows"] = dropped_invalid_rows

    return df


def load_primary_data() -> tuple[pd.DataFrame, str, list[str]]:
    attempts = [
        ("Published Google Sheet CSV", PUBLIC_CSV_URL),
        ("Local CSV backup", str(LOCAL_CSV_PATH)),
    ]
    errors = []

    for index, (label, source) in enumerate(attempts):
        try:
            df = load_data(source)
            notices = []
            dropped_invalid_rows = int(df.attrs.get("dropped_invalid_rows", 0))
            if dropped_invalid_rows:
                notices.append(
                    f"Ignored {dropped_invalid_rows} row(s) with missing or non-positive numeric values."
                )
            if index > 0:
                notices.insert(0, "Published Google Sheet CSV is unavailable, so the dashboard is using the local backup file.")
            return df, label, notices
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    raise RuntimeError(" | ".join(errors))


@st.cache_data(ttl=180)
def load_maintenance_data() -> tuple[pd.DataFrame, str]:
    empty = pd.DataFrame(
        columns=["date", "odo_km", "service_type", "details", "warning_km", "due_km", "due_days"]
    )

    client = get_gsheet_client()
    if client is None or not EDIT_SHEET_URL:
        return empty, "No Google Sheets write access configured"

    try:
        workbook = client.open_by_url(EDIT_SHEET_URL)
        worksheet = workbook.worksheet(MAINTENANCE_WORKSHEET_NAME)
    except Exception as exc:
        return empty, f"Could not read `{MAINTENANCE_WORKSHEET_NAME}`: {exc}"

    records = worksheet.get_all_records()
    if not records:
        return empty, f"`{MAINTENANCE_WORKSHEET_NAME}` is empty"

    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip().str.lower()

    if "date" not in df.columns or "service_type" not in df.columns:
        return empty, f"`{MAINTENANCE_WORKSHEET_NAME}` needs at least `date` and `service_type` columns"

    if "odo_km" not in df.columns:
        df["odo_km"] = np.nan
    if "details" not in df.columns:
        df["details"] = ""
    if "warning_km" not in df.columns:
        df["warning_km"] = np.nan
    if "due_km" not in df.columns:
        df["due_km"] = df["interval_km"] if "interval_km" in df.columns else np.nan
    if "due_days" not in df.columns:
        df["due_days"] = df["interval_days"] if "interval_days" in df.columns else np.nan

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["odo_km", "warning_km", "due_km", "due_days"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df.dropna(subset=["date", "service_type"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    return df[["date", "odo_km", "service_type", "details", "warning_km", "due_km", "due_days"]], "Loaded from maintenance log"


def get_latest_oil_service(maintenance_df: pd.DataFrame) -> pd.Series | None:
    if maintenance_df.empty:
        return None

    oil_rows = maintenance_df[maintenance_df["service_type"].map(_is_oil_service)].copy()
    if oil_rows.empty:
        return None
    return oil_rows.sort_values("date").iloc[-1]


def compute_km_since_service(fuel_df: pd.DataFrame, service_date: date, service_odo_km: float) -> tuple[float, str]:
    service_ts = pd.Timestamp(service_date)
    future_fills = fuel_df[fuel_df["date"] >= service_ts].sort_values("date").copy()

    if future_fills.empty:
        return 0.0, "No completed refuel has been logged since that service date yet."

    first_fill = future_fills.iloc[0]
    first_cycle_distance = float(first_fill["trip_km"])

    if pd.isna(service_odo_km):
        km_after_service_in_first_cycle = first_cycle_distance
        note = "Maintenance log is missing `odo_km`, so the first post-service tank is counted in full."
    else:
        km_after_service_in_first_cycle = max(first_cycle_distance - float(service_odo_km), 0.0)
        note = (
            "Distance since service is measured from the maintenance log `odo_km` inside the active fuel cycle."
        )

    later_km = float(future_fills.iloc[1:]["trip_km"].sum())
    return km_after_service_in_first_cycle + later_km, note


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
            measured_trip_km=("measurement_trip_km", "sum"),
            measured_liters=("measurement_liters", "sum"),
        )
    )
    monthly["km_per_l"] = monthly["measured_trip_km"] / monthly["measured_liters"]
    return monthly


def predict_refill(df: pd.DataFrame, latest_entry: pd.Series, tank_capacity_l: float) -> dict:
    if not bool(latest_entry["full_tank_flag"]):
        return {
            "range_km": np.nan,
            "remaining_km": np.nan,
            "days_left": np.nan,
            "date": None,
            "reason": "Latest entry is a partial refill",
        }

    avg_cons = df["consumption_l_100"].tail(min(4, len(df))).mean()

    if pd.isna(avg_cons) or avg_cons <= 0:
        return {
            "range_km": np.nan,
            "remaining_km": np.nan,
            "days_left": np.nan,
            "date": None,
            "reason": "Need more complete tanks",
        }

    est_range = tank_capacity_l / avg_cons * 100

    pace = df["daily_km"].dropna().tail(5).mean()
    if pd.isna(pace) or pace <= 0:
        return {
            "range_km": est_range,
            "remaining_km": est_range,
            "days_left": np.nan,
            "date": None,
            "reason": "Need more pace data",
        }

    refill_at = latest_entry["date"].to_pydatetime()
    now_local = _now_local()
    total_days_to_refill = est_range / pace
    next_date = refill_at + timedelta(days=float(total_days_to_refill))
    elapsed_days = max((now_local - refill_at).total_seconds() / 86400, 0.0)
    remaining_km = max(est_range - (pace * elapsed_days), 0.0)
    days_left = max((next_date - now_local).total_seconds() / 86400, 0.0)

    reason = ""
    if days_left == 0.0:
        reason = "Forecast says refill is due now"

    return {
        "range_km": est_range,
        "remaining_km": remaining_km,
        "days_left": days_left,
        "date": next_date,
        "reason": reason,
    }


def classify_efficiency(avg_cons: float) -> tuple[str, str]:
    if avg_cons <= 4.1:
        return "Excellent", "good"
    if avg_cons <= 4.8:
        return "Balanced", "info"
    return "Heavy", "warn"


def classify_oil_service(
    km_since: float,
    warning_km: float,
    due_km: float,
    days_left: int | None,
) -> tuple[str, str, str]:
    due_reasons = []
    if km_since >= due_km:
        due_reasons.append("distance limit reached")
    if days_left is not None and days_left <= 0:
        due_reasons.append("time interval reached")

    if due_reasons:
        detail = " and ".join(due_reasons).capitalize() + "."
        return "Overdue", "warn", detail

    if km_since >= warning_km:
        return "Due soon", "info", "Early warning threshold reached. Plan the oil change soon."

    if days_left is not None and days_left <= 30:
        return "Due soon", "info", "Time interval is getting close."
    return "On track", "good", "Oil service is comfortably inside the next maintenance window."


def predict_oil_due_date(km_left: float, pace_km_day: float, reference_dt: datetime) -> datetime | None:
    if km_left <= 0:
        return reference_dt
    if pd.isna(pace_km_day) or pace_km_day <= 0:
        return None
    return reference_dt + timedelta(days=float(km_left / pace_km_day))


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
try:
    df_all, data_source_label, data_notices = load_primary_data()
except Exception as exc:
    st.error(f"Could not load dashboard data: {exc}")
    st.stop()

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
    st.caption(f"Data source: {data_source_label}. Blackline mode: clean telemetry, forecasting, and live Google Sheets logging.")

for notice in data_notices:
    st.warning(notice)

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
latest_entry = df.iloc[-1]
analysis_df = df[df["measurement_ready"]].copy()

if analysis_df.empty:
    st.error("This selection has no completed full-tank cycles yet, so telemetry metrics cannot be calculated.")
    st.stop()

latest = analysis_df.iloc[-1]
pred = predict_refill(analysis_df, latest_entry, tank_capacity)

avg_cons = analysis_df["consumption_l_100"].mean()
avg_cost_km = analysis_df["cost_per_km"].mean()
avg_km_l = analysis_df["km_per_l"].mean()
eff_score = analysis_df["efficiency_score"].mean()
latest_price = float(latest_entry["price_per_l"])
status_label, status_class = classify_efficiency(avg_cons)

total_spent = df["cost_rm"].sum()
total_distance = df["trip_km"].sum()
total_liters = df["liters"].sum()

days_span = max((df["date"].max() - df["date"].min()).days, 1)
monthly_spend_est = (total_spent / days_span) * 30.44
liters_per_month_est = (total_liters / days_span) * 30.44
future_price = 3.87
future_monthly_cost = liters_per_month_est * future_price

tips = generate_tips(analysis_df, latest_price)
maintenance_df, maintenance_source_status = load_maintenance_data()
latest_oil_service = get_latest_oil_service(maintenance_df)

today_local = _now_local().date()
latest_log_date = df_all["date"].max().date()

st.session_state.setdefault(
    "oil_change_date",
    _secret_date("oil_change_date", latest_log_date),
)
st.session_state.setdefault(
    "oil_warning_km",
    _secret_float("oil_warning_km", 3000.0),
)
st.session_state.setdefault(
    "oil_due_km",
    _secret_float("oil_due_km", _secret_float("oil_interval_km", 4000.0)),
)
st.session_state.setdefault(
    "oil_due_days",
    _secret_int("oil_due_days", _secret_int("oil_interval_days", 180)),
)

oil_warning_km = max(float(st.session_state["oil_warning_km"]), 100.0)
oil_due_km = max(float(st.session_state["oil_due_km"]), oil_warning_km + 100.0)
oil_due_days = max(int(st.session_state["oil_due_days"]), 30)
oil_source_label = "Manual settings"
oil_service_note = "Using manual oil tracking settings."

if latest_oil_service is not None:
    oil_change_date = latest_oil_service["date"].date()
    if pd.notna(latest_oil_service["warning_km"]):
        oil_warning_km = max(float(latest_oil_service["warning_km"]), 100.0)
    if pd.notna(latest_oil_service["due_km"]):
        oil_due_km = max(float(latest_oil_service["due_km"]), oil_warning_km + 100.0)
    if pd.notna(latest_oil_service["due_days"]):
        oil_due_days = max(int(latest_oil_service["due_days"]), 30)

    oil_km_since, oil_service_note = compute_km_since_service(
        df_all,
        oil_change_date,
        latest_oil_service["odo_km"],
    )
    oil_source_label = "Maintenance log"
else:
    oil_change_date = st.session_state["oil_change_date"]
    oil_change_ts = pd.Timestamp(oil_change_date)
    oil_km_since = float(df_all.loc[df_all["date"] > oil_change_ts, "trip_km"].sum())

oil_days_since = max((today_local - oil_change_date).days, 0)
oil_warning_left = oil_warning_km - oil_km_since
oil_km_left = oil_due_km - oil_km_since
oil_days_left = oil_due_days - oil_days_since
oil_due_date = oil_change_date + timedelta(days=oil_due_days)
oil_status_label, oil_status_class, oil_status_detail = classify_oil_service(
    oil_km_since,
    oil_warning_km,
    oil_due_km,
    oil_days_left,
)
oil_warning_date = predict_oil_due_date(
    oil_warning_left,
    analysis_df["daily_km"].dropna().tail(5).mean(),
    _now_local(),
)
oil_km_due_date = predict_oil_due_date(
    oil_km_left,
    analysis_df["daily_km"].dropna().tail(5).mean(),
    _now_local(),
)
oil_next_trigger = None
oil_next_trigger_label = "Need more pace data"
trigger_candidates = []
if oil_warning_left > 0 and oil_warning_date is not None:
    trigger_candidates.append((oil_warning_date, "Predicted early warning"))
elif oil_km_left > 0 and oil_km_due_date is not None:
    trigger_candidates.append((oil_km_due_date, "Predicted change due"))

trigger_candidates.append((datetime.combine(oil_due_date, datetime.min.time()), "Calendar trigger"))

if trigger_candidates:
    oil_next_trigger, oil_next_trigger_label = min(trigger_candidates, key=lambda item: item[0])

oil_signal_state = "green"
oil_signal_label = "Oil OK"
oil_signal_copy = f"{oil_km_since:.0f} km since change"
if oil_km_since >= oil_due_km:
    oil_signal_state = "red"
    oil_signal_label = "Change Now"
    oil_signal_copy = f"{abs(oil_km_left):.0f} km overdue"
elif oil_km_since >= oil_warning_km:
    oil_signal_state = "orange"
    oil_signal_label = "Plan Service"
    oil_signal_copy = f"{oil_km_left:.0f} km until change"

# =========================================================
# HERO
# =========================================================
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-grid">
            <div>
                <div class="eyebrow">Motorbike Intelligence Console</div>
                <h1 class="hero-title">MT-25 Blackline</h1>
                <div class="hero-sub">
                    Live fuel telemetry, trend reading, refill forecasting, and clean ride economics —
                    all fed from your Google Sheet, not a dead CSV.
                </div>
                <div class="pillbar">
                    <span class="pill {status_class}">Efficiency: {status_label}</span>
                    <span class="pill info">Latest fuel: RM {latest_price:.2f}/L</span>
                    <span class="pill">Entries: {len(df)} | Completed tanks: {len(analysis_df)}</span>
                    <span class="pill">Average: {avg_cons:.2f} L/100km</span>
                </div>
            </div>
            <div class="oil-signal-card">
                <div class="oil-signal-head">Oil Watch</div>
                <div class="oil-signal-layout">
                    <div class="signal-stack">
                        <div class="signal-dot red {"active" if oil_signal_state == "red" else ""}"></div>
                        <div class="signal-dot orange {"active" if oil_signal_state == "orange" else ""}"></div>
                        <div class="signal-dot green {"active" if oil_signal_state == "green" else ""}"></div>
                    </div>
                    <div class="oil-signal-body">
                        <div class="oil-signal-label">{oil_signal_label}</div>
                        <div class="oil-signal-copy">{oil_signal_copy}</div>
                        <div class="micro-note">Warn at {oil_warning_km:.0f} km, due at {oil_due_km:.0f} km</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# TABS
# =========================================================
tab_overview, tab_trends, tab_costs, tab_maintenance, tab_logbook = st.tabs(
    ["Overview", "Trends", "Costs", "Maintenance", "Logbook"]
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
        _card_metric(
            "Estimated tank range",
            f"{_fmt_number(pred['range_km'], '.0f')} km",
            f"Remaining now: {_fmt_number(pred['remaining_km'], '.0f')} km",
        )
    with m4:
        _card_metric("Estimated monthly spend", f"RM {monthly_spend_est:.0f}", f"What RM 3.87/L does: RM {future_monthly_cost:.0f}")
    with m5:
        next_refill_text = pred["date"].strftime("%d %b %Y") if pred["date"] is not None else "Forecast pending"
        if pred["reason"]:
            next_refill_sub = pred["reason"]
        elif pd.notna(pred["days_left"]):
            next_refill_sub = f"In {pred['days_left']:.1f} days"
        else:
            next_refill_sub = "Forecast still tentative"
        _card_metric("Predicted next refill", next_refill_text, next_refill_sub)

    c1, c2 = st.columns([1.35, 0.9])

    with c1:
        st.markdown('<div class="section-kicker">Core telemetry</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Consumption curve</div>', unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=analysis_df["date"],
                y=analysis_df["consumption_l_100"],
                mode="lines+markers",
                name="Actual",
                line=dict(width=3),
                marker=dict(size=8),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=analysis_df["date"],
                y=analysis_df["rolling_consumption"],
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
            f"Your latest completed tank came in at <b>{latest['consumption_l_100']:.2f} L/100km</b>, "
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
        anomaly_count = int(analysis_df["is_anomaly"].sum())
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

    st.markdown('<div class="section-kicker">Maintenance</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Oil service snapshot</div>', unsafe_allow_html=True)
    service_cols = st.columns(3)
    with service_cols[0]:
        _card_insight(
            "Oil status",
            f"<b>{oil_status_label}</b><br>{oil_status_detail}<br><span class=\"micro-note\">Source: {oil_source_label}</span>",
        )
    with service_cols[1]:
        warn_line = (
            f"<b>{oil_warning_left:.0f} km until warning</b>"
            if oil_warning_left >= 0
            else f"<b>{abs(oil_warning_left):.0f} km past warning</b>"
        )
        _card_insight(
            "Early warning",
            f"{warn_line}<br>Tracked since {oil_change_date.isoformat()}: <b>{oil_km_since:.0f} km</b>.<br>"
            f"<span class=\"micro-note\">{oil_service_note}</span>",
        )
    with service_cols[2]:
        due_line = (
            f"<b>{oil_km_left:.0f} km until change</b>"
            if oil_km_left >= 0
            else f"<b>{abs(oil_km_left):.0f} km overdue</b>"
        )
        _card_insight(
            "Change due",
            f"{due_line}<br>Calendar due: <b>{oil_due_date.strftime('%d %b %Y')}</b>.",
        )

# =========================================================
# TRENDS
# =========================================================
with tab_trends:
    t1, t2 = st.columns(2)

    with t1:
        st.markdown('<div class="section-kicker">Shape</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Trip length vs consumption</div>', unsafe_allow_html=True)

        scatter = px.scatter(
            analysis_df,
            x="measurement_trip_km",
            y="consumption_l_100",
            size="measurement_liters",
            color="is_anomaly",
            hover_data=["date", "measurement_cost_rm", "price_per_l"],
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
            analysis_df,
            x="date",
            y="efficiency_score",
        )
        score_fig = make_plotly_layout(score_fig, height=380)
        score_fig.update_yaxes(title="Score / 100", range=[50, 100])
        st.plotly_chart(score_fig, use_container_width=True)

    top_col, bottom_col = st.columns(2)
    with top_col:
        st.markdown('<div class="section-title">Top 5 most efficient tanks</div>', unsafe_allow_html=True)
        top5 = analysis_df.sort_values("consumption_l_100", ascending=True)[
            ["date", "measurement_trip_km", "measurement_liters", "measurement_cost_rm", "consumption_l_100", "efficiency_score"]
        ].head(5).copy()
        top5["date"] = top5["date"].dt.strftime("%Y-%m-%d")
        top5.columns = ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
        st.dataframe(top5, use_container_width=True, hide_index=True)

    with bottom_col:
        st.markdown('<div class="section-title">5 heaviest tanks</div>', unsafe_allow_html=True)
        bottom5 = analysis_df.sort_values("consumption_l_100", ascending=False)[
            ["date", "measurement_trip_km", "measurement_liters", "measurement_cost_rm", "consumption_l_100", "efficiency_score"]
        ].head(5).copy()
        bottom5["date"] = bottom5["date"].dt.strftime("%Y-%m-%d")
        bottom5.columns = ["date", "trip_km", "liters", "cost_rm", "consumption_l_100", "efficiency_score"]
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
# MAINTENANCE
# =========================================================
with tab_maintenance:
    st.markdown('<div class="section-kicker">Service</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Oil change monitor</div>', unsafe_allow_html=True)
    body_text = (
        "Oil changes are read from the maintenance worksheet when available. "
        "Distance is tracked from the fuel log, so this works best when the log covers all riding."
    )
    if latest_oil_service is None:
        body_text = (
            "No oil change entry was found in the maintenance worksheet yet, so the tracker is using manual fallback settings. "
            "Distance is tracked from the fuel log, so this works best when the log covers all riding."
        )
    st.markdown(f'<div class="section-body">{body_text}</div>', unsafe_allow_html=True)
    st.caption(f"Oil source: {oil_source_label}. Maintenance worksheet status: {maintenance_source_status}.")

    if latest_oil_service is None:
        setup1, setup2, setup3, setup4 = st.columns(4)
        with setup1:
            st.date_input("Last oil change", key="oil_change_date")
        with setup2:
            st.number_input(
                "Early warning (km)",
                min_value=100.0,
                step=100.0,
                format="%.0f",
                key="oil_warning_km",
            )
        with setup3:
            st.number_input(
                "Change due (km)",
                min_value=200.0,
                step=100.0,
                format="%.0f",
                key="oil_due_km",
            )
        with setup4:
            st.number_input(
                "Calendar due (days)",
                min_value=30,
                step=30,
                key="oil_due_days",
            )
    else:
        setup1, setup2, setup3 = st.columns(3)
        with setup1:
            st.number_input(
                "Early warning (km)",
                min_value=100.0,
                step=100.0,
                format="%.0f",
                key="oil_warning_km",
            )
        with setup2:
            st.number_input(
                "Change due (km)",
                min_value=200.0,
                step=100.0,
                format="%.0f",
                key="oil_due_km",
            )
        with setup3:
            st.number_input(
                "Calendar due (days)",
                min_value=30,
                step=30,
                key="oil_due_days",
            )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        _card_metric("Oil service status", oil_status_label, oil_status_detail)
    with m2:
        _card_metric("Oil km since change", f"{oil_km_since:.0f} km", f"Service date: {oil_change_date.strftime('%d %b %Y')}")
    with m3:
        warn_value = f"{oil_warning_left:.0f} km" if oil_warning_left >= 0 else f"{abs(oil_warning_left):.0f} km past"
        _card_metric("Early warning", warn_value, f"Warning threshold: {oil_warning_km:.0f} km")
    with m4:
        next_trigger_text = oil_next_trigger.strftime("%d %b %Y") if oil_next_trigger is not None else "Need more pace data"
        _card_metric("Next oil trigger", next_trigger_text, oil_next_trigger_label)

    i1, i2, i3 = st.columns(3)
    with i1:
        base_text = (
            f"Last oil change is coming from <b>{oil_source_label}</b> on <b>{oil_change_date.strftime('%d %b %Y')}</b>."
        )
        if latest_oil_service is not None and pd.notna(latest_oil_service["odo_km"]):
            base_text += f" Logged `odo_km` at service: <b>{latest_oil_service['odo_km']:.1f} km</b>."
        _card_insight(
            "Service baseline",
            f"{base_text}<br>Warning at <b>{oil_warning_km:.0f} km</b>, change due at <b>{oil_due_km:.0f} km</b>, "
            f"calendar due at <b>{oil_due_days} days</b>.",
        )
    with i2:
        trigger_parts = []
        if oil_warning_date is not None and oil_warning_left > 0:
            trigger_parts.append(
                f"Early warning projects to about <b>{oil_warning_date.strftime('%d %b %Y')}</b>."
            )
        if oil_km_due_date is not None and oil_km_left > 0:
            trigger_parts.append(
                f"Change due projects to about <b>{oil_km_due_date.strftime('%d %b %Y')}</b>."
            )
        if not trigger_parts:
            trigger_parts.append("Not enough stable riding pace yet to predict the remaining distance triggers.")
        _card_insight("Distance triggers", " ".join(trigger_parts))
    with i3:
        log_note = (
            f"Fuel log currently runs through <b>{latest_log_date.strftime('%d %b %Y')}</b>. "
            f"If you have ridden since then, the tracked oil kilometers may be understated. "
            f"The maintenance log assumes `odo_km` means the trip reading inside the current fuel cycle when the service happened."
        )
        _card_insight("Tracking note", log_note)

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
