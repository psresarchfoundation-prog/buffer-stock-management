import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Buffer Stock Management System",
    page_icon="📦",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
body {background:#f4f6f9;}
.card {
    background:white;
    padding:20px;
    border-radius:14px;
    box-shadow:0 6px 20px rgba(0,0,0,0.08);
    margin-bottom:18px;
}
.header {font-size:26px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# =========================================================
# MASTER DATA
# =========================================================
DELIVERY_TAT = ["Same Day", "24 Hours", "48 Hours", "72 Hours"]
APPLICANT_HOD = ["Rajkumar", "Ajay Kumar", "Sandeep Singh"]
HANDOVER_PERSON = ["Shekhar", "Rohit Verma", "Amit Yadav"]
DEFAULT_FLOOR = "L4"

# =========================================================
# FILE CONFIG (NO DATA LOSS)
# =========================================================
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

def drive_download(fid, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}", path, quiet=True)

drive_download(BUFFER_FILE_ID, BUFFER_FILE)
drive_download(LOG_FILE_ID, LOG_FILE)

# =========================================================
# DATA FUNCTIONS
# =========================================================
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    df = pd.read_excel(LOG_FILE)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    return df

def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return out.getvalue()

# =========================================================
# LOGIN
# =========================================================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.markdown("<div class='card'><div class='header'>🔐 LOGIN</div></div>", unsafe_allow_html=True)
    user = st.selectbox("USER", ["TSD", "HOD"])
    pwd = st.text_input("PASSWORD", type="password")

    if st.button("LOGIN"):
        ok, role = authenticate(user, pwd)
        if ok:
            st.session_state.login = True
            st.session_state.user = user
            st.session_state.role = role
            st.rerun()
        else:
            st.error("INVALID LOGIN")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
buffer_df = load_buffer()
log_df = load_log()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# =========================================================
# DASHBOARD (FULLY UPDATED)
# =========================================================
if menu == "DASHBOARD":

    st.markdown("<div class='card'><div class='header'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("📥 TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("📤 TOTAL OUT", int(log_df["OUT QTY"].sum()))

    # ---------- LOW STOCK ----------
    st.markdown("### ⚠ Low Stock Alert (Below 5)")
    low_stock = buffer_df[buffer_df["GOOD QTY."] < 5][
        ["PART CODE", "DESCRIPTION", "MATERIAL ASSIGNING BASE", "GOOD QTY."]
    ]
    st.dataframe(low_stock if not low_stock.empty else pd.DataFrame(["All stock OK"]),
                 use_container_width=True)

    # ---------- LAST 3 MONTH CONSUMPTION ----------
    st.markdown("### 📉 Last 3 Months Consumption")
    last3 = log_df[
        log_df["DATE"] >= pd.Timestamp.today() - pd.DateOffset(months=3)
    ]

    consumption_3m = (
        last3
        .groupby(["PART CODE", "MATERIAL ASSIGNING BASE"], as_index=False)
        ["OUT QTY"]
        .sum()
        .rename(columns={"OUT QTY": "TOTAL CONSUMPTION (LAST 3 MONTHS)"})
    )

    st.dataframe(consumption_3m if not consumption_3m.empty else pd.DataFrame(["No data"]),
                 use_container_width=True)

    st.download_button(
        "⬇ Download All Part Stock",
        to_excel(buffer_df),
        "ALL_PART_STOCK.xlsx"
    )

    # ---------- DATE WISE OUT ----------
    st.markdown("### 📅 Date Wise OUT Consumption (Last 3 Months)")
    day_wise_out = (
        last3
        .groupby([last3["DATE"].dt.date, "PART CODE"], as_index=False)
        ["OUT QTY"]
        .sum()
        .rename(columns={"OUT QTY": "DAY WISE OUT"})
    )

    st.dataframe(day_wise_out, use_container_width=True)

    st.download_button(
        "📥 Download Date Wise OUT Consumption",
        to_excel(day_wise_out),
        "DATE_WISE_OUT_CONSUMPTION.xlsx"
    )

# =========================================================
# FULL BUFFER STOCK
# =========================================================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# =========================================================
# STOCK IN
# =========================================================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    st.info(f"CURRENT STOCK : {current}")
    qty = st.number_input("IN QTY", min_value=1, step=1)
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT)
    hod = st.selectbox("APPLICANT HOD", APPLICANT_HOD)
    hand = st.selectbox("HANDOVER PERSON", HANDOVER_PERSON)
    remark = st.text_area("REMARK")

    if st.button("✅ ADD STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1], "",
            tat, row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, current, qty, 0, current + qty,
            hod, hand, st.session_state.user,
            DEFAULT_FLOOR, remark, st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("STOCK IN SUCCESS")
        st.rerun()

# =========================================================
# STOCK OUT
# =========================================================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    st.info(f"CURRENT STOCK : {current}")
    if current <= 0:
        st.warning("NO STOCK AVAILABLE")
        st.stop()

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT)
    hod = st.selectbox("APPLICANT HOD", APPLICANT_HOD)
    hand = st.selectbox("HANDOVER PERSON", HANDOVER_PERSON)
    remark = st.text_area("REMARK")

    if st.button("❌ REMOVE STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1], "",
            tat, row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, current, 0, qty, current - qty,
            hod, hand, st.session_state.user,
            DEFAULT_FLOOR, remark, st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("STOCK OUT SUCCESS")
        st.rerun()

# =========================================================
# REPORT
# =========================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
