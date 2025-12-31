import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Buffer Stock Management System",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
body {background:#f5f7fa;}
.card {
    background:white;
    padding:20px;
    border-radius:14px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:16px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTS
# =====================================================
DELIVERY_TAT = ["Same Day", "24 Hours", "48 Hours", "72 Hours"]
APPLICANT_HOD = ["Rajkumar", "Ajay Kumar", "Sandeep Singh"]
HANDOVER_PERSON = ["Shekhar", "Rohit Verma", "Amit Yadav"]
DEFAULT_FLOOR = "L4"

# =====================================================
# FILE CONFIG
# =====================================================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

def drive_download(fid, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}", path, quiet=True)

drive_download(BUFFER_FILE_ID, BUFFER_FILE)
drive_download(LOG_FILE_ID, LOG_FILE)

# =====================================================
# DATA LOADERS (SAFE)
# =====================================================
def load_buffer():
    cols = [
        "PART CODE", "DESCRIPTION",
        "MATERIAL ASSIGNING BASE", "TYPE",
        "GOOD QTY."
    ]

    if not os.path.exists(BUFFER_FILE):
        return pd.DataFrame(columns=cols)

    df = pd.read_excel(BUFFER_FILE)
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df[cols]

def load_log():
    cols = [
        "DATE","MONTH","WEEK","SR NO",
        "DELIVERY TAT","MATERIAL ASSIGNING BASE",
        "DESCRIPTION","TYPE","PART CODE",
        "PREVIOUS STOCK","IN QTY","OUT QTY","BALANCE",
        "APPLICANT HOD","HANDOVER PERSON","USER",
        "FLOOR","REMARK","ENTRY BY"
    ]

    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=cols)

    df = pd.read_excel(LOG_FILE)
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    return df[cols]

def to_excel(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return bio.getvalue()

# =====================================================
# LOGIN
# =====================================================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.markdown("<div class='card'><h2>🔐 Login</h2></div>", unsafe_allow_html=True)
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
            st.error("❌ Invalid credentials")
    st.stop()

# =====================================================
# LOAD DATA
# =====================================================
buffer_df = load_buffer()
log_df = load_log()

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

if st.session_state.role == "READ":
    menu = st.sidebar.radio("MENU", ["DASHBOARD", "BUFFER", "REPORT"])
else:
    menu = st.sidebar.radio(
        "MENU",
        ["DASHBOARD", "BUFFER", "STOCK IN", "STOCK OUT", "REPORT"]
    )

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
if menu == "DASHBOARD":
    c1,c2,c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))
    st.dataframe(buffer_df, use_container_width=True)

# =====================================================
# BUFFER
# =====================================================
elif menu == "BUFFER":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ Download Buffer", to_excel(buffer_df), "buffer.xlsx")

# =====================================================
# STOCK IN
# =====================================================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"])
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    cur = int(row["GOOD QTY."])
    qty = st.number_input("IN QTY", min_value=1, step=1)

    if st.button("ADD STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1], "",
            "", row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, cur, qty, 0, cur+qty,
            "", "", st.session_state.user,
            DEFAULT_FLOOR, "", st.session_state.user
        ]
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ Stock Added")
        st.rerun()

# =====================================================
# STOCK OUT
# =====================================================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"])
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    cur = int(row["GOOD QTY."])

    qty = st.number_input("OUT QTY", min_value=1, max_value=cur)
    if st.button("REMOVE STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1], "",
            "", row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"], row["TYPE"],
            part, cur, 0, qty, cur-qty,
            "", "", st.session_state.user,
            DEFAULT_FLOOR, "", st.session_state.user
        ]
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ Stock Removed")
        st.rerun()

# =====================================================
# REPORT
# =====================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ Download Report", to_excel(log_df), "report.xlsx")
