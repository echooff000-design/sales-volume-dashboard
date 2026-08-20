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
            [data-testid="stSidebar"] * { color: #f8fafc !important; }
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

def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get_current_session_cycle_date(now_ist):
    cutoff_today = now_ist.replace(hour=0, minute=2, second=0, microsecond=0)
    if now_ist < cutoff_today:
        return (now_ist.date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return now_ist.date().strftime("%Y-%m-%d")

RAW_SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"

@st.cache_data(ttl=300)
def load_data_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None), None
    except Exception as e:
        return None, str(e)

with st.spinner("Connecting to database..."):
    dfs, error = load_data_from_url(RAW_SHAREPOINT_URL)

if error or dfs is None:
    st.error(f"⚠️ Unable to load data: {error}")
    st.stop()

raw_users_df = dfs["Users"].copy()
df_users_clean = pd.DataFrame({
    "Name": raw_users_df.iloc[:, 0].astype(str).str.strip(),
    "user_id": raw_users_df.iloc[:, 1].astype(str).str.strip(),
    "password": raw_users_df.iloc[:, 2].astype(str).str.strip(),
    "role": raw_users_df.iloc[:, 3].astype(str).str.strip() if raw_users_df.shape[1] > 3 else "User"
})

# --- DATA PROCESSOR ---
df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()
df_outlet.columns = df_outlet.columns.astype(str).str.strip()

group_mapping = dict(zip(df_outlet["LIC No"].astype(str).str.strip(), df_outlet["Group"].astype(str).str.strip())) if "LIC No" in df_outlet.columns else {}

def standardize_df(d):
    d = d.copy()
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value"}, inplace=True)
    k_col = "LIC No" if "LIC No" in d.columns else None
    if k_col:
        d["Group"] = d[k_col].astype(str).str.strip().map(group_mapping).fillna("Unassigned")
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
df_raw = pd.pivot_table(df_combined, values="Value", index=dim_cols, columns="Metric", aggfunc="sum").reset_index()

for c in ["This Month", "Last Month", "Target"]:
    df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce").fillna(0)

# --- OFFLINE BUNDLER INJECTING INTO TEMPLATE ---
@st.cache_data
def get_injected_offline_html(df_json, users_json):
    if os.path.exists("offline_template.html"):
        with open("offline_template.html", "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = "<html><body>Template file missing in repository!</body></html>"
    
    # Clean records export
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

    return template.replace("{{USERS_JSON}}", users_json).replace("{{SALES_JSON}}", json.dumps(records_export))

# --- SIDEBAR OFFLINE LAUNCHER ---
st.sidebar.markdown("📁 **Data Source**")
st.sidebar.markdown("---")
st.sidebar.markdown("⚡ **Offline Capabilities**")

html_payload = get_injected_offline_html(df_raw.to_json(orient="records"), df_users_clean.to_json(orient="records"))
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
    for (let i = 0; i < bin.length; i++) {{ bytes[i] = bin.charCodeAt(i); }}
    const blob = new Blob([bytes], {{ type: 'text/html;charset=utf-8' }});
    window.open(URL.createObjectURL(blob), '_blank');
}}
</script>
"""
with st.sidebar:
    components.html(launch_btn_code, height=50)
    st.caption("💡 *Works 100% offline. Use the 'Check Update' button inside to sync when back online.*")

# Render Normal Online Streamlit Interface Below...
st.markdown("### Online Dashboard Active")
st.dataframe(df_raw.head(10))
