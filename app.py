import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
from auth import authenticate
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM vFINAL",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.card {
    background:#ffffff;
    padding:25px;
    border-radius:16px;
    box-shadow:0 8px 25px rgba(0,0,0,0.12);
    margin-bottom:20px;
}
.header {
    font-size:26px;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTS
# =====================================================
OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Other"]

# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)
gc = gspread.authorize(creds)

buffer_ws = gc.open_by_key(
    st.secrets["google_sheets"]["buffer_sheet_id"]
).sheet1

log_ws = gc.open_by_key(
    st.secrets["google_sheets"]["inout_sheet_id"]
).sheet1

# =====================================================
# LOAD DATA
# =====================================================
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

buffer_df = load_buffer()
log_df = load_log()

# =====================================================
# LOGIN
# =====================================================
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

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# =====================================================
# DASHBOARD
# =====================================================
if menu == "DASHBOARD":
    st.markdown("""
    <div class="card">
        <div class="header">Tools & Equipment Dashboard</div>
        <hr>
        Confidential | Internal Use Only
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ LOW STOCK ALERT")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5], use_container_width=True)

    last_3_months = datetime.now() - DateOffset(months=3)
    cons = log_df[(log_df["DATE"] >= last_3_months) & (log_df["OUT QTY"] > 0)]
    summary = cons.groupby(
        ["PART CODE", "DESCRIPTION"], as_index=False
    )["OUT QTY"].sum()

    st.subheader("📉 LAST 3 MONTHS CONSUMPTION")
    st.dataframe(summary, use_container_width=True)

# =====================================================
# FULL BUFFER
# =====================================================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)

# =====================================================
# STOCK IN
# =====================================================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("IN QTY", min_value=1, step=1)
    gate = st.text_input("GATE PASS NO")
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT_LIST)
    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        buffer_ws.update(f"F{idx+2}", current + qty)

        log_ws.append_row([
            datetime.today().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            gate, tat, row["BASE (LOCAL LANGUAGE)"],
            row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"],
            part, current, qty, 0, current + qty,
            applicant, OPERATOR_NAME, OPERATOR_NAME,
            floor, remark, st.session_state.user
        ])

        st.success("✅ STOCK IN UPDATED")
        st.rerun()

# =====================================================
# STOCK OUT
# =====================================================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
    gate = st.text_input("GATE PASS NO")
    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("REMOVE STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        buffer_ws.update(f"F{idx+2}", current - qty)

        log_ws.append_row([
            datetime.today().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            gate, "OUT", row["BASE (LOCAL LANGUAGE)"],
            row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"],
            part, current, 0, qty, current - qty,
            applicant, OPERATOR_NAME, OPERATOR_NAME,
            floor, remark, st.session_state.user
        ])

        st.success("✅ STOCK OUT UPDATED")
        st.rerun()

# =====================================================
# REPORT
# =====================================================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
