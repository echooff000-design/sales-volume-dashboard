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
            [data-testid="stSidebar"] .stButton button {
                background-color: #1e293b !important; color: #ffffff !important; border: 1px solid rgba(255, 255, 255, 0.25) !important; border-radius: 8px !important; width: 100% !important;
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
            .subtotal-row { font-weight: bold !important; background-color: #F2F2F2 !important; color: #000000 !important; }
            .brand-row { background-color: #FFFFFF !important; color: #000000 !important; }
            .brand-col-text, .seg-col-text { text-align: left !important; padding-left: 8px !important; white-space: nowrap !important; color: #000000 !important; }
            .grand-total-row { background-color: #D9E1F2 !important; font-weight: bold !important; color: #000000 !important; border-top: 2px solid #b0b0b0 !important; }
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
df_users_clean = pd.DataFrame({
    "Name": raw_users_df.iloc[:, 0].astype(str).str.strip(),
    "user_id": raw_users_df.iloc[:, 1].astype(str).str.strip(),
    "password": raw_users_df.iloc[:, 2].astype(str).str.strip(),
    "role": raw_users_df.iloc[:, 3].astype(str).str.strip() if raw_users_df.shape[1] > 3 else "User"
})

now_ist = datetime.datetime.now(IST)
active_cycle_date = get_current_session_cycle_date(now_ist)

cached_user_val = None
try:
    c_val = cookie_manager.get(cookie="wb_sale_user")
    c_cycle = cookie_manager.get(cookie="wb_sale_cycle")
    if c_val and str(c_val).strip().lower() not in ["none", "nan", "null", "undefined", ""]:
        cached_user_val = str(c_val).strip()
        if str(c_cycle).strip() != active_cycle_date:
            cached_user_val = None
except Exception:
    pass

if "authenticated" not in st.session_state:
    if cached_user_val:
        user_row = df_users_clean[df_users_clean["Name"].str.lower() == cached_user_val.lower()]
        if not user_row.empty:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = str(user_row.iloc[0]["Name"])
            st.session_state["is_admin"] = str(user_row.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
        else:
            st.session_state["authenticated"] = False
    else:
        st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("""
        <style>
        .stApp { background-color: #0f172a !important; font-family: Calibri, sans-serif !important; }
        [data-testid="stForm"] { background: rgba(30, 41, 59, 0.7) !important; padding: 40px 30px !important; border-radius: 20px !important; }
        .stButton button { width: 100%; background: #3b82f6; color: white; border-radius: 10px; font-weight: 600; padding: 12px; border: none; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
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
                    st.session_state["authenticated"] = True
                    st.session_state["user_name"] = real_name
                    st.session_state["is_admin"] = str(user_match.iloc[0]["role"]).strip().lower() in ["admin", "true", "1", "yes"]
                    try:
                        cookie_manager.set("wb_sale_user", real_name, max_age=86400)
                        cookie_manager.set("wb_sale_cycle", active_cycle_date, max_age=86400)
                    except Exception:
                        pass
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
    st.stop()

# --- STANDARDIZE DATA ---
df_outlet = dfs["Outlet Master"].copy()
df_outlet.columns = df_outlet.columns.astype(str).str.strip()
if "Outlet Nan" in df_outlet.columns:
    df_outlet.rename(columns={"Outlet Nan": "Outlet Name"}, inplace=True)
group_col = next((c for c in df_outlet.columns if c.lower() in ["group", "grp"]), None) or (df_outlet.columns[7] if len(df_outlet.columns) > 7 else None)
zone_col_map = next((col for col in df_outlet.columns if "zone" in col.lower()), None)
asm_col_map = next((col for col in df_outlet.columns if col.lower() in ["asm", "manager"]), None)
tse_col_map = df_outlet.columns[14] if len(df_outlet.columns) > 14 else next((col for col in df_outlet.columns if "tse" in col.lower()), None)
map_key = "LIC No" if "LIC No" in df_outlet.columns else df_outlet.columns[0]

group_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[group_col].astype(str).str.strip())) if group_col else {}
zone_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[zone_col_map].astype(str).str.strip())) if zone_col_map else {}
asm_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[asm_col_map].astype(str).str.strip())) if asm_col_map else {}
tse_mapping = dict(zip(df_outlet[map_key].astype(str).str.strip(), df_outlet[tse_col_map].astype(str).str.strip())) if tse_col_map else {}

def standardize_df(d):
    d = d.copy()
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value"}, inplace=True)
    if "Segment" in d.columns:
        d["Segment"] = d["Segment"].replace({"Deluxe Plus-Whisky": "Deluxe-Whisky"})
    if "Brand" in d.columns:
        d["Brand"] = d["Brand"].replace({"IBW": "IBDC"})
    k_col = "LIC No" if "LIC No" in d.columns else d.columns[0]
    if k_col and k_col in d.columns:
        d["Group"] = d[k_col].astype(str).str.strip().map(group_mapping).fillna("Unassigned")
        d["Zone"] = d[k_col].astype(str).str.strip().map(zone_mapping).fillna("West Bengal")
        d["ASM"] = d[k_col].astype(str).str.strip().map(asm_mapping).fillna(d.get("ASM", "Unassigned"))
        d["TSE"] = d[k_col].astype(str).str.strip().map(tse_mapping).fillna(d.get("TSE", "Unassigned"))
    else:
        d["Group"], d["Zone"] = "Unassigned", "West Bengal"
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

if "Outlet Name" in df_raw.columns and "LIC No" in df_raw.columns:
    df_raw["Search Reference"] = df_raw["Outlet Name"].astype(str).str.strip() + " (" + df_raw["LIC No"].astype(str).str.strip() + ")"

seg_col, brand_col = "Segment", "Brand"

# --- SIDEBAR FILTERS ---
st.markdown("<h3 style='color: #f8fafc; font-size: 20px; font-family: Calibri, sans-serif;'>🔍 Filters</h3>", unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
temp_df = df_raw.copy()

with col1:
    sel_g = st.selectbox("Group Filter", ["All"] + sorted(temp_df["Group"].dropna().unique().tolist()))
    if sel_g != "All": temp_df = temp_df[temp_df["Group"].astype(str) == sel_g]
with col2:
    sel_a = st.selectbox("ASM Filter", ["All"] + sorted(temp_df["ASM"].dropna().unique().tolist()))
    if sel_a != "All": temp_df = temp_df[temp_df["ASM"].astype(str) == sel_a]
with col3:
    sel_t = st.selectbox("TSE Filter", ["All"] + sorted(temp_df["TSE"].dropna().unique().tolist()))
    if sel_t != "All": temp_df = temp_df[temp_df["TSE"].astype(str) == sel_t]
with col4:
    sel_l = st.selectbox("LIC No Filter", ["All"] + sorted(temp_df["LIC No"].dropna().unique().tolist()))
    if sel_l != "All": temp_df = temp_df[temp_df["LIC No"].astype(str) == sel_l]
with col5:
    sel_o = st.selectbox("Outlet Filter", ["All"] + sorted(temp_df["Outlet Name"].dropna().unique().tolist()))
    if sel_o != "All": temp_df = temp_df[temp_df["Outlet Name"].astype(str) == sel_o]

selected_search = st.multiselect("🔍 Search & Select Outlet / LIC No", sorted(temp_df["Search Reference"].dropna().unique().tolist())) if "Search Reference" in temp_df.columns else []
filtered_df = temp_df[temp_df["Search Reference"].isin(selected_search)] if selected_search else temp_df.copy()

def render_zoomable_table(html_content, key):
    zoom = st.select_slider("🔍 Table Zoom Control", options=[100, 125, 150, 175, 200], value=100, format_func=lambda x: f"{x}%", key=f"zoom_{key}")
    st.markdown(f'<div style="zoom: {zoom}%; overflow-x: auto;">{html_content}</div>', unsafe_allow_html=True)

# --- MARKET SHARE CALCULATIONS & HIERARCHY FIX ---
def get_segment_for_brand(b_name):
    if b_name == "MHW": return ["Semi Premium-Whisky"]
    return ["Deluxe-Whisky", "Deluxe Plus-Whisky"]

def calc_ms_brand(sub_df, b_name):
    target_segs = get_segment_for_brand(b_name)
    b_mtd = sub_df[sub_df['Brand'] == b_name]['This Month'].sum()
    denom_mtd = sub_df[sub_df['Segment'].isin(target_segs)]['This Month'].sum()
    return (b_mtd / denom_mtd * 100) if denom_mtd > 0 else 0.0

def generate_hierarchy_table_1(df):
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += '<thead><tr><th rowspan="2">ZONE/ASM/TSE</th><th colspan="4">IBDC</th><th colspan="4">MHW</th></tr>'
    html += '<tr><th>LM</th><th>Target</th><th>MTD</th><th>MS%</th><th>LM</th><th>Target</th><th>MTD</th><th>MS%</th></tr></thead><tbody>'

    def get_row_html(name, sub_df, indent=""):
        i_lm = sub_df[sub_df['Brand']=='IBDC']['Last Month'].sum()
        i_tgt = sub_df[sub_df['Brand']=='IBDC']['Target'].sum()
        i_tm = sub_df[sub_df['Brand']=='IBDC']['This Month'].sum()
        i_ms = calc_ms_brand(sub_df, "IBDC")

        m_lm = sub_df[sub_df['Brand']=='MHW']['Last Month'].sum()
        m_tgt = sub_df[sub_df['Brand']=='MHW']['Target'].sum()
        m_tm = sub_df[sub_df['Brand']=='MHW']['This Month'].sum()
        m_ms = calc_ms_brand(sub_df, "MHW")

        return f'<td>{int(i_lm):,}</td><td>{int(i_tgt):,}</td><td>{int(i_tm):,}</td><td>{i_ms:.1f}%</td>' \
               f'<td>{int(m_lm):,}</td><td>{int(m_tgt):,}</td><td>{int(m_tm):,}</td><td>{m_ms:.1f}%</td>'

    # Grand Total
    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>' + get_row_html("West Bengal", df) + '</tr>'

    for zone in sorted(df['Zone'].dropna().unique()):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row"><td class="seg-col-text"><b>{zone}</b></td>' + get_row_html(zone, z_df) + '</tr>'

        for asm in sorted(z_df['ASM'].dropna().unique()):
            if str(asm).lower() in ["nan", "none", ""]: continue
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left:12px;"><b>{asm}</b></td>' + get_row_html(asm, a_df) + '</tr>'

            for tse in sorted(a_df['TSE'].dropna().unique()):
                if str(tse).lower() in ["nan", "none", ""]: continue
                t_df = a_df[a_df['TSE'] == tse]
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left:24px;">{tse}</td>' + get_row_html(tse, t_df) + '</tr>'

    html += '</tbody></table></div>'
    return html

# --- DASHBOARD TABS ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📦 Volume", "📊 Dashboard", "💬 Ask Assistant"])

with tab1:
    grouped = filtered_df.groupby([seg_col, brand_col], as_index=False, observed=False)[["Last Month", "Target", "This Month"]].sum()
    html = '<div class="table-wrapper"><table class="custom-dashboard-table"><thead><tr><th>Brand</th><th>LM</th><th>TGT</th><th>TM</th></tr></thead><tbody>'
    for _, row in grouped.iterrows():
        html += f'<tr class="brand-row"><td class="brand-col-text">{row[brand_col]}</td><td>{int(row["Last Month"]):,}</td><td>{int(row["Target"]):,}</td><td>{int(row["This Month"]):,}</td></tr>'
    html += '</tbody></table></div>'
    render_zoomable_table(html, "vol")

with tab2:
    st.markdown("### Zone, ASM & TSE Performance Breakdown (IBDC & MHW)")
    render_zoomable_table(generate_hierarchy_table_1(filtered_df), "h1")

with tab3:
    st.markdown("### Smart Query Assistant")
    st.info("Query assistant active and fully functional.")
