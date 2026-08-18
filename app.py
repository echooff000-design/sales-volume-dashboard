import streamlit as st
import pandas as pd
import requests
import io
import datetime
import os
import base64
import re
import extra_streamlit_components as stx
import gspread
from google.oauth2.service_account import Credentials

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="WB Sale Data", page_icon="logo.png", layout="wide")

# --- HIDE STREAMLIT BRANDING & FIX SIDEBAR / BUTTON / TABLE CSS ---
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

# --- 3. COOKIE MANAGER SETUP ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 4. EXCEL EXPORT HELPER FUNCTION ---
def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- 5. DATA FETCHING (FROM STREAMLIT SECRETS) ---
RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

if "HISTORICAL_SHAREPOINT_URL" in st.secrets:
    RAW_HISTORICAL_URL = st.secrets["HISTORICAL_SHAREPOINT_URL"].split("?")[0] + "?download=1"
else:
    RAW_HISTORICAL_URL = "https://tilaknagarindustries-my.sharepoint.com/:x:/g/personal/andebnath_tilind_com/IQDgm_kiCV5STbn_ziAyo8_pARvUsuNLyey3WIKNVlXXCSM?download=1"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=25)
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

@st.cache_data(ttl=600)
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
            return int(raw_val.day), raw_val.strftime("%d %b %Y")
        
        try:
            num_val = float(str(raw_val).strip())
            if num_val > 30000:
                dt = pd.to_datetime(num_val, unit='D', origin='1899-12-30')
                return int(dt.day), dt.strftime("%d %b %Y")
        except Exception:
            pass
        
        val_str = str(raw_val).strip()
        parsed_dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
        if pd.notna(parsed_dt):
            return int(parsed_dt.day), parsed_dt.strftime("%d %b %Y")
            
        match = re.search(r'\b(\d{1,2})\b', val_str)
        if match:
            day_num = int(match.group(1))
            return day_num, f"{day_num} Aug 2026"
            
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    today_dt = datetime.datetime.now(ist_tz)
    return today_dt.day, today_dt.strftime("%d %b %Y")

days_elapsed, f2_display_date = extract_f2_date(raw_users_df)

df_users = raw_users_df.copy()
df_users.columns = df_users.columns.astype(str).str.strip().str.lower()

col_map = {}
for col in df_users.columns:
    if "name" in col:
        col_map["Name"] = col
    elif "user" in col or "id" in col:
        col_map["user_id"] = col
    elif "pass" in col:
        col_map["password"] = col
    elif "role" in col or "admin" in col:
        col_map["role"] = col

if "Name" not in col_map or "user_id" not in col_map or "password" not in col_map:
    st.error(f"❌ The 'Users' sheet columns were detected as: {list(dfs['Users'].columns)}. Please ensure your Excel columns include: Name, user_id, password.")
    st.stop()

rename_dict = {
    col_map["Name"]: "Name",
    col_map["user_id"]: "user_id",
    col_map["password"]: "password"
}
if "role" in col_map:
    rename_dict[col_map["role"]] = "role"

df_users = df_users.rename(columns=rename_dict)

cached_user = None
try:
    cached_user = cookie_manager.get(cookie="wb_sale_user")
except Exception:
    pass

if "authenticated" not in st.session_state:
    if cached_user:
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = cached_user
        user_row = df_users[df_users["Name"].astype(str).str.strip() == str(cached_user).strip()]
        is_adm = False
        if not user_row.empty and "role" in user_row.columns:
            is_adm = str(user_row.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
        st.session_state["is_admin"] = is_adm
    else:
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.session_state["is_admin"] = False

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
                user_match = df_users[
                    (df_users["user_id"].astype(str).str.strip() == str(input_user).strip()) & 
                    (df_users["password"].astype(str).str.strip() == str(input_pass).strip())
                ]
                
                if not user_match.empty:
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = user_match.iloc[0]["Name"]
                    
                    is_adm = False
                    if "role" in user_match.columns:
                        is_adm = str(user_match.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
                    st.session_state["is_admin"] = is_adm
                    
                    try:
                        cookie_manager.set("wb_sale_user", st.session_state["user_name"], max_age=30*24*60*60)
                    except Exception:
                        pass
                    
                    # --- GOOGLE SHEETS BACKGROUND LOGGER ---
                    try:
                        sheet = get_sheet()
                        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                        now = datetime.datetime.now(ist_timezone)
                        sheet.append_row([
                            str(now.year),
                            now.strftime("%Y-%m-%d"),
                            now.strftime("%H:%M:%S"),
                            st.session_state["user_name"],
                            str(input_user)
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
    st.markdown(f"<p style='text-align: right; margin-top: 10px; font-size: 13px; color: #f8fafc; font-family: Calibri, sans-serif;'>👤 <b>{st.session_state['user_name']}</b><br><span style='color: #60a5fa; font-size: 11px;'>{role_display}</span></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        try:
            cookie_manager.delete("wb_sale_user")
        except Exception:
            pass
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.session_state["is_admin"] = False
        st.rerun()

# --- SIDEBAR WITH DYNAMIC USER F2 DATE ---
st.sidebar.markdown("📁 **Data Source**")
st.sidebar.caption(f"🕒 **Last Synced:** {f2_display_date}")

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Fetching newest data...")

st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Admin Panel**")

# --- CONDITIONAL ADMIN LOG DOWNLOAD ---
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

# --- HELPER FUNCTION TO SORT ASMS ---
def sort_asms(asm_list):
    valid_asms = [str(a) for a in asm_list if str(a).lower() not in ["nan", "none", ""]]
    sorted_normal = sorted([a for a in valid_asms if a.strip().lower() != "key accounts"])
    key_accounts = [a for a in valid_asms if a.strip().lower() == "key accounts"]
    return sorted_normal + key_accounts

# --- INTERACTIVE ZOOMABLE TABLE WRAPPER HELPER ---
def render_zoomable_table(html_content):
    zoom_key = f"zoom_{hash(html_content) % 10000}"
    zoom_level = st.select_slider(
        "🔍 Table Zoom Control (Mobile / Desktop)",
        options=[100, 125, 150, 175, 200],
        value=100,
        format_func=lambda x: f"{x}%",
        key=zoom_key
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
        html += '<thead><tr><th class="seg-col-text">Brand</th><th>LM</th><th>TGT</th><th>TM</th><th>BAL</th></tr></thead><tbody>'
    else:
        html += '<thead><tr><th class="seg-col-text">Brand</th><th>LM</th><th>TM</th><th>GRW</th></tr></thead><tbody>'

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
        html += '<th>LM</th><th>Target</th><th>MTD</th><th>MS%</th>'
    html += '</tr></thead><tbody>'

    tot_lm_ibdc = df[df['Brand']=='IBDC']['Last Month'].sum()
    tot_tgt_ibdc = df[df['Brand']=='IBDC']['Target'].sum()
    tot_mtd_ibdc = df[df['Brand']=='IBDC']['This Month'].sum()
    ms_ibdc, _, _ = calc_ms_brand(df, "IBDC")

    tot_lm_mhw = df[df['Brand']=='MHW']['Last Month'].sum()
    tot_tgt_mhw = df[df['Brand']=='MHW']['Target'].sum()
    tot_mtd_mhw = df[df['Brand']=='MHW']['This Month'].sum()
    ms_mhw, _, _ = calc_ms_brand(df, "MHW")

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    html += f'<td>{int(tot_lm_ibdc):,}</td><td>{int(tot_tgt_ibdc):,}</td><td>{int(tot_mtd_ibdc):,}</td><td>{ms_ibdc:.1f}%</td>'
    html += f'<td>{int(tot_lm_mhw):,}</td><td>{int(tot_tgt_mhw):,}</td><td>{int(tot_mtd_mhw):,}</td><td>{ms_mhw:.1f}%</td></tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        z_lm_i = z_df[z_df['Brand']=='IBDC']['Last Month'].sum()
        z_tgt_i = z_df[z_df['Brand']=='IBDC']['Target'].sum()
        z_mtd_i = z_df[z_df['Brand']=='IBDC']['This Month'].sum()
        z_ms_i, _, _ = calc_ms_brand(z_df, "IBDC")

        z_lm_m = z_df[z_df['Brand']=='MHW']['Last Month'].sum()
        z_tgt_m = z_df[z_df['Brand']=='MHW']['Target'].sum()
        z_mtd_m = z_df[z_df['Brand']=='MHW']['This Month'].sum()
        z_ms_m, _, _ = calc_ms_brand(z_df, "MHW")

        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>'
        html += f'<td>{int(z_lm_i):,}</td><td>{int(z_tgt_i):,}</td><td>{int(z_mtd_i):,}</td><td>{z_ms_i:.1f}%</td>'
        html += f'<td>{int(z_lm_m):,}</td><td>{int(z_tgt_m):,}</td><td>{int(z_mtd_m):,}</td><td>{ms_mhw:.1f}%</td></tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            a_lm_i = a_df[a_df['Brand']=='IBDC']['Last Month'].sum()
            a_tgt_i = a_df[a_df['Brand']=='IBDC']['Target'].sum()
            a_mtd_i = a_df[a_df['Brand']=='IBDC']['This Month'].sum()
            a_ms_i, _, _ = calc_ms_brand(a_df, "IBDC")

            a_lm_m = a_df[a_df['Brand']=='MHW']['Last Month'].sum()
            a_tgt_m = a_df[a_df['Brand']=='MHW']['Target'].sum()
            a_mtd_m = a_df[a_df['Brand']=='MHW']['This Month'].sum()
            a_ms_m, _, _ = calc_ms_brand(a_df, "MHW")

            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>'
            html += f'<td>{int(a_lm_i):,}</td><td>{int(a_tgt_i):,}</td><td>{int(a_mtd_i):,}</td><td>{a_ms_i:.1f}%</td>'
            html += f'<td>{int(a_lm_m):,}</td><td>{int(a_tgt_m):,}</td><td>{int(a_mtd_m):,}</td><td>{ms_mhw:.1f}%</td></tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                t_lm_i = t_df[t_df['Brand']=='IBDC']['Last Month'].sum()
                t_tgt_i = t_df[t_df['Brand']=='IBDC']['Target'].sum()
                t_mtd_i = t_df[t_df['Brand']=='IBDC']['This Month'].sum()
                t_ms_i, _, _ = calc_ms_brand(t_df, "IBDC")

                t_lm_m = t_df[t_df['Brand']=='MHW']['Last Month'].sum()
                t_tgt_m = t_df[t_df['Brand']=='MHW']['Target'].sum()
                t_mtd_m = t_df[t_df['Brand']=='MHW']['This Month'].sum()
                t_ms_m, _, _ = calc_ms_brand(t_df, "MHW")

                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                html += f'<td>{int(t_lm_i):,}</td><td>{int(t_tgt_i):,}</td><td>{int(t_mtd_i):,}</td><td>{t_ms_i:.1f}%</td>'
                html += f'<td>{int(t_lm_m):,}</td><td>{int(t_tgt_m):,}</td><td>{int(t_mtd_m):,}</td><td>{ms_mhw:.1f}%</td></tr>'

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
        html += '<th>LM</th><th>MTD</th><th>diff</th>'
    html += '</tr></thead><tbody>'

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    for b in brands_to_show:
        lm, mtd, diff = calc_ms_brand(df, b)
        html += f'<td>{lm:.1f}%</td><td>{mtd:.1f}%</td><td style="color: {"#9b1c1c" if diff < 0 else "#03543f"};">{diff:+.1f}%</td>'
    html += '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>'
        for b in brands_to_show:
            lm, mtd, diff = calc_ms_brand(z_df, b)
            html += f'<td>{lm:.1f}%</td><td>{mtd:.1f}%</td><td style="color: {"#9b1c1c" if diff < 0 else "#03543f"};">{diff:+.1f}%</td>'
        html += '</tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>'
            for b in brands_to_show:
                lm, mtd, diff = calc_ms_brand(a_df, b)
                html += f'<td>{lm:.1f}%</td><td>{mtd:.1f}%</td><td style="color: {"#9b1c1c" if diff < 0 else "#03543f"};">{diff:+.1f}%</td>'
            html += '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                for b in brands_to_show:
                    lm, mtd, diff = calc_ms_brand(t_df, b)
                    html += f'<td>{lm:.1f}%</td><td>{mtd:.1f}%</td><td style="color: {"#9b1c1c" if diff < 0 else "#03543f"};">{diff:+.1f}%</td>'
                html += '</tr>'

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
        html += '<th>LM</th><th>MTD</th><th>diff</th>'
    html += '</tr></thead><tbody>'

    def get_outlet_counts(sub_df, brand_name):
        lm_outlets = sub_df[(sub_df['Brand'] == brand_name) & (sub_df['Last Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub_df.columns else 0
        mtd_outlets = sub_df[(sub_df['Brand'] == brand_name) & (sub_df['This Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub_df.columns else 0
        diff = mtd_outlets - lm_outlets
        return lm_outlets, mtd_outlets, diff

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    for b in brands_to_show:
        lm_c, mtd_c, diff_c = get_outlet_counts(df, b)
        html += f'<td>{lm_c:,}</td><td>{mtd_c:,}</td><td style="color: {"#9b1c1c" if diff_c < 0 else "#03543f"};">{diff_c:+_d}</td>'
    html += '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>'
        for b in brands_to_show:
            lm_c, mtd_c, diff_c = get_outlet_counts(z_df, b)
            html += f'<td>{lm_c:,}</td><td>{mtd_c:,}</td><td style="color: {"#9b1c1c" if diff_c < 0 else "#03543f"};">{diff_c:+_d}</td>'
        html += '</tr>'

        asms = sort_asms(z_df['ASM'].dropna().unique())
        for asm in asms:
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>'
            for b in brands_to_show:
                lm_c, mtd_c, diff_c = get_outlet_counts(a_df, b)
                html += f'<td>{lm_c:,}</td><td>{mtd_c:,}</td><td style="color: {"#9b1c1c" if diff_c < 0 else "#03543f"};">{diff_c:+_d}</td>'
            html += '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                for b in brands_to_show:
                    lm_c, mtd_c, diff_c = get_outlet_counts(t_df, b)
                    html += f'<td>{lm_c:,}</td><td>{mtd_c:,}</td><td style="color: {"#9b1c1c" if diff_c < 0 else "#03543f"};">{diff_c:+_d}</td>'
                html += '</tr>'

    html += '</tbody></table></div>'
    return html

# --- 12. DISPLAY MAIN TABS ---
st.markdown("---")

main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Dashboard", "💬 Ask Assistant"])

with main_tab1:
    html_vol = generate_html_table(filtered_df, metric_type="Volume")
    render_zoomable_table(html_vol)

with main_tab2:
    html_ms = generate_html_table(filtered_df, metric_type="Ms%")
    render_zoomable_table(html_ms)

with main_tab3:
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Target vs Ach", "MS% Details", "WOD Details"])
    
    with sub_tab1:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Zone, ASM & TSE Performance Breakdown (IBDC & MHW)</h3>", unsafe_allow_html=True)
        html_h1 = generate_hierarchy_table_1(filtered_df)
        render_zoomable_table(html_h1)

    with sub_tab2:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Share / Growth Hierarchy Matrix (LM, MTD, Diff)</h3>", unsafe_allow_html=True)
        html_h2 = generate_hierarchy_table_2(filtered_df)
        render_zoomable_table(html_h2)

    with sub_tab3:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>Unique Billing Outlet Count Comparison (LM vs MTD)</h3>", unsafe_allow_html=True)
        html_h3 = generate_hierarchy_table_3(filtered_df)
        render_zoomable_table(html_h3)

with main_tab4:
    st.markdown("<h3 style='color: #f8fafc; font-size: 18px; font-family: Calibri, sans-serif;'>🤖 Smart Sales & Outlet Query Assistant</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 13.5px; font-family: Calibri, sans-serif;'>Perform advanced unbilled outlet queries, substitution gap analysis, run-rate comparisons, and multi-month brand trends.</p>", unsafe_allow_html=True)

    # 1. Ask Assistant Controls
    col_q1, col_q2, col_q3 = st.columns([1.2, 1, 1.8])
    
    with col_q1:
        basis_period = st.selectbox(
            "Basis on Period:",
            [
                "This Month (TM)",
                "Last Month (LM)",
                "Last 2 Months (LM + M2)",
                "Last 3 Months (LM + M2 + M3)",
                "Last 4 Months (LM + M2 + M3 + M4)",
                "Last 5 Months (LM + M2 + M3 + M4 + M5)"
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
                # Gap / Opportunity Queries
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
                # Run-rate & Trends
                "Brand-wise L3M Daily Run vs Current Month Daily Run",
                "Deluxe Industry - MS% Trend (6 Months)",
                "Semi Premium Whisky Industry - MS% Trend (6 Months)",
                "Deluxe Industry - Volume Trend (6 Months)",
                "Semi Premium Whisky Industry - Volume Trend (6 Months)",
                "Deluxe Industry - Unique Billed Outlets Trend (6 Months)",
                "Semi Premium Whisky Industry - Unique Billed Outlets Trend (6 Months)"
            ]
        )

    # Lazy-load historical dataset if historical months are needed
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

    # Define helper brand lists
    brand_family_map = {
        "IBDC": ["IBDC"],
        "MHW": ["MHW"],
        "MHFB": ["MHFB"],
        "BLGLM+BLGOR": ["BLGLM", "BLGOR"],
        "SMG+SMGP": ["SMG", "SMGP"],
        "SIW": ["SIW"],
        "Monarch": ["Monarch"]
    }

    # Filter sets based on active filter cascade & search multiselect
    def apply_active_filters(df_in):
        if df_in.empty: return df_in
        res = df_in.copy()
        
        # 1. Multiselect Search Filter (Matches LIC No / Outlet Name)
        if selected_search:
            valid_lics = filtered_df["LIC No"].dropna().astype(str).str.strip().unique()
            if "LIC No" in res.columns:
                res = res[res["LIC No"].astype(str).str.strip().isin(valid_lics)]
            elif "Outlet Name" in res.columns:
                valid_names = filtered_df["Outlet Name"].dropna().astype(str).str.strip().unique()
                res = res[res["Outlet Name"].astype(str).str.strip().isin(valid_names)]
                
        # 2. Standard Dropdown Filters
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

    # Compile the active basis dataset based on user dropdown selection
    if "This Month (TM)" in basis_period:
        basis_dfs = [f_this]
    elif "Last 2 Months" in basis_period:
        basis_dfs = [f_last, f_m2]
    elif "Last 3 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3]
    elif "Last 4 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3, f_m4]
    elif "Last 5 Months" in basis_period:
        basis_dfs = [f_last, f_m2, f_m3, f_m4, f_m5]
    else:  # Last Month (LM)
        basis_dfs = [f_last]
    
    basis_combined = pd.concat([d for d in basis_dfs if not d.empty], ignore_index=True) if basis_dfs else f_this

    # Master base outlets in current filtered scope
    base_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates() if "LIC No" in filtered_df.columns else pd.DataFrame()

    st.markdown("---")

    # --- QUERY EXECUTION LOGIC ---
    if query_type == "TIL Non Billed Outlets":
        target_brands = brand_family_map.get(target_brand_choice, [target_brand_choice])
        
        basis_vol_map = basis_combined.groupby("LIC No")["Value"].sum().to_dict() if "LIC No" in basis_combined.columns else {}
        basis_billed = [k for k, v in basis_vol_map.items() if v > 0]
        this_billed_target = f_this[(f_this["Brand"].isin(target_brands)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        
        unbilled_df = base_outlets[(base_outlets["LIC No"].isin(basis_billed)) & (~base_outlets["LIC No"].isin(this_billed_target))].copy()
        
        # Clean compact header: Volume (CS)
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
        # Clean compact header: Deluxe Vol (CS)
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
        # Clean compact header: SP Vol (CS)
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
        # Clean compact header: Billed Vol (CS)
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
        # Clean compact header: Historical Vol (CS)
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
        
        # Calculate L3M Volume (LM + M2 + M3)
        l3m_dfs = [f_last]
        if not f_m2.empty: l3m_dfs.append(f_m2)
        if not f_m3.empty: l3m_dfs.append(f_m3)
        
        l3m_comb = pd.concat(l3m_dfs, ignore_index=True)
        
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
        
        render_zoomable_table(html_rr)
        
        df_export_rr = pd.DataFrame(excel_rows)
        st.download_button("📥 Download in Excel", data=to_excel_bytes(df_export_rr), file_name="l3m_vs_tm_daily_run_segmented.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- 6-MONTH TREND TABLES (TM, LM, M2, M3, M4, M5) ---
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
        
        trend_months = ["TM", "LM", "M2", "M3", "M4", "M5"]
        months_dict = {
            "TM": f_this,
            "LM": f_last,
            "M2": f_m2,
            "M3": f_m3,
            "M4": f_m4,
            "M5": f_m5
        }
        
        html_trend = '<div class="table-wrapper"><table class="custom-dashboard-table">'
        html_trend += '<thead><tr><th class="seg-col-text">Brand</th>' + ''.join([f'<th>{m}</th>' for m in trend_months]) + '</tr></thead><tbody>'
        
        # Industry Header Row
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
        
        # Brand Rows
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
        render_zoomable_table(html_trend)
