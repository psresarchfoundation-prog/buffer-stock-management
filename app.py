import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
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
# GLOBAL STYLE
# =========================================================
st.markdown("""
<style>
body {background-color:#f5f7fa;}
.card {
    background:white;
    padding:22px;
    border-radius:14px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:16px;
}
.title {font-size:26px;font-weight:700;}
.metric {font-size:22px;font-weight:700;}
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
# FILE CONFIG
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
    st.markdown("<div class='card'><div class='title'>🔐 System Login</div></div>", unsafe_allow_html=True)
    user = st.selectbox("User", ["TSD", "HOD"])
    pwd = st.text_input("Password", type="password")

    if st.button("LOGIN"):
        ok, role = authenticate(user, pwd)
        if ok:
            st.session_state.login = True
            st.session_state.user = user
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
buffer_df = load_buffer()
log_df = load_log()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.success(st.session_state.user)
st.sidebar.info(f"Role : {st.session_state.role}")

menu = st.sidebar.radio("MENU", [
    "DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"
])

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# =========================================================
# DASHBOARD
# =========================================================
if menu == "DASHBOARD":

    st.markdown("<div class='card'><div class='title'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Stock", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("Total In", int(log_df["IN QTY"].sum()))
    c3.metric("Total Out", int(log_df["OUT QTY"].sum()))

    # ---------- SMART LOW STOCK (1 YEAR DEMAND) ----------
    st.markdown("### ⚠ Smart Low Stock Alert (1 Year Demand Based)")

    one_year_ago = pd.Timestamp.today() - DateOffset(years=1)
    demand_1y = log_df[
        (log_df["DATE"] >= one_year_ago) &
        (log_df["OUT QTY"] > 0)
    ]

    demand = (
        demand_1y.groupby("PART CODE", as_index=False)["OUT QTY"]
        .sum()
        .rename(columns={"OUT QTY": "YEAR_CONSUMPTION"})
    )

    demand["AVG_MONTHLY_CONSUMPTION"] = (demand["YEAR_CONSUMPTION"] / 12).round(2)

    merged = buffer_df.merge(demand, on="PART CODE", how="left").fillna(0)

    LEAD_TIME_MONTHS = 2
    merged["REORDER_LEVEL"] = (merged["AVG_MONTHLY_CONSUMPTION"] * LEAD_TIME_MONTHS).round(0)

    low_stock = merged[merged["GOOD QTY."] < merged["REORDER_LEVEL"]]

    if low_stock.empty:
        st.success("✅ No low stock risk based on last 1 year consumption")
    else:
        st.dataframe(
            low_stock[[
                "PART CODE", "DESCRIPTION", "GOOD QTY.",
                "AVG_MONTHLY_CONSUMPTION", "REORDER_LEVEL"
            ]],
            use_container_width=True
        )

    # ---------- LAST 3 MONTHS ----------
    st.markdown("### 📉 Last 3 Months Consumption")
    last3 = log_df[log_df["DATE"] >= pd.Timestamp.today() - DateOffset(months=3)]

    cons = (
        last3.groupby(["PART CODE"], as_index=False)["OUT QTY"]
        .sum()
        .rename(columns={"OUT QTY": "TOTAL CONSUMPTION"})
    )

    st.dataframe(cons if not cons.empty else pd.DataFrame(["No consumption data"]))

# =========================================================
# FULL BUFFER
# =========================================================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ Download Buffer Stock", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# =========================================================
# STOCK IN
# =========================================================
elif menu == "STOCK IN":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("In Quantity", min_value=1, step=1)
    tat = st.selectbox("Delivery TAT", DELIVERY_TAT)
    hod = st.selectbox("Applicant HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover Person", HANDOVER_PERSON)
    remark = st.text_area("Remark")

    if st.button("Confirm Stock In"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), "", "", "",
            tat, row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, current, qty, 0, current + qty,
            hod, hand, st.session_state.user,
            DEFAULT_FLOOR, remark, st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("Stock Added")
        st.rerun()

# =========================================================
# STOCK OUT
# =========================================================
elif menu == "STOCK OUT":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    if current <= 0:
        st.warning("No stock available")
        st.stop()

    qty = st.number_input("Out Quantity", min_value=1, max_value=current, step=1)
    tat = st.selectbox("Delivery TAT", DELIVERY_TAT)
    hod = st.selectbox("Applicant HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover Person", HANDOVER_PERSON)
    remark = st.text_area("Remark")

    if st.button("Confirm Stock Out"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), "", "", "",
            tat, row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, current, 0, qty, current - qty,
            hod, hand, st.session_state.user,
            DEFAULT_FLOOR, remark, st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("Stock Issued")
        st.rerun()

# =========================================================
# REPORT
# =========================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ Download Report", to_excel(log_df), "IN_OUT_REPORT.xlsx")
