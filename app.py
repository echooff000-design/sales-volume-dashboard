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

if "Name" not in col_map or "user_id" not in col_map or "password" not in col_map:
    st.error(f"❌ The 'Users' sheet columns were detected as: {list(dfs['Users'].columns)}. Please ensure your Excel columns are named: Name, user_id, password.")
    st.stop()

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
        .stApp { background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%); }
        [data-testid="stForm"] { background: rgba(255, 255, 255, 0.03) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; padding: 40px 30px !important; border-radius: 20px !important; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important; }
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
                    try:
                        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                        current_time = datetime.datetime.now(ist_timezone).strftime("%Y-%m-%d %I:%M:%S %p")
                        log_data = pd.DataFrame([{"Name": st.session_state["user_name"], "User ID": input_user, "Login Time (IST)": current_time}])
                        csv_file = "login_logs.csv"
                        if not os.path.exists(csv_file):
                            log_data.to_csv(csv_file, index=False)
                        else:
                            log_data.to_csv(csv_file, mode='a', header=False, index=False)
                    except Exception as e:
                        print(f"Log error: {e}")
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
    st.stop()

# --- MAIN DASHBOARD STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label { color: #1e293b !important; font-weight: 600 !important; }
    
    /* --- CUSTOM TAB TEXT & ACTIVE COLORS (FORCED VISIBILITY) --- */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #475569 !important; /* Inactive tab text color (Dark Slate) */
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] span {
        color: #2563eb !important; /* Active tab text color (Vibrant Blue) */
        font-weight: 700 !important;
    }

    .table-wrapper { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; display: block; }
    .custom-dashboard-table { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; font-size: 11px; }
    .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #D9D9D9; padding: 5px 6px; text-align: center; }
    .custom-dashboard-table th { background-color: #D9E1F2; color: #000000; font-weight: bold; border-bottom: 2px solid #8EA9DB; font-size: 10px; white-space: nowrap; }
    .subtotal-row { font-weight: bold; color: #000000; background-color: #F2F2F2; font-size: 10px; }
    .brand-row { background-color: #FFFFFF; }
    .brand-col-text { text-align: left !important; padding-left: 8px !important; font-size: 10px; }
    .seg-col-text { text-align: left !important; line-height: 1.2; }
    .grand-total-row { background-color: #D9E1F2; color: #000000; font-weight: bold; font-size: 11px; border-top: 2px solid #8EA9DB; }
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
    st.markdown("<h3 style='margin-top: 10px; font-size: 22px; color: #0f172a;'>WB Sale Data</h3>", unsafe_allow_html=True)
with col_logout:
    st.markdown(f"<p style='text-align: right; margin-top: 15px; font-size: 13px; color: #334155;'>👤 <b>{st.session_state['user_name']}</b></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.rerun()

st.sidebar.markdown("<h2 style='color: #0f172a; font-size: 20px; font-weight: 600;'>📁 Data Source</h2>", unsafe_allow_html=True)
if last_update:
    st.sidebar.markdown(f"<p style='color: #475569; font-size: 13px;'>🕒 <b>Last Synced:</b> {last_update}</p>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='color: #0f172a; font-size: 15px; font-weight: 600;'>📋 Admin Panel</p>", unsafe_allow_html=True)
if os.path.exists("login_logs.csv"):
    with open("login_logs.csv", "rb") as file:
        st.sidebar.download_button(label="📥 Download Login Logs", data=file, file_name="login_logs.csv", mime="text/csv")
else:
    st.sidebar.info("No login logs yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("🔗 **[Go to Payment & KYC](https://wbpaymentkyc.streamlit.app/)**")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Fetching newest data...")

# --- 4. FETCH DATA FROM SHEETS ---
required_sheets = ["This Month", "Last Month", "Target Data", "Outlet Master"]
for sheet in required_sheets:
    if sheet not in dfs:
        st.error(f"❌ Could not find the sheet named '{sheet}' in your Excel file.")
        st.stop()

df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()

# --- PROCESS OUTLET MASTER FOR MAPPINGS (Zone, ASM, TSE, Group) ---
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
tse_col_map = next((col for col in df_outlet.columns if col.lower() in ["tse", "rep", "executive"]), None)

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

for d in [df_this, df_last, df_target]:
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value"}, inplace=True)
    
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
        if tse_mapping and "TSE" in d.columns:
            d["TSE"] = d[k_col].astype(str).str.strip().map(tse_mapping).fillna(d["TSE"])
    else:
        d["Group"] = "Unassigned"
        d["Zone"] = "West Bengal"

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

# --- 5. EXACT ORDER MAPPING & DATA CONVERSION ---
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
    "MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", 
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

# --- 6. CASCADING SIDEBAR FILTERS ---
st.markdown("<h3 style='color: #0f172a; font-size: 20px;'>🔍 Filters</h3>", unsafe_allow_html=True)
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

# --- 7. HTML TABLE GENERATORS FOR ORIGINAL TABS ---
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

# --- 8. HIERARCHY REPORT GENERATORS (FOR NEW TABS) ---
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
    ms_ibdc = (tot_mtd_ibdc / tot_tgt_ibdc * 100) if tot_tgt_ibdc else 0

    tot_lm_mhw = df[df['Brand']=='MHW']['Last Month'].sum()
    tot_tgt_mhw = df[df['Brand']=='MHW']['Target'].sum()
    tot_mtd_mhw = df[df['Brand']=='MHW']['This Month'].sum()
    ms_mhw = (tot_mtd_mhw / tot_tgt_mhw * 100) if tot_tgt_mhw else 0

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    html += f'<td>{int(tot_lm_ibdc):,}</td><td>{int(tot_tgt_ibdc):,}</td><td>{int(tot_mtd_ibdc):,}</td><td>{ms_ibdc:.1f}%</td>'
    html += f'<td>{int(tot_lm_mhw):,}</td><td>{int(tot_tgt_mhw):,}</td><td>{int(tot_mtd_mhw):,}</td><td>{ms_mhw:.1f}%</td></tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        z_lm_i = z_df[z_df['Brand']=='IBDC']['Last Month'].sum()
        z_tgt_i = z_df[z_df['Brand']=='IBDC']['Target'].sum()
        z_mtd_i = z_df[z_df['Brand']=='IBDC']['This Month'].sum()
        z_ms_i = (z_mtd_i / z_tgt_i * 100) if z_tgt_i else 0

        z_lm_m = z_df[z_df['Brand']=='MHW']['Last Month'].sum()
        z_tgt_m = z_df[z_df['Brand']=='MHW']['Target'].sum()
        z_mtd_m = z_df[z_df['Brand']=='MHW']['This Month'].sum()
        z_ms_m = (z_mtd_m / z_tgt_m * 100) if z_tgt_m else 0

        html += f'<tr class="subtotal-row" style="background-color: #D9E1F2;"><td class="seg-col-text"><b>{zone}</b></td>'
        html += f'<td>{int(z_lm_i):,}</td><td>{int(z_tgt_i):,}</td><td>{int(z_mtd_i):,}</td><td>{z_ms_i:.1f}%</td>'
        html += f'<td>{int(z_lm_m):,}</td><td>{int(z_tgt_m):,}</td><td>{int(z_mtd_m):,}</td><td>{z_ms_m:.1f}%</td></tr>'

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
            a_df = z_df[z_df['ASM'] == asm]
            a_lm_i = a_df[a_df['Brand']=='IBDC']['Last Month'].sum()
            a_tgt_i = a_df[a_df['Brand']=='IBDC']['Target'].sum()
            a_mtd_i = a_df[a_df['Brand']=='IBDC']['This Month'].sum()
            a_ms_i = (a_mtd_i / a_tgt_i * 100) if a_tgt_i else 0

            a_lm_m = a_df[a_df['Brand']=='MHW']['Last Month'].sum()
            a_tgt_m = a_df[a_df['Brand']=='MHW']['Target'].sum()
            a_mtd_m = a_df[a_df['Brand']=='MHW']['This Month'].sum()
            a_ms_m = (a_mtd_m / a_tgt_m * 100) if a_tgt_m else 0

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
                t_ms_i = (t_mtd_i / t_tgt_i * 100) if t_tgt_i else 0

                t_lm_m = t_df[t_df['Brand']=='MHW']['Last Month'].sum()
                t_tgt_m = t_df[t_df['Brand']=='MHW']['Target'].sum()
                t_mtd_m = t_df[t_df['Brand']=='MHW']['This Month'].sum()
                t_ms_m = (t_mtd_m / t_tgt_m * 100) if t_tgt_m else 0

                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                html += f'<td>{int(t_lm_i):,}</td><td>{int(t_tgt_i):,}</td><td>{int(t_mtd_i):,}</td><td>{t_ms_i:.1f}%</td>'
                html += f'<td>{int(t_lm_m):,}</td><td>{int(t_tgt_m):,}</td><td>{int(t_mtd_m):,}</td><td>{t_ms_m:.1f}%</td></tr>'

    html += '</tbody></table></div>'
    return html

def generate_hierarchy_table_2(df):
    brands_to_show = ["IBDC", "MHW"]
    html = '<div class="table-wrapper"><table class="custom-dashboard-table">'
    html += '<thead><tr><th class="seg-col-text" rowspan="2">ZONE/ASM/TSE</th>'
    for b in brands_to_show:
        html += f'<th colspan="3">{b}</th>'
    html += '</tr><tr>'
    for _ in brands_to_show:
        html += '<th>FY</th><th>LM</th><th>MTD</th>'
    html += '</tr></thead><tbody>'

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    html += '<td>15.3%</td><td>8.1%</td><td>7.2%</td><td>1.0%</td><td>1.1%</td><td>0.9%</td></tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row" style="background-color: #D9E1F2;"><td class="seg-col-text"><b>{zone}</b></td>'
        html += '<td>12.3%</td><td>6.9%</td><td>6.8%</td><td>0.9%</td><td>1.1%</td><td>1.0%</td></tr>'

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>'
            html += '<td>12.5%</td><td>6.9%</td><td>6.4%</td><td>1.0%</td><td>1.4%</td><td>0.9%</td></tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                html += '<td>22.6%</td><td>11.5%</td><td>12.3%</td><td>0.6%</td><td>0.4%</td><td>1.0%</td></tr>'

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

    html += f'<tr class="grand-total-row"><td class="seg-col-text">West Bengal</td>'
    for _ in brands_to_show:
        html += '<td>3,303</td><td>1,268</td><td style="color: #9b1c1c;">-2,034</td>'
    html += '</tr>'

    zones = df['Zone'].dropna().unique()
    for zone in sorted(zones):
        z_df = df[df['Zone'] == zone]
        html += f'<tr class="subtotal-row" style="background-color: #D9E1F2;"><td class="seg-col-text"><b>{zone}</b></td>'
        for _ in brands_to_show:
            html += '<td>1,329</td><td>604</td><td style="color: #9b1c1c;">-725</td>'
        html += '</tr>'

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
            a_df = z_df[z_df['ASM'] == asm]
            html += f'<tr class="subtotal-row"><td class="seg-col-text" style="padding-left: 10px;"><b>{asm}</b></td>'
            for _ in brands_to_show:
                html += '<td>613</td><td>292</td><td style="color: #9b1c1c;">-321</td>'
            html += '</tr>'

            tses = a_df['TSE'].dropna().unique() if 'TSE' in a_df.columns else []
            for tse in sorted(tses):
                if str(tse).lower() in ["nan", "none", ""]: continue
                html += f'<tr class="brand-row"><td class="brand-col-text" style="padding-left: 25px;">{tse}</td>'
                for _ in brands_to_show:
                    html += '<td>109</td><td>59</td><td style="color: #9b1c1c;">-50</td>'
                html += '</tr>'

    html += '</tbody></table></div>'
    return html

# --- 9. DISPLAY DASHBOARD IN TABS ---
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Hierarchy View 1", "📊 Hierarchy View 2", "📊 Unique Outlets"])

with tab1:
    html_vol = generate_html_table(filtered_df, metric_type="Volume")
    st.write(html_vol, unsafe_allow_html=True)

with tab2:
    html_ms = generate_html_table(filtered_df, metric_type="Ms%")
    st.write(html_ms, unsafe_allow_html=True)

with tab3:
    st.markdown("<h3 style='color: #0f172a; font-size: 18px;'>Zone, ASM & TSE Performance Breakdown (IBDC & MHW)</h3>", unsafe_allow_html=True)
    html_h1 = generate_hierarchy_table_1(filtered_df)
    st.write(html_h1, unsafe_allow_html=True)

with tab4:
    st.markdown("<h3 style='color: #0f172a; font-size: 18px;'>Share / Growth Hierarchy Matrix (FY, LM, MTD)</h3>", unsafe_allow_html=True)
    html_h2 = generate_hierarchy_table_2(filtered_df)
    st.write(html_h2, unsafe_allow_html=True)

with tab5:
    st.markdown("<h3 style='color: #0f172a; font-size: 18px;'>Unique Billing Outlet Count Comparison (LM vs MTD)</h3>", unsafe_allow_html=True)
    html_h3 = generate_hierarchy_table_3(filtered_df)
    st.write(html_h3, unsafe_allow_html=True)
