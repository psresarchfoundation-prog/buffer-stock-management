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
.card {background:white;padding:20px;border-radius:12px;
box-shadow:0 4px 12px rgba(0,0,0,.08);margin-bottom:15px;}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS
# =========================================================
DELIVERY_TAT = ["Same Day","24 Hours","48 Hours","72 Hours"]
APPLICANT_HOD = ["Rajkumar","Ajay Kumar","Sandeep Singh"]
HANDOVER_PERSON = ["Shekhar","Rohit Verma","Amit Yadav"]
DEFAULT_FLOOR = "L4"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

# =========================================================
# SAFE LOAD FUNCTIONS
# =========================================================
def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return pd.DataFrame(columns=[
            "PART CODE","DESCRIPTION","TYPE",
            "MATERIAL ASSIGNING BASE","GOOD QTY."
        ])
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=[
            "DATE","MONTH","WEEK","REFERENCE",
            "DELIVERY TAT","MATERIAL ASSIGNING BASE",
            "DESCRIPTION","TYPE","PART CODE",
            "OPENING","IN QTY","OUT QTY","CLOSING",
            "APPLICANT HOD","HANDOVER PERSON",
            "USER","FLOOR","REMARK","CREATED BY"
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
    "DASHBOARD","FULL BUFFER STOCK",
    "STOCK IN","STOCK OUT","REPORT"
])

# =========================================================
# DASHBOARD
# =========================================================
if menu == "DASHBOARD":
    st.metric("Total Stock", int(buffer_df["GOOD QTY."].sum()))
    st.metric("Total In", int(log_df["IN QTY"].sum()))
    st.metric("Total Out", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ Low Stock (<5)")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5])

    st.subheader("📉 Last 3 Months Consumption")
    last3 = log_df[log_df["DATE"] >= pd.Timestamp.today() - pd.DateOffset(months=3)]
    st.dataframe(last3.groupby("PART CODE")["OUT QTY"].sum().reset_index())

# =========================================================
# STOCK IN / OUT COMMON FUNCTION
# =========================================================
def stock_transaction(part, qty, mode, tat, hod, hand, remark):
    global buffer_df, log_df

    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    opening = int(row["GOOD QTY."])

    if mode == "OUT" and qty > opening:
        st.error("❌ Insufficient stock")
        return

    closing = opening + qty if mode == "IN" else opening - qty

    buffer_df.loc[buffer_df["PART CODE"]==part,"GOOD QTY."] = closing
    save_excel(buffer_df, BUFFER_FILE)

    log_df.loc[len(log_df)] = {
        "DATE": datetime.today(),
        "MONTH": datetime.today().strftime("%Y-%m"),
        "WEEK": datetime.today().isocalendar()[1],
        "REFERENCE":"",
        "DELIVERY TAT": tat,
        "MATERIAL ASSIGNING BASE": row["MATERIAL ASSIGNING BASE"],
        "DESCRIPTION": row["DESCRIPTION"],
        "TYPE": row["TYPE"],
        "PART CODE": part,
        "OPENING": opening,
        "IN QTY": qty if mode=="IN" else 0,
        "OUT QTY": qty if mode=="OUT" else 0,
        "CLOSING": closing,
        "APPLICANT HOD": hod,
        "HANDOVER PERSON": hand,
        "USER": st.session_state.user,
        "FLOOR": DEFAULT_FLOOR,
        "REMARK": remark,
        "CREATED BY": st.session_state.user
    }

    save_excel(log_df, LOG_FILE)
    st.success(f"✅ Stock {mode} Successful")
    st.rerun()

# =========================================================
# STOCK IN
# =========================================================
if menu == "STOCK IN":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    qty = st.number_input("In Qty", min_value=1)
    tat = st.selectbox("TAT", DELIVERY_TAT)
    hod = st.selectbox("HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover", HANDOVER_PERSON)
    remark = st.text_area("Remark")
    if st.button("Confirm IN"):
        stock_transaction(part, qty, "IN", tat, hod, hand, remark)

# =========================================================
# STOCK OUT
# =========================================================
if menu == "STOCK OUT":
    part = st.selectbox("Part Code", buffer_df["PART CODE"].unique())
    qty = st.number_input("Out Qty", min_value=1)
    tat = st.selectbox("TAT", DELIVERY_TAT)
    hod = st.selectbox("HOD", APPLICANT_HOD)
    hand = st.selectbox("Handover", HANDOVER_PERSON)
    remark = st.text_area("Remark")
    if st.button("Confirm OUT"):
        stock_transaction(part, qty, "OUT", tat, hod, hand, remark)

# =========================================================
# REPORT
# =========================================================
if menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
    st.download_button("Download Report", to_excel(log_df),"IN_OUT_REPORT.xlsx")
