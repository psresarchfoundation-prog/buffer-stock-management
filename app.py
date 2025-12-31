import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os

# ================= CONFIG =================
st.set_page_config("BUFFER STOCK MANAGEMENT SYSTEM", layout="wide")

DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/stock_log.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)

# ================= AUTH =================
if "logged" not in st.session_state:
    st.session_state.logged = False

if not st.session_state.logged:
    st.title("🔐 Login")

    user = st.selectbox("User", ["TSD", "HOD"])
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, role = authenticate(user, pwd)
        if ok:
            st.session_state.logged = True
            st.session_state.user = user
            st.session_state.role = role
            st.rerun()
        else:
            st.error("❌ Invalid Login")

    st.stop()

# ================= LOAD DATA =================
def load_buffer():
    cols = ["PART CODE","DESCRIPTION","BASE","TYPE","GOOD QTY"]
    if not os.path.exists(BUFFER_FILE):
        df = pd.DataFrame([
            ["P1001","RAM 8GB","IT","ELECTRONIC",50],
            ["P1002","SSD 512GB","IT","ELECTRONIC",30],
            ["P1003","Keyboard","IT","ACCESSORY",100]
        ], columns=cols)
        df.to_excel(BUFFER_FILE, index=False)

    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY"] = pd.to_numeric(df["GOOD QTY"], errors="coerce").fillna(0)
    return df

def load_log():
    cols = [
        "DATE","PART CODE","DESCRIPTION",
        "PREVIOUS","IN","OUT","BALANCE",
        "REMARK","ENTRY BY"
    ]
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=cols).to_excel(LOG_FILE, index=False)
    return pd.read_excel(LOG_FILE)

buffer_df = load_buffer()
log_df = load_log()

# ================= UI =================
st.sidebar.success(f"👤 {st.session_state.user} ({st.session_state.role})")

menu = st.sidebar.radio("MENU", ["Dashboard","Stock In","Stock Out","Logs","Logout"])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Buffer Stock Dashboard")
    st.dataframe(buffer_df, use_container_width=True)

# ================= STOCK IN =================
elif menu == "Stock In":
    if st.session_state.role != "ADMIN":
        st.error("❌ Read Only Access")
        st.stop()

    st.title("➕ Stock In")

    part = st.selectbox("Part", buffer_df["PART CODE"])
    qty = st.number_input("In Quantity", min_value=1)
    remark = st.text_input("Remark")

    if st.button("Submit Stock In"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY"]
        buffer_df.at[idx, "GOOD QTY"] += qty

        log_df.loc[len(log_df)] = [
            datetime.now(), part,
            buffer_df.at[idx,"DESCRIPTION"],
            prev, qty, 0,
            buffer_df.at[idx,"GOOD QTY"],
            remark, st.session_state.user
        ]

        buffer_df.to_excel(BUFFER_FILE, index=False)
        log_df.to_excel(LOG_FILE, index=False)

        st.success("✅ Stock Added")

# ================= STOCK OUT =================
elif menu == "Stock Out":
    if st.session_state.role != "ADMIN":
        st.error("❌ Read Only Access")
        st.stop()

    st.title("➖ Stock Out")

    part = st.selectbox("Part", buffer_df["PART CODE"])
    qty = st.number_input("Out Quantity", min_value=1)
    remark = st.text_input("Remark")

    if st.button("Submit Stock Out"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY"]

        if qty > prev:
            st.error("❌ Insufficient Stock")
        else:
            buffer_df.at[idx, "GOOD QTY"] -= qty

            log_df.loc[len(log_df)] = [
                datetime.now(), part,
                buffer_df.at[idx,"DESCRIPTION"],
                prev, 0, qty,
                buffer_df.at[idx,"GOOD QTY"],
                remark, st.session_state.user
            ]

            buffer_df.to_excel(BUFFER_FILE, index=False)
            log_df.to_excel(LOG_FILE, index=False)

            st.success("✅ Stock Deducted")

# ================= LOGS =================
elif menu == "Logs":
    st.title("📜 Stock Logs")
    st.dataframe(log_df, use_container_width=True)

# ================= LOGOUT =================
elif menu == "Logout":
    st.session_state.clear()
    st.rerun()
