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
    page_title="BUFFER STOCK MANAGEMENT SYSTEM vFINAL+",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# CONSTANTS
# =====================================================
OPERATOR_NAME = "Santosh Kumar"

HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
HANDOVER_LIST = ["Santosh Kumar", "Store", "Security", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
REMARK_LIST = ["Routine Use", "Replacement", "New Requirement", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Next Day", "Other"]

LOW_STOCK_DEFAULT = 10

# =====================================================
# GOOGLE SHEETS
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
    if "LOW STOCK" not in df.columns:
        df["LOW STOCK"] = LOW_STOCK_DEFAULT
    return df

def load_log():
    df = pd.DataFrame(log_ws.get_all_records())
    if df.empty:
        return df
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
menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

# =====================================================
# DASHBOARD
# =====================================================
if menu == "DASHBOARD":

    st.metric("📦 TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))

    low_stock = buffer_df[buffer_df["GOOD QTY."] <= buffer_df["LOW STOCK"]]
    st.subheader("⚠ LOW STOCK MATERIAL ALERT")
    st.dataframe(low_stock, use_container_width=True)

    last_3_months = datetime.now() - DateOffset(months=3)
    cons = log_df[(log_df["DATE"] >= last_3_months) & (log_df["OUT QTY"] > 0)]

    summary = cons.groupby(
        ["MATERIAL ASSIGNING BASE", "DESCRIPTION", "TYPE", "PART CODE"],
        as_index=False
    )["OUT QTY"].sum()

    st.subheader("📉 LAST 3 MONTHS CONSUMPTION")
    st.dataframe(summary, use_container_width=True)

# =====================================================
# FULL BUFFER STOCK
# =====================================================
elif menu == "FULL BUFFER STOCK":

    st.dataframe(buffer_df, use_container_width=True)

    # EXPORT
    output = BytesIO()
    buffer_df.to_excel(output, index=False)
    st.download_button(
        "⬇ Download Buffer Stock Excel",
        output.getvalue(),
        "buffer_stock.xlsx"
    )

# =====================================================
# COMMON DATE
# =====================================================
today = datetime.today()
DATE = today.strftime("%Y-%m-%d")
MONTH = today.strftime("%B")
WEEK = today.isocalendar()[1]

# =====================================================
# STOCK IN
# =====================================================
elif menu == "STOCK IN":

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    st.info(f"📦 CURRENT STOCK : {current}")

    qty = st.number_input("IN QTY", min_value=1, step=1)
    gate = st.text_input("GATE PASS NO")
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT_LIST)

    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    handover = st.selectbox("HANDOVER PERSON", HANDOVER_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.selectbox("REMARK", REMARK_LIST)

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        buffer_ws.update(f"F{idx+2}", current + qty)

        log_ws.append_row([
            DATE, MONTH, WEEK,
            gate, tat,
            row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"],
            row["TYPE"],
            part,
            current,
            qty,
            0,
            current + qty,
            applicant,
            handover,
            OPERATOR_NAME,
            floor,
            remark,
            st.session_state.user
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

    st.info(f"📦 CURRENT STOCK : {current}")

    if current <= 0:
        st.warning("⚠ No stock available")
        st.stop()

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
    gate = st.text_input("GATE PASS NO")

    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    handover = st.selectbox("HANDOVER PERSON", HANDOVER_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.selectbox("REMARK", REMARK_LIST)

    if st.button("REMOVE STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        buffer_ws.update(f"F{idx+2}", current - qty)

        log_ws.append_row([
            DATE, MONTH, WEEK,
            gate, "OUT",
            row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"],
            row["TYPE"],
            part,
            current,
            0,
            qty,
            current - qty,
            applicant,
            handover,
            OPERATOR_NAME,
            floor,
            remark,
            st.session_state.user
        ])

        st.success("✅ STOCK OUT UPDATED")
        st.rerun()

# =====================================================
# REPORT
# =====================================================
elif menu == "REPORT":

    st.dataframe(log_df, use_container_width=True)

    out = BytesIO()
    log_df.to_excel(out, index=False)
    st.download_button(
        "⬇ Download Full Report Excel",
        out.getvalue(),
        "stock_report.xlsx"
    )
