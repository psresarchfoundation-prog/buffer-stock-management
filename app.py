import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config("BUFFER STOCK MANAGEMENT SYSTEM v3.1", layout="wide")

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
.card {
    background:white;
    padding:22px;
    border-radius:16px;
    box-shadow:0 8px 25px rgba(0,0,0,0.12);
    margin-bottom:18px;
}
.header{font-size:26px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# =========================================================
# MASTER DATA (DEFAULT)
# =========================================================
DELIVERY_TAT = ["Same Day", "24 Hours", "48 Hours", "72 Hours"]
MATERIAL_BASE = ["Warehouse", "Assembly", "Testing", "Repair", "Production"]
APPLICANT_HOD = ["Mr. Rishu Khanna", "Mr. Ajay Kumar", "Mr. Sandeep Singh"]
HANDOVER_PERSON = ["Santosh Kumar", "Rohit Verma", "Amit Yadav"]
FLOOR_LIST = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor"]

# =========================================================
# FILE CONFIG
# =========================================================
DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR, exist_ok=True)

# =========================================================
# GOOGLE DRIVE
# =========================================================
BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

def drive_download(fid, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}", path, quiet=True)

drive_download(BUFFER_FILE_ID, BUFFER_FILE)
drive_download(LOG_FILE_ID, LOG_FILE)

# =========================================================
# LOGIN
# =========================================================
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
            st.error("INVALID LOGIN")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data(ttl=5)
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

@st.cache_data(ttl=5)
def load_log():
    df = pd.read_excel(LOG_FILE)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0)
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0)
    return df

buffer_df = load_buffer()
log_df = load_log()

# =========================================================
# SELECT OR ADD (AUTO FROM EXCEL)
# =========================================================
def select_or_add(label, default_list, df, col):
    excel_vals = []
    if col in df.columns:
        excel_vals = df[col].dropna().astype(str).unique().tolist()
    values = sorted(set(default_list + excel_vals))
    choice = st.selectbox(label, values + ["➕ Add New"])
    if choice == "➕ Add New":
        return st.text_input(f"Enter {label}")
    return choice

# =========================================================
# EXCEL DOWNLOAD
# =========================================================
def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return out.getvalue()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio("MENU", [
    "DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"
])

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# =========================================================
# DASHBOARD
# =========================================================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>📊 Dashboard</div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("📥 TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("📤 TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ LOW STOCK ALERT")
    low = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low if not low.empty else pd.DataFrame(["ALL STOCK OK"]))

    st.subheader("📉 LAST 3 MONTH CONSUMPTION")
    last3 = log_df[log_df["DATE"] >= (pd.Timestamp.today() - pd.DateOffset(months=3))]
    cons = last3.groupby("PART CODE")["OUT QTY"].sum().reset_index()
    st.dataframe(cons if not cons.empty else pd.DataFrame(["NO DATA"]))

# =========================================================
# FULL BUFFER
# =========================================================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER_STOCK.xlsx")

# =========================================================
# STOCK IN
# =========================================================
elif menu == "STOCK IN":
    with st.container():
        part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
        idx = buffer_df.index[buffer_df["PART CODE"] == part][0]
        current = int(buffer_df.at[idx, "GOOD QTY."])
        st.info(f"CURRENT STOCK : {current}")

        qty = st.number_input("IN QTY", min_value=1, step=1)
        tat = select_or_add("DELIVERY TAT", DELIVERY_TAT, log_df, "DELIVERY TAT")
        base = select_or_add("MATERIAL ASSIGNING BASE", MATERIAL_BASE, log_df, "MATERIAL ASSIGNING BASE")
        hod = select_or_add("APPLICANT HOD", APPLICANT_HOD, log_df, "APPLICANT HOD")
        hand = select_or_add("HANDOVER PERSON", HANDOVER_PERSON, log_df, "HANDOVER PERSON")
        floor = select_or_add("FLOOR", FLOOR_LIST, log_df, "FLOOR")
        remark = st.text_area("REMARK")

        if st.button("✅ ADD STOCK"):
            buffer_df.at[idx, "GOOD QTY."] += qty
            buffer_df.to_excel(BUFFER_FILE, index=False)

            log_df.loc[len(log_df)] = [
                datetime.today(), datetime.today().strftime("%B"),
                datetime.today().isocalendar()[1], "",
                tat, base, "", "IN",
                part, current, qty, 0, current + qty,
                hod, hand, st.session_state.user,
                floor, remark, st.session_state.user
            ]
            log_df.to_excel(LOG_FILE, index=False)
            st.cache_data.clear()
            st.success("STOCK IN SUCCESS")
            st.rerun()

# =========================================================
# STOCK OUT
# =========================================================
elif menu == "STOCK OUT":
    with st.container():
        part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna().unique())
        idx = buffer_df.index[buffer_df["PART CODE"] == part][0]
        current = int(buffer_df.at[idx, "GOOD QTY."])
        st.info(f"CURRENT STOCK : {current}")

        if current <= 0:
            st.warning("NO STOCK AVAILABLE")
            st.stop()

        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        tat = select_or_add("DELIVERY TAT", DELIVERY_TAT, log_df, "DELIVERY TAT")
        base = select_or_add("MATERIAL ASSIGNING BASE", MATERIAL_BASE, log_df, "MATERIAL ASSIGNING BASE")
        hod = select_or_add("APPLICANT HOD", APPLICANT_HOD, log_df, "APPLICANT HOD")
        hand = select_or_add("HANDOVER PERSON", HANDOVER_PERSON, log_df, "HANDOVER PERSON")
        floor = select_or_add("FLOOR", FLOOR_LIST, log_df, "FLOOR")
        remark = st.text_area("REMARK")

        if st.button("❌ REMOVE STOCK"):
            buffer_df.at[idx, "GOOD QTY."] -= qty
            buffer_df.to_excel(BUFFER_FILE, index=False)

            log_df.loc[len(log_df)] = [
                datetime.today(), datetime.today().strftime("%B"),
                datetime.today().isocalendar()[1], "",
                tat, base, "", "OUT",
                part, current, 0, qty, current - qty,
                hod, hand, st.session_state.user,
                floor, remark, st.session_state.user
            ]
            log_df.to_excel(LOG_FILE, index=False)
            st.cache_data.clear()
            st.success("STOCK OUT SUCCESS")
            st.rerun()

# =========================================================
# REPORT
# =========================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
