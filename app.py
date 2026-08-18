import streamlit as st
import pandas as pd
import requests
import io
import datetime
import os
import base64
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
            
            /* --- FORCE SIDEBAR TO STAY DARK & VISIBLE IN ALL MODES --- */
            [data-testid="stSidebar"] {
                background-color: #0f172a !important;
                border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
            }
            [data-testid="stSidebar"] * {
                color: #f8fafc !important;
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
            
            /* --- CLEAN THIN BORDER STYLING & MOBILE TWO-FINGER ZOOM SUPPORT --- */
            .table-wrapper { 
                width: 100%; 
                overflow-x: auto; 
                -webkit-overflow-scrolling: touch; 
                margin-bottom: 20px; 
                display: block; 
                touch-action: pan-x pan-y pinch-zoom !important;
            }
            .custom-dashboard-table {
                border: 1px solid #d3d3d3 !important;
                border-collapse: collapse !important;
                background-color: #ffffff !important;
                touch-action: pan-x pan-y pinch-zoom !important;
            }
            .custom-dashboard-table th, .custom-dashboard-table td {
                border: 1px solid #d3d3d3 !important;
                padding: 4px 3px !important;
            }
            .custom-dashboard-table th {
                background-color: #D9E1F2 !important;
                border-bottom: 2px solid #b0b0b0 !important;
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

# --- 4. DATA FETCHING (FROM STREAMLIT SECRETS) ---
RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

# Read 2nd Historical Excel link from st.secrets with safe fallback
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
        
        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        fetch_time = datetime.datetime.now(ist_timezone).strftime("%d %b %Y, %I:%M %p")
        
        return dfs, None, fetch_time
    except Exception as e:
        return None, str(e), None

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
    dfs, error, last_update = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

# --- 5. LOGIN CREDENTIAL SYSTEM ---
if "Users" not in dfs:
    st.error("❌ Could not find the 'Users' sheet in your Excel file. Please add it with columns: Name, user_id, password.")
    st.stop()

raw_users_df = dfs["Users"].copy()

# Read F2 Date if available
days_elapsed = None
try:
    if raw_users_df.shape[1] >= 6 and raw_users_df.shape[0] >= 1:
        f2_val = raw_users_df.iloc[0, 5]
        if pd.notna(f2_val):
            if isinstance(f2_val, (datetime.datetime, datetime.date, pd.Timestamp)):
                days_elapsed = f2_val.day
            else:
                parsed_d = pd.to_datetime(str(f2_val).strip(), errors='coerce')
                if pd.notna(parsed_d):
                    days_elapsed = parsed_d.day
                else:
                    days_elapsed = int(str(f2_val).split('-')[0].strip())
except Exception:
    pass

if not days_elapsed:
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    days_elapsed = datetime.datetime.now(ist_tz).day

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
        .stApp { background-color: #0f172a !important; }
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
    .stApp { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label { color: #f8fafc !important; font-weight: 600 !important; }
    
    .stTabs [data-baseweb="tab-list"] button div p, 
    .stTabs [data-baseweb="tab-list"] button span,
    .stTabs [data-baseweb="tab"] p {
        color: #ef4444 !important;
        font-weight: 600 !important;
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

    .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; display: block; }
    .custom-dashboard-table { width: 100%; table-layout: auto; border-collapse: collapse !important; font-family: sans-serif; background-color: #ffffff; color: #000000; font-size: 8.5px; border: 1px solid #d3d3d3 !important; }
    .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #d3d3d3 !important; padding: 4px 3px !important; text-align: center; white-space: nowrap !important; }
    .custom-dashboard-table th { background-color: #D9E1F2; color: #000000; font-weight: bold; border-bottom: 2px solid #b0b0b0 !important; font-size: 8px; white-space: nowrap !important; }
    .subtotal-row { font-weight: bold; color: #000000; background-color: #F2F2F2; font-size: 8px; }
    .brand-row { background-color: #FFFFFF; color: #000000; }
    .brand-col-text { text-align: left !important; padding-left: 4px !important; font-size: 8px; white-space: nowrap !important; color: #000000; }
    .seg-col-text { text-align: left !important; line-height: 1.1; font-size: 8px; white-space: nowrap !important; color: #000000; }
    .grand-total-row { background-color: #D9E1F2; color: #000000; font-weight: bold; font-size: 9px; border-top: 2px solid #b0b0b0 !important; white-space: nowrap !important; }
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
    st.markdown("<h3 style='margin-top: 10px; font-size: 22px; color: #f8fafc;'>WB Sale Data</h3>", unsafe_allow_html=True)
with col_logout:
    role_display = "Admin" if st.session_state.get("is_admin", False) else "User"
    st.markdown(f"<p style='text-align: right; margin-top: 10px; font-size: 13px; color: #f8fafc;'>👤 <b>{st.session_state['user_name']}</b><br><span style='color: #60a5fa; font-size: 11px;'>{role_display}</span></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        try:
            cookie_manager.delete("wb_sale_user")
        except Exception:
            pass
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.session_state["is_admin"] = False
        st.rerun()

st.sidebar.markdown("📁 **Data Source**")
if last_update:
    st.sidebar.caption(f"🕒 **Last Synced:** {last_update}")

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

# --- 6. FETCH DATA FROM SHEETS ---
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
    df_raw["Search Reference"] = df_raw["Outlet Name"].astype(str) + " (" + df_raw["LIC No"].astype(str) + ")"

# --- 7. EXACT ORDER MAPPING & DATA CONVERSION ---
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

# --- 8. CASCADING SIDEBAR FILTERS ---
st.markdown("<h3 style='color: #f8fafc; font-size: 20px;'>🔍 Filters</h3>", unsafe_allow_html=True)
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

# --- 9. HTML TABLE GENERATORS FOR ORIGINAL TABS ---
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

# --- 10. UPDATED HIERARCHY REPORT GENERATORS ---
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
        html += f'<td>{int(z_lm_m):,}</td><td>{int(z_tgt_m):,}</td><td>{int(z_mtd_m):,}</td><td>{z_ms_m:.1f}%</td></tr>'

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
            html += f'<td>{int(a_lm_m):,}</td><td>{int(a_tgt_m):,}</td><td>{int(a_mtd_m):,}</td><td>{a_ms_m:.1f}%</td></tr>'

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
                html += f'<td>{int(t_lm_m):,}</td><td>{int(t_tgt_m):,}</td><td>{int(t_mtd_m):,}</td><td>{t_ms_m:.1f}%</td></tr>'

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

# --- 11. DISPLAY MAIN TABS ---
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
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Zone, ASM & TSE Performance Breakdown (IBDC & MHW)</h3>", unsafe_allow_html=True)
        html_h1 = generate_hierarchy_table_1(filtered_df)
        render_zoomable_table(html_h1)

    with sub_tab2:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Share / Growth Hierarchy Matrix (LM, MTD, Diff)</h3>", unsafe_allow_html=True)
        html_h2 = generate_hierarchy_table_2(filtered_df)
        render_zoomable_table(html_h2)

    with sub_tab3:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Unique Billing Outlet Count Comparison (LM vs MTD)</h3>", unsafe_allow_html=True)
        html_h3 = generate_hierarchy_table_3(filtered_df)
        render_zoomable_table(html_h3)

with main_tab4:
    st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>🤖 Smart Sales & Outlet Query Assistant</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 13px;'>Perform advanced unbilled outlet queries, substitution gap analysis, run-rate comparisons, and 5-month brand trends.</p>", unsafe_allow_html=True)

    # 1. Ask Assistant Controls
    col_q1, col_q2, col_q3 = st.columns([1.2, 1, 1.8])
    
    with col_q1:
        basis_period = st.selectbox(
            "Basis on Period:",
            [
                "Last Month (LM)",
                "Last 2 Months (LM + M2)",
                "Last 3 Months (LM + M2 + M3)",
                "Last 4 Months (LM + M2 + M3 + M4)"
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
                "Not Billed Outlet",
                "MMV Billed but BLGLM+BLGOR Not Billed",
                "MCD Lux Billed but IBDC Not Billed",
                "IQ Billed but IBDC Not Billed",
                "Deluxe & Deluxe Plus Industry > 30 cs but IBDC Not Billed",
                "Semi Premium Whisky Industry > 50 cs but MHW Not Billed",
                "RSW Billed but MHW Not Billed",
                "RGW Billed but MHW Not Billed",
                "SRB7 Billed but MHW Not Billed",
                "RCW Billed but MHW Not Billed",
                "All Season Billed but MHW Not Billed",
                "SMG+SMGP Not Repeated Outlet List",
                "SIW Not Repeated Outlet List",
                # Run-rate & Trends
                "Brand wise L3M Avg Run vs Current Month Daily Run",
                "Deluxe Industry - MS% Trend (5 Months)",
                "Semi Premium Whisky Industry - MS% Trend (5 Months)",
                "Deluxe Industry - Volume Trend (5 Months)",
                "Semi Premium Whisky Industry - Volume Trend (5 Months)",
                "Deluxe Industry - Unique Billed Outlets Trend (5 Months)",
                "Semi Premium Whisky Industry - Unique Billed Outlets Trend (5 Months)"
            ]
        )

    # Lazy-load historical dataset if historical months are needed
    needs_history = any(x in query_type for x in ["Trend", "L3M", "Repeated"]) or "2" in basis_period or "3" in basis_period or "4" in basis_period
    
    df_m2 = pd.DataFrame()
    df_m3 = pd.DataFrame()
    df_m4 = pd.DataFrame()

    if needs_history:
        with st.spinner("Fetching 5-month historical data (M2, M3, M4)..."):
            hist_dfs, hist_err = load_historical_data_from_url(RAW_HISTORICAL_URL)
            if hist_err or not hist_dfs:
                st.warning(f"⚠️ Note: Could not load historical Excel (M2-M4): {hist_err}. Analysis will run on available data.")
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

    # Filter historical sets based on current scope
    def apply_active_filters(df_in):
        if df_in.empty: return df_in
        res = df_in.copy()
        if selected_group != "All" and "Group" in res.columns:
            res = res[res["Group"].astype(str) == selected_group]
        if selected_asm != "All" and "ASM" in res.columns:
            res = res[res["ASM"].astype(str) == selected_asm]
        if selected_tse != "All" and "TSE" in res.columns:
            res = res[res["TSE"].astype(str) == selected_tse]
        if selected_lic != "All" and "LIC No" in res.columns:
            res = res[res["LIC No"].astype(str) == selected_lic]
        if selected_outlet != "All" and "Outlet Name" in res.columns:
            res = res[res["Outlet Name"].astype(str) == selected_outlet]
        return res

    f_this = apply_active_filters(df_this)
    f_last = apply_active_filters(df_last)
    f_m2 = apply_active_filters(df_m2)
    f_m3 = apply_active_filters(df_m3)
    f_m4 = apply_active_filters(df_m4)

    # Master base outlets in current filtered scope
    base_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates() if "LIC No" in filtered_df.columns else pd.DataFrame()

    st.markdown("---")

    # --- QUERY EXECUTION LOGIC ---
    if query_type == "Not Billed Outlet":
        st.markdown(f"#### 🔍 Outlets that have not billed **{target_brand_choice}** this month:")
        target_brands = brand_family_map.get(target_brand_choice, [target_brand_choice])
        
        # Outlets billed in selected basis period
        basis_dfs = [f_last]
        if "2" in basis_period: basis_dfs += [f_m2]
        elif "3" in basis_period: basis_dfs += [f_m2, f_m3]
        elif "4" in basis_period: basis_dfs += [f_m2, f_m3, f_m4]
        
        basis_combined = pd.concat(basis_dfs, ignore_index=True) if basis_dfs else f_last
        basis_billed = basis_combined[basis_combined["Value"] > 0]["LIC No"].unique() if "LIC No" in basis_combined.columns else []
        
        this_billed_target = f_this[(f_this["Brand"].isin(target_brands)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        
        # Outlets that were active in basis period but unbilled for target brand in TM
        unbilled_df = base_outlets[(base_outlets["LIC No"].isin(basis_billed)) & (~base_outlets["LIC No"].isin(this_billed_target))]
        
        if not unbilled_df.empty:
            st.dataframe(unbilled_df, use_container_width=True)
            st.download_button("📥 Download Unbilled Outlets CSV", data=unbilled_df.to_csv(index=False).encode('utf-8'), file_name=f"unbilled_{target_brand_choice}.csv", mime="text/csv")
        else:
            st.success(f"🎉 No unbilled outlets found for {target_brand_choice} within the active filter scope!")

    elif "Billed but" in query_type or "Billed But" in query_type or "Billed" in query_type and "Not Billed" in query_type:
        if "MMV" in query_type:
            driver_b, target_b = ["MMV"], ["BLGLM", "BLGOR"]
        elif "MCD Lux" in query_type:
            driver_b, target_b = ["MCD Lux"], ["IBDC"]
        elif "IQ" in query_type:
            driver_b, target_b = ["IQ"], ["IBDC"]
        elif "RSW" in query_type:
            driver_b, target_b = ["RSW"], ["MHW"]
        elif "RGW" in query_type:
            driver_b, target_b = ["RGW"], ["MHW"]
        elif "SRB7" in query_type:
            driver_b, target_b = ["SRB7"], ["MHW"]
        elif "RCW" in query_type:
            driver_b, target_b = ["RCW"], ["MHW"]
        elif "All Season" in query_type:
            driver_b, target_b = ["All Season"], ["MHW"]
        else:
            driver_b, target_b = [], []

        st.markdown(f"#### 🔍 Outlets Billing **{'/'.join(driver_b)}** but NOT Billing **{'/'.join(target_b)}** this month:")
        
        driver_outlets = f_this[(f_this["Brand"].isin(driver_b)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        target_outlets = f_this[(f_this["Brand"].isin(target_b)) & (f_this["Value"] > 0)]["LIC No"].unique() if "LIC No" in f_this.columns else []
        
        gap_lics = set(driver_outlets) - set(target_outlets)
        gap_df = base_outlets[base_outlets["LIC No"].isin(gap_lics)]
        
        if not gap_df.empty:
            st.dataframe(gap_df, use_container_width=True)
            st.download_button("📥 Download Gap Outlets CSV", data=gap_df.to_csv(index=False).encode('utf-8'), file_name="brand_gap_outlets.csv", mime="text/csv")
        else:
            st.success("🎉 No gap outlets found!")

    elif "Deluxe & Deluxe Plus Industry > 30 cs" in query_type:
        st.markdown("#### 🔍 Outlets with Deluxe Industry Volume > 30 cases but IBDC NOT Billed (This Month):")
        deluxe_vol = f_this[f_this["Segment"].isin(["Deluxe-Whisky", "Deluxe Plus-Whisky"])].groupby("LIC No")["Value"].sum()
        deluxe_30_lics = deluxe_vol[deluxe_vol > 30].index.tolist()
        ibdc_billed = f_this[(f_this["Brand"] == "IBDC") & (f_this["Value"] > 0)]["LIC No"].unique()
        
        target_lics = set(deluxe_30_lics) - set(ibdc_billed)
        res_df = base_outlets[base_outlets["LIC No"].isin(target_lics)].copy()
        res_df["Deluxe Industry Vol"] = res_df["LIC No"].map(deluxe_vol)
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            st.download_button("📥 Download Deluxe > 30cs Gap CSV", data=res_df.to_csv(index=False).encode('utf-8'), file_name="deluxe_30cs_ibdc_unbilled.csv", mime="text/csv")
        else:
            st.success("🎉 No outlets found matching this condition!")

    elif "Semi Premium Whisky Industry > 50 cs" in query_type:
        st.markdown("#### 🔍 Outlets with Semi Premium Whisky Volume > 50 cases but MHW NOT Billed (This Month):")
        sp_vol = f_this[f_this["Segment"] == "Semi Premium-Whisky"].groupby("LIC No")["Value"].sum()
        sp_50_lics = sp_vol[sp_vol > 50].index.tolist()
        mhw_billed = f_this[(f_this["Brand"] == "MHW") & (f_this["Value"] > 0)]["LIC No"].unique()
        
        target_lics = set(sp_50_lics) - set(mhw_billed)
        res_df = base_outlets[base_outlets["LIC No"].isin(target_lics)].copy()
        res_df["Semi Premium Vol"] = res_df["LIC No"].map(sp_vol)
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            st.download_button("📥 Download Semi Premium > 50cs Gap CSV", data=res_df.to_csv(index=False).encode('utf-8'), file_name="sp_50cs_mhw_unbilled.csv", mime="text/csv")
        else:
            st.success("🎉 No outlets found matching this condition!")

    elif "Not Repeated Outlet List" in query_type:
        target_brands = ["SMG", "SMGP"] if "SMG" in query_type else ["SIW"]
        brand_name_str = "SMG+SMGP" if "SMG" in query_type else "SIW"
        st.markdown(f"#### 🔍 Outlets that Billed **{brand_name_str}** in Previous Months (LM/M2/M3) but have NOT Repeated This Month:")
        
        prev_billed = set()
        for d in [f_last, f_m2, f_m3]:
            if not d.empty and "Brand" in d.columns:
                prev_billed.update(d[(d["Brand"].isin(target_brands)) & (d["Value"] > 0)]["LIC No"].dropna().unique())
        
        tm_billed = set(f_this[(f_this["Brand"].isin(target_brands)) & (f_this["Value"] > 0)]["LIC No"].dropna().unique()) if not f_this.empty else set()
        
        not_repeated = prev_billed - tm_billed
        res_df = base_outlets[base_outlets["LIC No"].isin(not_repeated)]
        
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
            st.download_button(f"📥 Download {brand_name_str} Lapsed Outlets CSV", data=res_df.to_csv(index=False).encode('utf-8'), file_name=f"{brand_name_str}_not_repeated.csv", mime="text/csv")
        else:
            st.success(f"🎉 All previous billers have repeated for {brand_name_str} this month!")

    elif "Brand wise L3M Avg Run vs Current Month Daily Run" in query_type:
        st.markdown(f"#### 📊 Brand wise L3M Daily Run (L3M Vol / 90) vs TM Daily Run (TM Vol / {days_elapsed} days):")
        
        # Calculate L3M Volume (LM + M2 + M3)
        l3m_dfs = [f_last]
        if not f_m2.empty: l3m_dfs.append(f_m2)
        if not f_m3.empty: l3m_dfs.append(f_m3)
        
        l3m_comb = pd.concat(l3m_dfs, ignore_index=True)
        l3m_brand = l3m_comb.groupby("Brand", observed=False)["Value"].sum()
        tm_brand = f_this.groupby("Brand", observed=False)["Value"].sum()
        
        all_b_names = sorted(list(set(l3m_brand.index).union(set(tm_brand.index))))
        rr_data = []
        for b in all_b_names:
            l3m_v = l3m_brand.get(b, 0)
            tm_v = tm_brand.get(b, 0)
            l3m_daily = round(l3m_v / 90.0, 1)
            tm_daily = round(tm_v / float(days_elapsed), 1)
            growth = round(tm_daily - l3m_daily, 1)
            rr_data.append({
                "Brand": b,
                "L3M Total Vol": int(l3m_v),
                "L3M Daily Avg (/90)": l3m_daily,
                "TM Vol": int(tm_v),
                f"TM Daily Avg (/{days_elapsed})": tm_daily,
                "Diff / Growth": growth
            })
            
        df_rr = pd.DataFrame(rr_data)
        st.dataframe(df_rr, use_container_width=True)
        st.download_button("📥 Download Run-Rate CSV", data=df_rr.to_csv(index=False).encode('utf-8'), file_name="l3m_vs_tm_daily_run.csv", mime="text/csv")

    # --- 5-MONTH TREND TABLES ---
    elif "Trend (5 Months)" in query_type:
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
        
        months_dict = {
            "TM": f_this,
            "LM": f_last,
            "M2": f_m2,
            "M3": f_m3,
            "M4": f_m4
        }
        
        # Build 5-Month Table Structure
        html_trend = '<div class="table-wrapper"><table class="custom-dashboard-table">'
        html_trend += '<thead><tr><th class="seg-col-text">Brand</th><th>TM</th><th>LM</th><th>M2</th><th>M3</th><th>M4</th></tr></thead><tbody>'
        
        # Industry Header Row
        html_trend += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{target_industry_name}</b></td>'
        for m_key in ["TM", "LM", "M2", "M3", "M4"]:
            m_df = months_dict[m_key]
            if m_df.empty:
                html_trend += '<td>-</td>'
                continue
            ind_sub = m_df[m_df["Segment"].isin(industry_segs)]
            if is_ms:
                html_trend += '<td>100.0%</td>'
            elif is_vol:
                html_trend += f'<td>{int(ind_sub["Value"].sum()):,}</td>'
            elif is_wod:
                html_trend += f'<td>{ind_sub[ind_sub["Value"] > 0]["LIC No"].nunique():,}</td>'
        html_trend += '</tr>'
        
        # Brand Rows
        for b in brand_list:
            html_trend += f'<tr class="brand-row"><td class="brand-col-text">{b}</td>'
            for m_key in ["TM", "LM", "M2", "M3", "M4"]:
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
