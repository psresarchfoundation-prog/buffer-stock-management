import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM v3.4",
    layout="wide"
)

# ---------------- STYLE ----------------
st.markdown("""
<style>
.card {
    background: rgba(255,255,255,0.95);
    padding: 25px;
    border-radius: 16px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header { font-size: 28px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- FILE CONFIG ----------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

def download_drive(file_id, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={file_id}", path, quiet=False)

download_drive(BUFFER_FILE_ID, BUFFER_FILE)
download_drive(LOG_FILE_ID, LOG_FILE)

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
            st.experimental_rerun()
        else:
            st.error("❌ INVALID LOGIN")
    st.stop()

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_log():
    df = pd.read_excel(LOG_FILE)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    return df

buffer_df = load_buffer()
log_df = load_log()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")
menu = st.sidebar.radio("MENU", [
    "DASHBOARD","FULL BUFFER STOCK","STOCK IN","STOCK OUT","REPORT"
])

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.experimental_rerun()

# ---------------- DASHBOARD ----------------
if menu == "DASHBOARD":
    st.markdown("<div class='card header'>📊 Dashboard</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    low = buffer_df[buffer_df["GOOD QTY."] < 5]
    if low.empty:
        st.success("All stocks are sufficient ✅")
    else:
        st.warning("⚠ Low Stock Items")
        st.dataframe(low, use_container_width=True)

# ---------------- बाकी modules (STOCK IN / OUT / REPORT) 
# v2.3 वाला logic SAFE है — वही रखना 👍
