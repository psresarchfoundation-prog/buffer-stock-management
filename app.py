import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Buffer Stock Management System",
    page_icon="📦",
    layout="wide"
)

# =====================================================
# USER / ROLE (STATIC AS PER REQUIREMENT)
# =====================================================
USER = "TSD"
ROLE = "TSD"

# =====================================================
# GOOGLE SHEET CONFIG
# =====================================================
BUFFER_SHEET_ID = "13XzWDCbuA7ZWZLyjezLCBm7oFxb35me6Z53RozF9yaE"
LOG_SHEET_ID = "12Hnk3k2D3JReYZnbsCYCbvIbTb23zfbE5UuuaEj4UTg"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
buffer_ws = client.open_by_key(BUFFER_SHEET_ID).sheet1
log_ws = client.open_by_key(LOG_SHEET_ID).sheet1

# =====================================================
# LOAD DATA
# =====================================================
def load_buffer():
    return pd.DataFrame(buffer_ws.get_all_records())

def save_buffer(df):
    buffer_ws.clear()
    buffer_ws.update([df.columns.values.tolist()] + df.values.tolist())

buffer_df = load_buffer()

# =====================================================
# SIDEBAR MENU
# =====================================================
st.sidebar.title("📦 BUFFER SYSTEM")
st.sidebar.markdown(f"**USER:** {USER}")
st.sidebar.markdown(f"**ROLE:** {ROLE}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

# =====================================================
# DASHBOARD
# =====================================================
if menu == "DASHBOARD":
    st.title("📊 Dashboard")

    total_items = len(buffer_df)
    total_qty = buffer_df["QTY"].sum()
    low_stock = buffer_df[buffer_df["QTY"] <= buffer_df["MIN_QTY"]]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Items", total_items)
    col2.metric("Total Quantity", total_qty)
    col3.metric("Low Stock Items", len(low_stock))

    st.subheader("⚠️ Low Stock Alert")
    st.dataframe(low_stock, use_container_width=True)

# =====================================================
# FULL BUFFER STOCK
# =====================================================
elif menu == "FULL BUFFER STOCK":
    st.title("📦 Full Buffer Stock")
    st.dataframe(buffer_df, use_container_width=True)

# =====================================================
# STOCK IN
# =====================================================
elif menu == "STOCK IN":
    st.title("⬆️ Stock IN")

    part = st.selectbox("PART CODE", buffer_df["PART_CODE"].unique())
    qty = st.number_input("IN QTY", min_value=1, step=1)

    if st.button("ADD STOCK"):
        idx = buffer_df[buffer_df["PART_CODE"] == part].index[0]
        buffer_df.loc[idx, "QTY"] += qty

        save_buffer(buffer_df)

        log_ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            part,
            "IN",
            qty,
            USER
        ])

        st.success("Stock Added Successfully ✅")

# =====================================================
# STOCK OUT (ERROR FIXED)
# =====================================================
elif menu == "STOCK OUT":
    st.title("⬇️ Stock OUT")

    part = st.selectbox("PART CODE", buffer_df["PART_CODE"].unique())
    row = buffer_df[buffer_df["PART_CODE"] == part].iloc[0]
    current = int(row["QTY"])

    st.info(f"Current Stock: {current}")

    if current <= 0:
        st.error("❌ Stock is ZERO. OUT not allowed.")
    else:
        qty = st.number_input(
            "OUT QTY",
            min_value=1,
            max_value=current,
            step=1
        )

        if st.button("REMOVE STOCK"):
            idx = buffer_df[buffer_df["PART_CODE"] == part].index[0]
            buffer_df.loc[idx, "QTY"] -= qty

            save_buffer(buffer_df)

            log_ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                part,
                "OUT",
                qty,
                USER
            ])

            st.success("Stock Removed Successfully ✅")

# =====================================================
# REPORT
# =====================================================
elif menu == "REPORT":
    st.title("📑 Stock Movement Report")

    report_df = pd.DataFrame(log_ws.get_all_records())
    st.dataframe(report_df, use_container_width=True)

    csv = report_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Report",
        csv,
        "stock_report.csv",
        "text/csv"
    )
