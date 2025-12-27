import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v2.4", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.card {
    background: rgba(255,255,255,0.95);
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header { font-size: 26px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- FILE CONFIG ----------------
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- GOOGLE DRIVE CONFIG ----------------
BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

BUFFER_URL = f"https://drive.google.com/uc?id={BUFFER_FILE_ID}"
LOG_URL = f"https://drive.google.com/uc?id={LOG_FILE_ID}"

def download_from_drive(url, path):
    try:
        gdown.download(url, path, quiet=True)
    except:
        pass

download_from_drive(BUFFER_URL, BUFFER_FILE)
download_from_drive(LOG_URL, LOG_FILE)

# ---------------- LOAD DATA SAFE ----------------
def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return pd.DataFrame()
    df = pd.read_excel(BUFFER_FILE)
    if "GOOD QTY." in df.columns:
        df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    df = pd.read_excel(LOG_FILE)
    for c in ["IN QTY", "OUT QTY"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    return df

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL EXPORT ----------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ---------------- LOGIN ----------------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 LOGIN")
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
            st.error("❌ INVALID LOGIN")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])
if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    total_stock = int(buffer_df["GOOD QTY."].sum()) if not buffer_df.empty else 0
    total_in = int(log_df["IN QTY"].sum()) if not log_df.empty else 0
    total_out = int(log_df["OUT QTY"].sum()) if not log_df.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", total_stock)
    c2.metric("TOTAL IN", total_in)
    c3.metric("TOTAL OUT", total_out)

    st.subheader(⚠️ LOW STOCK ALERT")
    if not buffer_df.empty:
        low = buffer_df[buffer_df["GOOD QTY."] < 5]
        st.dataframe(low, use_container_width=True)
    else:
        st.info("No data found")

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>📦 FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇️ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>➕ STOCK IN</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    idx = buffer_df.index[buffer_df["PART CODE"] == part][0]

    qty = st.number_input("IN QTY", min_value=1, step=1)
    if st.button("ADD STOCK"):
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.now().strftime("%H:%M:%S"),
            part, prev, qty, 0, prev + qty, st.session_state.user
        ]
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>➖ STOCK OUT</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    idx = buffer_df.index[buffer_df["PART CODE"] == part][0]
    current = int(buffer_df.at[idx, "GOOD QTY."])

    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        if st.button("REMOVE STOCK"):
            buffer_df.at[idx, "GOOD QTY."] -= qty
            buffer_df.to_excel(BUFFER_FILE, index=False)

            log_df.loc[len(log_df)] = [
                datetime.today(), datetime.now().strftime("%H:%M:%S"),
                part, current, 0, qty, current - qty, st.session_state.user
            ]
            log_df.to_excel(LOG_FILE, index=False)
            st.success("✅ STOCK OUT UPDATED")
    else:
        st.warning("❌ STOCK ZERO")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>📑 IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇️ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
