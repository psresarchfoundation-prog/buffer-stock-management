import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from auth import authenticate

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v2.2", layout="wide")

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

# ---------------- CONSTANTS ----------------
BUFFER_SHEET_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_SHEET_ID    = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Other"]

# ---------------- GOOGLE AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

buffer_ws = client.open_by_key(BUFFER_SHEET_ID).sheet1
log_ws = client.open_by_key(LOG_SHEET_ID).sheet1

# ---------------- LOAD DATA ----------------
def load_buffer():
    df = pd.DataFrame(buffer_ws.get_all_records())
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    df = pd.DataFrame(log_ws.get_all_records())
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    return df

def save_buffer(df):
    buffer_ws.clear()
    buffer_ws.update([df.columns.values.tolist()] + df.values.tolist())

def append_log(row):
    log_ws.append_row(list(row.values()))

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL DOWNLOAD ----------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

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

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])
if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("LOW STOCK ALERT")
    low = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low, use_container_width=True)

    st.subheader("LAST 3 MONTHS CONSUMPTION")
    last_3 = datetime.now() - DateOffset(months=3)
    cons = log_df[(log_df["DATE"] >= last_3) & (log_df["OUT QTY"] > 0)]
    summary = cons.groupby("PART CODE", as_index=False)["OUT QTY"].sum()
    st.dataframe(summary, use_container_width=True)

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    qty = st.number_input("IN QTY", min_value=1, step=1)
    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] += qty
        save_buffer(buffer_df)

        append_log({
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": "",
            "DELIVERY TAT": "",
            "MATERIAL ASSIGNING BASE": row["BASE (LOCAL LANGUAGE)"],
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": qty,
            "OUT QTY": 0,
            "BALANCE": prev + qty,
            "APPLICANT HOD": "",
            "HANDOVER PERSON": OPERATOR_NAME,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": "",
            "REMARK": "",
            "USER": st.session_state.user
        })
        st.success("✅ STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("OUT QTY", min_value=1, max_value=current)
    if st.button("REMOVE STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] -= qty
        save_buffer(buffer_df)

        append_log({
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": "",
            "DELIVERY TAT": "",
            "MATERIAL ASSIGNING BASE": row["BASE (LOCAL LANGUAGE)"],
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": 0,
            "OUT QTY": qty,
            "BALANCE": prev - qty,
            "APPLICANT HOD": "",
            "HANDOVER PERSON": OPERATOR_NAME,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": "",
            "REMARK": "",
            "USER": st.session_state.user
        })
        st.success("✅ STOCK OUT UPDATED")

# ================= REPORT =================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
