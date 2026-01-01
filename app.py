import streamlit as st
import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import DateOffset
from auth import authenticate
import gspread
from google.oauth2.service_account import Credentials

# ================= PAGE CONFIG =================
st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM v3.0", layout="wide")

# ================= STYLE =================
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

# ================= GOOGLE SHEETS CONFIG =================
BUFFER_SHEET_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
INOUT_SHEET_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
# Streamlit secrets me service account ka credentials
creds_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client = gspread.authorize(creds)

buffer_ws = client.open_by_key(BUFFER_SHEET_ID).sheet1
log_ws = client.open_by_key(INOUT_SHEET_ID).sheet1

# ================= LOGIN =================
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

# ================= LOAD DATA =================
def load_buffer():
    data = buffer_ws.get_all_records()
    df = pd.DataFrame(data)
    if "GOOD QTY." in df.columns:
        df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    data = log_ws.get_all_records()
    df = pd.DataFrame(data)
    for col in ["IN QTY", "OUT QTY"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    return df

def save_buffer(df):
    buffer_ws.clear()
    buffer_ws.update([df.columns.values.tolist()] + df.values.tolist())

def save_log(df):
    log_ws.clear()
    log_ws.update([df.columns.values.tolist()] + df.values.tolist())

buffer_df = load_buffer()
log_df = load_log()

# ================= EXCEL DOWNLOAD =================
from io import BytesIO
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= SIDEBAR =================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")
menu = st.sidebar.radio("MENU", ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"])
if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]
DELIVERY_TAT_LIST = ["Same Day", "Other"]

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

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()))

    # Low stock
    st.subheader("LOW STOCK ALERT")
    low_stock_df = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low_stock_df, use_container_width=True)
    if not low_stock_df.empty:
        st.download_button("DOWNLOAD LOW STOCK", to_excel(low_stock_df), "LOW_STOCK.xlsx")

    # Recent activity
    st.subheader("RECENT ACTIVITY")
    recent_df = log_df.tail(10)
    st.dataframe(recent_df, use_container_width=True)
    if not recent_df.empty:
        st.download_button("DOWNLOAD RECENT ACTIVITY", to_excel(recent_df), "RECENT_ACTIVITY.xlsx")

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
    base = row["BASE (LOCAL LANGUAGE)"]
    st.text_input("MATERIAL ASSIGNING BASE", base, disabled=True)
    st.text_input("MATERIAL DESCRIPTION", row["MATERIAL DESCRIPTION (CHINA)"], disabled=True)
    st.text_input("TYPE", row["TYPES"], disabled=True)

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")
    qty = st.number_input("IN QTY", min_value=1, step=1)
    gate = st.text_input("GATE PASS NO")
    tat = st.selectbox("DELIVERY TAT", DELIVERY_TAT_LIST)
    tat_remark = st.text_input("Delivery Remark") if tat=="Other" else ""
    applicant_option = st.selectbox("APPLICANT HOD", ["Pankaj Sir", "Other"])
    applicant = st.text_input("Enter Applicant HOD") if applicant_option=="Other" else applicant_option
    handover = OPERATOR_NAME
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] += qty
        save_buffer(buffer_df)

        log_df.loc[len(log_df)] = {
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": gate,
            "DELIVERY TAT": tat_remark if tat=="Other" else tat,
            "MATERIAL ASSIGNING BASE": base,
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": qty,
            "OUT QTY": 0,
            "BALANCE": prev + qty,
            "APPLICANT HOD": applicant,
            "HANDOVER PERSON": handover,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": floor,
            "REMARK": remark,
            "USER": st.session_state.user
        }
        save_log(log_df)
        st.success("✅ STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>STOCK OUT</h3></div>", unsafe_allow_html=True)
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    base = row["BASE (LOCAL LANGUAGE)"]
    st.text_input("MATERIAL ASSIGNING BASE", base, disabled=True)
    st.text_input("MATERIAL DESCRIPTION", row["MATERIAL DESCRIPTION (CHINA)"], disabled=True)
    st.text_input("TYPE", row["TYPES"], disabled=True)

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        remove_enabled = True
    else:
        st.warning("⚠️ STOCK IS ZERO, CANNOT REMOVE")
        qty = 0
        remove_enabled = False

    gate = st.text_input("GATE PASS NO")
    tat = st.text_input("DELIVERY TAT")
    applicant_option = st.selectbox("APPLICANT HOD", HOD_LIST)
    applicant = st.text_input("Enter Applicant HOD") if applicant_option=="Other" else applicant_option

    previous_handover = log_df["HANDOVER PERSON"].dropna().unique().tolist()
    handover_list = list(previous_handover)
    if OPERATOR_NAME not in handover_list:
        handover_list.append(OPERATOR_NAME)
    handover_list.append("Other")
    handover_option = st.selectbox("HANDOVER PERSON", handover_list)
    handover = st.text_input("Enter Handover Person") if handover_option == "Other" else handover_option

    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("REMOVE STOCK") and remove_enabled:
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]
        buffer_df.at[idx, "GOOD QTY."] -= qty
        save_buffer(buffer_df)

        log_df.loc[len(log_df)] = {
            "DATE": datetime.today().date(),
            "TIME": datetime.now().strftime("%H:%M:%S"),
            "MONTH": datetime.today().strftime("%B"),
            "WEEK": datetime.today().isocalendar()[1],
            "GATE PASS NO": gate,
            "DELIVERY TAT": tat,
            "MATERIAL ASSIGNING BASE": base,
            "DESCRIPTION": row["MATERIAL DESCRIPTION (CHINA)"],
            "TYPE": row["TYPES"],
            "PART CODE": part,
            "PREVIOUS STOCK": prev,
            "IN QTY": 0,
            "OUT QTY": qty,
            "BALANCE": prev - qty,
            "APPLICANT HOD": applicant,
            "HANDOVER PERSON": handover,
            "OPERATOR": OPERATOR_NAME,
            "FLOOR": floor,
            "REMARK": remark,
            "USER": st.session_state.user
        }
        save_log(log_df)
        st.success("✅ STOCK OUT UPDATED")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    if not log_df.empty:
        st.download_button("DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
