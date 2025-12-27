import streamlit as st
import pandas as pd
from datetime import datetime
from auth import authenticate
import os
from io import BytesIO
import gdown

# ================= PAGE CONFIG =================
st.set_page_config("BUFFER STOCK MANAGEMENT SYSTEM v3.2", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.card{background:white;padding:22px;border-radius:16px;
box-shadow:0 8px 25px rgba(0,0,0,0.12);margin-bottom:18px}
.header{font-size:26px;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ================= MASTER DATA =================
DELIVERY_TAT = ["Same Day","24 Hours","48 Hours","72 Hours"]
FLOOR_LIST = ["Ground Floor","1st Floor","2nd Floor","3rd Floor"]

# ================= FILE CONFIG =================
DATA_DIR="data"
BUFFER_FILE=f"{DATA_DIR}/buffer_stock.xlsx"
LOG_FILE=f"{DATA_DIR}/in_out_log.xlsx"
os.makedirs(DATA_DIR,exist_ok=True)

def drive_download(fid,path):
    if not os.path.exists(path):
        gdown.download(f"https://drive.google.com/uc?id={fid}",path,quiet=True)

drive_download("16qT02u7QKi7GrDHwczq99OjhCsFyay_h",BUFFER_FILE)
drive_download("1ThuZsaJsunOs46-teJTkgLs9KkctNwhS",LOG_FILE)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

if not st.session_state.login:
    st.title("🔐 LOGIN")
    user=st.selectbox("USER",["TSD","HOD"])
    pwd=st.text_input("PASSWORD",type="password")
    if st.button("LOGIN"):
        ok,role=authenticate(user,pwd)
        if ok:
            st.session_state.login=True
            st.session_state.user=user
            st.rerun()
        else:
            st.error("INVALID LOGIN")
    st.stop()

# ================= LOAD DATA =================
@st.cache_data(ttl=5)
def load_buffer():
    df=pd.read_excel(BUFFER_FILE)
    df["GOOD QTY."]=pd.to_numeric(df["GOOD QTY."],errors="coerce").fillna(0)
    return df

@st.cache_data(ttl=5)
def load_log():
    df=pd.read_excel(LOG_FILE)
    df["DATE"]=pd.to_datetime(df["DATE"],errors="coerce")
    return df

buffer_df=load_buffer()
log_df=load_log()

# ================= SELECT OR ADD =================
def select_or_add(label,default,df,col):
    excel_vals=df[col].dropna().astype(str).unique().tolist() if col in df.columns else []
    values=sorted(set(default+excel_vals))
    choice=st.selectbox(label,values+["➕ Add New"])
    return st.text_input(f"Enter {label}") if choice=="➕ Add New" else choice

# ================= DOWNLOAD =================
def to_excel(df):
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        df.to_excel(w,index=False)
    return out.getvalue()

# ================= SIDEBAR =================
menu=st.sidebar.radio("MENU",[
    "DASHBOARD","FULL BUFFER STOCK","STOCK IN","STOCK OUT","REPORT"
])

# ================= DASHBOARD =================
if menu=="DASHBOARD":
    st.markdown("<div class='card header'>📊 Dashboard</div>",unsafe_allow_html=True)

    c1,c2,c3=st.columns(3)
    c1.metric("TOTAL STOCK",int(buffer_df["GOOD QTY."].sum()))
    c2.metric("TOTAL IN",int(log_df["IN QTY"].sum()))
    c3.metric("TOTAL OUT",int(log_df["OUT QTY"].sum()))

    st.subheader("⚠ LOW STOCK ALERT")
    st.dataframe(buffer_df[buffer_df["GOOD QTY."]<5],use_container_width=True)

# ================= STOCK IN =================
elif menu=="STOCK IN":
    part=st.selectbox("PART CODE",buffer_df["PART CODE"].dropna().unique())
    row=buffer_df[buffer_df["PART CODE"]==part].iloc[0]

    base=row["MATERIAL ASSIGNING BASE"]
    desc=row["DESCRIPTION"]
    typ=row["TYPE"]
    prev=int(row["GOOD QTY."])

    st.info(f"CURRENT STOCK : {prev}")
    st.write(f"**BASE:** {base} | **TYPE:** {typ}")

    qty=st.number_input("IN QTY",1)
    tat=select_or_add("DELIVERY TAT",DELIVERY_TAT,log_df,"DELIVERY TAT")
    hod=select_or_add("APPLICANT HOD",[],log_df,"APPLICANT HOD")
    hand=select_or_add("HANDOVER PERSON",[],log_df,"HANDOVER PERSON")
    floor=select_or_add("FLOOR",FLOOR_LIST,log_df,"FLOOR")
    remark=st.text_area("REMARK")

    if st.button("ADD STOCK"):
        idx=row.name
        buffer_df.at[idx,"GOOD QTY."]=prev+qty
        buffer_df.to_excel(BUFFER_FILE,index=False)

        log_df.loc[len(log_df)]=[
            datetime.today(),datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1],"",
            tat,base,desc,typ,part,
            prev,qty,0,prev+qty,
            hod,hand,st.session_state.user,
            floor,remark,st.session_state.user
        ]
        log_df.to_excel(LOG_FILE,index=False)
        st.cache_data.clear()
        st.success("STOCK IN SUCCESS")
        st.rerun()

# ================= STOCK OUT =================
elif menu=="STOCK OUT":
    part=st.selectbox("PART CODE",buffer_df["PART CODE"].dropna().unique())
    row=buffer_df[buffer_df["PART CODE"]==part].iloc[0]
    prev=int(row["GOOD QTY."])

    if prev<=0:
        st.warning("NO STOCK AVAILABLE")
        st.stop()

    qty=st.number_input("OUT QTY",1,max_value=prev)
    tat=select_or_add("DELIVERY TAT",DELIVERY_TAT,log_df,"DELIVERY TAT")
    hod=select_or_add("APPLICANT HOD",[],log_df,"APPLICANT HOD")
    hand=select_or_add("HANDOVER PERSON",[],log_df,"HANDOVER PERSON")
    floor=select_or_add("FLOOR",FLOOR_LIST,log_df,"FLOOR")
    remark=st.text_area("REMARK")

    if st.button("REMOVE STOCK"):
        idx=row.name
        buffer_df.at[idx,"GOOD QTY."]=prev-qty
        buffer_df.to_excel(BUFFER_FILE,index=False)

        log_df.loc[len(log_df)]=[
            datetime.today(),datetime.today().strftime("%Y-%m"),
            datetime.today().isocalendar()[1],"",
            tat,row["MATERIAL ASSIGNING BASE"],
            row["DESCRIPTION"],row["TYPE"],part,
            prev,0,qty,prev-qty,
            hod,hand,st.session_state.user,
            floor,remark,st.session_state.user
        ]
        log_df.to_excel(LOG_FILE,index=False)
        st.cache_data.clear()
        st.success("STOCK OUT SUCCESS")
        st.rerun()

# ================= REPORT =================
elif menu=="REPORT":
    st.dataframe(log_df,use_container_width=True)
    st.download_button("⬇ DOWNLOAD REPORT",to_excel(log_df),"IN_OUT_REPORT.xlsx")
