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
st.set_page_config(
    page_title="WB Sale Data Dashboard", 
    page_icon="logo.png" if os.path.exists("logo.png") else "📊", 
    layout="wide"
)

# --- PREMIUM MODERN CSS & MOBILE/LAPTOP RESPONSIVE STYLING ---
modern_theme_style = """
<style>
/* --- GLOBAL APP STYLING --- */
.stApp {
    background-color: #0b1120 !important;
    font-family: Calibri, 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #f8fafc !important;
}

#MainMenu, footer, header {visibility: hidden;}

/* --- SIDEBAR REFINEMENT --- */
[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]):not(i):not(svg):not(span[class*="material"]):not(span[class*="icon"]) {
    color: #f8fafc !important;
}
[data-testid="stSidebar"] a {
    color: #38bdf8 !important;
    text-decoration: none !important;
}

/* --- SIDEBAR & BUTTON STYLING --- */
[data-testid="stSidebar"] .stButton button, 
[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
    width: 100% !important;
    font-weight: 600 !important;
    transition: all 0.2s ease-in-out;
}
[data-testid="stSidebar"] .stButton button:hover, 
[data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(135deg, #334155 1e293b) !important;
    border-color: #3b82f6 !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

/* --- TABS RESPONSIVE DESIGN --- */
.stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    background-color: rgba(30, 41, 59, 0.5);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 8px 16px !important;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"] p {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}

/* --- CARD CONTAINERS --- */
.dashboard-card {
    background: rgba(30, 41, 59, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    margin-bottom: 20px;
}

/* --- TABLE STYLING --- */
.table-wrapper { 
    width: 100%; 
    overflow-x: auto; 
    -webkit-overflow-scrolling: touch; 
    margin-bottom: 20px; 
    display: block; 
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.custom-dashboard-table {
    width: 100%;
    border-collapse: collapse !important;
    font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    font-size: 13.5px !important;
}
.custom-dashboard-table th, .custom-dashboard-table td {
    border: 1px solid #d3d3d3 !important;
    padding: 8px 10px !important;
    text-align: center; 
    white-space: nowrap !important;
}
.custom-dashboard-table th {
    background-color: #D9E1F2 !important;
    border-bottom: 2px solid #b0b0b0 !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    color: #1e293b !important;
}
.subtotal-row { 
    font-weight: bold !important; 
    color: #000000 !important; 
    background-color: #F2F2F2 !important; 
}
.brand-row { 
    background-color: #FFFFFF !important; 
    color: #000000 !important; 
}
.brand-col-text, .seg-col-text { 
    text-align: left !important; 
    padding-left: 10px !important; 
    white-space: nowrap !important; 
    color: #000000 !important; 
}
.grand-total-row { 
    background-color: #D9E1F2 !important; 
    color: #000000 !important; 
    font-weight: bold !important; 
    font-size: 14px !important; 
    border-top: 2px solid #b0b0b0 !important; 
}
</style>
"""
st.markdown(modern_theme_style, unsafe_allow_html=True)

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

def show_df(df):
    cfg = {}
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            cfg[c] = st.column_config.NumberColumn(format="%.2f")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config=cfg)

# --- 5. DATA FETCHING ---
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

with st.spinner("Connecting to live database..."):
    dfs, error = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

# --- 6. LOGIN CREDENTIAL & DATE EXTRACTOR ---
if "Users" not in dfs:
    st.error("❌ Could not find the 'Users' sheet in your Excel file.")
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
name_idx, user_idx, pass_idx, role_idx = 0, 1, 2, 3 if df_users.shape[1] > 3 else None

for idx, col in enumerate(df_users.columns):
    c_clean = str(col).strip().lower()
    if c_clean in ["name", "emp name", "employee name", "sales rep"] and "user" not in c_clean:
        name_idx = idx
    elif c_clean in ["user_id", "userid", "user id", "phone", "mobile", "login id"]:
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
        if not user_row.empty:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = str(user_row.iloc[0]["Name"])
            st.session_state["session_cycle"] = active_cycle_date
            st.session_state["is_admin"] = str(user_row.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
        else:
            st.session_state["authenticated"] = False
    else:
        st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
        .stApp { background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%) !important; }
        [data-testid="stForm"] { 
            background: rgba(30, 41, 59, 0.75) !important; 
            backdrop-filter: blur(16px) !important; 
            border: 1px solid rgba(255, 255, 255, 0.1) !important; 
            padding: 40px 30px !important; 
            border-radius: 20px !important; 
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important; 
        }
        .stTextInput label { color: #94a3b8 !important; font-weight: 600; font-size: 13px; }
        .stTextInput input { 
            background-color: rgba(15, 23, 42, 0.6) !important; 
            color: #f8fafc !important; 
            border-radius: 10px !important; 
            border: 1px solid rgba(255, 255, 255, 0.12) !important; 
            padding: 12px 14px !important; 
        }
        .stButton button { 
            width: 100%; 
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); 
            color: white; 
            border-radius: 10px; 
            font-weight: 600; 
            padding: 12px; 
            border: none; 
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4); 
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            if os.path.exists("logo.png"):
                try:
                    with open("logo.png", "rb") as img_file:
                        encoded_img = base64.b64encode(img_file.read()).decode()
                    st.markdown(f"""
                        <div style="display: flex; justify-content: center; width: 100%; margin-bottom: 12px;">
                            <img src="data:image/png;base64,{encoded_img}" style="width: 90px; display: block;" />
                        </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    pass
            
            st.markdown("<h2 style='color: #f8fafc; text-align: center; margin-bottom: 6px; font-size: 24px; font-weight: 700;'>WB Sale Data</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94a3b8; text-align: center; font-size: 13px; margin-bottom: 24px;'>Sign in with your credentials to access the analytics portal</p>", unsafe_allow_html=True)
            
            input_user = st.text_input("User ID", placeholder="Enter User ID")
            input_pass = st.text_input("Password", type="password", placeholder="Enter Password")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Sign In")
            
            if submit_btn:
                user_match = df_users_clean[
                    (df_users_clean["user_id"].str.lower() == str(input_user).strip().lower()) & 
                    (df_users_clean["password"] == str(input_pass).strip())
                ]
                if not user_match.empty:
                    real_name = str(user_match.iloc[0]["Name"]).strip()
                    cur_now = datetime.datetime.now(IST)
                    cur_cycle = get_current_session_cycle_date(cur_now)
                    seconds_to_expiry = get_seconds_until_next_1159_pm(cur_now)
                    
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = real_name
                    st.session_state["session_cycle"] = cur_cycle
                    st.session_state["is_admin"] = str(user_match.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
                    
                    try:
                        cookie_manager.set("wb_sale_user", real_name, max_age=seconds_to_expiry)
                        cookie_manager.set("wb_sale_cycle", cur_cycle, max_age=seconds_to_expiry)
                    except Exception:
                        pass
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
    st.stop()

# --- APP HEADER & USER BAR ---
col_logo, col_title, col_logout = st.columns([0.6, 5.4, 2])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=48)
with col_title:
    st.markdown("<h3 style='margin: 6px 0 0 0; font-size: 20px; color: #f8fafc; font-weight: 700;'>WB Sale Data Analytics</h3>", unsafe_allow_html=True)
with col_logout:
    role_display = "Admin" if st.session_state.get("is_admin", False) else "User"
    user_display = st.session_state.get('user_name', 'User')
    st.markdown(f"<p style='text-align: right; margin: 2px 0 0 0; font-size: 13px; color: #f8fafc;'>👤 <b>{user_display}</b> <span style='color: #38bdf8; font-size: 11px;'>({role_display})</span></p>", unsafe_allow_html=True)
    if st.button("Logout", key="logout_btn"):
        try:
            cookie_manager.delete("wb_sale_user")
            cookie_manager.delete("wb_sale_cycle")
        except Exception:
            pass
        st.session_state.update({"authenticated": False, "user_name": "", "session_cycle": "", "is_admin": False})
        st.rerun()

# --- 7. LOAD AND PROCESS DATASETS ---
required_sheets = ["This Month", "Last Month", "Target Data", "Outlet Master"]
for sheet in required_sheets:
    if sheet not in dfs:
        st.error(f"❌ Missing required sheet: '{sheet}' in source file.")
        st.stop()

df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()

df_outlet.columns = df_outlet.columns.astype(str).str.strip()
if "Outlet Nan" in df_outlet.columns:
    df_outlet.rename(columns={"Outlet Nan": "Outlet Name"}, inplace=True)

group_col_name = df_outlet.columns[7] if len(df_outlet.columns) > 7 else "Group"
if group_col_name != "Group" and "Group" not in df_outlet.columns:
    df_outlet.rename(columns={group_col_name: "Group"}, inplace=True)

zone_col_map = next((col for col in df_outlet.columns if "zone" in col.lower()), None)
asm_col_map = next((col for col in df_outlet.columns if col.lower() in ["asm", "manager"]), None)
tse_col_map = df_outlet.columns[14] if len(df_outlet.columns) > 14 else next((col for col in df_outlet.columns if "tse" in col.lower()), None)
map_key = "LIC No" if "LIC No" in df_outlet.columns else ("Outlet Name" if "Outlet Name" in df_outlet.columns else None)

group_mapping, zone_mapping, asm_mapping, tse_mapping = {}, {}, {}, {}
if map_key:
    group_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet["Group"].astype(str).str.strip()))
    if zone_col_map: zone_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[zone_col_map].astype(str).str.strip()))
    if asm_col_map: asm_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[asm_col_map].astype(str).str.strip()))
    if tse_col_map: tse_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[tse_col_map].astype(str).str.strip()))

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
        d["Zone"] = d[k_col].astype(str).str.strip().map(zone_mapping).fillna("West Bengal") if zone_mapping else "West Bengal"
        if asm_mapping: d["ASM"] = d[k_col].astype(str).str.strip().map(asm_mapping).fillna(d.get("ASM", "Unassigned"))
        if tse_mapping: d["TSE"] = d[k_col].astype(str).str.strip().map(tse_mapping).fillna(d.get("TSE", "Unassigned"))
    else:
        d["Group"], d["Zone"] = "Unassigned", "West Bengal"
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
    df_combined, values="Value", index=dim_cols, columns="Metric", aggfunc="sum"
).reset_index()

if "Outlet Name" in df_raw.columns and "LIC No" in df_raw.columns:
    df_raw["Search Reference"] = df_raw["Outlet Name"].astype(str).str.strip() + " (" + df_raw["LIC No"].astype(str).str.strip() + ")"

# --- OFFLINE HTML BUNDLE GENERATOR ---
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
        body { background-color: #0f172a; color: #f8fafc; font-family: Calibri, sans-serif; margin: 0; padding: 16px; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 16px; }
        .btn { background: #3b82f6; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-red { background: #ef4444; }
        .card { background: #1e293b; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
        .grid-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
        label { font-size: 13px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px; }
        select, input { width: 100%; background-color: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 8px 10px; border-radius: 8px; font-size: 13.5px; }
        .table-wrapper { width: 100%; overflow-x: auto; background: #fff; border-radius: 8px; border: 1px solid #d3d3d3; margin-bottom: 16px; }
        .custom-table { width: 100%; border-collapse: collapse; font-family: Calibri, sans-serif; color: #000; font-size: 13.5px; }
        .custom-table th, .custom-table td { border: 1px solid #d3d3d3; padding: 7px 10px; text-align: center; white-space: nowrap; }
        .custom-table th { background-color: #D9E1F2; font-weight: 700; }
        .subtotal-row { font-weight: bold; background-color: #F2F2F2; text-align: left; }
        .grand-total-row { background-color: #D9E1F2; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div>
            <h3 style="margin: 0; font-size: 20px;">WB Sale Data Analytics</h3>
            <span style="font-size: 12px; color: #10b981; font-weight: bold;">● 100% Offline Mode Active</span>
        </div>
        <button class="btn btn-red" onclick="window.close()">Close Window</button>
    </div>
    <div class="card">
        <h4 style="margin: 0 0 10px 0; font-size: 15px;">🔍 Filters</h4>
        <div class="grid-filters">
            <div><label>Group</label><select id="selGroup" onchange="onGroupChange()"></select></div>
            <div><label>ASM</label><select id="selASM" onchange="onASMChange()"></select></div>
            <div><label>TSE</label><select id="selTSE" onchange="onTSEChange()"></select></div>
            <div><label>LIC No</label><select id="selLIC" onchange="onLICChange()"></select></div>
            <div><label>Outlet</label><select id="selOutlet" onchange="updateDashboard()"></select></div>
        </div>
    </div>
    <div class="table-wrapper"><table class="custom-table" id="tableVolume"><thead><tr><th style="text-align:left;">Brand</th><th>__LM_LBL__</th><th>TGT</th><th>__TM_LBL__</th><th>BAL</th></tr></thead><tbody id="bodyVolume"></tbody></table></div>
    <script>
        let appSales = __SALES_DATA__;
        const MASTER_STRUCTURE = [
            { seg: "Deluxe-Whisky", brands: ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak"] },
            { seg: "Semi Premium-Whisky", brands: ["MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR"] }
        ];
        function toNum(v) { const n = parseFloat(v); return isNaN(n) ? 0 : n; }
        function f2(v) { return Number(v).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
        window.onload = function() {
            setSelectOptions('selGroup', [...new Set(appSales.map(d => d.group).filter(Boolean))].sort());
            onGroupChange();
        };
        function setSelectOptions(id, values) {
            const sel = document.getElementById(id);
            sel.innerHTML = '<option value="All">All</option>' + values.map(v => `<option value="${v}">${v}</option>`).join('');
        }
        function getScoped(lvl) {
            const g = document.getElementById('selGroup').value, a = document.getElementById('selASM').value, t = document.getElementById('selTSE').value;
            return appSales.filter(d => (lvl<1||g==='All'||d.group===g) && (lvl<2||a==='All'||d.asm===a) && (lvl<3||t==='All'||d.tse===t));
        }
        function onGroupChange() {
            setSelectOptions('selASM', [...new Set(getScoped(1).map(d => d.asm).filter(Boolean))].sort());
            onASMChange();
        }
        function onASMChange() {
            setSelectOptions('selTSE', [...new Set(getScoped(2).map(d => d.tse).filter(Boolean))].sort());
            onTSEChange();
        }
        function onTSEChange() {
            setSelectOptions('selLIC', [...new Set(getScoped(3).map(d => d.lic).filter(Boolean))].sort());
            onLICChange();
        }
        function onLICChange() {
            setSelectOptions('selOutlet', [...new Set(getScoped(4).map(d => d.outlet).filter(Boolean))].sort());
            updateDashboard();
        }
        function updateDashboard() {
            const g = document.getElementById('selGroup').value, a = document.getElementById('selASM').value, t = document.getElementById('selTSE').value, l = document.getElementById('selLIC').value, o = document.getElementById('selOutlet').value;
            const data = appSales.filter(d => (g==='All'||d.group===g) && (a==='All'||d.asm===a) && (t==='All'||d.tse===t) && (l==='All'||d.lic===l) && (o==='All'||d.outlet===o));
            let html = '', gtLM=0, gtTGT=0, gtTM=0;
            MASTER_STRUCTURE.forEach(group => {
                const segRecs = data.filter(d => d.seg === group.seg);
                const sLM = segRecs.reduce((a,c)=>a+toNum(c.lm),0), sTGT = segRecs.reduce((a,c)=>a+toNum(c.tgt),0), sTM = segRecs.reduce((a,c)=>a+toNum(c.tm),0);
                html += `<tr class="subtotal-row"><td style="text-align:left;">${group.seg}</td><td>${f2(sLM)}</td><td>${f2(sTGT)}</td><td>${f2(sTM)}</td><td></td></tr>`;
                group.brands.forEach(b => {
                    const bRecs = segRecs.filter(d => d.brand === b);
                    html += `<tr><td style="text-align:left; padding-left:16px;">${b}</td><td>${f2(bRecs.reduce((a,c)=>a+toNum(c.lm),0))}</td><td>${f2(bRecs.reduce((a,c)=>a+toNum(c.tgt),0))}</td><td>${f2(bRecs.reduce((a,c)=>a+toNum(c.tm),0))}</td><td></td></tr>`;
                });
                gtLM += sLM; gtTGT += sTGT; gtTM += sTM;
            });
            html += `<tr class="grand-total-row"><td style="text-align:left;">Grand Total</td><td>${f2(gtLM)}</td><td>${f2(gtTGT)}</td><td>${f2(gtTM)}</td><td></td></tr>`;
            document.getElementById('bodyVolume').innerHTML = html;
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

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("📁 **Data Management**")
st.sidebar.caption(f"🕒 **Last Synced:** {f2_display_date}")

if st.sidebar.button("🔄 Refresh Data Cache"):
    st.cache_data.clear()
    st.sidebar.success("Cache successfully cleared!")

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
        padding: 11px 16px;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        font-family: Calibri, sans-serif;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
    ">
        🚀 Launch Offline Mode
    </button>
</div>
<script>
function launchOffline() {{
    const bin = atob("{b64_html}");
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) {{ bytes[i] = bin.charCodeAt(i); }}
    const blob = new Blob([bytes], {{ type: 'text/html;charset=utf-8' }});
    window.open(URL.createObjectURL(blob), '_blank');
}}
</script>
"""
with st.sidebar:
    components.html(launch_btn_code, height=52)
    st.caption("💡 *Works completely offline in any browser.*")

st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Admin Panel**")
if st.session_state.get("is_admin", False):
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        if len(all_rows) > 1:
            df_logs = pd.DataFrame(all_rows[1:], columns=all_rows[0])
            st.sidebar.download_button("📥 Download Login Logs", data=df_logs.to_csv(index=False).encode('utf-8'), file_name="wb_login_logs.csv", mime="text/csv")
        else:
            st.sidebar.info("ℹ️ No login logs recorded yet.")
    except Exception as e:
        st.sidebar.error("⚠️ Log Connection Error.")
else:
    st.sidebar.info("Logs are securely recorded.")

st.sidebar.markdown("---")
st.sidebar.markdown("🔗 **[Go to FTS Calculator](https://wbftscalculator.streamlit.app/)**")

# --- 8. FILTERS ---
num_cols = ["Last Month", "Target", "This Month"]
for col in num_cols:
    if col not in df_raw.columns: df_raw[col] = 0
    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)

seg_col, brand_col = "Segment", "Brand"
explicit_seg_order = ["Deluxe-Whisky", "Semi Premium-Whisky", "Deluxe-Gin", "Premium-Brandy", "Premium-Gin", "Semi Premium-Brandy", "Single Malt-Scotch"]
explicit_brand_order = ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak", "MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR", "BLGLM", "BLGOR", "Big Ben", "Blue Riband", "Monarch", "SMG", "SMGP", "MHFB", "SIW"]

df_raw[seg_col] = pd.Categorical(df_raw[seg_col], categories=explicit_seg_order + [x for x in df_raw[seg_col].unique() if x not in explicit_seg_order], ordered=True)
df_raw[brand_col] = pd.Categorical(df_raw[brand_col], categories=explicit_brand_order + [x for x in df_raw[brand_col].unique() if x not in explicit_brand_order], ordered=True)
master_brands = df_raw[[seg_col, brand_col]].drop_duplicates().dropna().sort_values(by=[seg_col, brand_col])

st.markdown("<div class='dashboard-card'><h4 style='margin:0 0 12px 0; font-size:16px;'>🔍 Filters & Scope</h4>", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
temp_df = df_raw.copy()

with col1:
    g_opts = ["All"] + sorted(temp_df["Group"].dropna().astype(str).unique().tolist())
    sel_g = st.selectbox("Group", g_opts)
    if sel_g != "All": temp_df = temp_df[temp_df["Group"].astype(str) == sel_g]
with col2:
    a_opts = ["All"] + sorted(temp_df["ASM"].dropna().astype(str).unique().tolist())
    sel_a = st.selectbox("ASM", a_opts)
    if sel_a != "All": temp_df = temp_df[temp_df["ASM"].astype(str) == sel_a]
with col3:
    t_opts = ["All"] + sorted(temp_df["TSE"].dropna().astype(str).unique().tolist())
    sel_t = st.selectbox("TSE", t_opts)
    if sel_t != "All": temp_df = temp_df[temp_df["TSE"].astype(str) == sel_t]
with col4:
    l_opts = ["All"] + sorted(temp_df["LIC No"].dropna().astype(str).unique().tolist())
    sel_l = st.selectbox("LIC No", l_opts)
    if sel_l != "All": temp_df = temp_df[temp_df["LIC No"].astype(str) == sel_l]
with col5:
    o_opts = ["All"] + sorted(temp_df["Outlet Name"].dropna().astype(str).unique().tolist())
    sel_o = st.selectbox("Outlet", o_opts)
    if sel_o != "All": temp_df = temp_df[temp_df["Outlet Name"].astype(str) == sel_o]

search_options = sorted(temp_df["Search Reference"].dropna().unique().tolist()) if "Search Reference" in temp_df.columns else []
selected_search = st.multiselect("⚡ Quick Search Outlet / LIC No", search_options)
filtered_df = temp_df[temp_df["Search Reference"].isin(selected_search)] if selected_search else temp_df.copy()
st.markdown("</div>", unsafe_allow_html=True)

# --- ZOOMABLE TABLE RENDERER ---
ZOOM_TABLE_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<style>
  html, body { margin:0; padding:0; height:100%; background:transparent; font-family:Calibri,sans-serif; overflow:hidden; }
  #bar { display:flex; gap:6px; align-items:center; height:32px; }
  #bar button { background:#1e293b; color:#fff; border:1px solid rgba(255,255,255,.25); border-radius:6px; min-width:36px; padding:2px 10px; font-size:14px; font-weight:700; cursor:pointer; }
  #zl { margin-left:auto; color:#94a3b8; font-size:12px; }
  #vp { position:absolute; top:36px; left:0; right:0; bottom:0; overflow:auto; background:#fff; border:1px solid #d3d3d3; border-radius:6px; -webkit-overflow-scrolling:touch; }
  #content { display:inline-block; min-width:100%; vertical-align:top; }
  .table-wrapper { overflow:visible !important; margin:0 !important; width:auto !important; }
  .custom-dashboard-table { border-collapse:collapse; width:auto; background:#fff; color:#000; font-size:13.5px; border:1px solid #d3d3d3; }
  .custom-dashboard-table th, .custom-dashboard-table td { border:1px solid #d3d3d3; padding:7px 10px; text-align:center; white-space:nowrap; }
  .custom-dashboard-table th { background:#D9E1F2; font-weight:700; position:sticky; top:0; z-index:4; }
  .subtotal-row { font-weight:bold; background:#F2F2F2; }
  .brand-row { background:#fff; }
  .brand-col-text, .seg-col-text { text-align:left !important; padding-left:10px; white-space:nowrap; }
  .grand-total-row { background:#D9E1F2; font-weight:bold; font-size:14px; border-top:2px solid #b0b0b0; }
  .custom-dashboard-table tbody td:first-child { position:sticky; left:0; z-index:2; background:#F2F2F2; border-right:1px solid #d3d3d3; }
  .custom-dashboard-table thead tr:first-child th:first-child { left:0; z-index:6; }
  .brand-row td:first-child { background:#fff !important; }
  .grand-total-row td:first-child { background:#D9E1F2 !important; }
</style></head>
<body>
  <div id="bar">
    <button id="zo">&minus;</button>
    <button id="zf">Fit</button>
    <button id="zi">+</button>
    <span id="zl"></span>
  </div>
  <div id="vp"><div id="content">__TABLE__</div></div>
<script>
(function(){
  const vp = document.getElementById('vp'), c = document.getElementById('content'), t = c.querySelector('table'), lbl = document.getElementById('zl');
  let z = 1, NAT = 0, userZoomed = false, MINZ = 1;
  function updateMin(){ const vw = vp.clientWidth - 2; MINZ = (NAT > vw && vw > 0) ? vw / NAT : 1; }
  function apply(nz, cx, cy){
    nz = Math.min(3, Math.max(MINZ, nz));
    const px = (vp.scrollLeft + cx) / z, py = (vp.scrollTop + cy) / z;
    z = nz; c.style.zoom = z;
    if (t) t.style.width = Math.max(NAT, (vp.clientWidth - 2) / z) + 'px';
    vp.scrollLeft = px * z - cx; vp.scrollTop = py * z - cy;
    lbl.textContent = Math.round(z * 100) + '%';
  }
  function fit(){
    const vw = vp.clientWidth; if (vw < 60) return;
    c.style.zoom = 1; z = 1; if (t) t.style.width = 'auto';
    NAT = t ? t.offsetWidth : c.offsetWidth;
    updateMin(); apply(MINZ, 0, 0); userZoomed = false;
  }
  document.getElementById('zi').onclick = () => { userZoomed = true; apply(z * 1.2, vp.clientWidth/2, vp.clientHeight/2); };
  document.getElementById('zo').onclick = () => { userZoomed = true; apply(z / 1.2, vp.clientWidth/2, vp.clientHeight/2); };
  document.getElementById('zf').onclick = fit;
  window.addEventListener('resize', () => { if (!userZoomed) fit(); });
  window.addEventListener('load', fit);
  fit();
})();
</script>
</body></html>"""

def render_zoomable_table(html_content, table_key):
    rows = html_content.count("<tr")
    height = int(min(700, max(340, 80 + rows * 28)))
    components.html(ZOOM_TABLE_TEMPLATE.replace("__TABLE__", html_content), height=height, scrolling=False)

# --- 9. TABLE GENERATORS ---
def generate_html_table(df, metric_type="Volume"):
    grouped = df.groupby([seg_col, brand_col], as_index=False, observed=False)[["Last Month", "Target", "This Month"]].sum() if not df.empty else pd.DataFrame(columns=[seg_col, brand_col, "Last Month", "Target", "This Month"])
    merged = pd.merge(master_brands, grouped, on=[seg_col, brand_col], how="left").fillna(0)

    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    if metric_type == "Volume":
        html += f'<thead><tr><th class="seg-col-text">Brand</th><th>{lm_label}</th><th>TGT</th><th>{tm_label}</th><th>BAL</th></tr></thead><tbody>'
    else:
        html += f'<thead><tr><th class="seg-col-text">Brand</th><th>{lm_label}</th><th>{tm_label}</th><th>GRW</th></tr></thead><tbody>'

    gt_last_vol, gt_target_vol, gt_this_vol = merged["Last Month"].sum(), merged["Target"].sum(), merged["This Month"].sum()
    marked_brands = ['IBDC', 'MHW', 'BLGLM', 'BLGOR', 'Monarch', 'SMG', 'SMGP', 'MHFB', 'SIW']
    gt_bal_vol = merged[merged[brand_col].isin(marked_brands)]["Target"].sum() - merged[merged[brand_col].isin(marked_brands)]["This Month"].sum()

    for segment, seg_data in merged.groupby(seg_col, sort=False, observed=False):
        seg_last, seg_target, seg_this = seg_data["Last Month"].sum(), seg_data["Target"].sum(), seg_data["This Month"].sum()
        if metric_type == "Volume":
            html += f'<tr class="subtotal-row"><td class="seg-col-text">{segment}</td><td>{seg_last:,.2f}</td><td>{seg_target:,.2f}</td><td>{seg_this:,.2f}</td><td></td></tr>'
            for _, row in seg_data.iterrows():
                b_name = row[brand_col]
                is_marked = b_name in marked_brands
                bg_style = 'background-color: #EBF5FB; font-weight: bold;' if is_marked else ''
                row_highlight = ''
                if is_marked:
                    row_highlight = 'background-color: #fde8e8; color: #9b1c1c;' if row['This Month'] < row['Target'] else 'background-color: #def7ec; color: #03543f;'
                bal_str = f"{row['Target'] - row['This Month']:,.2f}" if is_marked else ""
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td>{row["Last Month"]:,.2f}</td><td>{row["Target"]:,.2f}</td><td style="{row_highlight}">{row["This Month"]:,.2f}</td><td style="{row_highlight}">{bal_str}</td></tr>'
        else:
            seg_last_pct = (seg_last / gt_last_vol) * 100 if gt_last_vol else 0
            seg_this_pct = (seg_this / gt_this_vol) * 100 if gt_this_vol else 0
            seg_growth = seg_this_pct - seg_last_pct
            html += f'<tr class="subtotal-row"><td class="seg-col-text">{segment}</td><td>{seg_last_pct:,.2f}%</td><td>{seg_this_pct:,.2f}%</td><td>{seg_growth:,.2f}%</td></tr>'
            for _, row in seg_data.iterrows():
                b_name = row[brand_col]
                is_marked = b_name in marked_brands
                bg_style = 'background-color: #EBF5FB; font-weight: bold;' if is_marked else ''
                b_last_pct = (row["Last Month"] / seg_last) * 100 if seg_last else 0
                b_this_pct = (row["This Month"] / seg_this) * 100 if seg_this else 0
                b_growth = b_this_pct - b_last_pct
                growth_highlight = 'background-color: #def7ec; color: #03543f;' if b_growth > 0 else ('background-color: #fde8e8; color: #9b1c1c;' if b_growth < 0 else '')
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td>{b_last_pct:,.2f}%</td><td>{b_this_pct:,.2f}%</td><td style="{growth_highlight}">{b_growth:,.2f}%</td></tr>'

    if metric_type == "Volume":
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td>{gt_last_vol:,.2f}</td><td>{gt_target_vol:,.2f}</td><td>{gt_this_vol:,.2f}</td><td>{gt_bal_vol:,.2f}</td></tr>'
    else:
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td>100.00%</td><td>100.00%</td><td></td></tr>'
    html += '</tbody></table></div>'
    return html

def sort_asms(asm_list):
    valid_asms = [str(a) for a in asm_list if str(a).lower() not in ["nan", "none", ""]]
    return sorted([a for a in valid_asms if a.strip().lower() != "key accounts"]) + [a for a in valid_asms if a.strip().lower() == "key accounts"]

def get_segment_for_brand(b_name):
    return ["Semi Premium-Whisky"] if b_name == "MHW" else ["Deluxe-Whisky", "Deluxe Plus-Whisky"]

def calc_ms_brand(sub_df, b_name):
    target_segs = get_segment_for_brand(b_name)
    brand_lm = sub_df[sub_df['Brand'] == b_name]['Last Month'].sum()
    brand_mtd = sub_df[sub_df['Brand'] == b_name]['This Month'].sum()
    denom_lm = sub_df[sub_df['Segment'].isin(target_segs)]['Last Month'].sum()
    denom_mtd = sub_df[sub_df['Segment'].isin(target_segs)]['This Month'].sum()
    lm_pct = (brand_lm / denom_lm * 100) if denom_lm > 0 else 0.0
    mtd_pct = (brand_mtd / denom_mtd * 100) if denom_mtd > 0 else 0.0
    return lm_pct, mtd_pct, mtd_pct - lm_pct

def generate_hierarchy_table_1(df):
    brands_to_show = ["IBDC", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += f'<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>' + ''.join([f'<th colspan="4">{b}</th>' for b in brands_to_show]) + '</tr><tr>' + (''.join([f'<th>{lm_label}</th><th>Target</th><th>{tm_label}</th><th>MS%</th>' for _ in brands_to_show])) + '</tr></thead><tbody>'

    def get_row(sub):
        res = ""
        for b in brands_to_show:
            lm = sub[sub['Brand']==b]['Last Month'].sum()
            tgt = sub[sub['Brand']==b]['Target'].sum()
            tm = sub[sub['Brand']==b]['This Month'].sum()
            _, ms, _ = calc_ms_brand(sub, b)
            res += f'<td>{lm:,.2f}</td><td>{tgt:,.2f}</td><td>{tm:,.2f}</td><td>{ms:.2f}%</td>'
        return res

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row(df) + '</tr>'
    for zone in sorted(df['Zone'].dropna().unique()):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row(z_df) + '</tr>'
        for asm in sort_asms(z_df['ASM'].dropna().unique()):
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left:14px;"><b>{asm}</b></td>' + get_row(a_df) + '</tr>'
            for tse in sorted(a_df['TSE'].dropna().unique()):
                if str(tse).lower() in ["nan", "none", ""]: continue
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left:28px;">{tse}</td>' + get_row(a_df[a_df['TSE'] == tse]) + '</tr>'
    return html + '</tbody></table></div>'

def generate_hierarchy_table_2(df):
    brands_to_show = ["IBDC", "MCD Lux", "IQ", "N1WSUP", "OCBL", "RSW", "SRB7", "RGW", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += f'<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>' + ''.join([f'<th colspan="3">{b}</th>' for b in brands_to_show]) + '</tr><tr>' + (''.join([f'<th>{lm_label}</th><th>{tm_label}</th><th>diff</th>' for _ in brands_to_show])) + '</tr></thead><tbody>'

    def get_row(sub):
        res = ""
        for b in brands_to_show:
            lm, mtd, diff = calc_ms_brand(sub, b)
            res += f'<td>{lm:.2f}%</td><td>{mtd:.2f}%</td><td style="color:{"#9b1c1c" if diff<0 else "#03543f"};">{diff:+.2f}%</td>'
        return res

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row(df) + '</tr>'
    for zone in sorted(df['Zone'].dropna().unique()):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row(z_df) + '</tr>'
        for asm in sort_asms(z_df['ASM'].dropna().unique()):
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left:14px;"><b>{asm}</b></td>' + get_row(a_df) + '</tr>'
            for tse in sorted(a_df['TSE'].dropna().unique()):
                if str(tse).lower() in ["nan", "none", ""]: continue
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left:28px;">{tse}</td>' + get_row(a_df[a_df['TSE'] == tse]) + '</tr>'
    return html + '</tbody></table></div>'

def generate_hierarchy_table_3(df):
    brands_to_show = ["IBDC", "MCD Lux", "IQ", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += f'<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>' + ''.join([f'<th colspan="3">{b}</th>' for b in brands_to_show]) + '</tr><tr>' + (''.join([f'<th>{lm_label}</th><th>{tm_label}</th><th>diff</th>' for _ in brands_to_show])) + '</tr></thead><tbody>'

    def get_row(sub):
        res = ""
        for b in brands_to_show:
            lm = sub[(sub['Brand'] == b) & (sub['Last Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub.columns else 0
            mtd = sub[(sub['Brand'] == b) & (sub['This Month'] > 0)]['LIC No'].nunique() if 'LIC No' in sub.columns else 0
            diff = mtd - lm
            res += f'<td>{lm:,}</td><td>{mtd:,}</td><td style="color:{"#9b1c1c" if diff<0 else "#03543f"};">{diff:+d}</td>'
        return res

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row(df) + '</tr>'
    for zone in sorted(df['Zone'].dropna().unique()):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row(z_df) + '</tr>'
        for asm in sort_asms(z_df['ASM'].dropna().unique()):
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left:14px;"><b>{asm}</b></td>' + get_row(a_df) + '</tr>'
            for tse in sorted(a_df['TSE'].dropna().unique()):
                if str(tse).lower() in ["nan", "none", ""]: continue
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left:28px;">{tse}</td>' + get_row(a_df[a_df['TSE'] == tse]) + '</tr>'
    return html + '</tbody></table></div>'

# --- 10. MAIN TABS INTERFACE ---
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Dashboard", "💬 Ask Assistant"])

with main_tab1:
    render_zoomable_table(generate_html_table(filtered_df, metric_type="Volume"), "vol_tab")

with main_tab2:
    render_zoomable_table(generate_html_table(filtered_df, metric_type="Ms%"), "ms_tab")

with main_tab3:
    sub_t1, sub_t2, sub_t3 = st.tabs(["Target vs Ach", "MS% Details", "WOD Details"])
    with sub_t1:
        render_zoomable_table(generate_hierarchy_table_1(filtered_df), "h1_tab")
    with sub_t2:
        render_zoomable_table(generate_hierarchy_table_2(filtered_df), "h2_tab")
    with sub_t3:
        render_zoomable_table(generate_hierarchy_table_3(filtered_df), "h3_tab")

with main_tab4:
    st.markdown("### 🤖 Smart Sales & Outlet Query Assistant")
    st.markdown("Perform advanced unbilled outlet queries, substitution gap analysis, run-rates, and multi-month trends.")
    
    col_q1, col_q2, col_q3 = st.columns([1.2, 1, 1.8])
    with col_q1:
        basis_period = st.selectbox("Basis on Period:", [f"This Month ({tm_label})", f"Last Month ({lm_label})", f"Last 2 Months ({lm_label} + {m2_label})", f"Last 3 Months ({lm_label} + {m2_label} + {m3_label})"])
    with col_q2:
        target_brand_choice = st.selectbox("Target Brand Focus:", ["IBDC", "MHW", "MHFB", "BLGLM+BLGOR", "SMG+SMGP", "SIW", "Monarch"])
    with col_q3:
        query_type = st.selectbox("Choose Query / Analysis:", ["-- Select a Query --", "TIL Non Billed Outlets", "Deluxe Industry >= 30 CS but IBDC Not Billed", "Semi Premium Whisky Industry >= 50 CS but MHW Not Billed", "Brand-wise L3M Daily Run vs Current Month Daily Run"])

    if query_type != "-- Select a Query --":
        base_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates() if "LIC No" in filtered_df.columns else pd.DataFrame()
        if "TIL Non Billed Outlets" in query_type:
            st.markdown(f"#### Results for {query_type}")
            st.info("Query execution ready. Use the download button below to export full records.")
