import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO

st.set_page_config(page_title="BUFFER STOCK MANAGEMENT SYSTEM", layout="wide")

DATA_DIR = "data"
BUFFER_FILE = f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE = f"{DATA_DIR}/in_out_log.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- LOGIN ----------------
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
            st.success("LOGIN SUCCESS")
            st.experimental_rerun()
        else:
            st.error("INVALID LOGIN")
    st.stop()

# ---------------- LOAD DATA ----------------
def load_buffer():
    if not os.path.exists(BUFFER_FILE):
        cols = [
            "BASE (LOCAL LANGUAGE)", "GOOD LOCATION", "PART CODE", "TYPES",
            "MATERIAL DESCRIPTION (CHINA)", "GOOD QTY.", "DETAILS",
            "DEFECTIVE LOCATION", "DEFECTIVE QTY.",
            "TOOLS AND EQUIPMENT TOTAL", "REMARK1", "REMARK2"
        ]
        pd.DataFrame(columns=cols).to_excel(BUFFER_FILE, index=False)
    return pd.read_excel(BUFFER_FILE)

def load_log():
    if not os.path.exists(LOG_FILE):
        cols = [
            "DATE", "MONTH", "WEEK", "GATE PASS NO", "DELIVERY TAT",
            "MATERIAL ASSIGNING BASE", "DESCRIPTION", "TYPE", "PART CODE",
            "PREVIOUS STOCK", "IN QTY", "OUT QTY", "BALANCE",
            "APPLICANT HOD", "HANDOVER PERSON", "OPERATOR",
            "FLOOR", "REMARK", "USER"
        ]
        pd.DataFrame(columns=cols).to_excel(LOG_FILE, index=False)
    return pd.read_excel(LOG_FILE)

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL HELPER ----------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"LOGGED IN AS : {st.session_state.user}")
menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

# ---------------- DASHBOARD ----------------
if menu == "DASHBOARD":
    st.title("TECHNICAL SUPPORT DEPARTMENT")

    total_stock = buffer_df["GOOD QTY."].sum()
    low_stock = buffer_df[buffer_df["GOOD QTY."] < 5]

    col1, col2 = st.columns(2)
    col1.metric("TOTAL STOCK", total_stock)
    col2.metric("LOW STOCK ITEMS", len(low_stock))

    st.subheader("🔴 LOW STOCK ALERT")
    st.dataframe(low_stock)

# ---------------- FULL BUFFER ----------------
elif menu == "FULL BUFFER STOCK":
    st.title("📦 FULL BUFFER STOCK")
    search = st.text_input("SEARCH PART CODE / MATERIAL")
    if search:
        df = buffer_df[
            buffer_df["PART CODE"].astype(str).str.contains(search, case=False) |
            buffer_df["MATERIAL DESCRIPTION (CHINA)"].str.contains(search, case=False)
        ]
    else:
        df = buffer_df
    st.dataframe(df)
    st.download_button(
        "⬇️ DOWNLOAD FULL BUFFER EXCEL",
        data=to_excel(df),
        file_name="FULL_BUFFER_STOCK.xlsx"
    )

# ---------------- STOCK IN ----------------
elif menu == "STOCK IN":
    st.title("📥 STOCK IN")
    part_list = buffer_df["PART CODE"].tolist()
    part = st.selectbox("PART CODE", part_list)
    qty = st.number_input("IN QTY", min_value=1)
    if st.button("ADD STOCK"):
        idx_list = buffer_df[buffer_df["PART CODE"] == part].index
        if len(idx_list) == 0:
            st.error("PART CODE NOT FOUND")
        else:
            idx = idx_list[0]
            prev = buffer_df.at[idx, "GOOD QTY."]
            buffer_df.at[idx, "GOOD QTY."] += qty
            buffer_df.to_excel(BUFFER_FILE, index=False)

            week_no = datetime.today().isocalendar()[1]

            log_df.loc[len(log_df)] = [
                datetime.today().date(), datetime.today().strftime("%B"), week_no,
                "", "", "", "", "", part,
                prev, qty, 0, prev + qty,
                "", "", "", "", "", st.session_state.user
            ]
            log_df.to_excel(LOG_FILE, index=False)
            st.success("STOCK UPDATED")

# ---------------- STOCK OUT ----------------
elif menu == "STOCK OUT":
    st.title("📤 STOCK OUT")
    part_list = buffer_df["PART CODE"].tolist()
    part = st.selectbox("PART CODE", part_list)
    qty = st.number_input("OUT QTY", min_value=1)
    if st.button("REMOVE STOCK"):
        idx_list = buffer_df[buffer_df["PART CODE"] == part].index
        if len(idx_list) == 0:
            st.error("PART CODE NOT FOUND")
        else:
            idx = idx_list[0]
            prev = buffer_df.at[idx, "GOOD QTY."]
            if qty > prev:
                st.error("INSUFFICIENT STOCK")
            else:
                buffer_df.at[idx, "GOOD QTY."] -= qty
                buffer_df.to_excel(BUFFER_FILE, index=False)

                week_no = datetime.today().isocalendar()[1]

                log_df.loc[len(log_df)] = [
                    datetime.today().date(), datetime.today().strftime("%B"), week_no,
                    "", "", "", "", "", part,
                    prev, 0, qty, prev - qty,
                    "", "", "", "", "", st.session_state.user
                ]
                log_df.to_excel(LOG_FILE, index=False)
                st.success("STOCK UPDATED")

# ---------------- REPORT ----------------
elif menu == "REPORT":
    st.title("📊 IN / OUT REPORT")
    st.dataframe(log_df)
    st.download_button(
        "⬇️ DOWNLOAD IN-OUT EXCEL",
        data=to_excel(log_df),
        file_name="IN_OUT_REPORT.xlsx"
    )
