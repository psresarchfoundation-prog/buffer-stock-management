import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v2.3", layout="wide")

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
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- GOOGLE DRIVE CONFIG ----------------
BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

BUFFER_URL = f"https://drive.google.com/uc?id={BUFFER_FILE_ID}"
LOG_URL = f"https://drive.google.com/uc?id={LOG_FILE_ID}"

def download_from_drive(url, path):
    if not os.path.exists(path):
        gdown.download(url, path, quiet=True)

download_from_drive(BUFFER_URL, BUFFER_FILE)
download_from_drive(LOG_URL, LOG_FILE)

# ---------------- CONSTANT ----------------
OPERATOR_NAME = "Santosh Kumar"

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

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_log():
    df = pd.read_excel(LOG_FILE)
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    return df

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL DOWNLOAD ----------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("📥 TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("📤 TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ LOW STOCK ALERT")
    low = buffer_df[buffer_df["GOOD QTY."] < 5]
    if low.empty:
        st.success("All stocks are sufficient ✅")
    else:
        st.dataframe(low, use_container_width=True)

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>📦 FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>➕ STOCK IN</h3></div>", unsafe_allow_html=True)

    parts = buffer_df["PART CODE"].dropna().unique()
    if len(parts) == 0:
        st.warning("No PART CODE found")
        st.stop()

    part = st.selectbox("PART CODE", parts)
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    st.info(f"CURRENT STOCK : {int(row['GOOD QTY.'])}")
    qty = st.number_input("IN QTY", min_value=1, step=1)

    if st.button("ADD STOCK"):
        idx = buffer_df.index[buffer_df["PART CODE"] == part][0]
        prev = buffer_df.at[idx, "GOOD QTY."]

        buffer_df.at[idx, "GOOD QTY."] = prev + qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"), datetime.today().isocalendar()[1],
            "", "", "", row.get("MATERIAL DESCRIPTION (CHINA)", ""),
            row.get("TYPES", ""), part, prev, qty, 0, prev + qty,
            "", OPERATOR_NAME, OPERATOR_NAME, "", "", st.session_state.user
        ]
        log_df.to_excel(LOG_FILE, index=False)

        st.cache_data.clear()
        st.success("✅ STOCK IN UPDATED")
        st.rerun()

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>➖ STOCK OUT</h3></div>", unsafe_allow_html=True)

    parts = buffer_df["PART CODE"].dropna().unique()
    part = st.selectbox("PART CODE", parts)

    idx = buffer_df.index[buffer_df["PART CODE"] == part][0]
    current = int(buffer_df.at[idx, "GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    if current <= 0:
        st.error("❌ STOCK ZERO")
        st.stop()

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)

    if st.button("REMOVE STOCK"):
        buffer_df.at[idx, "GOOD QTY."] = current - qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        row = buffer_df.loc[idx]
        log_df.loc[len(log_df)] = [
            datetime.today(), datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"), datetime.today().isocalendar()[1],
            "", "", "", row.get("MATERIAL DESCRIPTION (CHINA)", ""),
            row.get("TYPES", ""), part, current, 0, qty, current - qty,
            "", OPERATOR_NAME, OPERATOR_NAME, "", "", st.session_state.user
        ]
        log_df.to_excel(LOG_FILE, index=False)

        st.cache_data.clear()
        st.success("✅ STOCK OUT UPDATED")
        st.rerun()

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>📑 IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
