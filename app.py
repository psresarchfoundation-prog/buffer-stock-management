import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="BUFFER STOCK MANAGEMENT SYSTEM",
    layout="wide"
)

# ---------------- GLOBAL STYLE ----------------
st.markdown("""
<style>
body {
    background-color: #f4f6f9;
}
.card {
    background: white;
    padding: 25px;
    border-radius: 16px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    margin-bottom: 20px;
}
.header {
    font-size: 32px;
    font-weight: 700;
}
.sub {
    color: gray;
}
</style>
""", unsafe_allow_html=True)

# ---------------- FILE CONFIG ----------------
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
    df = pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."] = pd.to_numeric(df["GOOD QTY."], errors="coerce")
    return df

def load_log():
    if not os.path.exists(LOG_FILE):
        cols = [
            "DATE","TIME","MONTH","WEEK",
            "GATE PASS NO","DELIVERY TAT","MATERIAL ASSIGNING BASE",
            "DESCRIPTION","TYPE","PART CODE",
            "PREVIOUS STOCK","IN QTY","OUT QTY","BALANCE",
            "APPLICANT HOD","HANDOVER PERSON","OPERATOR",
            "FLOOR","REMARK","USER"
        ]
        pd.DataFrame(columns=cols).to_excel(LOG_FILE, index=False)
    df = pd.read_excel(LOG_FILE)
    df["IN QTY"] = pd.to_numeric(df["IN QTY"], errors="coerce")
    df["OUT QTY"] = pd.to_numeric(df["OUT QTY"], errors="coerce")
    return df

buffer_df = load_buffer()
log_df = load_log()

# ---------------- EXCEL DOWNLOAD ----------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"USER : {st.session_state.user}")
st.sidebar.info(f"ROLE : {st.session_state.role}")

menu = st.sidebar.radio(
    "MENU",
    ["DASHBOARD", "FULL BUFFER STOCK", "STOCK IN", "STOCK OUT", "REPORT"]
)

# ================= DASHBOARD =================
if menu == "DASHBOARD":
    st.markdown("""
    <div class="card">
        <div class="header">Tools & Equipments Report</div>
        <hr>
        <b>Confidentiality :</b> INTERNAL USE<br>
        <b>Owner :</b> 叶芳<br>
        <b>Prepared by :</b> 客户服务中心 CC<br>
        <b>Release Date :</b> 2024
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 TOTAL STOCK", int(buffer_df["GOOD QTY."].sum()))
    c2.metric("📥 TOTAL IN", int(log_df["IN QTY"].sum()))
    c3.metric("📤 TOTAL OUT", int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ LOW STOCK ALERT")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."] < 5], use_container_width=True)

    st.subheader("🕒 RECENT ACTIVITY")
    st.dataframe(log_df.tail(5), use_container_width=True)

# ================= FULL BUFFER =================
elif menu == "FULL BUFFER STOCK":
    st.markdown("<div class='card'><h3>📦 FULL BUFFER STOCK</h3></div>", unsafe_allow_html=True)
    st.dataframe(buffer_df, use_container_width=True)
    st.download_button("⬇️ DOWNLOAD BUFFER", to_excel(buffer_df), "BUFFER.xlsx")

# ================= STOCK IN =================
elif menu == "STOCK IN":
    st.markdown("<div class='card'><h3>📥 STOCK IN</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    st.info(f"CURRENT STOCK : {int(row['GOOD QTY.'])}")
    qty = st.number_input("IN QTY", min_value=1)

    gate = st.text_input("GATE PASS NO")
    tat = st.text_input("DELIVERY TAT")
    base = st.text_input("MATERIAL ASSIGNING BASE")

    applicant = st.text_input("APPLICANT HOD", value="Mr. Rishu Khanna")
    handover = st.text_input("HANDOVER PERSON")
    operator = st.text_input("OPERATOR")
    floor = st.text_input("FLOOR")
    remark = st.text_area("REMARK")

    if st.button("✅ ADD STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]

        buffer_df.at[idx, "GOOD QTY."] += qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today().date(),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            gate, tat, base,
            row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"], part,
            prev, qty, 0, prev + qty,
            applicant, handover, operator, floor, remark,
            st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("STOCK IN UPDATED")

# ================= STOCK OUT =================
elif menu == "STOCK OUT":
    st.markdown("<div class='card'><h3>📤 STOCK OUT</h3></div>", unsafe_allow_html=True)

    part = st.selectbox("PART CODE", buffer_df["PART CODE"].dropna())
    row = buffer_df[buffer_df["PART CODE"] == part].iloc[0]

    current = int(row["GOOD QTY."])
    st.info(f"CURRENT STOCK : {current}")

    if current <= 0:
        st.error("NO STOCK AVAILABLE")
        st.stop()

    qty = st.number_input("OUT QTY", min_value=1, max_value=current)

    gate = st.text_input("GATE PASS NO")
    tat = st.text_input("DELIVERY TAT")
    base = st.text_input("MATERIAL ASSIGNING BASE")

    applicant = st.text_input("APPLICANT HOD", value="Mr. Rishu Khanna")
    handover = st.text_input("HANDOVER PERSON")
    operator = st.text_input("OPERATOR")
    floor = st.text_input("FLOOR")
    remark = st.text_area("REMARK")

    if st.button("❌ REMOVE STOCK"):
        idx = buffer_df[buffer_df["PART CODE"] == part].index[0]
        prev = buffer_df.at[idx, "GOOD QTY."]

        buffer_df.at[idx, "GOOD QTY."] -= qty
        buffer_df.to_excel(BUFFER_FILE, index=False)

        log_df.loc[len(log_df)] = [
            datetime.today().date(),
            datetime.now().strftime("%H:%M:%S"),
            datetime.today().strftime("%B"),
            datetime.today().isocalendar()[1],
            gate, tat, base,
            row["MATERIAL DESCRIPTION (CHINA)"], row["TYPES"], part,
            prev, 0, qty, prev - qty,
            applicant, handover, operator, floor, remark,
            st.session_state.user
        ]

        log_df.to_excel(LOG_FILE, index=False)
        st.success("STOCK OUT UPDATED")

# ================= REPORT =================
elif menu == "REPORT":
    st.markdown("<div class='card'><h3>📊 IN / OUT REPORT</h3></div>", unsafe_allow_html=True)
    st.dataframe(log_df, use_container_width=True)
    st.download_button("⬇️ DOWNLOAD REPORT", to_excel(log_df), "IN_OUT_REPORT.xlsx")
