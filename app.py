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
.card {
    background: rgba(255,255,255,0.95);
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header {
    font-size: 26px;
    font-weight: 700;
}
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
        cols = [
            "BASE (LOCAL LANGUAGE)", "GOOD LOCATION", "PART CODE", "TYPES",
            "MATERIAL DESCRIPTION (CHINA)", "GOOD QTY.", "DETAILS",
            "DEFECTIVE LOCATION", "DEFECTIVE QTY.",
            "TOOLS AND EQUIPMENT TOTAL", "REMARK1", "REMARK2"
        ]
        pd.DataFrame(columns=cols).to_excel(BUFFER_FILE, index=False)
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

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>📊 Tools & Equipments Dashboard</div></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))
    
    st.subheader("⚠️ LOW STOCK ALERT")
    low_stock_df = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low_stock_df, use_container_width=True)
    if not low_stock_df.empty:
        st.download_button("⬇ DOWNLOAD LOW STOCK", to_excel(low_stock_df), "LOW_STOCK.xlsx")
    
    st.subheader("RECENT ACTIVITY")
    recent_df = log_df.tail(10)
    st.dataframe(recent_df, use_container_width=True)
    if not recent_df.empty:
        st.download_button("⬇ DOWNLOAD RECENT ACTIVITY", to_excel(recent_df), "RECENT_ACTIVITY.xlsx")

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>📦 FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>➕ STOCK IN</h3></div>", unsafe_allow_html=True)
    
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    
    st.text_input("MATERIAL ASSIGNING BASE", row["BASE (LOCAL LANGUAGE)"], disabled=True)
    st.text_input("MATERIAL DESCRIPTION", row["MATERIAL DESCRIPTION (CHINA)"], disabled=True)
    st.text_input("TYPE", row["TYPES"], disabled=True)
    
    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK: {current}")
    
    qty = st.number_input("IN QTY", min_value=1, step=1)
    gate = st.text_input("GATE PASS NO")
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT_LIST)
    tat_remark = st.text_input("Delivery Remark") if tat=="Other" else ""
    applicant_option = st.selectbox("APPLICANT HOD", HOD_LIST)
    applicant = st.text_input("Enter Applicant HOD") if applicant_option=="Other" else applicant_option
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")
    
    if st.button("CONFIRM STOCK IN"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)
        
        log_df.loc[len(log_df)] = {
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": gate,
            "DELIVERY TAT": tat_remark if tat=="Other" else tat,
            "MATERIAL ASSIGNING BASE": row["BASE (LOCAL LANGUAGE)"],
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": qty,
            "OUT QTY": 0,
            "BALANCE": prev + qty,
            "APPLICANT HOD": applicant,
            "HANDOVER PERSON": OPERATOR_NAME,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": floor,
            "REMARK": remark,
            "USER": st.session_state.user
        }
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>➖ STOCK OUT</h3></div>", unsafe_allow_html=True)
    
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    
    st.text_input("MATERIAL ASSIGNING BASE", row["BASE (LOCAL LANGUAGE)"], disabled=True)
    st.text_input("MATERIAL DESCRIPTION", row["MATERIAL DESCRIPTION (CHINA)"], disabled=True)
    st.text_input("TYPE", row["TYPES"], disabled=True)
    
    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK: {current}")
    
    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        remove_enabled = True
    else:
        st.warning("⚠️ STOCK IS ZERO, CANNOT REMOVE")
        qty = 0
        remove_enabled = False

    gate = st.text_input("GATE PASS NO")
    applicant_option = st.selectbox("APPLICANT HOD", HOD_LIST)
    applicant = st.text_input("Enter Applicant HOD") if applicant_option=="Other" else applicant_option
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")
    
    if st.button("CONFIRM STOCK OUT") and remove_enabled:
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)
        
        log_df.loc[len(log_df)] = {
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": gate,
            "DELIVERY TAT": "",
            "MATERIAL ASSIGNING BASE": row["BASE (LOCAL LANGUAGE)"],
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": 0,
            "OUT QTY": qty,
            "BALANCE": prev - qty,
            "APPLICANT HOD": applicant,
            "HANDOVER PERSON": OPERATOR_NAME,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": floor,
            "REMARK": remark,
            "USER": st.session_state.user
        }
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ STOCK OUT UPDATED")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>📑 IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    if not log_df.empty:
        st.download_button("⬇ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
