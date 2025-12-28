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
st.set_page_config(
    page_title="Buffer Stock Management System",
    page_icon="📦",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
body {background-color:#f5f7fa;}
.card {
    background:white;
    padding:22px;
    border-radius:14px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:16px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS
# =========================================================
DEFAULT_FLOOR = "L4"
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

BUFFER_FILE_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
LOG_FILE_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

# =========================================================
# GOOGLE DRIVE DOWNLOAD
# =========================================================
def drive_download(fid, path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}", path, quiet=True)

drive_download(BUFFER_FILE_ID, BUFFER_FILE)
drive_download(LOG_FILE_ID, LOG_FILE)

# =========================================================
# LOAD FUNCTIONS (SAFE)
# =========================================================
def load_buffer():
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=[
            "DATE","MONTH","WEEK","GATE PASS NO",
            "DELIVERY TAT","MATERIAL ASSIGNING BASE",
            "DESCRIPTION","TYPE","PART CODE",
            "PREVIOUS STOCK","IN QTY","OUT QTY","BALANCE",
            "APPLICANT HOD","HANDOVER PERSON",
            "OPERATOR","FLOOR","REMARK","USER"
        ])
    df = pd.read_excel(LOG_FILE)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    return df

def save_excel(df, path):
    df.to_excel(path, index=False)

def to_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return out.getvalue()

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def auto_date():
    now = datetime.today()
    return now, now.strftime("%Y-%m"), now.isocalendar()[1]

def get_list(df, col):
    if col not in df.columns:
        return ["➕ Add New"]
    return ["➕ Add New"] + sorted(df[col].dropna().astype(str).unique().tolist())

def select_or_add(label, options):
    choice = st.selectbox(label, options)
    if choice == "➕ Add New":
        return st.text_input(f"Enter {label}")
    return choice

# =========================================================
# LOGIN
# =========================================================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    user = st.selectbox("User", ["TSD","HOD"])
    pwd = st.text_input("Password", type="password")
    if st.button("LOGIN"):
        ok, role = authenticate(user, pwd)
        if ok:
            st.session_state.login = True
            st.session_state.user = user
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid Login")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
buffer_df = load_buffer()
log_df = load_log()

# =========================================================
# SIDEBAR
# =========================================================
menu = st.sidebar.radio("MENU",[
    "DASHBOARD","FULL BUFFER STOCK","STOCK IN","STOCK OUT","REPORT"
])

# =========================================================
# DASHBOARD
# =========================================================
if menu == "DASHBOARD":
    st.metric("Total Stock", int(buffer_df["GOOD QTY."].sum()))
    st.metric("Total In", int(log_df["IN QTY"].sum()))
    st.metric("Total Out", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ Low Stock")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5])

# =========================================================
# FULL BUFFER
# =========================================================
elif menu == "FULL BUFFER STOCK":
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("Download Buffer", to_excel(buffer_df),"BUFFER.xlsx")

# =========================================================
# STOCK IN
# =========================================================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    prev = int(row["GOOD QTY."])

    gate = st.text_input("GATE PASS NO")
    tat = select_or_add("DELIVERY TAT", get_list(log_df,"DELIVERY TAT"))
    hod = select_or_add("APPLICANT HOD", get_list(log_df,"APPLICANT HOD"))
    hand = select_or_add("HANDOVER PERSON", get_list(log_df,"HANDOVER PERSON"))
    user_sel = select_or_add("USER", get_list(log_df,"USER"))

    qty = st.number_input("IN QTY", min_value=1)
    bal = prev + qty
    st.metric("BALANCE", bal)
    remark = st.text_area("REMARK")

    if st.button("CONFIRM STOCK IN"):
        date, month, week = auto_date()
        buffer_df.loc[buffer_df["PART CODE"]==part,"GOOD QTY."] = bal
        save_excel(buffer_df, BUFFER_FILE)

        log_df.loc[len(log_df)] = {
            "DATE":date,"MONTH":month,"WEEK":week,
            "GATE PASS NO":gate,"DELIVERY TAT":tat,
            "MATERIAL ASSIGNING BASE":row["MATERIAL ASSIGNING BASE"],
            "DESCRIPTION":row["DESCRIPTION"],"TYPE":row["TYPE"],
            "PART CODE":part,"PREVIOUS STOCK":prev,
            "IN QTY":qty,"OUT QTY":0,"BALANCE":bal,
            "APPLICANT HOD":hod,"HANDOVER PERSON":hand,
            "OPERATOR":st.session_state.user,
            "FLOOR":DEFAULT_FLOOR,"REMARK":remark,"USER":user_sel
        }

        save_excel(log_df, LOG_FILE)
        st.success("Stock In Successful")
        st.rerun()

# =========================================================
# STOCK OUT
# =========================================================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    prev = int(row["GOOD QTY."])

    gate = st.text_input("GATE PASS NO")
    tat = select_or_add("DELIVERY TAT", get_list(log_df,"DELIVERY TAT"))
    hod = select_or_add("APPLICANT HOD", get_list(log_df,"APPLICANT HOD"))
    hand = select_or_add("HANDOVER PERSON", get_list(log_df,"HANDOVER PERSON"))
    user_sel = select_or_add("USER", get_list(log_df,"USER"))

    qty = st.number_input("OUT QTY", min_value=1, max_value=prev)
    bal = prev - qty
    st.metric("BALANCE", bal)
    remark = st.text_area("REMARK")

    if st.button("CONFIRM STOCK OUT"):
        date, month, week = auto_date()
        buffer_df.loc[buffer_df["PART CODE"]==part,"GOOD QTY."] = bal
        save_excel(buffer_df, BUFFER_FILE)

        log_df.loc[len(log_df)] = {
            "DATE":date,"MONTH":month,"WEEK":week,
            "GATE PASS NO":gate,"DELIVERY TAT":tat,
            "MATERIAL ASSIGNING BASE":row["MATERIAL ASSIGNING BASE"],
            "DESCRIPTION":row["DESCRIPTION"],"TYPE":row["TYPE"],
            "PART CODE":part,"PREVIOUS STOCK":prev,
            "IN QTY":0,"OUT QTY":qty,"BALANCE":bal,
            "APPLICANT HOD":hod,"HANDOVER PERSON":hand,
            "OPERATOR":st.session_state.user,
            "FLOOR":DEFAULT_FLOOR,"REMARK":remark,"USER":user_sel
        }

        save_excel(log_df, LOG_FILE)
        st.success("Stock Out Successful")
        st.rerun()

# =========================================================
# REPORT
# =========================================================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("Download Report", to_excel(log_df),"REPORT.xlsx")
