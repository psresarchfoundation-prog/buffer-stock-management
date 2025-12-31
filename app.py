import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO

# ================= CONFIG =================
st.set_page_config("Buffer Stock System", "📦", layout="wide")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

# ================= INIT FILES (VERY IMPORTANT) =================
def init_files():
    if not os.path.exists(BUFFER_FILE):
        df = pd.DataFrame([
            ["P1001","RAM 8GB","IT","ELECTRONIC",50],
            ["P1002","SSD 512GB","IT","ELECTRONIC",30],
            ["P1003","Keyboard","IT","ACCESSORY",100],
        ], columns=[
            "PART CODE","DESCRIPTION",
            "MATERIAL ASSIGNING BASE","TYPE","GOOD QTY."
        ])
        df.to_excel(BUFFER_FILE, index=False)

    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=[
            "DATE","MONTH","WEEK",
            "PART CODE","PREVIOUS STOCK",
            "IN QTY","OUT QTY","BALANCE",
            "USER","REMARK"
        ])
        df.to_excel(LOG_FILE, index=False)

init_files()

# ================= LOAD DATA =================
buffer_df = pd.read_excel(BUFFER_FILE)
log_df = pd.read_excel(LOG_FILE)

buffer_df["GOOD QTY."] = pd.to_numeric(
    buffer_df["GOOD QTY."], errors="coerce"
).fillna(0)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 LOGIN")
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
            st.error("❌ Wrong login")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

if st.session_state.role == "READ":
    menu = st.sidebar.radio("MENU", ["DASHBOARD","BUFFER","REPORT"])
else:
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
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum()) if not log_df.empty else 0)
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum()) if not log_df.empty else 0)
    st.dataframe(buffer_df, use_container_width=True)

# ================= BUFFER =================
elif menu == "BUFFER":
    st.dataframe(buffer_df, use_container_width=True)

# ================= STOCK IN =================
elif menu == "STOCK IN":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"])
    idx = buffer_df[buffer_df["PART CODE"]==part].index[0]
    cur = int(buffer_df.at[idx,"GOOD QTY."])

    qty = st.number_input("IN QTY", min_value=1, step=1)
    remark = st.text_input("Remark")

    if st.button("ADD STOCK"):
        buffer_df.at[idx,"GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            part, cur, qty, 0, cur+qty,
            st.session_state.user, remark
        ]
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ Stock Added")
        st.rerun()

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    part = st.selectbox("PART CODE", buffer_df["PART CODE"])
    idx = buffer_df[buffer_df["PART CODE"]==part].index[0]
    cur = int(buffer_df.at[idx,"GOOD QTY."])

    st.info(f"Current Stock : {cur}")
    qty = st.number_input("OUT QTY", min_value=1, max_value=cur)
    remark = st.text_input("Remark")

    if st.button("REMOVE STOCK"):
        buffer_df.at[idx,"GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today(),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            part, cur, 0, qty, cur-qty,
            st.session_state.user, remark
        ]
        log_df.to_excel(LOG_FILE, index=False)
        st.success("✅ Stock Removed")
        st.rerun()

# ================= REPORT =================
elif menu == "REPORT":
    st.dataframe(log_df, use_container_width=True)
