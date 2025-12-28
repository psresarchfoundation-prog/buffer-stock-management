import streamlit as st
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
import gdown
from auth import authenticate

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Buffer Stock Management System",
    page_icon="📦",
    layout="wide"
)

# ======================================================
# STYLE
# ======================================================
st.markdown("""
<style>
body {background:#f4f6f9;}
.card {
    background:white;
    padding:20px;
    border-radius:12px;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
    margin-bottom:15px;
}
.title {font-size:26px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# CONSTANTS
# ======================================================
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

DELIVERY_TAT = ["Same Day", "24 Hours", "48 Hours", "72 Hours"]
APPLICANT_HOD = ["Rajkumar", "Ajay Kumar", "Sandeep Singh"]
HANDOVER_PERSON = ["Shekhar", "Rohit Verma", "Amit Yadav"]
DEFAULT_FLOOR = "L4"

os.makedirs(DATA_DIR, exist_ok=True)

# ======================================================
# DRIVE DOWNLOAD
# ======================================================
def drive_download(fid, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}", path, quiet=True)

drive_download(BUFFER_FILE_ID, BUFFER_FILE)
drive_download(LOG_FILE_ID, LOG_FILE)

# ======================================================
# REQUIRED COLUMNS
# ======================================================
BUFFER_COLS = [
    "PART CODE","MATERIAL ASSIGNING BASE",
    "DESCRIPTION","TYPE","GOOD QTY."
]

LOG_COLS = [
    "DATE","MONTH","WEEK","GATE PASS NO","DELIVERY TAT",
    "MATERIAL ASSIGNING BASE","DESCRIPTION","TYPE","PART CODE",
    "PREVIOUS STOCK","IN QTY","OUT QTY","BALANCE",
    "APPLICANT HOD","HANDOVER PERSON","OPERATOR",
    "FLOOR","REMARK","USER"
]

def ensure_columns(df, cols):
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df

# ======================================================
# LOAD DATA
# ======================================================
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df = ensure_columns(df, BUFFER_COLS)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0).astype(int)
    return df

def load_log():
    df = pd.read_excel(LOG_FILE)
    df = ensure_columns(df, LOG_COLS)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df[["IN QTY","OUT QTY","BALANCE"]] = df[["IN QTY","OUT QTY","BALANCE"]].fillna(0).astype(int)
    return df

def to_excel(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return bio.getvalue()

# ======================================================
# SAFE STOCK UPDATE
# ======================================================
def update_stock(part, qty, mode, meta):
    global buffer_df, log_df

    idx = buffer_df.index[buffer_df["PART CODE"] == part]
    if idx.empty:
        st.error("Invalid Part Code")
        return False

    i = idx[0]
    current = int(buffer_df.at[i, "GOOD QTY."])

    if mode == "OUT" and qty > current:
        st.error("❌ Insufficient Stock")
        return False

    new_qty = current + qty if mode == "IN" else current - qty
    buffer_df.at[i, "GOOD QTY."] = new_qty
    buffer_df.to_excel(BUFFER_FILE, index=False)

    log_df.loc[len(log_df)] = {
        "DATE": datetime.now(),
        "MONTH": datetime.now().strftime("%Y-%m"),
        "WEEK": datetime.now().isocalendar()[1],
        "GATE PASS NO": "",
        "DELIVERY TAT": meta["tat"],
        "MATERIAL ASSIGNING BASE": buffer_df.at[i, "MATERIAL ASSIGNING BASE"],
        "DESCRIPTION": buffer_df.at[i, "DESCRIPTION"],
        "TYPE": buffer_df.at[i, "TYPE"],
        "PART CODE": part,
        "PREVIOUS STOCK": current,
        "IN QTY": qty if mode == "IN" else 0,
        "OUT QTY": qty if mode == "OUT" else 0,
        "BALANCE": new_qty,
        "APPLICANT HOD": meta["hod"],
        "HANDOVER PERSON": meta["hand"],
        "OPERATOR": st.session_state.user,
        "FLOOR": DEFAULT_FLOOR,
        "REMARK": meta["remark"],
        "USER": st.session_state.user
    }

    log_df.to_excel(LOG_FILE, index=False)
    return True

# ======================================================
# LOGIN
# ======================================================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.markdown("<div class='card'><div class='title'>🔐 Login</div></div>", unsafe_allow_html=True)
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

# ======================================================
# LOAD DATA
# ======================================================
buffer_df = load_buffer()
log_df = load_log()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.success(st.session_state.user)
menu = st.sidebar.radio("MENU", [
    "DASHBOARD","FULL BUFFER STOCK","STOCK IN","STOCK OUT","REPORT"
])

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ======================================================
# DASHBOARD
# ======================================================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='title'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    c1.metric("Total Stock", buffer_df["GOOD QTY."].sum())
    c2.metric("Total In", log_df["IN QTY"].sum())
    c3.metric("Total Out", log_df["OUT QTY"].sum())

    st.markdown("### ⚠ Low Stock (<5)")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5], use_container_width=True)

# ======================================================
# FULL BUFFER
# ======================================================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ Download", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# ======================================================
# STOCK IN
# ======================================================
elif menu == "STOCK IN":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    current = int(buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."].iloc[0])
    st.info(f"Current Stock : {current}")

    qty = st.number_input("IN Quantity", min_value=1, step=1)
    tat = st.selectbox("Delivery TAT", DELIVERY_TAT)
    hod = st.selectbox("Applicant HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover Person", HANDOVER_PERSON)
    remark = st.text_area("Remark")

    if st.button("CONFIRM IN"):
        if update_stock(part, qty, "IN", {
            "tat": tat, "hod": hod, "hand": hand, "remark": remark
        }):
            st.success("Stock Added Successfully")
            st.rerun()

# ======================================================
# STOCK OUT
# ======================================================
elif menu == "STOCK OUT":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    current = int(buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."].iloc[0])
    st.info(f"Current Stock : {current}")

    if current <= 0:
        st.warning("No Stock Available")
        st.stop()

    qty = st.number_input("OUT Quantity", min_value=1, max_value=current, step=1)
    tat = st.selectbox("Delivery TAT", DELIVERY_TAT)
    hod = st.selectbox("Applicant HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover Person", HANDOVER_PERSON)
    remark = st.text_area("Remark")

    if st.button("CONFIRM OUT"):
        if update_stock(part, qty, "OUT", {
            "tat": tat, "hod": hod, "hand": hand, "remark": remark
        }):
            st.success("Stock Issued Successfully")
            st.rerun()

# ======================================================
# REPORT
# ======================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ Download Report", to_excel(log_df), "IN_OUT_REPORT.xlsx")
