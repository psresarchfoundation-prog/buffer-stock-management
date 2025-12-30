import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from auth import authenticate

# ================= PAGE CONFIG =================
st.set_page_config("BUFFER STOCK MANAGEMENT", layout="wide")

# ================= CONSTANTS =================
BUFFER_SHEET_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_SHEET_ID    = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"
OPERATOR_NAME = "Santosh Kumar"

# ================= GOOGLE AUTH =================
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)

client = get_client()

def safe_open(sheet_id):
    try:
        return client.open_by_key(sheet_id).sheet1
    except Exception as e:
        st.error("❌ Google Sheet Permission / ID Error")
        st.stop()

buffer_ws = safe_open(BUFFER_SHEET_ID)
log_ws    = safe_open(LOG_SHEET_ID)

# ================= LOAD DATA =================
def load_df(ws, cols):
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(data)

buffer_df = load_df(
    buffer_ws,
    ["PART CODE", "DESCRIPTION", "GOOD QTY."]
)
log_df = load_df(
    log_ws,
    ["DATE","TIME","MONTH","WEEK","PART CODE",
     "PREVIOUS STOCK","IN QTY","OUT QTY",
     "BALANCE","OPERATOR","USER"]
)

buffer_df["GOOD QTY."] = pd.to_numeric(buffer_df["GOOD QTY."], errors="coerce").fillna(0)
log_df["IN QTY"] = pd.to_numeric(log_df["IN QTY"], errors="coerce").fillna(0)
log_df["OUT QTY"] = pd.to_numeric(log_df["OUT QTY"], errors="coerce").fillna(0)
log_df["DATE"] = pd.to_datetime(log_df["DATE"], errors="coerce")

# ================= SAVE FUNCTIONS =================
def save_buffer(df):
    buffer_ws.clear()
    buffer_ws.update([df.columns.tolist()] + df.fillna("").values.tolist())

def append_log(row):
    log_ws.append_row(list(row.values()))

def to_excel(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return bio.getvalue()

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 LOGIN")
    u = st.selectbox("USER", ["TSD", "HOD"])
    p = st.text_input("PASSWORD", type="password")
    if st.button("LOGIN"):
        ok, role = authenticate(u, p)
        if ok:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = role
            st.rerun()
        else:
            st.error("❌ Invalid Login")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD","BUFFER","STOCK IN","STOCK OUT","REPORT"]
)

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    c1,c2,c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))
    st.dataframe(buffer_df, use_container_width=True)

# ================= BUFFER =================
elif menu == "BUFFER":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("DOWNLOAD BUFFER", to_excel(buffer_df), "buffer.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    if buffer_df.empty:
        st.warning("⚠️ Buffer sheet empty")
    else:
        part = st.selectbox("PART CODE", buffer_df["PART CODE"])
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        qty = st.number_input("IN QTY", min_value=1, step=1)
        if st.button("ADD"):
            prev = buffer_df.at[idx,"GOOD QTY."]
            buffer_df.at[idx,"GOOD QTY."] += qty
            save_buffer(buffer_df)
            append_log({
                "DATE": datetime.today().date(),
                "TIME": datetime.now().strftime("%H:%M:%S"),
                "MONTH": datetime.today().strftime("%B"),
                "WEEK": datetime.today().isocalendar()[1],
                "PART CODE": part,
                "PREVIOUS STOCK": prev,
                "IN QTY": qty,
                "OUT QTY": 0,
                "BALANCE": prev+qty,
                "OPERATOR": OPERATOR_NAME,
                "USER": st.session_state.user
            })
            st.success("✅ Stock Added")
            st.rerun()

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    if buffer_df.empty:
        st.warning("⚠️ Buffer sheet empty")
    else:
        part = st.selectbox("PART CODE", buffer_df["PART CODE"])
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        cur = int(buffer_df.at[idx,"GOOD QTY."])
        st.info(f"Current Stock : {cur}")
        if cur > 0:
            qty = st.number_input("OUT QTY", min_value=1, max_value=cur)
            if st.button("REMOVE"):
                buffer_df.at[idx,"GOOD QTY."] -= qty
                save_buffer(buffer_df)
                append_log({
                    "DATE": datetime.today().date(),
                    "TIME": datetime.now().strftime("%H:%M:%S"),
                    "MONTH": datetime.today().strftime("%B"),
                    "WEEK": datetime.today().isocalendar()[1],
                    "PART CODE": part,
                    "PREVIOUS STOCK": cur,
                    "IN QTY": 0,
                    "OUT QTY": qty,
                    "BALANCE": cur-qty,
                    "OPERATOR": OPERATOR_NAME,
                    "USER": st.session_state.user
                })
                st.success("✅ Stock Removed")
                st.rerun()

# ================= REPORT =================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("DOWNLOAD REPORT", to_excel(log_df), "report.xlsx")
