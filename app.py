import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM",
    layout="wide"
)

# ================= STYLE =================
st.markdown("""
<style>
.card {
    background: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header {
    font-size: 26px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE AUTH =================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPE
)
gc = gspread.authorize(creds)

# ================= SHEET URLS =================
BUFFER_SHEET_URL = "https://docs.google.com/spreadsheets/d/16qT02u7QKi7GrDHwczq99OjhCsFyay_h/edit"
LOG_SHEET_URL    = "https://docs.google.com/spreadsheets/d/1ThuZsaJsunOs46-teJTkgLs9KkctNwhS/edit"

buffer_ws = gc.open_by_url(BUFFER_SHEET_URL).sheet1
log_ws = gc.open_by_url(LOG_SHEET_URL).sheet1

# ================= LOAD DATA =================
@st.cache_data(ttl=30)
def load_buffer():
    df = get_as_dataframe(buffer_ws).fillna("")
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce").fillna(0).astype(int)
    return df

@st.cache_data(ttl=30)
def load_log():
    df = get_as_dataframe(log_ws).fillna("")
    if "IN QTY" in df.columns:
        df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce").fillna(0).astype(int)
    if "OUT QTY" in df.columns:
        df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce").fillna(0).astype(int)
    return df

buffer_df = load_buffer()
log_df = load_log()

# ================= EXCEL DOWNLOAD =================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ================= SIDEBAR =================
OPERATOR_NAME = "Santosh Kumar"
HOD_LIST = ["Pankaj Sir", "Kevin Sir", "Aiyousha", "Other"]
FLOOR_LIST = ["GF", "1F", "2F", "3F", "Other"]

st.sidebar.success(f"OPERATOR : {OPERATOR_NAME}")
menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("<div class='card'><div class='header'>Dashboard</div></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN", int(log_df["IN QTY"].sum() if "IN QTY" in log_df else 0))
    c3.metric("TOTAL OUT", int(log_df["OUT QTY"].sum() if "OUT QTY" in log_df else 0))

    st.subheader("LOW STOCK ( < 5 )")
    low_df = buffer_df[buffer_df["GOOD QTY."] < 5]
    st.dataframe(low_df, use_container_width=True)
    st.download_button("Download Low Stock", to_excel(low_df), "low_stock.xlsx")

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><div class='header'>Full Buffer Stock</div></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("Download Buffer", to_excel(buffer_df), "buffer_stock.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><div class='header'>Stock In</div></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    st.write("**Description:**", row["MATERIAL DESCRIPTION (CHINA)"])
    current = int(row["GOOD QTY."])
    st.info(f"Current Stock : {current}")

    qty = st.number_input("IN QTY", min_value=1, step=1)
    remark = st.text_input("Remark")

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        buffer_df.at[idx, "GOOD QTY."] = current + qty
        set_with_dataframe(buffer_ws, buffer_df)

        log_df.loc[len(log_df)] = {
            "DATE": datetime.now().strftime("%Y-%m-%d"),
            "PART CODE": part,
            "IN QTY": qty,
            "OUT QTY": 0,
            "BALANCE": current + qty,
            "OPERATOR": OPERATOR_NAME,
            "REMARK": remark
        }
        set_with_dataframe(log_ws, log_df)

        st.success("✅ Stock Added")
        st.cache_data.clear()

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><div class='header'>Stock Out</div></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].unique())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    current = int(row["GOOD QTY."])
    st.info(f"Current Stock : {current}")

    if current > 0:
        qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)
        remark = st.text_input("Remark")

        if st.button("REMOVE STOCK"):
            idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
            buffer_df.at[idx, "GOOD QTY."] = current - qty
            set_with_dataframe(buffer_ws, buffer_df)

            log_df.loc[len(log_df)] = {
                "DATE": datetime.now().strftime("%Y-%m-%d"),
                "PART CODE": part,
                "IN QTY": 0,
                "OUT QTY": qty,
                "BALANCE": current - qty,
                "OPERATOR": OPERATOR_NAME,
                "REMARK": remark
            }
            set_with_dataframe(log_ws, log_df)

            st.success("✅ Stock Removed")
            st.cache_data.clear()
    else:
        st.warning("Stock is ZERO")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><div class='header'>Stock Report</div></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("Download Report", to_excel(log_df), "stock_report.xlsx")
