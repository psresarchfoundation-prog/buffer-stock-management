import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
from auth import authenticate
import os
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM vLocal",
    page_icon="📦",
    layout="wide"
)

# ---------------- STYLE ----------------
st.markdown("""
<style>
.card { background: rgba(255,255,255,0.95); padding: 22px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); margin-bottom: 20px; }
.header { font-size: 26px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- FILE CONFIG ----------------
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- CONSTANTS ----------------
OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Other"]

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
            st.error("❌ INVALID USER OR PASSWORD")
    st.stop()

# ---------------- LOAD DATA ----------------
def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        # --- Add initial sample row to avoid empty selectbox ---
        cols = [
            "BASE (LOCAL LANGUAGE)", "GOOD LOCATION", "PART CODE", "TYPES",
            "MATERIAL DESCRIPTION (CHINA)", "GOOD QTY.", "DETAILS",
            "DEFECTIVE LOCATION", "DEFECTIVE QTY.",
            "TOOLS AND EQUIPMENT TOTAL", "REMARK1", "REMARK2"
        ]
        # Sample initial row
        data = [{
            "BASE (LOCAL LANGUAGE)": "Base1",
            "GOOD LOCATION": "Loc1",
            "PART CODE": "P001",
            "TYPES": "TypeA",
            "MATERIAL DESCRIPTION (CHINA)": "Material A",
            "GOOD QTY.": 10,
            "DETAILS": "",
            "DEFECTIVE LOCATION": "",
            "DEFECTIVE QTY.": 0,
            "TOOLS AND EQUIPMENT TOTAL": 10,
            "REMARK1": "",
            "REMARK2": ""
        }]
        pd.DataFrame(data, columns=cols).to_excel(BUFFER_FILE, index=False)
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        cols = [
            "DATE","TIME","MONTH","WEEK",
            "GATE PASS NO","DELIVERY TAT","MATERIAL ASSIGNING BASE",
            "DESCRIPTION","TYPE","PART CODE",
            "PREVIOUS STOCK","IN QTY","OUT QTY","BALANCE",
            "APPLICANT HOD","HANDOVER PERSON","OPERATOR",
            "FLOOR","REMARK","USER"
        ]
        pd.DataFrame(columns=cols).to_excel(LOG_FILE, index=False)
    df = pd.read_excel(LOG_FILE)
    if not df.empty:
        df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
        df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    return df

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL DOWNLOAD ----------------
def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])
if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ------------------ DASHBOARD ------------------
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>📊 Tools & Equipments Dashboard</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum() if not log_df.empty else 0))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum() if not log_df.empty else 0))
    
    st.subheader("⚠️ LOW STOCK ALERT")
    if buffer_df.empty:
        st.info("Buffer stock is empty.")
    else:
        low_stock_df = buffer_df[buffer_df["GOOD QTY."] < 5]
        st.dataframe(low_stock_df, use_container_width=True)
        if not low_stock_df.empty:
            st.download_button("⬇ DOWNLOAD LOW STOCK", to_excel(low_stock_df), "LOW_STOCK.xlsx")
    
    st.subheader("RECENT ACTIVITY")
    if log_df.empty:
        st.info("No in/out logs yet.")
    else:
        recent_df = log_df.tail(10)
        st.dataframe(recent_df, use_container_width=True)
        st.download_button("⬇ DOWNLOAD RECENT ACTIVITY", to_excel(recent_df), "RECENT_ACTIVITY.xlsx")
