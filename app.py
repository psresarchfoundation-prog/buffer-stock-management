import streamlit as st
import pandas as pd
from datetime import datetime
import gdown
from io import BytesIO

# ================= CONFIG =================
st.set_page_config("BUFFER STOCK MANAGEMENT", layout="wide")

BUFFER_SHEET_ID = "16qT02u7QKi7GrDHwczq99OjhCsFyay_h"
TRANS_SHEET_ID = "1ThuZsaJsunOs46-teJTkgLs9KkctNwhS"

# ================= FUNCTIONS =================
@st.cache_data
def load_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    output = "data.xlsx"
    gdown.download(url, output, quiet=True)
    return pd.read_excel(output)

def download_excel(df, name):
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button(
        "⬇ Download Excel",
        buffer.getvalue(),
        file_name=name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ================= LOAD DATA =================
stock_df = load_sheet(BUFFER_SHEET_ID)
trans_df = load_sheet(TRANS_SHEET_ID)

stock_df["CURRENT_STOCK"] = stock_df["CURRENT_STOCK"].fillna(0).astype(int)

# ================= LOGIN (DUMMY) =================
st.sidebar.title("🔐 LOGIN")
user = st.sidebar.text_input("USER")
pwd = st.sidebar.text_input("PASSWORD", type="password")

if user != "TSD" or pwd != "TSD":
    st.warning("Login = TSD / TSD")
    st.stop()

# ================= MENU =================
menu = st.sidebar.radio("MENU", [
    "DASHBOARD",
    "FULL BUFFER STOCK",
    "STOCK IN",
    "STOCK OUT",
    "REPORT"
])

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.title("📊 DASHBOARD")

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 TOTAL ITEMS", len(stock_df))
    c2.metric("📥 TOTAL IN", trans_df[trans_df["TYPE"]=="IN"]["QTY"].sum())
    c3.metric("📤 TOTAL OUT", trans_df[trans_df["TYPE"]=="OUT"]["QTY"].sum())

    st.subheader("Current Stock")
    st.dataframe(stock_df)

    download_excel(stock_df, "buffer_stock.xlsx")

# ================= FULL STOCK =================
elif menu == "FULL BUFFER STOCK":
    st.title("📦 FULL BUFFER STOCK")
    st.dataframe(stock_df)
    download_excel(stock_df, "full_stock.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.title("📥 STOCK IN")

    part = st.selectbox("PART CODE", stock_df["PART_CODE"])
    qty = st.number_input("IN QTY", min_value=1, step=1)

    if st.button("SAVE IN"):
        stock_df.loc[stock_df["PART_CODE"]==part, "CURRENT_STOCK"] += qty

        trans_df.loc[len(trans_df)] = [
            datetime.now(), part, "IN", qty
        ]

        st.success("Stock In Added")
        st.cache_data.clear()

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.title("📤 STOCK OUT")

    part = st.selectbox("PART CODE", stock_df["PART_CODE"])
    current = int(stock_df.loc[stock_df["PART_CODE"]==part, "CURRENT_STOCK"].values[0])

    st.info(f"Current Stock: {current}")

    if current == 0:
        st.warning("No Stock Available")
        st.stop()

    qty = st.number_input("OUT QTY", min_value=1, max_value=current, step=1)

    if st.button("SAVE OUT"):
        stock_df.loc[stock_df["PART_CODE"]==part, "CURRENT_STOCK"] -= qty

        trans_df.loc[len(trans_df)] = [
            datetime.now(), part, "OUT", qty
        ]

        st.success("Stock Out Added")
        st.cache_data.clear()

# ================= REPORT =================
elif menu == "REPORT":
    st.title("📑 TRANSACTION REPORT")
    st.dataframe(trans_df)
    download_excel(trans_df, "transaction_report.xlsx")
