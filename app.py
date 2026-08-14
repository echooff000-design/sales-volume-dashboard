import streamlit as st
import pandas as pd
import requests
import io
import datetime
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="WB Sale Data", page_icon="logo.png", layout="wide")

# --- HIDE STREAMLIT BRANDING ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        try:
            dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="pyxlsb")
        except:
            try:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="openpyxl")
            except:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        fetch_time = datetime.datetime.now(ist_timezone).strftime("%d %b %Y, %I:%M %p")
        return dfs, None, fetch_time
    except Exception as e:
        return None, str(e), None

with st.spinner("Connecting..."):
    dfs, error, last_update = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

# --- 3. LOGIN & LOGGING ---
df_users = dfs["Users"].copy()
df_users.columns = df_users.columns.astype(str).str.strip().str.lower()
df_users = df_users.rename(columns={col: col.replace(" ", "_") for col in df_users.columns})

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_name"] = ""

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
        .stApp { background-color: #0f172a !important; }
        [data-testid="stForm"] { background: rgba(30, 41, 59, 0.7) !important; backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 40px !important; border-radius: 20px !important; }
        [data-testid="stForm"] img { display: block; margin: 0 auto; max-width: 120px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.image("logo.png")
            input_user = st.text_input("User ID")
            input_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                user_match = df_users[(df_users["user_id"].astype(str).str.strip() == str(input_user).strip()) & (df_users["password"].astype(str).str.strip() == str(input_pass).strip())]
                if not user_match.empty:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = user_match.iloc[0]["name"]
                    # Log yearly entry
                    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
                    log_entry = pd.DataFrame([{"Year": now.year, "Date": now.strftime("%Y-%m-%d"), "Time": now.strftime("%H:%M:%S"), "Name": st.session_state["user_name"], "User_ID": input_user}])
                    log_entry.to_csv("login_logs.csv", mode='a', header=not os.path.exists("login_logs.csv"), index=False, encoding='utf-8')
                    st.rerun()
    st.stop()

# --- 4. MAIN DASHBOARD ---
st.markdown("""
    <style>
    .stApp { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .stTabs [data-baseweb="tab-list"] button div p, .stTabs [data-baseweb="tab-list"] button span, .stTabs [data-baseweb="tab"] p { color: #ef4444 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] div p, .stTabs [data-baseweb="tab"][aria-selected="true"] span, .stTabs [data-baseweb="tab"][aria-selected="true"] p { color: #ef4444 !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #ef4444 !important; }
    .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; display: block; }
    .custom-dashboard-table { width: 100%; table-layout: auto; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; font-size: 8.5px; }
    .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #D9D9D9; padding: 3px 2px; text-align: center; white-space: nowrap !important; }
    .custom-dashboard-table th { background-color: #D9E1F2; color: #000000; font-weight: bold; border-bottom: 2px solid #8EA9DB; font-size: 8px; }
    .subtotal-row { font-weight: bold; color: #000000; background-color: #F2F2F2; font-size: 8px; }
    .brand-row { background-color: #FFFFFF; color: #000000; }
    .brand-col-text { text-align: left !important; padding-left: 4px !important; font-size: 8px; white-space: nowrap !important; }
    .seg-col-text { text-align: left !important; line-height: 1.1; font-size: 8px; white-space: nowrap !important; }
    .grand-total-row { background-color: #D9E1F2; color: #000000; font-weight: bold; font-size: 9px; border-top: 2px solid #8EA9DB; white-space: nowrap !important; }
    </style>
""", unsafe_allow_html=True)

# Sidebar Admin Panel
st.sidebar.markdown("📁 **Data Source**")
if last_update: st.sidebar.caption(f"🕒 **Last Synced:** {last_update}")
if st.sidebar.button("🔄 Refresh Data Now"): st.cache_data.clear(); st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Admin Panel**")
if os.path.exists("login_logs.csv"):
    with open("login_logs.csv", "rb") as f:
        st.sidebar.download_button("📥 Download Full Yearly Logs", f, "full_yearly_login_logs.csv", "text/csv")

# Logic omitted for brevity (same as previous)
# Ensure you maintain the functions: generate_html_table, generate_hierarchy_table_1/2/3
