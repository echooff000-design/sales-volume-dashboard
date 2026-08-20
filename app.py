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

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            [data-testid="stSidebar"] {
                background-color: #0f172a !important;
                border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
                font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
            }
            [data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]):not(i):not(svg):not(span[class*="material"]):not(span[class*="icon"]) {
                color: #f8fafc !important;
                font-family: Calibri, 'Segoe UI', Arial, sans-serif !important;
            }
            [data-testid="stSidebar"] a { color: #60a5fa !important; }
            [data-testid="stSidebar"] .stButton button, 
            [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
                background-color: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.25) !important;
                border-radius: 8px !important;
                width: 100% !important;
            }
            .table-wrapper th:first-child, .table-wrapper td:first-child {
                position: sticky !important; left: 0 !important; z-index: 2 !important; background-color: #F2F2F2 !important; border-right: 1px solid #d3d3d3 !important;
            }
            .table-wrapper th:first-child { background-color: #D9E1F2 !important; z-index: 3 !important; }
            .table-wrapper { width: 100%; overflow-x: auto; margin-bottom: 20px; display: block; }
            .custom-dashboard-table {
                width: 100%; border-collapse: collapse !important; font-family: Calibri, sans-serif !important; background-color: #ffffff !important; color: #000000 !important; font-size: 13.5px !important; border: 1px solid #d3d3d3 !important;
            }
            .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #d3d3d3 !important; padding: 6px 8px !important; text-align: center; white-space: nowrap !important; }
            .custom-dashboard-table th { background-color: #D9E1F2 !important; font-weight: 700 !important; }
            .subtotal-row { font-weight: bold !important; background-color: #F2F2F2 !important; }
            .brand-row { background-color: #FFFFFF !important; }
            .brand-col-text, .seg-col-text { text-align: left !important; padding-left: 8px !important; white-space: nowrap !important; }
            .grand-total-row { background-color: #D9E1F2 !important; font-weight: bold !important; border-top: 2px solid #b0b0b0 !important; }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

SHEET_ID = "1iEBhkOnErBiWiXgl74dYV3fYxLJvCKnff8ptkxHZ8eo"

def get_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds).open_by_key(SHEET_ID).sheet1

cookie_manager = stx.CookieManager()
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get_current_session_cycle_date(now_ist):
    cutoff_today = now_ist.replace(hour=0, minute=2, second=0, microsecond=0)
    if now_ist < cutoff_today:
        return (now_ist.date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return now_ist.date().strftime("%Y-%m-%d")

def get_seconds_until_next_1202_am(now_ist):
    target_today = now_ist.replace(hour=0, minute=2, second=0, microsecond=0)
    if now_ist < target_today:
        next_cutoff = target_today
    else:
        next_cutoff = target_today + datetime.timedelta(days=1)
    return max(int((next_cutoff - now_ist).total_seconds()), 60)

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
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

raw_users_df = dfs["Users"].copy()

def extract_f2_date(df_u):
    raw_val = None
    date_col = next((c for c in df_u.columns if 'date' in str(c).strip().lower()), None)
    if date_col is not None and len(df_u) > 0:
        raw_val = df_u[date_col].iloc[0]
    if (pd.isna(raw_val) or str(raw_val).strip() == "") and df_u.shape[1] >= 6 and len(df_u) > 0:
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
        parsed_dt = pd.to_datetime(str(raw_val).strip(), errors='coerce', dayfirst=True)
        if pd.notna(parsed_dt):
            return int(parsed_dt.day), parsed_dt.strftime("%d %b %Y")
    today_dt = datetime.datetime.now(IST)
    return today_dt.day, today_dt.strftime("%d %b %Y")

days_elapsed, f2_display_date = extract_f2_date(raw_users_df)

df_users = raw_users_df.copy()
df_users_clean = pd.DataFrame({
    "Name": df_users.iloc[:, 0].astype(str).str.strip(),
    "user_id": df_users.iloc[:, 1].astype(str).str.strip(),
    "password": df_users.iloc[:, 2].astype(str).str.strip(),
    "role": df_users.iloc[:, 3].astype(str).str.strip() if df_users.shape[1] > 3 else "User"
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
    if cached_user_val:
        user_row = df_users_clean[df_users_clean["Name"].str.lower() == cached_user_val.lower()]
        if not user_row.empty and str(user_row.iloc[0]["Name"]).lower() not in ["nan", "none", ""]:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = str(user_row.iloc[0]["Name"])
            st.session_state["session_cycle"] = active_cycle_date
            st.session_state["is_admin"] = str(user_row.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
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

if st.session_state.get("authenticated", False) and st.session_state.get("session_cycle") != active_cycle_date:
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
        [data-testid="stForm"] { background: rgba(30, 41, 59, 0.7) !important; backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 40px 30px !important; border-radius: 20px !important; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important; }
        .stTextInput label { color: #94a3b8 !important; font-weight: 500; font-size: 13px; }
        .stTextInput input { background-color: rgba(15, 23, 42, 0.6) !important; color: #f8fafc !important; border-radius: 10px !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 12px 14px !important; }
        .stButton button { width: 100%; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; border-radius: 10px; font-weight: 600; padding: 12px; border: none; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("<h2 style='color: #f8fafc; text-align: center;'>Welcome Back</h2>", unsafe_allow_html=True)
            input_user = st.text_input("User ID", placeholder="Enter your User ID")
            input_pass = st.text_input("Password", type="password", placeholder="Enter your password")
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
                    seconds_to_expiry = get_seconds_until_next_1202_am(cur_now)
                    
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

# --- FETCH & STANDARDIZE DATA ---
df_this = standardize_df = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()
df_outlet.columns = df_outlet.columns.astype(str).str.strip()
if "Outlet Nan" in df_outlet.columns:
    df_outlet.rename(columns={"Outlet Nan": "Outlet Name"}, inplace=True)

group_mapping = dict(zip(df_outlet["LIC No"].astype(str).str.strip(), df_outlet[df_outlet.columns[7]].astype(str).str.strip())) if "LIC No" in df_outlet.columns and len(df_outlet.columns) > 7 else {}

def standardize_df(d):
    d = d.copy()
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value"}, inplace=True)
    k_col = "LIC No" if "LIC No" in d.columns else None
    if k_col:
        d["Group"] = d[k_col].astype(str).str.strip().map(group_mapping).fillna("Unassigned")
        d["Zone"] = "West Bengal"
    return d

df_this = standardize_df(dfs["This Month"])
df_last = standardize_df(dfs["Last Month"])
df_target = standardize_df(dfs["Target Data"])
df_this["Metric"], df_last["Metric"], df_target["Metric"] = "This Month", "Last Month", "Target"

df_combined = pd.concat([df_this, df_last, df_target], ignore_index=True)
dim_cols = [c for c in df_combined.columns if c not in ["Metric", "Value"]]
df_raw = pd.pivot_table(df_combined, values="Value", index=dim_cols, columns="Metric", aggfunc="sum").reset_index()

for c in ["This Month", "Last Month", "Target"]:
    df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce").fillna(0)

# --- INLINE OFFLINE TEMPLATE (BYPASSES LOGIN AUTOMATICALLY) ---
def get_inline_offline_html(df_json, user_name, user_role):
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>WB Sale Data (Offline PWA)</title>
    <style>
        body {{ background-color: #0f172a; color: #f8fafc; font-family: Calibri, sans-serif; margin: 0; padding: 15px; }}
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 15px; }}
        .card {{ background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 14px; margin-bottom: 15px; }}
        .grid-filters {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }}
        label {{ font-size: 13px; font-weight: 600; color: #f8fafc; display: block; margin-bottom: 4px; }}
        select {{ width: 100%; background-color: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 7px 10px; border-radius: 6px; }}
        .btn {{ background: #10b981; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
        .tab-bar {{ display: flex; gap: 12px; border-bottom: 2px solid #334155; margin-bottom: 15px; }}
        .tab-btn {{ background: none; border: none; color: #ef4444; font-size: 14px; font-weight: 600; padding: 10px 14px; cursor: pointer; }}
        .tab-btn.active {{ font-weight: 700; border-bottom: 3px solid #ef4444; }}
        .table-wrapper {{ width: 100%; overflow-x: auto; margin-bottom: 20px; background: #ffffff; border: 1px solid #d3d3d3; }}
        .custom-table {{ width: 100%; border-collapse: collapse; font-family: Calibri, sans-serif; background-color: #ffffff; color: #000000; font-size: 13.5px; }}
        .custom-table th, .custom-table td {{ border: 1px solid #d3d3d3; padding: 6px 8px; text-align: center; white-space: nowrap; }}
        .custom-table th {{ background-color: #D9E1F2; font-weight: 700; }}
        .subtotal-row {{ font-weight: bold; background-color: #F2F2F2; text-align: left; }}
        .grand-total-row {{ background-color: #D9E1F2; font-weight: bold; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header-bar">
        <div>
            <h3 style="margin: 0;">WB Sale Data</h3>
            <span style="font-size: 12px; font-weight: bold; color: #10b981;">● Logged in as {user_name} ({user_role})</span>
        </div>
        <button class="btn" onclick="location.reload()">🔄 Refresh Data</button>
    </div>
    <div class="card">
        <h4>🔍 Filters</h4>
        <div class="grid-filters">
            <div><label>Group</label><select id="selGroup" onchange="updateDashboard()"></select></div>
            <div><label>ASM</label><select id="selASM" onchange="updateDashboard()"></select></div>
            <div><label>TSE</label><select id="selTSE" onchange="updateDashboard()"></select></div>
            <div><label>LIC No</label><select id="selLIC" onchange="updateDashboard()"></select></div>
            <div><label>Outlet</label><select id="selOutlet" onchange="updateDashboard()"></select></div>
        </div>
    </div>
    <div class="table-wrapper">
        <table class="custom-table">
            <thead><tr><th>Brand</th><th>LM</th><th>TGT</th><th>TM</th></tr></thead>
            <tbody id="bodyVol"></tbody>
        </table>
    </div>
    <script>
        const appSales = {json.dumps(records_export)};
        window.onload = function() {{
            const groups = [...new Set(appSales.map(d => d.group))].sort();
            document.getElementById('selGroup').innerHTML = '<option value="All">All</option>' + groups.map(g => `<option value="${{g}}">${{g}}</option>`).join('');
            updateDashboard();
        }};
        function updateDashboard() {{
            const grp = document.getElementById('selGroup').value;
            let filtered = appSales.filter(d => grp === 'All' || d.group === grp);
            let lm = filtered.reduce((a,c)=>a+c.lm,0);
            let tgt = filtered.reduce((a,c)=>a+c.tgt,0);
            let tm = filtered.reduce((a,c)=>a+c.tm,0);
            document.getElementById('bodyVol').innerHTML = `<tr class="grand-total-row"><td>Grand Total</td><td>${{Math.round(lm)}}</td><td>${{Math.round(tgt)}}</td><td>${{Math.round(tm)}}</td></tr>`;
        }}
    </script>
</body>
</html>"""

# --- SIDEBAR OFFLINE LAUNCHER ---
st.sidebar.markdown("📁 **Data Source**")
st.sidebar.markdown("---")
st.sidebar.markdown("⚡ **Offline Capabilities**")

active_name = st.session_state.get("user_name", "User")
active_role = "Admin" if st.session_state.get("is_admin", False) else "User"

html_payload = get_inline_offline_html(df_raw.to_json(orient="records"), active_name, active_role)
b64_html = base64.b64encode(html_payload.encode("utf-8")).decode("utf-8")

launch_btn_code = f"""
<div style="width: 100%;">
    <button onclick="window.open('data:text/html;base64,{b64_html}', '_blank')" style="
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
"""
with st.sidebar:
    components.html(launch_btn_code, height=50)
    st.caption("💡 *Bypasses login and opens instantly with your user session.*")

st.markdown("### Online Dashboard Active")
st.dataframe(df_raw.head(10))
