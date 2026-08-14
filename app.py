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

# --- 2. DATA FETCHING (ONLINE SHAREPOINT DIRECT LINK) ---
RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        try:
            dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="pyxlsb")
        except Exception:
            try:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="openpyxl")
            except Exception:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        fetch_time = datetime.datetime.now(ist_timezone).strftime("%d %b %Y, %I:%M %p")
        
        return dfs, None, fetch_time
    except Exception as e:
        return None, str(e), None

with st.spinner("Connecting to database..."):
    dfs, error, last_update = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

# --- 3. LOGIN CREDENTIAL SYSTEM ---
if "Users" not in dfs:
    st.error("❌ Could not find the 'Users' sheet in your Excel file. Please add it with columns: Name, user_id, password.")
    st.stop()

df_users = dfs["Users"].copy()
df_users.columns = df_users.columns.astype(str).str.strip().str.lower()

col_map = {}
for col in df_users.columns:
    if "name" in col:
        col_map["Name"] = col
    elif "user" in col or "id" in col:
        col_map["user_id"] = col
    elif "pass" in col:
        col_map["password"] = col

df_users = df_users.rename(columns={
    col_map["Name"]: "Name",
    col_map["user_id"]: "user_id",
    col_map["password"]: "password"
})

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_name"] = ""

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
        .stApp { background-color: #0f172a !important; }
        [data-testid="stForm"] { background: rgba(30, 41, 59, 0.7) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 40px 30px !important; border-radius: 20px !important; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important; }
        [data-testid="stForm"] img { max-width: 120px !important; display: block; margin: 0 auto; }
        .stTextInput label { color: #94a3b8 !important; font-weight: 500; font-size: 13px; }
        .stTextInput input { background-color: rgba(15, 23, 42, 0.6) !important; color: #f8fafc !important; border-radius: 10px !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 12px 14px !important; transition: all 0.3s ease; }
        .stTextInput input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        .stButton button { width: 100%; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border-radius: 10px; font-weight: 600; padding: 12px; border: none; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); transition: all 0.3s ease; }
        .stButton button:hover { background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4); color: white; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            col_img1, col_img2, col_img3 = st.columns([1.5, 1, 1.5])
            with col_img2:
                try:
                    st.image("logo.png", use_container_width=True)
                except Exception:
                    pass
            st.markdown("<h2 style='color: #f8fafc; text-align: center; margin-top: 5px; margin-bottom: 5px; font-size: 24px; font-weight: 700;'>Welcome Back</h2>", unsafe_allow_html=True)
            input_user = st.text_input("User ID", placeholder="Enter your User ID")
            input_pass = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_btn = st.form_submit_button("Sign In")
            
            if submit_btn:
                user_match = df_users[
                    (df_users["user_id"].astype(str).str.strip() == str(input_user).strip()) & 
                    (df_users["password"].astype(str).str.strip() == str(input_pass).strip())
                ]
                if not user_match.empty:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = user_match.iloc[0]["Name"]
                    
                    # Log yearly entry
                    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                    now = datetime.datetime.now(ist)
                    log_data = pd.DataFrame([{
                        "Year": now.year, 
                        "Date": now.strftime("%Y-%m-%d"), 
                        "Time": now.strftime("%H:%M:%S"), 
                        "Name": st.session_state["user_name"], 
                        "User_ID": input_user
                    }])
                    csv_file = "login_logs.csv"
                    log_data.to_csv(csv_file, mode='a', header=not os.path.exists(csv_file), index=False, encoding='utf-8')
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
    st.stop()

# --- MAIN DASHBOARD STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; display: block; }
    .custom-dashboard-table { width: 100%; table-layout: auto; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; font-size: 8.5px; }
    .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #D9D9D9; padding: 3px 2px; text-align: center; white-space: nowrap !important; }
    .custom-dashboard-table th { background-color: #D9E1F2; color: #000000; font-weight: bold; border-bottom: 2px solid #8EA9DB; font-size: 8px; white-space: nowrap !important; }
    .subtotal-row { font-weight: bold; color: #000000; background-color: #F2F2F2; font-size: 8px; }
    .brand-row { background-color: #FFFFFF; color: #000000; }
    .brand-col-text { text-align: left !important; padding-left: 4px !important; font-size: 8px; white-space: nowrap !important; color: #000000; }
    .seg-col-text { text-align: left !important; line-height: 1.1; font-size: 8px; white-space: nowrap !important; color: #000000; }
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

# --- REMAINING DASHBOARD LOGIC (Volume, MS%, Hierarchy Tables) ---
# [Ensure your existing generate_html_table and generate_hierarchy_table_1/2/3 functions remain here]
