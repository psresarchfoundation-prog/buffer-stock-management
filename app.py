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
    page_title="BUFFER STOCK MANAGEMENT SYSTEM v4.0",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# STYLE
# =====================================================
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

# =====================================================
# GOOGLE SHEET IDS
# =====================================================
BUFFER_SHEET_ID = "13XzWDCbuA7ZWZLyjezLCBm7oFxb35me6Z53RozF9yaE"
INOUT_SHEET_ID  = "12Hnk3k2D3JReYZnbsCYCbvIbTb23zfbE5UuuaEj4UTg"

# =====================================================
# GOOGLE AUTH (STREAMLIT CLOUD SAFE)
# =====================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)
client = gspread.authorize(creds)

buffer_ws = client.open_by_key(BUFFER_SHEET_ID).sheet1
log_ws    = client.open_by_key(INOUT_SHEET_ID).sheet1

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
            st.error("❌ INVALID USER OR PASSWORD")
    st.stop()

# =====================================================
# LOAD DATA
# =====================================================
def load_buffer():
    df = pd.DataFrame(buffer_ws.get_all_records())
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    df = pd.DataFrame(log_ws.get_all_records())
    df["IN QTY"]  = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    df["DATE"]    = pd.to_datetime(df["DATE"], errors="coerce")
    return df

def save_sheet(ws, df):
    ws.clear()
    ws.update([df.columns.tolist()] + df.astype(str).values.tolist())

buffer_df = load_buffer()
log_df    = load_log()

# =====================================================
# EXCEL DOWNLOAD
# =====================================================
def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

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
# CONSTANTS
# =====================================================
OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]

# =====================================================
# DASHBOARD
# =====================================================
if menu == "DASHBOARD":
    st.markdown("""
    <div class="card">
        <div class="header">📊 Tools & Equipments Dashboard</div>
        <hr>
        <b>Confidentiality :</b> INTERNAL USE<br>
        <b>Prepared by :</b> CC Department<br>
        <b>Year :</b> 2025
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠️ LOW STOCK ALERT")
    low_df = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low_df, use_container_width=True)

    st.subheader("🕒 RECENT IN / OUT (LAST 10)")
    recent_df = log_df.sort_values("DATE").tail(10)
    st.dataframe(recent_df, use_container_width=True)

    st.subheader("📉 LAST 3 MONTHS CONSUMPTION")
    last_3_months = datetime.now() - DateOffset(months=3)
    cons_df = log_df[(log_df["DATE"] >= last_3_months) & (log_df["OUT QTY"] > 0)]

    summary = (
        cons_df
        .groupby(["PART CODE", "DESCRIPTION"], as_index=False)["OUT QTY"]
        .sum()
        .rename(columns={"OUT QTY": "TOTAL CONSUMPTION"})
    )
    st.dataframe(summary, use_container_width=True)

# =====================================================
# FULL BUFFER
# =====================================================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>📦 FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# =====================================================
# STOCK IN
# =====================================================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>➕ STOCK IN</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    qty = st.number_input("IN QTY", min_value=1, step=1)
    remark = st.text_input("REMARK")

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] += qty
        save_sheet(buffer_ws, buffer_df)

        log_df.loc[len(log_df)] = [
            datetime.today().date(),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            "",
            "",
            row["BASE (LOCAL LANGUAGE)"],
            row["MATERIAL DESCRIPTION (CHINA)"],
            row["TYPES"],
            part,
            prev,
            qty,
            0,
            prev + qty,
            "",
            OPERATOR_NAME,
            OPERATOR_NAME,
            "",
            remark,
            st.session_state.user
        ]
        save_sheet(log_ws, log_df)
        st.success("✅ STOCK IN UPDATED")

# =====================================================
# STOCK OUT
# =====================================================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>➖ STOCK OUT</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
    remark = st.text_input("REMARK")

    if st.button("REMOVE STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] -= qty
        save_sheet(buffer_ws, buffer_df)

        log_df.loc[len(log_df)] = [
            datetime.today().date(),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            "",
            "",
            row["BASE (LOCAL LANGUAGE)"],
            row["MATERIAL DESCRIPTION (CHINA)"],
            row["TYPES"],
            part,
            prev,
            0,
            qty,
            prev - qty,
            "",
            OPERATOR_NAME,
            OPERATOR_NAME,
            "",
            remark,
            st.session_state.user
        ]
        save_sheet(log_ws, log_df)
        st.success("✅ STOCK OUT UPDATED")

# =====================================================
# REPORT
# =====================================================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>📑 IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
