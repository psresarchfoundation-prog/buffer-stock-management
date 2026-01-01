import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM v3.1",
    layout="wide"
)

# ================= FILE PATH =================
BUFFER_FILE = "buffer_stock.csv"
LOG_FILE = "inout_log.csv"

OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]

# ================= STYLE =================
st.markdown("""
<style>
.card {
    background:#ffffff;
    padding:25px;
    border-radius:15px;
    box-shadow:0 6px 20px rgba(0,0,0,.15);
    margin-bottom:20px;
}
</style>
""", unsafe_allow_html=True)

# ================= LOAD DATA =================
def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        return pd.DataFrame(columns=["PART CODE","PART NAME","GOOD QTY."])
    df = pd.read_csv(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0)
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=[
            "DATE","TIME","GATE TYPE","PART CODE",
            "IN QTY","OUT QTY","BALANCE",
            "HOD","OPERATOR","FLOOR","REMARK","USER"
        ])
    return pd.read_csv(LOG_FILE)

def save_buffer(df):
    df.to_csv(BUFFER_FILE, index=False)

def save_log(df):
    df.to_csv(LOG_FILE, index=False)

buffer_df = load_buffer()
log_df = load_log()

# ================= LOGIN =================
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

# ================= SIDEBAR =================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

if st.sidebar.button("LOGOUT"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><h2>Dashboard</h2></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()) if not log_df.empty else 0)
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()) if not log_df.empty else 0)

    st.subheader("⚠ LOW STOCK ALERT")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5], use_container_width=True)

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)

# ================= STOCK IN =================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("IN QTY", min_value=1, step=1)
    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("ADD STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] = current + qty
        save_buffer(buffer_df)

        log_df.loc[len(log_df)] = [
            datetime.today().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            "IN", part, qty, 0, current + qty,
            applicant, OPERATOR_NAME, floor, remark, st.session_state.user
        ]
        save_log(log_df)
        st.success("✅ STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]
    current = int(row["GOOD QTY."])

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
    applicant = st.selectbox("APPLICANT HOD", HOD_LIST)
    floor = st.selectbox("FLOOR", FLOOR_LIST)
    remark = st.text_input("REMARK")

    if st.button("REMOVE STOCK"):
        buffer_df.loc[buffer_df["PART CODE"] == part, "GOOD QTY."] = current - qty
        save_buffer(buffer_df)

        log_df.loc[len(log_df)] = [
            datetime.today().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            "OUT", part, 0, qty, current - qty,
            applicant, OPERATOR_NAME, floor, remark, st.session_state.user
        ]
        save_log(log_df)
        st.success("✅ STOCK OUT UPDATED")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
