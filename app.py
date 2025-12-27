import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v3.5", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.card { background: rgba(255,255,255,0.92); padding: 25px; border-radius: 16px; box-shadow: 0 8px 25px rgba(0,0,0,0.12); margin-bottom: 20px;}
.header { font-size: 28px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEET AUTH ----------------
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
gc = gspread.authorize(creds)

# ---------------- SHEET LINKS ----------------
BUFFER_SHEET_URL = "YOUR_BUFFER_SHEET_URL_HERE"
LOG_SHEET_URL = "YOUR_LOG_SHEET_URL_HERE"

buffer_ws = gc.open_by_url(BUFFER_SHEET_URL).sheet1
log_ws = gc.open_by_url(LOG_SHEET_URL).sheet1

# ---------------- LOAD DATA ----------------
def load_buffer():
    df = get_as_dataframe(buffer_ws, evaluate_formulas=True).fillna("")
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."].fillna(0))
    return df

def load_log():
    df = get_as_dataframe(log_ws, evaluate_formulas=True).fillna("")
    df["IN QTY"] = pd.to_numeric(df["IN QTY"].fillna(0))
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"].fillna(0))
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
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
OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]

st.sidebar.success(f"OPERATOR : {OPERATOR_NAME}")
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])

# ---------------- DASHBOARD ----------------
if menu=="DASHBOARD":
    st.markdown("<div class='card'><div class='header'>Buffer Stock Dashboard</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))
    st.subheader("LOW STOCK ALERT (<5)")
    low_stock_df = buffer_df[buffer_df["GOOD QTY."]<5]
    st.dataframe(low_stock_df, use_container_width=True)
    st.download_button("DOWNLOAD LOW STOCK", to_excel(low_stock_df), "LOW_STOCK.xlsx")

# ---------------- FULL BUFFER ----------------
elif menu=="FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# ---------------- STOCK IN ----------------
elif menu=="STOCK IN":
    # [STOCK IN LOGIC HERE: Same as earlier code]

# ---------------- STOCK OUT ----------------
elif menu=="STOCK OUT":
    # [STOCK OUT LOGIC HERE: Same as earlier code]

# ---------------- REPORT ----------------
elif menu=="REPORT":
    st.markdown("<div class='card'><h3>IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
