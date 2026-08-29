import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import io
import datetime
import os
import base64
import re
import json
import extra_streamlit_components as stx
import gspread
from google.oauth2.service_account import Credentials

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="WB Sale Data", page_icon="logo.png", layout="wide")

# --- HIDE STREAMLIT BRANDING & FIX SIDEBAR / BUTTON / TABLE / TAB CSS FOR MOBILE ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* --- FORCE SIDEBAR TO STAY DARK & PRESERVE MATERIAL ICONS --- */
            [data-testid="stSidebar"] {
                background-color: #0f172a !important;
                border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
                font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
            }
            [data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]):not(i):not(svg):not(span[class*="material"]):not(span[class*="icon"]) {
                color: #f8fafc !important;
                font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
            }
            [data-testid="stSidebar"] a {
                color: #60a5fa !important;
            }
            
            /* --- FIX SIDEBAR BUTTONS & DOWNLOAD BUTTONS VISIBILITY IN LIGHT/NORMAL MODE --- */
            [data-testid="stSidebar"] .stButton button, 
            [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
                background-color: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.25) !important;
                border-radius: 8px !important;
                width: 100% !important;
            }
            [data-testid="stSidebar"] .stButton button p, 
            [data-testid="stSidebar"] [data-testid="stDownloadButton"] button p,
            [data-testid="stSidebar"] .stButton button span, 
            [data-testid="stSidebar"] [data-testid="stDownloadButton"] button span {
                color: #ffffff !important;
                font-weight: 600 !important;
            }
            [data-testid="stSidebar"] .stButton button:hover, 
            [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
                background-color: #334155 !important;
                border-color: #3b82f6 !important;
                color: #ffffff !important;
            }
            
            /* --- RESPONSIVE MOBILE FIXES FOR TABS --- */
            .stTabs [data-baseweb="tab-list"] {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 4px !important;
            }
            
            /* --- FREEZE PANE STICKY COLUMN STYLING --- */
            .table-wrapper th:first-child,
            .table-wrapper td:first-child {
                position: sticky !important;
                left: 0 !important;
                z-index: 2 !important;
                background-color: #F2F2F2 !important;
                border-right: 1px solid #d3d3d3 !important;
            }
            .table-wrapper th:first-child {
                background-color: #D9E1F2 !important;
                z-index: 3 !important;
            }
            .custom-dashboard-table .brand-row td:first-child {
                background-color: #FFFFFF !important;
            }
            .custom-dashboard-table .subtotal-row td:first-child {
                background-color: #F2F2F2 !important;
            }
            .custom-dashboard-table .grand-total-row td:first-child {
                background-color: #D9E1F2 !important;
            }
            
            /* --- STANDARD CALIBRI FONT & CLEAN TABLE STYLING --- */
            .table-wrapper { 
                width: 100%; 
                overflow-x: auto; 
                -webkit-overflow-scrolling: touch; 
                margin-bottom: 20px; 
                display: block; 
                touch-action: pan-x pan-y pinch-zoom !important;
            }
            .custom-dashboard-table {
                width: 100%;
                border-collapse: collapse !important;
                font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
                background-color: #ffffff !important;
                color: #000000 !important;
                font-size: 13.5px !important;
                border: 1px solid #d3d3d3 !important;
                touch-action: pan-x pan-y pinch-zoom !important;
            }
            .custom-dashboard-table th, .custom-dashboard-table td {
                border: 1px solid #d3d3d3 !important;
                padding: 6px 8px !important;
                text-align: center; 
                white-space: nowrap !important;
            }
            .custom-dashboard-table th {
                background-color: #D9E1F2 !important;
                border-bottom: 2px solid #b0b0b0 !important;
                font-weight: 700 !important;
                font-size: 13.5px !important;
            }
            .subtotal-row { 
                font-weight: bold !important; 
                color: #000000 !important; 
                background-color: #F2F2F2 !important; 
                font-size: 13.5px !important; 
            }
            .brand-row { 
                background-color: #FFFFFF !important; 
                color: #000000 !important; 
                font-size: 13px !important; 
            }
            .brand-col-text { 
                text-align: left !important; 
                padding-left: 8px !important; 
                font-size: 13px !important; 
                white-space: nowrap !important; 
                color: #000000 !important; 
            }
            .seg-col-text { 
                text-align: left !important; 
                padding-left: 8px !important; 
                line-height: 1.2 !important; 
                font-size: 13.5px !important; 
                white-space: nowrap !important; 
                color: #000000 !important; 
            }
            .grand-total-row { 
                background-color: #D9E1F2 !important; 
                color: #000000 !important; 
                font-weight: bold !important; 
                font-size: 14px !important; 
                border-top: 2px solid #b0b0b0 !important; 
                white-space: nowrap !important; 
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS CONNECTION HANDLER ---
SHEET_ID = "1iEBhkOnErBiWiXgl74dYV3fYxLJvCKnff8ptkxHZ8eo"

def get_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# --- 3. COOKIE MANAGER & 11:59 PM IST EXPIRATION HELPERS ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get_current_session_cycle_date(now_ist):
    return now_ist.date().strftime("%Y-%m-%d")

def get_seconds_until_next_1159_pm(now_ist):
    target_today = now_ist.replace(hour=23, minute=59, second=0, microsecond=0)
    if now_ist < target_today:
        next_cutoff = target_today
    else:
        next_cutoff = target_today + datetime.timedelta(days=1)
    diff = int((next_cutoff - now_ist).total_seconds())
    return max(diff, 60)

# --- 4. EXCEL EXPORT HELPER FUNCTION ---
def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 5. DATA FETCHING (FROM STREAMLIT SECRETS WITH STABLE TTL CACHING) ---
RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

if "HISTORICAL_SHAREPOINT_URL" in st.secrets:
    RAW_HISTORICAL_URL = st.secrets["HISTORICAL_SHAREPOINT_URL"].split("?")[0] + "?download=1"
else:
    RAW_HISTORICAL_URL = "https://tilaknagarindustries-my.sharepoint.com/:x:/g/personal/andebnath_tilind_com/IQDgm_kiCV5STbn_ziAyo8_pARvUsuNLyey3WIKNVlXXCSM?download=1"

@st.cache_data(ttl=3600, show_spinner=False)
def load_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="pyxlsb")
        except Exception:
            try:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="openpyxl")
            except Exception:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        
        return dfs, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=3600, show_spinner=False)
def load_historical_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="pyxlsb")
        except Exception:
            try:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine="openpyxl")
            except Exception:
                dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        return dfs, None
    except Exception as e:
        return None, str(e)

with st.spinner("Connecting to database..."):
    dfs, error = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

# --- 6. LOGIN CREDENTIAL & EXACT F2 DATE EXTRACTOR ---
if "Users" not in dfs:
    st.error("❌ Could not find the 'Users' sheet in your Excel file. Please add it with columns: Name, user_id, password.")
    st.stop()

raw_users_df = dfs["Users"].copy()

def extract_f2_date(df_u):
    raw_val = None
    date_col = next((c for c in df_u.columns if 'date' in str(c).strip().lower()), None)
    if date_col is not None and len(df_u) > 0:
        raw_val = df_u[date_col].iloc[0]
    
    if (pd.isna(raw_val) or raw_val is None or str(raw_val).strip() == "") and df_u.shape[1] >= 6 and len(df_u) > 0:
        raw_val = df_u.iloc[0, 5]
        
    if pd.notna(raw_val) and str(raw_val).strip() != "":
        if isinstance(raw_val, (datetime.datetime, datetime.date, pd.Timestamp)):
            return int(raw_val.day), raw_val.strftime("%d %b %Y"), pd.Timestamp(raw_val)
        
        try:
            num_val = float(str(raw_val).strip())
            if num_val > 30000:
                dt = pd.to_datetime(num_val, unit='D', origin='1899-12-30')
                return int(dt.day), dt.strftime("%d %b %Y"), dt
        except Exception:
            pass
        
        val_str = str(raw_val).strip()
        parsed_dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
        if pd.notna(parsed_dt):
            return int(parsed_dt.day), parsed_dt.strftime("%d %b %Y"), parsed_dt
            
        match = re.search(r'\b(\d{1,2})\b', val_str)
        if match:
            day_num = int(match.group(1))
            dt = datetime.datetime(2026, 8, day_num)
            return day_num, dt.strftime("%d %b %Y"), dt
            
    today_dt = datetime.datetime.now(IST)
    return today_dt.day, today_dt.strftime("%d %b %Y"), pd.Timestamp(today_dt)

days_elapsed, f2_display_date, f2_dt_object = extract_f2_date(raw_users_df)

# --- DYNAMIC MONTH NAME GENERATOR HELPERS ---
def get_previous_month_dt(dt, months_back):
    y = dt.year
    m = dt.month - months_back
    while m <= 0:
        m += 12
        y -= 1
    return datetime.datetime(y, m, 1)

tm_label = f2_dt_object.strftime("%b")
lm_label = get_previous_month_dt(f2_dt_object, 1).strftime("%b")
m2_label = get_previous_month_dt(f2_dt_object, 2).strftime("%b")
m3_label = get_previous_month_dt(f2_dt_object, 3).strftime("%b")
m4_label = get_previous_month_dt(f2_dt_object, 4).strftime("%b")
m5_label = get_previous_month_dt(f2_dt_object, 5).strftime("%b")

df_users = raw_users_df.copy()
name_idx = 0
user_idx = 1 if df_users.shape[1] > 1 else 0
pass_idx = 2 if df_users.shape[1] > 2 else 0
role_idx = 3 if df_users.shape[1] > 3 else None

for idx, col in enumerate(df_users.columns):
    c_clean = str(col).strip().lower()
    if c_clean in ["name", "emp name", "employee name", "sales rep"] and "user" not in c_clean and "id" not in c_clean:
        name_idx = idx
    elif c_clean in ["user_id", "userid", "user id", "phone", "mobile", "login id", "user_name"]:
        user_idx = idx
    elif "pass" in c_clean:
        pass_idx = idx
    elif "role" in c_clean or "admin" in c_clean:
        role_idx = idx

df_users_clean = pd.DataFrame({
    "Name": df_users.iloc[:, name_idx].astype(str).str.strip(),
    "user_id": df_users.iloc[:, user_idx].astype(str).str.strip(),
    "password": df_users.iloc[:, pass_idx].astype(str).str.strip(),
    "role": df_users.iloc[:, role_idx].astype(str).str.strip() if role_idx is not None else "User"
})

now_ist = datetime.datetime.now(IST)
active_cycle_date = get_current_session_cycle_date(now_ist)

cached_user_val = None
cached_user_cycle = None
try:
    c_val = cookie_manager.get(cookie="wb_sale_user")
    c_cycle = cookie_manager.get(cookie="wb_sale_cycle")
    if c_val and str(c_val).strip().lower() not in ["none", "nan", "null", "undefined", ""]:
        cached_user_val = str(c_val).strip()
        cached_user_cycle = str(c_cycle).strip() if c_cycle else None
except Exception:
    pass

if cached_user_val and cached_user_cycle != active_cycle_date:
    try:
        cookie_manager.delete("wb_sale_user")
        cookie_manager.delete("wb_sale_cycle")
    except Exception:
        pass
    cached_user_val = None

if "authenticated" not in st.session_state:
    if cached_user_val and cached_user_cycle == active_cycle_date:
        user_row = df_users_clean[df_users_clean["Name"].str.lower() == cached_user_val.lower()]
        if not user_row.empty and str(user_row.iloc[0]["Name"]).lower() not in ["nan", "none", ""]:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = str(user_row.iloc[0]["Name"])
            st.session_state["session_cycle"] = active_cycle_date
            is_adm = str(user_row.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
            st.session_state["is_admin"] = is_adm
        else:
            st.session_state["authenticated"] = False
            st.session_state["user_name"] = ""
            st.session_state["session_cycle"] = ""
            st.session_state["is_admin"] = False
    else:
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.session_state["session_cycle"] = ""
        st.session_state["is_admin"] = False

if st.session_state.get("authenticated", False):
    if st.session_state.get("session_cycle") != active_cycle_date:
        try:
            cookie_manager.delete("wb_sale_user")
            cookie_manager.delete("wb_sale_cycle")
        except Exception:
            pass
        st.session_state.update({"authenticated": False, "user_name": "", "session_cycle": "", "is_admin": False})
        st.rerun()

if st.session_state.get("authenticated", False) and str(st.session_state.get("user_name", "")).strip().lower() in ["nan", "none", ""]:
    try:
        cookie_manager.delete("wb_sale_user")
        cookie_manager.delete("wb_sale_cycle")
    except Exception:
        pass
    st.session_state.update({"authenticated": False, "user_name": "", "session_cycle": "", "is_admin": False})
    st.rerun()

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
        .stApp { background-color: #0f172a !important; font-family: Calibri, 'Segoe UI', Arial, sans-serif !important; }
        [data-testid="stForm"] { background: rgba(30, 41, 59, 0.7) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 40px 30px !important; border-radius: 20px !important; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important; }
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
            try:
                with open("logo.png", "rb") as img_file:
                    encoded_img = base64.b64encode(img_file.read()).decode()
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: center; width: 100%; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{encoded_img}" style="width: 100px; display: block;" />
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            except Exception:
                pass
                    
            st.markdown("<h2 style='color: #f8fafc; text-align: center; margin-top: 5px; margin-bottom: 5px; font-size: 24px; font-weight: 700;'>Welcome Back</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94a3b8; text-align: center; font-size: 13px; margin-bottom: 25px;'>Sign in to access WB Sale Data Dashboard</p>", unsafe_allow_html=True)
            
            input_user = st.text_input("User ID", placeholder="Enter your User ID")
            input_pass = st.text_input("Password", type="password", placeholder="Enter your password")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Sign In")
            
            if submit_btn:
                user_match = df_users_clean[
                    (df_users_clean["user_id"].str.lower() == str(input_user).strip().lower()) & 
                    (df_users_clean["password"] == str(input_pass).strip())
                ]
                
                if not user_match.empty:
                    real_name = str(user_match.iloc[0]["Name"]).strip()
                    if real_name.lower() in ["nan", "none", ""]:
                        real_name = str(input_user).strip()
                    
                    cur_now = datetime.datetime.now(IST)
                    cur_cycle = get_current_session_cycle_date(cur_now)
                    seconds_to_expiry = get_seconds_until_next_1159_pm(cur_now)
                    
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = real_name
                    st.session_state["session_cycle"] = cur_cycle
                    
                    is_adm = str(user_match.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
                    st.session_state["is_admin"] = is_adm
                    
                    try:
                        cookie_manager.set("wb_sale_user", real_name, max_age=seconds_to_expiry)
                        cookie_manager.set("wb_sale_cycle", cur_cycle, max_age=seconds_to_expiry)
                    except Exception:
                        pass
                    
                    try:
                        sheet = get_sheet()
                        now_log = datetime.datetime.now(IST)
                        sheet.append_row([
                            str(now_log.year),
                            now_log.strftime("%Y-%m-%d"),
                            now_log.strftime("%H:%M:%S"),
                            real_name,
                            str(input_user).strip()
                        ])
                    except Exception as e:
                        print(f"Logging error: {e}")
                    
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
    st.stop()

# --- MAIN DASHBOARD STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0f172a !important; font-family: Calibri, 'Segoe UI', Arial, sans-serif !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label { color: #f8fafc !important; font-weight: 600 !important; font-size: 13px !important; }
    
    .stTabs [data-baseweb="tab-list"] button div p, 
    .stTabs [data-baseweb="tab-list"] button span,
    .stTabs [data-baseweb="tab"] p {
        color: #ef4444 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] div p, 
    .stTabs [data-baseweb="tab"][aria-selected="true"] span,
    .stTabs [data-baseweb="tab"][aria-selected="true"] p {
        color: #ef4444 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #ef4444 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CUSTOM TITLE & LOGOUT ---
col_logo, col_title, col_logout = st.columns([1, 5, 2])
with col_logo:
    try:
        st.image("logo.png", width=60)
    except Exception:
        st.warning("logo.png missing")
with col_title:
    st.markdown("<h3 style='margin-top: 10px; font-size: 22px; color: #f8fafc; font-family: Calibri, sans-serif;'>WB Sale Data</h3>", unsafe_allow_html=True)
with col_logout:
    role_display = "Admin" if st.session_state.get("is_admin", False) else "User"
    user_display = st.session_state.get('user_name', 'User')
    st.markdown(f"<p style='text-align: right; margin-top: 10px; font-size: 13px; color: #f8fafc; font-family: Calibri, sans-serif;'>👤 <b>{user_display}</b><br><span style='color: #60a5fa; font-size: 11px;'>{role_display}</span></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        try:
            cookie_manager.delete("wb_sale_user")
            cookie_manager.delete("wb_sale_cycle")
        except Exception:
            pass
        st.session_state.update({"authenticated": False, "user_name": "", "session_cycle": "", "is_admin": False})
        st.rerun()

# --- 7. FETCH DATA FROM SHEETS ---
required_sheets = ["This Month", "Last Month", "Target Data", "Outlet Master"]
for sheet in required_sheets:
    if sheet not in dfs:
        st.error(f"❌ Could not find the sheet named '{sheet}' in your Excel file.")
        st.stop()

df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()

# --- PROCESS OUTLET MASTER FOR MAPPINGS ---
df_outlet.columns = df_outlet.columns.astype(str).str.strip()
if "Outlet Nan" in df_outlet.columns:
    df_outlet.rename(columns={"Outlet Nan": "Outlet Name"}, inplace=True)

if len(df_outlet.columns) > 7:
    group_col_name = df_outlet.columns[7]
    df_outlet.rename(columns={group_col_name: "Group"}, inplace=True)
else:
    if "Group" not in df_outlet.columns:
        df_outlet["Group"] = "Unassigned"

zone_col_map = next((col for col in df_outlet.columns if "zone" in col.lower()), None)
asm_col_map = next((col for col in df_outlet.columns if col.lower() in ["asm", "manager"]), None)
tse_col_map = df_outlet.columns[14] if len(df_outlet.columns) > 14 else next((col for col in df_outlet.columns if "tse" in col.lower()), None)

map_key = "LIC No" if "LIC No" in df_outlet.columns else ("Outlet Name" if "Outlet Name" in df_outlet.columns else None)

group_mapping, zone_mapping, asm_mapping, tse_mapping = {}, {}, {}, {}
if map_key:
    group_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet["Group"].astype(str).str.strip()))
    if zone_col_map:
        zone_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[zone_col_map].astype(str).str.strip()))
    if asm_col_map:
        asm_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[asm_col_map].astype(str).str.strip()))
    if tse_col_map:
        tse_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[tse_col_map].astype(str).str.strip()))

def standardize_df(d):
    d = d.copy()
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value", "volume": "Value", "val": "Value"}, inplace=True)
    if "Segment" in d.columns:
        d["Segment"] = d["Segment"].replace({"Deluxe Plus-Whisky": "Deluxe-Whisky"})
    if "Brand" in d.columns:
        d["Brand"] = d["Brand"].replace({"IBW": "IBDC"})
    k_col = "LIC No" if "LIC No" in d.columns else ("Outlet Name" if "Outlet Name" in d.columns else None)
    if k_col and k_col in d.columns:
        d["Group"] = d[k_col].astype(str).str.strip().map(group_mapping).fillna("Unassigned")
        if zone_mapping:
            d["Zone"] = d[k_col].astype(str).str.strip().map(zone_mapping).fillna("West Bengal")
        else:
            d["Zone"] = "West Bengal"
        if asm_mapping:
            d["ASM"] = d[k_col].astype(str).str.strip().map(asm_mapping).fillna(d.get("ASM", "Unassigned"))
        if tse_mapping:
            d["TSE"] = d[k_col].astype(str).str.strip().map(tse_mapping).fillna(d.get("TSE", "Unassigned"))
    else:
        d["Group"] = "Unassigned"
        d["Zone"] = "West Bengal"
    return d

df_this = standardize_df(df_this)
df_last = standardize_df(df_last)
df_target = standardize_df(df_target)

df_this["Metric"] = "This Month"
df_last["Metric"] = "Last Month"
df_target["Metric"] = "Target"

df_combined = pd.concat([df_this, df_last, df_target], ignore_index=True)
dim_cols = [c for c in df_combined.columns if c not in ["Metric", "Value"]]

df_raw = pd.pivot_table(
    df_combined, 
    values="Value", 
    index=dim_cols, 
    columns="Metric", 
    aggfunc="sum"
).reset_index()

if "Outlet Name" in df_raw.columns and "LIC No" in df_raw.columns:
    df_raw["Search Reference"] = df_raw["Outlet Name"].astype(str).str.strip() + " (" + df_raw["LIC No"].astype(str).str.strip() + ")"

# --- DYNAMIC OFFLINE STANDALONE HTML GENERATOR ---
@st.cache_data
def get_offline_html_bundle(df_json, user_name, user_role, tm_lbl, lm_lbl):
    records_export = []
    for row in json.loads(df_json):
        records_export.append({
            "lic": str(row.get("LIC No", "")).strip(),
            "outlet": str(row.get("Outlet Name", "")).strip(),
            "group": str(row.get("Group", "Unassigned")).strip(),
            "zone": str(row.get("Zone", "West Bengal")).strip(),
            "asm": str(row.get("ASM", "Unassigned")).strip(),
            "tse": str(row.get("TSE", "Unassigned")).strip(),
            "seg": str(row.get("Segment", "Deluxe-Whisky")).strip(),
            "brand": str(row.get("Brand", "")).strip(),
            "tm": float(row.get("This Month", 0) or 0),
            "lm": float(row.get("Last Month", 0) or 0),
            "tgt": float(row.get("Target", 0) or 0)
        })

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WB Sale Data (Offline Mode)</title>
    <style>
        * { box-sizing: border-box; }
        body { background-color: #0f172a; color: #f8fafc; font-family: Calibri, 'Segoe UI', Arial, sans-serif; margin: 0; padding: 15px; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 10px; margin-bottom: 15px; }
        .user-badge { text-align: right; font-size: 13px; color: #f8fafc; }
        .user-badge span { color: #60a5fa; font-size: 11px; }
        .card { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 14px; margin-bottom: 15px; }
        .grid-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
        label { font-size: 13px; font-weight: 600; color: #f8fafc; display: block; margin-bottom: 4px; }
        select, input { width: 100%; background-color: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 7px 10px; border-radius: 6px; font-family: Calibri, sans-serif; font-size: 13px; }
        .btn { background: #1e293b; color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.25); padding: 8px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn:hover { background: #334155; border-color: #3b82f6; }
        .btn-green { background: #10b981; border-color: #10b981; }
        .btn-red { background: #ef4444; border-color: #ef4444; }
        .tab-bar { display: flex; gap: 12px; border-bottom: 2px solid #334155; margin-bottom: 15px; overflow-x: auto; flex-wrap: wrap; }
        .tab-btn { background: none; border: none; color: #ef4444; font-size: 14px; font-weight: 600; padding: 10px 14px; cursor: pointer; white-space: nowrap; }
        .tab-btn.active { font-weight: 700; border-bottom: 3px solid #ef4444; }
        .sub-tab-bar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        .sub-tab-btn { background: #1e293b; border: 1px solid #475569; color: #94a3b8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12.5px; font-weight: 600; }
        .sub-tab-btn.active { background: #3b82f6; color: #ffffff; border-color: #3b82f6; }
        .table-wrapper { width: 100%; overflow-x: auto; margin-bottom: 20px; background: #ffffff; border: 1px solid #d3d3d3; border-radius: 4px; }
        .custom-table { width: 100%; border-collapse: collapse; font-family: Calibri, sans-serif; background-color: #ffffff; color: #000000; font-size: 13.5px; }
        .custom-table th, .custom-table td { border: 1px solid #d3d3d3; padding: 6px 8px; text-align: center; white-space: nowrap; }
        .custom-table th { background-color: #D9E1F2; border-bottom: 2px solid #b0b0b0; font-weight: 700; }
        .subtotal-row { font-weight: bold; background-color: #F2F2F2; text-align: left; }
        .brand-row { background-color: #FFFFFF; color: #000000; }
        .brand-col-text { text-align: left; padding-left: 8px; white-space: nowrap; }
        .grand-total-row { background-color: #D9E1F2; color: #000000; font-weight: bold; font-size: 14px; border-top: 2px solid #b0b0b0; }
        .highlight-green { background-color: #def7ec !important; color: #03543f !important; }
        .highlight-red { background-color: #fde8e8 !important; color: #9b1c1c !important; }
        .marked-brand { background-color: #EBF5FB; font-weight: bold; }
        .custom-table th:first-child, .custom-table td:first-child { position: sticky; left: 0; z-index: 2; background-color: #F2F2F2; border-right: 1px solid #d3d3d3; }
        .custom-table th:first-child { background-color: #D9E1F2; z-index: 3; }
    </style>
</head>
<body>
    <div id="mainDashboard">
        <div class="header-bar">
            <div>
                <h3 style="margin: 0; font-size: 22px;">WB Sale Data</h3>
                <span style="font-size: 12px; font-weight: bold; color: #10b981;">● 100% Offline Mode Active</span>
            </div>
            <div style="display: flex; gap: 15px; align-items: center;">
                <div class="user-badge">👤 <b>__USER_NAME__</b><br><span>__USER_ROLE__</span></div>
                <button class="btn btn-red" onclick="window.close()">Close</button>
            </div>
        </div>
        <div class="card">
            <h4 style="margin: 0 0 10px 0; font-size: 16px;">🔍 Filters</h4>
            <div class="grid-filters">
                <div><label>Group Filter</label><select id="selGroup" onchange="onGroupChange()"></select></div>
                <div><label>ASM Filter</label><select id="selASM" onchange="onASMChange()"></select></div>
                <div><label>TSE Filter</label><select id="selTSE" onchange="onTSEChange()"></select></div>
                <div><label>LIC No Filter</label><select id="selLIC" onchange="onLICChange()"></select></div>
                <div><label>Outlet Filter</label><select id="selOutlet" onchange="onOutletChange()"></select></div>
            </div>
        </div>
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchMainTab('tabVol')">📦 Volume</button>
            <button class="tab-btn" onclick="switchMainTab('tabMS')">📈 Ms%</button>
            <button class="tab-btn" onclick="switchMainTab('tabDash')">📊 Dashboard</button>
            <button class="tab-btn" onclick="switchMainTab('tabAsk')">💬 Ask Assistant</button>
        </div>

        <!-- TAB 1: VOLUME -->
        <div id="tabVol">
            <div class="table-wrapper"><table class="custom-table" id="tableVolume"><thead><tr><th class="brand-col-text">Brand</th><th>__LM_LBL__</th><th>TGT</th><th>__TM_LBL__</th><th>BAL</th></tr></thead><tbody id="bodyVolume"></tbody></table></div>
        </div>

        <!-- TAB 2: MS% -->
        <div id="tabMS" style="display: none;">
            <div class="table-wrapper"><table class="custom-table" id="tableMS"><thead><tr><th class="brand-col-text">Brand</th><th>__LM_LBL__</th><th>__TM_LBL__</th><th>GRW</th></tr></thead><tbody id="bodyMS"></tbody></table></div>
        </div>

        <!-- TAB 3: DASHBOARD HIERARCHIES -->
        <div id="tabDash" style="display: none;">
            <div class="sub-tab-bar">
                <button class="sub-tab-btn active" onclick="switchSubTab('subTarget')">Target vs Ach</button>
                <button class="sub-tab-btn" onclick="switchSubTab('subMS')">MS% Details</button>
                <button class="sub-tab-btn" onclick="switchSubTab('subWOD')">WOD Details</button>
            </div>
            <div id="subTarget"><div class="table-wrapper"><table class="custom-table" id="tableH1"></table></div></div>
            <div id="subMS" style="display: none;"><div class="table-wrapper"><table class="custom-table" id="tableH2"></table></div></div>
            <div id="subWOD" style="display: none;"><div class="table-wrapper"><table class="custom-table" id="tableH3"></table></div></div>
        </div>

        <!-- TAB 4: ASK ASSISTANT -->
        <div id="tabAsk" style="display: none;">
            <div class="card">
                <div class="grid-filters">
                    <div>
                        <label>Choose a Query / Analysis:</label>
                        <select id="askQuery" onchange="runAskAssistant()">
                            <option>Deluxe Industry >= 30 CS but IBDC Not Billed</option>
                            <option>Semi Premium Whisky Industry >= 50 CS but MHW Not Billed</option>
                            <option>TIL Non Billed Outlets</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="table-wrapper"><table class="custom-table" id="askTable"></table></div>
        </div>
    </div>

    <script>
        let appSales = __SALES_DATA__;

        const MASTER_STRUCTURE = [
            { seg: "Deluxe-Whisky", brands: ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak"] },
            { seg: "Semi Premium-Whisky", brands: ["MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR"] },
            { seg: "Deluxe-Gin", brands: ["BLGLM", "BLGOR", "Big Ben", "Blue Riband"] },
            { seg: "Premium-Brandy", brands: ["Monarch"] },
            { seg: "Premium-Gin", brands: ["SMG", "SMGP"] },
            { seg: "Semi Premium-Brandy", brands: ["MHFB"] },
            { seg: "Single Malt-Scotch", brands: ["SIW"] }
        ];
        const MARKED_BRANDS = ['IBDC', 'MHW', 'BLGLM', 'BLGOR', 'Monarch', 'SMG', 'SMGP', 'MHFB', 'SIW'];

        function toNum(v) { const n = parseFloat(v); return isNaN(n) ? 0 : n; }

        window.onload = function() {
            initCascadingFilters();
            updateDashboard();
        };

        function getScopedRecords(level) {
            const grp = decodeURIComponent(document.getElementById('selGroup').value || 'All');
            const asm = decodeURIComponent(document.getElementById('selASM').value || 'All');
            const tse = decodeURIComponent(document.getElementById('selTSE').value || 'All');
            const lic = decodeURIComponent(document.getElementById('selLIC').value || 'All');
            return appSales.filter(d => {
                if (level >= 1 && grp !== 'All' && d.group !== grp) return false;
                if (level >= 2 && asm !== 'All' && d.asm !== asm) return false;
                if (level >= 3 && tse !== 'All' && d.tse !== tse) return false;
                if (level >= 4 && lic !== 'All' && d.lic !== lic) return false;
                return true;
            });
        }

        function setSelectOptions(id, values) {
            const sel = document.getElementById(id);
            const prev = decodeURIComponent(sel.value || 'All');
            sel.innerHTML = '<option value="All">All</option>' + values.map(v => `<option value="${encodeURIComponent(v)}">${v}</option>`).join('');
            if (values.includes(prev)) sel.value = encodeURIComponent(prev);
            else sel.value = 'All';
        }

        function initCascadingFilters() {
            setSelectOptions('selGroup', [...new Set(appSales.map(d => d.group).filter(Boolean))].sort());
            onGroupChange();
        }

        function onGroupChange() {
            setSelectOptions('selASM', [...new Set(getScopedRecords(1).map(d => d.asm).filter(Boolean))].sort());
            onASMChange();
        }
        function onASMChange() {
            setSelectOptions('selTSE', [...new Set(getScopedRecords(2).map(d => d.tse).filter(Boolean))].sort());
            onTSEChange();
        }
        function onTSEChange() {
            setSelectOptions('selLIC', [...new Set(getScopedRecords(3).map(d => d.lic).filter(Boolean))].sort());
            onLICChange();
        }
        function onLICChange() {
            setSelectOptions('selOutlet', [...new Set(getScopedRecords(4).map(d => d.outlet).filter(Boolean))].sort());
            updateDashboard();
        }
        function onOutletChange() { updateDashboard(); }

        function getFilteredData() {
            const grp = decodeURIComponent(document.getElementById('selGroup').value || 'All');
            const asm = decodeURIComponent(document.getElementById('selASM').value || 'All');
            const tse = decodeURIComponent(document.getElementById('selTSE').value || 'All');
            const lic = decodeURIComponent(document.getElementById('selLIC').value || 'All');
            const out = decodeURIComponent(document.getElementById('selOutlet').value || 'All');

            return appSales.filter(d => {
                if (grp !== 'All' && d.group !== grp) return false;
                if (asm !== 'All' && d.asm !== asm) return false;
                if (tse !== 'All' && d.tse !== tse) return false;
                if (lic !== 'All' && d.lic !== lic) return false;
                if (out !== 'All' && d.outlet !== out) return false;
                return true;
            });
        }

        function updateDashboard() {
            const data = getFilteredData();
            renderVol(data);
            renderMS(data);
            renderHierarchies(data);
            runAskAssistant();
        }

        function renderVol(data) {
            let html = '', gtLM = 0, gtTGT = 0, gtTM = 0, gtBAL = 0;
            MASTER_STRUCTURE.forEach(group => {
                const segRecords = data.filter(d => d.seg === group.seg);
                const sLM = segRecords.reduce((a,c)=>a + toNum(c.lm), 0);
                const sTGT = segRecords.reduce((a,c)=>a + toNum(c.tgt), 0);
                const sTM = segRecords.reduce((a,c)=>a + toNum(c.tm), 0);
                html += `<tr class="subtotal-row"><td>${group.seg}</td><td>${Math.round(sLM).toLocaleString()}</td><td>${Math.round(sTGT).toLocaleString()}</td><td>${Math.round(sTM).toLocaleString()}</td><td></td></tr>`;
                group.brands.forEach(b => {
                    const bRecords = segRecords.filter(d => d.brand === b);
                    const lm = bRecords.reduce((a,c)=>a + toNum(c.lm), 0);
                    const tgt = bRecords.reduce((a,c)=>a + toNum(c.tgt), 0);
                    const tm = bRecords.reduce((a,c)=>a + toNum(c.tm), 0);
                    const isM = MARKED_BRANDS.includes(b);
                    const bal = isM ? (tgt - tm) : '';
                    if (isM) gtBAL += (tgt - tm);
                    const hl = isM ? (tm < tgt ? 'highlight-red' : 'highlight-green') : '';
                    html += `<tr class="brand-row"><td class="brand-col-text ${isM?'marked-brand':''}">${b}</td><td>${Math.round(lm).toLocaleString()}</td><td>${Math.round(tgt)}</td><td class="${hl}">${Math.round(tm).toLocaleString()}</td><td class="${hl}">${bal!==''?Math.round(bal):''}</td></tr>`;
                });
                gtLM += sLM; gtTGT += sTGT; gtTM += sTM;
            });
            html += `<tr class="grand-total-row"><td>Grand Total</td><td>${Math.round(gtLM).toLocaleString()}</td><td>${Math.round(gtTGT).toLocaleString()}</td><td>${Math.round(gtTM).toLocaleString()}</td><td>${Math.round(gtBAL)}</td></tr>`;
            document.getElementById('bodyVolume').innerHTML = html;
        }

        function renderMS(data) {
            const gtLM = data.reduce((a,c)=>a + toNum(c.lm), 0) || 1;
            const gtTM = data.reduce((a,c)=>a + toNum(c.tm), 0) || 1;
            let html = '';
            MASTER_STRUCTURE.forEach(group => {
                const segRecords = data.filter(d => d.seg === group.seg);
                const sLM = segRecords.reduce((a,c)=>a + toNum(c.lm), 0);
                const sTM = segRecords.reduce((a,c)=>a + toNum(c.tm), 0);
                const sLMPct = (sLM / gtLM) * 100;
                const sTMPct = (sTM / gtTM) * 100;
                const sGrw = sTMPct - sLMPct;
                html += `<tr class="subtotal-row"><td>${group.seg}</td><td>${sLMPct.toFixed(1)}%</td><td>${sTMPct.toFixed(1)}%</td><td>${sGrw.toFixed(1)}%</td></tr>`;
                group.brands.forEach(b => {
                    const bRecords = segRecords.filter(d => d.brand === b);
                    const lm = bRecords.reduce((a,c)=>a + toNum(c.lm), 0);
                    const tm = bRecords.reduce((a,c)=>a + toNum(c.tm), 0);
                    const bLMPct = sLM > 0 ? (lm / sLM) * 100 : 0;
                    const bTMPct = sTM > 0 ? (tm / sTM) * 100 : 0;
                    const grw = bTMPct - bLMPct;
                    html += `<tr class="brand-row"><td class="brand-col-text">${b}</td><td>${bLMPct.toFixed(1)}%</td><td>${bTMPct.toFixed(1)}%</td><td class="${grw>0?'highlight-green':(grw<0?'highlight-red':'')}">${grw.toFixed(1)}%</td></tr>`;
                });
            });
            html += `<tr class="grand-total-row"><td>Grand Total</td><td>100.0%</td><td>100.0%</td><td></td></tr>`;
            document.getElementById('bodyMS').innerHTML = html;
        }

        function calcMS(sub, brand) {
            const segs = brand === 'MHW' ? ['Semi Premium-Whisky'] : ['Deluxe-Whisky', 'Deluxe Plus-Whisky'];
            const bVal = sub.filter(d => d.brand === brand).reduce((a,c)=>a + toNum(c.tm), 0);
            const dVal = sub.filter(d => segs.includes(d.seg)).reduce((a,c)=>a + toNum(c.tm), 0);
            return dVal > 0 ? (bVal / dVal * 100) : 0.0;
        }

        function renderHierarchies(data) {
            let h1 = '<thead><tr><th rowspan="2">ZONE/ASM/TSE</th><th colspan="4">IBDC</th><th colspan="4">MHW</th></tr><tr><th>__LM_LBL__</th><th>Target</th><th>__TM_LBL__</th><th>MS%</th><th>__LM_LBL__</th><th>Target</th><th>__TM_LBL__</th><th>MS%</th></tr></thead><tbody>';
            
            function makeH1Row(name, sub, cls, pad) {
                const iLM = sub.filter(d => d.brand==='IBDC').reduce((a,c)=>a+toNum(c.lm),0);
                const iTGT = sub.filter(d => d.brand==='IBDC').reduce((a,c)=>a+toNum(c.tgt),0);
                const iTM = sub.filter(d => d.brand==='IBDC').reduce((a,c)=>a+toNum(c.tm),0);
                const iMS = calcMS(sub, 'IBDC');

                const mLM = sub.filter(d => d.brand==='MHW').reduce((a,c)=>a+toNum(c.lm),0);
                const mTGT = sub.filter(d => d.brand==='MHW').reduce((a,c)=>a+toNum(c.tgt),0);
                const mTM = sub.filter(d => d.brand==='MHW').reduce((a,c)=>a+toNum(c.tm),0);
                const mMS = calcMS(sub, 'MHW');

                return `<tr class="${cls}"><td class="brand-col-text" style="padding-left:${pad}px;">${name}</td><td>${Math.round(iLM).toLocaleString()}</td><td>${Math.round(iTGT).toLocaleString()}</td><td>${Math.round(iTM).toLocaleString()}</td><td>${iMS.toFixed(1)}%</td><td>${Math.round(mLM).toLocaleString()}</td><td>${Math.round(mTGT).toLocaleString()}</td><td>${Math.round(mTM).toLocaleString()}</td><td>${mMS.toFixed(1)}%</td></tr>`;
            }

            h1 += makeH1Row('West Bengal', data, 'grand-total-row', 8);
            const zones = [...new Set(data.map(d => d.zone).filter(Boolean))].sort();
            zones.forEach(z => {
                const zData = data.filter(d => d.zone === z);
                h1 += makeH1Row(z, zData, 'subtotal-row', 8);
                const asms = [...new Set(zData.map(d => d.asm).filter(Boolean))].sort();
                asms.forEach(a => {
                    const aData = zData.filter(d => d.asm === a);
                    h1 += makeH1Row(a, aData, 'subtotal-row', 18);
                    const tses = [...new Set(aData.map(d => d.tse).filter(Boolean))].sort();
                    tses.forEach(t => {
                        const tData = aData.filter(d => d.tse === t);
                        h1 += makeH1Row(t, tData, 'brand-row', 28);
                    });
                });
            });
            document.getElementById('tableH1').innerHTML = h1 + '</tbody>';
        }

        function runAskAssistant() {
            const data = getFilteredData();
            const uniqueOutlets = [...new Set(data.map(d => d.outlet).filter(Boolean))].sort();
            let html = '<thead><tr><th>LIC No</th><th>Outlet Name</th><th>ASM</th><th>TSE</th><th>Volume (CS)</th></tr></thead><tbody>';
            let cnt = 0;
            uniqueOutlets.forEach(out => {
                const rows = data.filter(d => d.outlet === out);
                const dVol = rows.filter(d => d.seg && d.seg.includes('Deluxe')).reduce((a,c)=>a + toNum(c.tm), 0);
                const iVol = rows.filter(d => d.brand === 'IBDC').reduce((a,c)=>a + toNum(c.tm), 0);
                if (dVol >= 30 && iVol === 0) {
                    cnt++;
                    html += `<tr><td>${rows[0].lic}</td><td style="text-align:left;">${rows[0].outlet}</td><td>${rows[0].asm}</td><td>${rows[0].tse}</td><td><b>${Math.round(dVol)}</b></td></tr>`;
                }
            });
            if (!cnt) html += '<tr><td colspan="5">🎉 No gap outlets found!</td></tr>';
            document.getElementById('askTable').innerHTML = html + '</tbody>';
        }

        function switchMainTab(id) {
            document.querySelectorAll('.tab-bar .tab-btn').forEach(b => b.classList.remove('active'));
            ['tabVol','tabMS','tabDash','tabAsk'].forEach(t => document.getElementById(t).style.display = 'none');
            document.getElementById(id).style.display = 'block';
            event.target.classList.add('active');
        }

        function switchSubTab(id) {
            document.querySelectorAll('.sub-tab-bar .sub-tab-btn').forEach(b => b.classList.remove('active'));
            ['subTarget','subMS','subWOD'].forEach(t => document.getElementById(t).style.display = 'none');
            document.getElementById(id).style.display = 'block';
            event.target.classList.add('active');
        }
    </script>
</body>
</html>"""

    return (html_template
            .replace("__USER_NAME__", str(user_name))
            .replace("__USER_ROLE__", str(user_role))
            .replace("__SALES_DATA__", json.dumps(records_export))
            .replace("__TM_LBL__", str(tm_lbl))
            .replace("__LM_LBL__", str(lm_lbl)))

# --- SIDEBAR WITH OFFLINE LAUNCHER & ADMIN PANEL ---
st.sidebar.markdown("📁 **Data Source**")
st.sidebar.caption(f"🕒 **Last Synced:** {f2_display_date}")

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Fetching newest data...")

st.sidebar.markdown("---")
st.sidebar.markdown("⚡ **Offline Capabilities**")

active_name = st.session_state.get("user_name", "User")
active_role = "Admin" if st.session_state.get("is_admin", False) else "User"

html_payload = get_offline_html_bundle(df_raw.to_json(orient="records"), active_name, active_role, tm_label, lm_label)
b64_html = base64.b64encode(html_payload.encode("utf-8")).decode("utf-8")

launch_btn_code = f"""
<div style="width: 100%;">
    <button onclick="launchOffline()" style="
        width: 100%;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 10px 14px;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        font-family: Calibri, sans-serif;
        font-size: 13.5px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
    ">
        🚀 Launch Offline Mode
    </button>
</div>
<script>
function launchOffline() {{
    const bin = atob("{b64_html}");
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) {{
        bytes[i] = bin.charCodeAt(i);
    }}
    const blob = new Blob([bytes], {{ type: 'text/html;charset=utf-8' }});
    const blobUrl = URL.createObjectURL(blob);
    window.open(blobUrl, '_blank');
}}
</script>
"""
with st.sidebar:
    components.html(launch_btn_code, height=50)
    st.caption("💡 *Works 100% offline. Bypasses login using your active session.*")

st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Admin Panel**")

if st.session_state.get("is_admin", False):
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        if len(all_rows) > 1:
            headers = all_rows[0]
            rows = all_rows[1:]
            df_logs = pd.DataFrame(rows, columns=headers)
            csv_logs = df_logs.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="📥 Download Google Sheet Logs",
                data=csv_logs,
                file_name="wb_login_logs.csv",
                mime="text/csv"
            )
        else:
            st.sidebar.info("ℹ️ Google Sheet connected. No logins recorded yet.")
    except Exception as e:
        err_msg = str(e).strip() if str(e).strip() else repr(e)
        st.sidebar.error(f"⚠️ Log Connection Error: {err_msg}")
else:
    st.sidebar.info("Logs are saved securely in Google Sheets.")

st.sidebar.markdown("---")
st.sidebar.markdown("🔗 **[Go to FTS Calculator](https://wbftscalculator.streamlit.app/)**")

# --- 8. EXACT ORDER MAPPING & DATA CONVERSION ---
num_cols = ["Last Month", "Target", "This Month"]
for col in num_cols:
    if col not in df_raw.columns:
        df_raw[col] = 0
    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

seg_col = "Segment" if "Segment" in df_raw.columns else None
brand_col = "Brand" if "Brand" in df_raw.columns else None

if not seg_col or not brand_col:
    st.error("❌ Missing 'Segment' and 'Brand' columns. Dashboard cannot group data.")
    st.stop()

explicit_seg_order = [
    "Deluxe-Whisky", "Semi Premium-Whisky", 
    "Deluxe-Gin", "Premium-Brandy", "Premium-Gin", 
    "Semi Premium-Brandy", "Single Malt-Scotch"
]
explicit_brand_order = [
    "IBDC", "N1WSUP", "OCBL", 
    "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak", 
    "MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR",
    "BLGLM", "BLGOR", "Big Ben", "Blue Riband", 
    "Monarch", 
    "SMG", "SMGP", 
    "MHFB", 
    "SIW"
]

unique_segs = df_raw[seg_col].dropna().unique().tolist()
unique_brands = df_raw[brand_col].dropna().unique().tolist()
final_seg_order = explicit_seg_order + [x for x in unique_segs if x not in explicit_seg_order]
final_brand_order = explicit_brand_order + [x for x in unique_brands if x not in explicit_brand_order]

df_raw[seg_col] = pd.Categorical(df_raw[seg_col], categories=final_seg_order, ordered=True)
df_raw[brand_col] = pd.Categorical(df_raw[brand_col], categories=final_brand_order, ordered=True)

master_brands = df_raw[[seg_col, brand_col]].drop_duplicates().dropna().sort_values(by=[seg_col, brand_col])

# --- 9. CASCADING SIDEBAR FILTERS ---
st.markdown("<h3 style='color: #f8fafc; font-size: 20px; font-family: Calibri, sans-serif;'>🔍 Filters</h3>", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)

temp_df = df_raw.copy()

with col1:
    group_options = ["All"] + sorted(temp_df["Group"].dropna().astype(str).unique().tolist()) if "Group" in temp_df.columns else ["All"]
    selected_group = st.selectbox("Group Filter", group_options)
    if selected_group != "All":
        temp_df = temp_df[temp_df["Group"].astype(str) == selected_group]

with col2:
    asm_options = ["All"] + sorted(temp_df["ASM"].dropna().astype(str).unique().tolist()) if "ASM" in temp_df.columns else ["All"]
    selected_asm = st.selectbox("ASM Filter", asm_options)
    if selected_asm != "All":
        temp_df = temp_df[temp_df["ASM"].astype(str) == selected_asm]

with col3:
    tse_options = ["All"] + sorted(temp_df["TSE"].dropna().astype(str).unique().tolist()) if "TSE" in temp_df.columns else ["All"]
    selected_tse = st.selectbox("TSE Filter", tse_options)
    if selected_tse != "All":
        temp_df = temp_df[temp_df["TSE"].astype(str) == selected_tse]

with col4:
    lic_options = ["All"] + sorted(temp_df["LIC No"].dropna().astype(str).unique().tolist()) if "LIC No" in temp_df.columns else ["All"]
    selected_lic = st.selectbox("LIC No Filter", lic_options)
    if selected_lic != "All":
        temp_df = temp_df[temp_df["LIC No"].astype(str) == selected_lic]

with col5:
    outlet_options = ["All"] + sorted(temp_df["Outlet Name"].dropna().astype(str).unique().tolist()) if "Outlet Name" in temp_df.columns else ["All"]
    selected_outlet = st.selectbox("Outlet Filter", outlet_options)
    if selected_outlet != "All":
        temp_df = temp_df[temp_df["Outlet Name"].astype(str) == selected_outlet]

if "Search Reference" in temp_df.columns:
    search_options = sorted(temp_df["Search Reference"].dropna().unique().tolist())
    selected_search = st.multiselect("🔍 Search & Select Outlet / LIC No", search_options)
else:
    selected_search = []

if selected_search:
    filtered_df = temp_df[temp_df["Search Reference"].isin(selected_search)]
else:
    filtered_df = temp_df.copy()

def sort_asms(asm_list):
    valid_asms = [str(a) for a in asm_list if str(a).lower() not in ["nan", "none", ""]]
    sorted_normal = sorted([a for a in valid_asms if a.strip().lower() != "key accounts"])
    key_accounts = [a for a in valid_asms if a.strip().lower() == "key accounts"]
    return sorted_normal + key_accounts

def render_zoomable_table(html_content, table_key):
    zoom_level = st.select_slider(
        "🔍 Table Zoom Control (Mobile / Desktop)",
        options=[100, 125, 150, 175, 200],
        value=100,
        format_func=lambda x: f"{x}%",
        key=f"zoom_ctrl_{table_key}"
    )
    wrapped_html = f"""
    <div style="zoom: {zoom_level}%; -moz-transform: scale({zoom_level/100}); -moz-transform-origin: top left; overflow-x: auto; touch-action: pan-x pan-y pinch-zoom;">
        {html_content}
    </div>
    """
    st.markdown(wrapped_html, unsafe_allow_html=True)

# --- 10. HTML TABLE GENERATORS FOR ORIGINAL TABS ---
def generate_html_table(df, metric_type="Volume"):
    if not df.empty:
        df = df.copy()
        grouped = df.groupby([seg_col, brand_col], as_index=False, observed=False)[["Last Month", "Target", "This Month"]].sum()
    else:
        grouped = pd.DataFrame(columns=[seg_col, brand_col, "Last Month", "Target", "This Month"])

    merged = pd.merge(master_brands, grouped, on=[seg_col, brand_col], how="left").fillna(0)

    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    if metric_type == "Volume":
        html += f'<thead><tr><th class="seg-col-text">Brand</th><th>{lm_label}</th><th>TGT</th><th>{tm_label}</th><th>BAL</th></tr></thead><tbody>'
    else:
        html += f'<thead><tr><th class="seg-col-text">Brand</th><th>{lm_label}</th><th>{tm_label}</th><th>GRW</th></tr></thead><tbody>'

    gt_last_vol = merged["Last Month"].sum()
    gt_target_vol = merged["Target"].sum()
    gt_this_vol = merged["This Month"].sum()
    marked_brands = ['IBDC', 'MHW', 'BLGLM', 'BLGOR', 'Monarch', 'SMG', 'SMGP', 'MHFB', 'SIW']
    marked_data = merged[merged[brand_col].isin(marked_brands)]
    gt_bal_vol = marked_data["Target"].sum() - marked_data["This Month"].sum()

    for segment, seg_data in merged.groupby(seg_col, sort=False, observed=False):
        seg_last = seg_data["Last Month"].sum()
        seg_target = seg_data["Target"].sum()
        seg_this = seg_data["This Month"].sum()
        
        if metric_type == "Volume":
            html += f'<tr class="subtotal-row"><td class="seg-col-text">{segment}</td><td>{int(seg_last):,}</td><td>{int(seg_target):,}</td><td>{int(seg_this):,}</td><td></td></tr>'
            for _, row in seg_data.iterrows():
                b_name = row[brand_col]
                is_marked = b_name in marked_brands
                bg_style = 'background-color: #EBF5FB; font-weight: bold;' if is_marked else ''
                row_highlight = ''
                if is_marked:
                    if row['This Month'] < row['Target']:
                        row_highlight = 'background-color: #fde8e8; color: #9b1c1c;'
                    else:
                        row_highlight = 'background-color: #def7ec; color: #03543f;'
                bal_str = f"{int(row['Target'] - row['This Month']):,}" if is_marked else ""
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td style="white-space:nowrap;">{int(row["Last Month"]):,}</td><td style="white-space:nowrap;">{int(row["Target"]):,}</td><td style="white-space:nowrap; {row_highlight}">{int(row["This Month"]):,}</td><td style="white-space:nowrap; {row_highlight}">{bal_str}</td></tr>'
        else: 
            seg_last_pct = (seg_last / gt_last_vol) * 100 if gt_last_vol else 0
            seg_this_pct = (seg_this / gt_this_vol) * 100 if gt_this_vol else 0
            seg_growth = seg_this_pct - seg_last_pct
            html += f'<tr class="subtotal-row"><td class="seg-col-text">{segment}</td><td>{seg_last_pct:,.1f}%</td><td>{seg_this_pct:,.1f}%</td><td>{seg_growth:,.1f}%</td></tr>'
            for _, row in seg_data.iterrows():
                b_name = row[brand_col]
                is_marked = b_name in marked_brands
                bg_style = 'background-color: #EBF5FB; font-weight: bold;' if is_marked else ''
                b_last_pct = (row["Last Month"] / seg_last) * 100 if seg_last else 0
                b_this_pct = (row["This Month"] / seg_this) * 100 if seg_this else 0
                b_growth = b_this_pct - b_last_pct
                growth_highlight = ''
                if b_growth > 0:
                    growth_highlight = 'background-color: #def7ec; color: #03543f;'
                elif b_growth < 0:
                    growth_highlight = 'background-color: #fde8e8; color: #9b1c1c;'
                growth_str = f"{b_growth:,.1f}%"
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td style="white-space:nowrap;">{b_last_pct:,.1f}%</td><td style="white-space:nowrap;">{b_this_pct:,.1f}%</td><td style="white-space:nowrap; {growth_highlight}">{growth_str}</td></tr>'

    if metric_type == "Volume":
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td style="white-space:nowrap;">{int(gt_last_vol):,}</td><td style="white-space:nowrap;">{int(gt_target_vol):,}</td><td style="white-space:nowrap;">{int(gt_this_vol):,}</td><td style="white-space:nowrap;">{int(gt_bal_vol):,}</td></tr>'
    else:
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td style="white-space:nowrap;">100.0%</td><td style="white-space:nowrap;">100.0%</td><td></td></tr>'
    html += '</tbody></table></div>'
    return html

# --- 11. HIERARCHY REPORT GENERATORS ---
def get_segment_for_brand(b_name):
    if b_name == "MHW":
        return ["Semi Premium-Whisky"]
    elif b_name in ["IBDC", "N1WSUP", "OCBL", "RSW", "SRB7", "RGW", "MCD Lux", "IQ"]:
        return ["Deluxe-Whisky", "Deluxe Plus-Whisky"]
    return ["Deluxe-Whisky", "Deluxe Plus-Whisky"]

def calc_ms_brand(sub_df, b_name):
    target_segs = get_segment_for_brand(b_name)
    brand_lm = sub_df[sub_df['Brand'] == b_name]['Last Month'].sum()
    brand_mtd = sub_df[sub_df['Brand'] == b_name]['This Month'].sum()
    
    denom_lm = sub_df[sub_df['Segment'].isin(target_segs)]['Last Month'].sum()
    denom_mtd = sub_df[sub_df['Segment'].isin(target_segs)]['This Month'].sum()
    
    lm_pct = (brand_lm / denom_lm * 100) if denom_lm > 0 else 0.0
    mtd_pct = (brand_mtd / denom_mtd * 100) if denom_mtd > 0 else 0.0
    diff = mtd_pct - lm_pct
    return lm_pct, mtd_pct, diff

def generate_hierarchy_table_1(df):
    brands_to_show = ["IBDC", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += '<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>'
    for b in brands_to_show:
        html += f'<th colspan="4">{b}</th>'
    html += '</tr><tr>'
    for _ in brands_to_show:
        html += f'<th>{lm_label}</th><th>Target</th><th>{tm_label}</th><th>MS%</th>'
    html += '</tr></thead><tbody>'

    def get_row_html(sub_df):
        i_lm = sub_df[sub_df['Brand']=='IBDC']['Last Month'].sum()
        i_tgt = sub_df[sub_df['Brand']=='IBDC']['Target'].sum()
        i_tm = sub_df[sub_df['Brand']=='IBDC']['This Month'].sum()
        _, i_ms, _ = calc_ms_brand(sub_df, "IBDC")

        m_lm = sub_df[sub_df['Brand']=='MHW']['Last Month'].sum()
        m_tgt = sub_df[sub_df['Brand']=='MHW']['Target'].sum()
        m_tm = sub_df[sub_df['Brand']=='MHW']['This Month'].sum()
        _, m_ms, _ = calc_ms_brand(sub_df, "MHW")

        return f'<td>{int(i_lm):,}</td><td>{int(i_tgt):,}</td><td>{int(i_tm):,}</td><td>{i_ms:.1f}%</td>' \
               f'<td>{int(m_lm):,}</td><td>{int(m_tgt):,}</td><td>{int(m_tm):,}</td><td>{m_ms:.1f}%</td>'

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row_html(df) + '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row_html(z_df) + '</tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>' + get_row_html(a_df) + '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>' + get_row_html(t_df) + '</tr>'

    html += '</tbody></table></div>'
    return html

def generate_hierarchy_table_2(df):
    brands_to_show = ["IBDC", "MCD Lux", "IQ", "N1WSUP", "OCBL", "RSW", "SRB7", "RGW", "MHW"]
    
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += '<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>'
    for b in brands_to_show:
        html += f'<th colspan="3">{b}</th>'
    html += '</tr><tr>'
    for _ in brands_to_show:
        html += f'<th>{lm_label}</th><th>{tm_label}</th><th>diff</th>'
    html += '</tr></thead><tbody>'

    def get_row_html_h2(sub_df):
        res_html = ""
        for b in brands_to_show:
            lm, mtd, diff = calc_ms_brand(sub_df, b)
            res_html += f'<td>{lm:.1f}%</td><td>{mtd:.1f}%</td><td style="color: {"#9b1c1c" if diff < 0 else "#03543f"};">{diff:+.1f}%</td>'
        return res_html

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row_html_h2(df) + '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row_html_h2(z_df) + '</tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>' + get_row_html_h2(a_df) + '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>' + get_row_html_h2(t_df) + '</tr>'

    html += '</tbody></table></div>'
    return html

def generate_hierarchy_table_3(df):
    brands_to_show = ["IBDC", "MCD Lux", "IQ", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += '<thead><tr><th class="seg-col-text" rowspan="2">Unique Billing Outlet<br>ZONE/ASM/TSE</th>'
    for b in brands_to_show:
        html += f'<th colspan="3">{b}</th>'
    html += '</tr><tr>'
    for _ in brands_to_show:
        html += f'<th>{lm_label}</th><th>{tm_label}</th><th>diff</th>'
    html += '</tr></thead><tbody>'

    def get_outlet_counts(sub_df, brand_name):
        lm_outlets = sub_df[(sub_df['Brand'] == brand_name) & (sub_df['Last Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub_df.columns else 0
        mtd_outlets = sub_df[(sub_df['Brand'] == brand_name) & (sub_df['This Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub_df.columns else 0
        diff = mtd_outlets - lm_outlets
        return lm_outlets, mtd_outlets, diff

    def get_row_html_h3(sub_df):
        res_html = ""
        for b in brands_to_show:
            lm_c, mtd_c, diff_c = get_outlet_counts(sub_df, b)
            res_html += f'<td>{lm_c:,}</td><td>{mtd_c:,}</td><td style="color: {"#9b1c1c" if diff_c < 0 else "#03543f"};">{diff_c:+d}</td>'
        return res_html

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row_html_h3(df) + '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row_html_h3(z_df) + '</tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>' + get_row_html_h3(a_df) + '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>' + get_row_html_h3(t_df) + '</tr>'

    html += '</tbody></table></div>'
    return html

# --- 12. DISPLAY MAIN TABS ---
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Dashboard", "💬 Ask Assistant"])

with main_tab1:
    html_vol = generate_html_table(filtered_df, metric_type="Volume")
    render_zoomable_table(html_vol, "vol_tab")

with main_tab2:
    html_ms = generate_html_table(filtered_df, metric_type="Ms%")
    render_zoomable_table(html_ms, "ms_tab")

with main_tab3:
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Target vs Ach", "MS% Details", "WOD Details"])
    
    with sub_tab1:
        st.markdown(f"<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Zone, ASM & TSE Performance Breakdown (IBDC & MHW)</h3>", unsafe_allow_html=True)
        html_h1 = generate_hierarchy_table_1(filtered_df)
        render_zoomable_table(html_h1, "h1_tab")

    with sub_tab2:
        st.markdown(f"<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Share / Growth Hierarchy Matrix ({lm_label}, {tm_label}, Diff)</h3>", unsafe_allow_html=True)
        html_h2 = generate_hierarchy_table_2(filtered_df)
        render_zoomable_table(html_h2, "h2_tab")

    with sub_tab3:
        st.markdown(f"<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Unique Billing Outlet Count Comparison ({lm_label} vs {tm_label})</h3>", unsafe_allow_html=True)
        html_h3 = generate_hierarchy_table_3(filtered_df)
        render_zoomable_table(html_h3, "h3_tab")

with main_tab4:
    st.markdown("<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>🤖 Smart Sales & Outlet Query Assistant</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 13.5px; font-family: Calibri, sans-serif;'>Perform advanced unbilled outlet queries, substitution gap analysis, run-rate comparisons, and multi-month brand trends.</p>", unsafe_allow_html=True)

    col_q1, col_q2, col_q3 = st.columns([1.2, 1, 1.8])
    
    with col_q1:
        basis_period = st.selectbox(
            "Basis on Period:",
            [
                f"This Month ({tm_label})",
                f"Last Month ({lm_label})",
                f"Last 2 Months ({lm_label} + {m2_label})",
                f"Last 3 Months ({lm_label} + {m2_label} + {m3_label})",
                f"Last 4 Months ({lm_label} + {m2_label} + {m3_label} + {m4_label})",
                f"Last 5 Months ({lm_label} + {m2_label} + {m3_label} + {m4_label} + {m5_label})"
            ]
        )
        
    with col_q2:
        target_brand_choice = st.selectbox(
            "Target Brand Focus:",
            ["IBDC", "MHW", "MHFB", "BLGLM+BLGOR", "SMG+SMGP", "SIW", "Monarch"]
        )

    with col_q3:
        query_type = st.selectbox(
            "Choose a Query / Analysis:",
            [
                "-- Select a Query --",
                "TIL Non Billed Outlets",
                "Deluxe Industry >= 30 CS but IBDC Not Billed",
                "Semi Premium Whisky Industry >= 50 CS but MHW Not Billed",
                "Magic Moments Billed but BLG Not Billed",
                "MCD Lux Billed but IBDC Not Billed",
                "IQ Billed but IBDC Not Billed",
                "RSW Billed but MHW Not Billed",
                "RGW Billed but MHW Not Billed",
                "SRB7 Billed but MHW Not Billed",
                "RCW Billed but MHW Not Billed",
                "All Season Billed but MHW Not Billed",
                "SMG + SMGP Lapsed Outlets (Not Repeated)",
                "SIW Lapsed Outlets (Not Repeated)",
                "Brand-wise L3M Daily Run vs Current Month Daily Run",
                "Deluxe Industry - MS% Trend (6 Months)",
                "Semi Premium Whisky Industry - MS% Trend (6 Months)",
                "Deluxe Industry - Volume Trend (6 Months)",
                "Semi Premium Whisky Industry - Volume Trend (6 Months)",
                "Deluxe Industry - Unique Billed Outlets Trend (6 Months)",
                "Semi Premium Whisky Industry - Unique Billed Outlets Trend (6 Months)"
            ]
        )

    needs_history = any(x in query_type for x in ["Trend", "L3M", "Lapsed", "Billed", "Industry"]) or any(k in basis_period for k in ["2", "3", "4", "5"])
    
    df_m2, df_m3, df_m4, df_m5 = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if needs_history:
        with st.spinner("Fetching historical data (M2, M3, M4, M5)..."):
            hist_dfs, hist_err = load_historical_data_from_url(RAW_HISTORICAL_URL)
            if hist_err or not hist_dfs:
                st.warning(f"⚠️ Note: Could not load historical Excel (M2-M5): {hist_err}. Analysis will run on available data.")
            else:
                if "M2" in hist_dfs:
                    df_m2 = standardize_df(hist_dfs["M2"])
                    df_m2["Metric"] = "M2"
                if "M3" in hist_dfs:
                    df_m3 = standardize_df(hist_dfs["M3"])
                    df_m3["Metric"] = "M3"
                if "M4" in hist_dfs:
                    df_m4 = standardize_df(hist_dfs["M4"])
                    df_m4["Metric"] = "M4"
                if "M5" in hist_dfs:
                    df_m5 = standardize_df(hist_dfs["M5"])
                    df_m5["Metric"] = "M5"

    brand_family_map = {
        "IBDC": ["IBDC"],
        "MHW": ["MHW"],
        "MHFB": ["MHFB"],
        "BLGLM+BLGOR": ["BLGLM", "BLGOR"],
        "SMG+SMGP": ["SMG", "SMGP"],
        "SIW": ["SIW"],
        "Monarch": ["Monarch"]
    }

    def apply_active_filters(df_in):
        if df_in.empty: return df_in
        res = df_in.copy()
        
        if selected_search:
            valid_lics = filtered_df["LIC No"].dropna().astype(str).str.strip().unique()
            if "LIC No" in res.columns:
                res = res[res["LIC No"].astype(str).str.strip().isin(valid_lics)]
            elif "Outlet Name" in res.columns:
                valid_names = filtered_df["Outlet Name"].dropna().astype(str).str.strip().unique()
                res = res[res["Outlet Name"].astype(str).str.strip().isin(valid_names)]
                
        if selected_group != "All" and "Group" in res.columns:
            res = res[res["Group"].astype(str).str.strip() == str(selected_group).strip()]
        if selected_asm != "All" and "ASM" in res.columns:
            res = res[res["ASM"].astype(str).str.strip() == str(selected_asm).strip()]
        if selected_tse != "All" and "TSE" in res.columns:
            res = res[res["TSE"].astype(str).str.strip() == str(selected_tse).strip()]
        if selected_lic != "All" and "LIC No" in res.columns:
            res = res[res["LIC No"].astype(str).str.strip() == str(selected_lic).strip()]
        if selected_outlet != "All" and "Outlet Name" in res.columns:
            res = res[res["Outlet Name"].astype(str).str.strip() == str(selected_outlet).strip()]
            
        return res

    f_this = apply_active_filters(df_this)
    f_last = apply_active_filters(df_last)
    f_m2 = apply_active_filters(df_m2)
    f_m3 = apply_active_filters(df_m3)
    f_m4 = apply_active_filters(df_m4)
    f_m5 = apply_active_filters(df_m5)

    if tm_label in basis_period:
        basis_dfs = [f_this]
    elif f"Last 2 Months" in basis_period:
        basis_dfs = [f_last, f_m2]
    elif f"Last 3 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3]
    elif f"Last 4 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3, f_m4]
    elif f"Last 5 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3, f_m4, f_m5]
    else: 
        basis_dfs = [f_last]
    
    valid_basis_dfs = [d for d in basis_dfs if not d.empty]
    basis_combined = pd.concat(valid_basis_dfs, ignore_index=True) if len(valid_basis_dfs) > 0 else f_this

    base_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates() if "LIC No" in filtered_df.columns else pd.DataFrame()

    st.markdown("---")

    if query_type == "TIL Non Billed Outlets":
        target_brands = brand_family_map.get(target_brand_choice, [target_brand_choice])
        
        basis_vol_map = basis_combined.groupby("LIC No")["Value"].sum().to_dict() if "LIC No" in basis_combined.columns else {}
        basis_billed = [k for k, v in basis_vol_map.items() if v > 0]
        this_billed_target = f_this[(f_this["Brand"].isin(target_brands)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        
        unbilled_df = base_outlets[(base_outlets["LIC No"].isin(basis_billed)) & (~base_outlets["LIC No"].isin(this_billed_target))].copy()
        
        unbilled_df["Volume (CS)"] = unbilled_df["LIC No"].map(basis_vol_map).fillna(0).astype(int)
        unbilled_df = unbilled_df.sort_values(by="Outlet Name", ascending=True)
        out_cnt = len(unbilled_df)
        
        st.markdown(f"#### 🔍 Outlets that Billed in **{basis_period}** but Have NOT Billed **TIL Brands** this Month (Total: {out_cnt:,} Outlets):")
        
        if not unbilled_df.empty:
            st.dataframe(unbilled_df, use_container_width=True, hide_index=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(unbilled_df), file_name=f"til_non_billing_{target_brand_choice}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("🎉 No unbilled outlets found for TIL Brands within the active filter scope!")

    elif "Deluxe Industry >=" in query_type or "Deluxe Industry >" in query_type:
        deluxe_vol = basis_combined[basis_combined["Segment"].isin(["Deluxe-Whisky", "Deluxe Plus-Whisky"])].groupby("LIC No")["Value"].sum()
        deluxe_30_lics = deluxe_vol[deluxe_vol >= 30].index.tolist()
        ibdc_billed = f_this[(f_this["Brand"] == "IBDC") & (f_this["Value"] > 0)]["LIC No"].unique() if "Brand" in f_this.columns else []
        
        target_lics = set(deluxe_30_lics) - set(ibdc_billed)
        res_df = base_outlets[base_outlets["LIC No"].isin(target_lics)].copy()
        res_df["Deluxe Vol (CS)"] = res_df["LIC No"].map(deluxe_vol).fillna(0).astype(int)
        res_df = res_df.sort_values(by="Outlet Name", ascending=True)
        out_cnt = len(res_df)
        
        st.markdown(f"#### 🔍 Outlets with Deluxe Industry Volume >= 30 CS in **{basis_period}** but IBDC NOT Billed this Month (Total: {out_cnt:,} Outlets):")
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(res_df), file_name="deluxe_30cs_ibdc_unbilled.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("🎉 No gap outlets found!")

    elif "Semi Premium Whisky Industry >=" in query_type or "Semi Premium Whisky Industry >" in query_type:
        sp_vol = basis_combined[basis_combined["Segment"] == "Semi Premium-Whisky"].groupby("LIC No")["Value"].sum()
        sp_50_lics = sp_vol[sp_vol >= 50].index.tolist()
        mhw_billed = f_this[(f_this["Brand"] == "MHW") & (f_this["Value"] > 0)]["LIC No"].unique() if "Brand" in f_this.columns else []
        
        target_lics = set(sp_50_lics) - set(mhw_billed)
        res_df = base_outlets[base_outlets["LIC No"].isin(target_lics)].copy()
        res_df["SP Vol (CS)"] = res_df["LIC No"].map(sp_vol).fillna(0).astype(int)
        res_df = res_df.sort_values(by="Outlet Name", ascending=True)
        out_cnt = len(res_df)
        
        st.markdown(f"#### 🔍 Outlets with Semi Premium Whisky Volume >= 50 CS in **{basis_period}** but MHW NOT Billed this Month (Total: {out_cnt:,} Outlets):")
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(res_df), file_name="sp_50cs_mhw_unbilled.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("🎉 No gap outlets found!")

    elif any(x in query_type for x in ["Magic Moments", "MCD Lux", "IQ", "RSW", "RGW", "SRB7", "RCW", "All Season"]):
        if "Magic Moments" in query_type:
            driver_b, target_b = ["MMV", "MMFLV"], ["BLGLM", "BLGOR"]
            display_driver, display_target = "Magic Moments", "BLG"
        elif "MCD Lux" in query_type:
            driver_b, target_b = ["MCD Lux"], ["IBDC"]
            display_driver, display_target = "MCD Lux", "IBDC"
        elif "IQ" in query_type:
            driver_b, target_b = ["IQ"], ["IBDC"]
            display_driver, display_target = "IQ", "IBDC"
        elif "RSW" in query_type:
            driver_b, target_b = ["RSW"], ["MHW"]
            display_driver, display_target = "RSW", "MHW"
        elif "RGW" in query_type:
            driver_b, target_b = ["RGW"], ["MHW"]
            display_driver, display_target = "RGW", "MHW"
        elif "SRB7" in query_type:
            driver_b, target_b = ["SRB7"], ["MHW"]
            display_driver, display_target = "SRB7", "MHW"
        elif "RCW" in query_type:
            driver_b, target_b = ["RCW"], ["MHW"]
            display_driver, display_target = "RCW", "MHW"
        elif "All Season" in query_type:
            driver_b, target_b = ["All Season"], ["MHW"]
            display_driver, display_target = "All Season", "MHW"
        else:
            driver_b, target_b = [], []
            display_driver, display_target = "", ""

        driver_vol_series = basis_combined[basis_combined["Brand"].isin(driver_b)].groupby("LIC No")["Value"].sum()
        driver_outlets = driver_vol_series[driver_vol_series > 0].index.tolist()
        target_outlets = f_this[(f_this["Brand"].isin(target_b)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        
        gap_lics = set(driver_outlets) - set(target_outlets)
        gap_df = base_outlets[base_outlets["LIC No"].isin(gap_lics)].copy()
        gap_df["Billed Vol (CS)"] = gap_df["LIC No"].map(driver_vol_series).fillna(0).astype(int)
        gap_df = gap_df.sort_values(by="Outlet Name", ascending=True)
        out_cnt = len(gap_df)
        
        st.markdown(f"#### 🔍 Outlets Billing **{display_driver}** in **{basis_period}** but NOT Billing **{display_target}** this Month (Total: {out_cnt:,} Outlets):")
        
        if not gap_df.empty:
            st.dataframe(gap_df, use_container_width=True, hide_index=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(gap_df), file_name="brand_gap_outlets.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("🎉 No gap outlets found!")

    elif "Lapsed Outlets" in query_type:
        target_brands = ["SMG", "SMGP"] if "SMG" in query_type else ["SIW"]
        brand_name_str = "SMG + SMGP" if "SMG" in query_type else "SIW"
        
        all_time_dfs = [f_this, f_last, f_m2, f_m3, f_m4, f_m5]
        all_time_combined = pd.concat([d for d in all_time_dfs if not d.empty], ignore_index=True)
        
        target_hist_vol = all_time_combined[all_time_combined["Brand"].isin(target_brands)].groupby("LIC No")["Value"].sum()
        anytime_billed = target_hist_vol[target_hist_vol > 0].index.tolist()
        
        selected_period_billed = set(basis_combined[(basis_combined["Brand"].isin(target_brands)) & (basis_combined["Value"] > 0)]["LIC No"].dropna().unique()) if not basis_combined.empty else set()
        tm_billed = set(f_this[(f_this["Brand"].isin(target_brands)) & (f_this["Value"] > 0)]["LIC No"].dropna().unique()) if not f_this.empty else set()
        
        not_repeated = set(anytime_billed) - (selected_period_billed.union(tm_billed))
        res_df = base_outlets[base_outlets["LIC No"].isin(not_repeated)].copy()
        res_df["Historical Vol (CS)"] = res_df["LIC No"].map(target_hist_vol).fillna(0).astype(int)
        res_df = res_df.sort_values(by="Outlet Name", ascending=True)
        out_cnt = len(res_df)
        
        st.markdown(f"#### 🔍 Outlets that Billed **{brand_name_str}** Historically (Any Time) but NOT Billed in **{basis_period}** (Total: {out_cnt:,} Outlets):")
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(res_df), file_name=f"{brand_name_str}_lapsed.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success(f"🎉 No lapsed outlets found for {brand_name_str} under the active criteria!")

    elif "Brand-wise L3M Daily Run vs Current Month Daily Run" in query_type:
        st.markdown(f"#### 📊 Brand-wise L3M Daily Run (L3M Vol / 90) vs TM Daily Run (TM Vol / {days_elapsed} Days):")
        st.caption(f"ℹ️ *Current calculation basis: **{f2_display_date}** (Elapsed Days: **{days_elapsed}** from 'Users' Sheet Cell F2)*")
        
        valid_l3m = [d for d in [f_last, f_m2, f_m3] if not d.empty]
        l3m_comb = pd.concat(valid_l3m, ignore_index=True) if len(valid_l3m) > 0 else f_last
        
        grp_l3m = l3m_comb.groupby([seg_col, brand_col], as_index=False, observed=False)["Value"].sum().rename(columns={"Value": "L3M_Vol"})
        grp_tm = f_this.groupby([seg_col, brand_col], as_index=False, observed=False)["Value"].sum().rename(columns={"Value": "TM_Vol"})
        
        rr_merged = pd.merge(master_brands, grp_l3m, on=[seg_col, brand_col], how="left").fillna(0)
        rr_merged = pd.merge(rr_merged, grp_tm, on=[seg_col, brand_col], how="left").fillna(0)
        
        marked_brands = ['IBDC', 'MHW', 'BLGLM', 'BLGOR', 'Monarch', 'SMG', 'SMGP', 'MHFB', 'SIW']
        
        html_rr = '<div class="table-wrapper"><table class="custom-dashboard-table">'
        html_rr += f'<thead><tr><th class="seg-col-text">Brand</th><th>L3M Total</th><th>L3M Daily (/90)</th><th>TM Total</th><th>TM Daily (/{days_elapsed}D)</th><th>Growth (CS)</th><th>Growth %</th></tr></thead><tbody>'
        
        gt_l3m_vol = rr_merged["L3M_Vol"].sum()
        gt_tm_vol = rr_merged["TM_Vol"].sum()
        gt_l3m_daily = round(gt_l3m_vol / 90.0, 1)
        gt_tm_daily = round(gt_tm_vol / float(days_elapsed), 1)
        gt_growth_cs = round(gt_tm_daily - gt_l3m_daily, 1)
        gt_growth_pct = round(((gt_tm_daily - gt_l3m_daily) / gt_l3m_daily) * 100, 1) if gt_l3m_daily > 0 else 0.0

        excel_rows = []

        for segment, seg_data in rr_merged.groupby(seg_col, sort=False, observed=False):
            seg_l3m_v = seg_data["L3M_Vol"].sum()
            seg_tm_v = seg_data["TM_Vol"].sum()
            seg_l3m_d = round(seg_l3m_v / 90.0, 1)
            seg_tm_d = round(seg_tm_v / float(days_elapsed), 1)
            seg_g_cs = round(seg_tm_d - seg_l3m_d, 1)
            seg_g_pct = round(((seg_tm_d - seg_l3m_d) / seg_l3m_d) * 100, 1) if seg_l3m_d > 0 else 0.0
            
            html_rr += f'<tr class="subtotal-row"><td class="seg-col-text">{segment}</td><td>{int(seg_l3m_v):,}</td><td>{seg_l3m_d:,.1f}</td><td>{int(seg_tm_v):,}</td><td>{seg_tm_d:,.1f}</td><td>{seg_g_cs:+,.1f}</td><td>{seg_g_pct:+,.1f}%</td></tr>'
            
            for _, row in seg_data.iterrows():
                b_name = row[brand_col]
                b_l3m_v = row["L3M_Vol"]
                b_tm_v = row["TM_Vol"]
                b_l3m_d = round(b_l3m_v / 90.0, 1)
                b_tm_d = round(b_tm_v / float(days_elapsed), 1)
                b_g_cs = round(b_tm_d - b_l3m_d, 1)
                b_g_pct = round(((b_tm_d - b_l3m_d) / b_l3m_d) * 100, 1) if b_l3m_d > 0 else (100.0 if b_tm_d > 0 else 0.0)
                
                is_marked = b_name in marked_brands
                bg_style = 'background-color: #EBF5FB; font-weight: bold;' if is_marked else ''
                growth_highlight = 'background-color: #def7ec; color: #03543f;' if b_g_cs > 0 else ('background-color: #fde8e8; color: #9b1c1c;' if b_g_cs < 0 else '')
                
                html_rr += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td>{int(b_l3m_v):,}</td><td>{b_l3m_d:,.1f}</td><td>{int(b_tm_v):,}</td><td>{b_tm_d:,.1f}</td><td style="{growth_highlight}">{b_g_cs:+,.1f}</td><td style="{growth_highlight}">{b_g_pct:+,.1f}%</td></tr>'
                
                excel_rows.append({
                    "Segment": segment,
                    "Brand": b_name,
                    "L3M Total Vol": int(b_l3m_v),
                    "L3M Daily Run (/90)": b_l3m_d,
                    "TM Total Vol": int(b_tm_v),
                    f"TM Daily Run (/{days_elapsed} Days)": b_tm_d,
                    "Growth (CS)": b_g_cs,
                    "Growth %": f"{b_g_pct:+,.1f}%"
                })

        html_rr += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td>{int(gt_l3m_vol):,}</td><td>{gt_l3m_daily:,.1f}</td><td>{int(gt_tm_vol):,}</td><td>{gt_tm_daily:,.1f}</td><td>{gt_growth_cs:+,.1f}</td><td>{gt_growth_pct:+,.1f}%</td></tr>'
        html_rr += '</tbody></table></div>'
        
        render_zoomable_table(html_rr, "rr_query")
        
        df_export_rr = pd.DataFrame(excel_rows)
        st.download_button("📥 Download in Excel", data=to_excel_bytes(df_export_rr), file_name="l3m_vs_tm_daily_run_segmented.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif "Trend" in query_type:
        is_deluxe = "Deluxe" in query_type
        is_sp = "Semi Premium" in query_type
        is_ms = "MS%" in query_type
        is_vol = "Volume" in query_type
        is_wod = "Unique Billed" in query_type
        
        deluxe_brands = ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak"]
        sp_brands = ["MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR"]
        
        target_industry_name = "Deluxe-Whisky" if is_deluxe else "Semi Premium-Whisky"
        brand_list = deluxe_brands if is_deluxe else sp_brands
        industry_segs = ["Deluxe-Whisky", "Deluxe Plus-Whisky"] if is_deluxe else ["Semi Premium-Whisky"]
        
        trend_months = [tm_label, lm_label, m2_label, m3_label, m4_label, m5_label]
        months_dict = {
            tm_label: f_this,
            lm_label: f_last,
            m2_label: df_m2,
            m3_label: df_m3,
            m4_label: df_m4,
            m5_label: df_m5
        }
        
        html_trend = '<div class="table-wrapper"><table class="custom-dashboard-table">'
        html_trend += '<thead><tr><th class="seg-col-text">Brand</th>' + ''.join([f'<th>{m}</th>' for m in trend_months]) + '</tr></thead><tbody>'
        
        html_trend += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{target_industry_name}</b></td>'
        for m_key in trend_months:
            m_df = months_dict[m_key]
            if m_df.empty:
                html_trend += '<td>-</td>'
                continue
            ind_sub = m_df[m_df["Segment"].isin(industry_segs)]
            if is_ms:
                ind_sum = ind_sub["Value"].sum()
                html_trend += '<td>100.0%</td>' if ind_sum > 0 else '<td>0.0%</td>'
            elif is_vol:
                html_trend += f'<td>{int(ind_sub["Value"].sum()):,}</td>'
            elif is_wod:
                html_trend += f'<td>{ind_sub[ind_sub["Value"] > 0]["LIC No"].nunique():,}</td>'
        html_trend += '</tr>'
        
        for b in brand_list:
            html_trend += f'<tr class="brand-row"><td class="brand-col-text">{b}</td>'
            for m_key in trend_months:
                m_df = months_dict[m_key]
                if m_df.empty:
                    html_trend += '<td>-</td>'
                    continue
                ind_sub = m_df[m_df["Segment"].isin(industry_segs)]
                b_sub = ind_sub[ind_sub["Brand"] == b]
                
                if is_ms:
                    ind_tot = ind_sub["Value"].sum()
                    b_tot = b_sub["Value"].sum()
                    ms_pct = (b_tot / ind_tot * 100) if ind_tot > 0 else 0.0
                    html_trend += f'<td>{ms_pct:.1f}%</td>'
                elif is_vol:
                    html_trend += f'<td>{int(b_sub["Value"].sum()):,}</td>'
                elif is_wod:
                    html_trend += f'<td>{b_sub[b_sub["Value"] > 0]["LIC No"].nunique():,}</td>'
            html_trend += '</tr>'
            
        html_trend += '</tbody></table></div>'
        st.markdown(f"#### 📈 {query_type}:")
        render_zoomable_table(html_trend, "trend_query")
