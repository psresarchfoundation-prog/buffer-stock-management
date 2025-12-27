import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
from auth import authenticate
import os
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v2.2", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.card {
    background: rgba(255,255,255,0.92);
    padding: 25px;
    border-radius: 16px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header { font-size: 28px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEETS CONFIG ----------------
BUFFER_SHEET_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_SHEET_ID    = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

def sheet_csv_url(sheet_id):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

# ---------------- LOCAL FILE CONFIG (WRITE PURPOSE) ----------------
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Other"]

# ---------------- LOGIN ----------------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("LOGIN")
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

# ---------------- LOAD DATA FROM GOOGLE SHEETS ----------------
def load_buffer():
    try:
        df = pd.read_csv(sheet_csv_url(BUFFER_SHEET_ID))
    except:
        st.error("❌ BUFFER STOCK LOAD FAILED")
        return pd.DataFrame()

    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    try:
        df = pd.read_csv(sheet_csv_url(LOG_SHEET_ID))
    except:
        st.error("❌ IN / OUT LOG LOAD FAILED")
        return pd.DataFrame()

    df["IN QTY"]  = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    df["DATE"]    = pd.to_datetime(df["DATE"], errors="coerce")
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
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])
if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("""
    <div class="card">
        <div class="header">Tools & Equipments Report</div>
        <hr>
        <b>Confidentiality :</b> INTERNAL USE<br>
        <b>Owner :</b> 叶芳<br>
        <b>Prepared by :</b> 客户服务中心 CC<br>
        <b>Release Date :</b> 2024
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("LOW STOCK ALERT")
    low_stock_df = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low_stock_df, use_container_width=True)

    st.subheader("RECENT ACTIVITY")
    st.dataframe(log_df.tail(10), use_container_width=True)

    last_3_months = datetime.now() - DateOffset(months=3)
    cons_df = log_df[(log_df["DATE"] >= last_3_months) & (log_df["OUT QTY"] > 0)]
    summary = cons_df.groupby(
        ["PART CODE", "DESCRIPTION"], as_index=False
    )["OUT QTY"].sum().rename(
        columns={"OUT QTY": "TOTAL CONSUMPTION (LAST 3 MONTHS)"}
    )

    st.subheader("LAST 3 MONTHS MATERIAL CONSUMPTION")
    st.dataframe(summary, use_container_width=True)

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>STOCK IN</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    qty = st.number_input("IN QTY", min_value=1, step=1)

    if st.button("ADD STOCK"):
        row["GOOD QTY."] += qty
        st.success("✅ STOCK IN UPDATED (Google Sheet READ MODE)")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>STOCK OUT</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        if st.button("REMOVE STOCK"):
            st.success("✅ STOCK OUT UPDATED (Google Sheet READ MODE)")
    else:
        st.warning("❌ CURRENT STOCK IS ZERO")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
