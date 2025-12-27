import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config("BUFFER STOCK MANAGEMENT SYSTEM", layout="wide")

OPERATOR_NAME = "Santosh Kumar"

# ---------------- AUTH GOOGLE ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "YOUR_GOOGLE_SHEET_ID"
sheet = client.open_by_key(SPREADSHEET_ID)

buffer_ws = sheet.worksheet("BUFFER")
log_ws = sheet.worksheet("IN_OUT_LOG")
master_ws = sheet.worksheet("MASTER")

# ---------------- LOAD DATA ----------------
buffer_df = pd.DataFrame(buffer_ws.get_all_records())
log_df = pd.DataFrame(log_ws.get_all_records())
master_df = pd.DataFrame(master_ws.get_all_records())

# ---------------- MASTER LISTS ----------------
tat_list = master_df["DELIVERY TAT"].dropna().unique().tolist()
hod_list = master_df["APPLICANT HOD"].dropna().unique().tolist()
user_list = master_df["USER"].dropna().unique().tolist()

# ---------------- UI ----------------
st.title("BUFFER STOCK MANAGEMENT SYSTEM")

menu = st.sidebar.radio("MENU", ["STOCK IN", "STOCK OUT", "REPORT"])

# ================= STOCK IN =================
if menu == "STOCK IN":

    part = st.selectbox("PART CODE", buffer_df["PART CODE"])

    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    st.text_input("MATERIAL ASSIGNING BASE", row["BASE (LOCAL LANGUAGE)"], disabled=True)
    st.text_input("DESCRIPTION", row["MATERIAL DESCRIPTION (CHINA)"], disabled=True)
    st.text_input("TYPE", row["TYPES"], disabled=True)

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    qty = st.number_input("IN QTY", min_value=1, step=1)
    gate = st.text_input("GATE PASS NO")

    tat = st.selectbox("DELIVERY TAT", tat_list + ["Add New"])
    if tat == "Add New":
        tat = st.text_input("New DELIVERY TAT")
        if tat:
            master_ws.append_row(["", "", ""])
            master_ws.update_cell(master_ws.row_count, 1, tat)

    applicant = st.selectbox("APPLICANT HOD", hod_list + ["Add New"])
    if applicant == "Add New":
        applicant = st.text_input("New APPLICANT HOD")
        if applicant:
            master_ws.append_row(["", applicant, ""])

    user = st.selectbox("USER", user_list + ["Add New"])
    if user == "Add New":
        user = st.text_input("New USER")
        if user:
            master_ws.append_row(["", "", user])

    floor = st.selectbox("FLOOR", ["GF", "1F", "2F", "3F", "Other"])
    remark = st.text_input("REMARK")

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        new_stock = current + qty

        buffer_ws.update_cell(idx + 2, buffer_df.columns.get_loc("GOOD QTY.") + 1, new_stock)

        now = datetime.now()

        log_ws.append_row([
            now.date(), now.strftime("%H:%M:%S"),
            now.strftime("%B"), now.isocalendar()[1],
            gate, tat, row["BASE (LOCAL LANGUAGE)"],
            row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"], part,
            current, qty, 0, new_stock,
            applicant, OPERATOR_NAME, OPERATOR_NAME,
            floor, remark, user
        ])

        st.success("✅ STOCK IN UPDATED IN GOOGLE SHEET")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":

    part = st.selectbox("PART CODE", buffer_df["PART CODE"])
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current)
        gate = st.text_input("GATE PASS NO")
        floor = st.selectbox("FLOOR", ["GF", "1F", "2F", "3F", "Other"])
        remark = st.text_input("REMARK")

        if st.button("REMOVE STOCK"):
            new_stock = current - qty

            idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
            buffer_ws.update_cell(idx + 2, buffer_df.columns.get_loc("GOOD QTY.") + 1, new_stock)

            now = datetime.now()

            log_ws.append_row([
                now.date(), now.strftime("%H:%M:%S"),
                now.strftime("%B"), now.isocalendar()[1],
                gate, "", row["BASE (LOCAL LANGUAGE)"],
                row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"], part,
                current, 0, qty, new_stock,
                "", OPERATOR_NAME, OPERATOR_NAME,
                floor, remark, ""
            ])

            st.success("✅ STOCK OUT UPDATED IN GOOGLE SHEET")

# ================= REPORT =================
else:
    st.dataframe(log_df, use_container_width=True)
