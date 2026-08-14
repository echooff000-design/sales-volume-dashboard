import streamlit as st
import pandas as pd
import requests
import io
import datetime
import os
import base64
import extra_streamlit_components as stx

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

# --- 2. AUTOMATIC LOG FILE FIXER (SELF-HEALING) ---
csv_file = "login_logs.csv"
if os.path.exists(csv_file):
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if len(lines) > 0 and not lines[0].startswith("Year,Date,Time,Name,User ID"):
            new_lines = ["Year,Date,Time,Name,User ID\n"]
            for line in lines:
                line = line.strip()
                if not line: continue
                parts = line.split(",")
                
                if parts[0] == "Name" or parts[0] == "Year": 
                    continue
                    
                if len(parts) == 3: 
                    name, uid, time_val = parts[0], parts[1], parts[2]
                    try:
                        dt = pd.to_datetime(time_val)
                        year = str(dt.year)
                        date = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        year = "2026"
                        date = time_val[:10]
                        time_str = time_val[11:]
                    new_lines.append(f"{year},{date},{time_str},{name},{uid}\n")
                    
                elif len(parts) >= 5: 
                    new_lines.append(line + "\n")
            
            with open(csv_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception as e:
        pass

# --- 3. COOKIE MANAGER SETUP ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 4. DATA FETCHING (ONLINE SHAREPOINT DIRECT LINK) ---
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

# --- 5. LOGIN CREDENTIAL SYSTEM ---
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

cached_user = None
try:
    cached_user = cookie_manager.get(cookie="wb_sale_user")
except Exception:
    pass

if "authenticated" not in st.session_state:
    if cached_user:
        st.session_state["authenticated"] = True
        st.session_state["user_name"] = cached_user
    else:
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""

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
                    
                    try:
                        cookie_manager.set("wb_sale_user", st.session_state["user_name"], max_age=30*24*60*60)
                    except Exception:
                        pass
                    
                    try:
                        ist_timezone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                        now = datetime.datetime.now(ist_timezone)
                        log_data = pd.DataFrame([{
                            "Year": now.year,
                            "Date": now.strftime("%Y-%m-%d"),
                            "Time": now.strftime("%H:%M:%S"),
                            "Name": st.session_state["user_name"],
                            "User ID": input_user
                        }])
                        file_exists = os.path.exists(csv_file)
                        log_data.to_csv(csv_file, mode='a', header=not file_exists, index=False, encoding='utf-8')
                    except Exception as e:
                        print(f"Log error: {e}")
                    
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
    st.markdown(f"<p style='text-align: right; margin-top: 15px; font-size: 13px; color: #f8fafc;'>👤 <b>{st.session_state['user_name']}</b></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        try:
            cookie_manager.delete("wb_sale_user")
        except Exception:
            pass
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.rerun()

st.sidebar.markdown("📁 **Data Source**")
if last_update:
    st.sidebar.caption(f"🕒 **Last Synced:** {last_update}")

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Fetching newest data...")

st.sidebar.markdown("---")
st.sidebar.markdown("📋 **Admin Panel**")
if os.path.exists("login_logs.csv"):
    with open("login_logs.csv", "rb") as file:
        st.sidebar.download_button(label="📥 Download Full Yearly Logs", data=file, file_name="full_yearly_login_logs.csv", mime="text/csv")
else:
    st.sidebar.info("No login logs yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("🔗 **[Go to Payment & KYC](https://wbpaymentkyc.streamlit.app/)**")

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
        if tse_mapping:
            d["TSE"] = d[k_col].astype(str).str.strip().map(tse_mapping).fillna(d.get("TSE", "Unassigned"))
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

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
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

    # Grand Total Row
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

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
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

        asms = z_df['ASM'].dropna().unique()
        for asm in sorted(asms):
            if str(asm).lower() in ["nan", "none", ""]: continue
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
    st.write(html_vol, unsafe_allow_html=True)

with main_tab2:
    html_ms = generate_html_table(filtered_df, metric_type="Ms%")
    st.write(html_ms, unsafe_allow_html=True)

with main_tab3:
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Target vs Ach", "MS% Details", "WOD Details"])
    
    with sub_tab1:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Zone, ASM & TSE Performance Breakdown (IBDC & MHW)</h3>", unsafe_allow_html=True)
        html_h1 = generate_hierarchy_table_1(filtered_df)
        st.write(html_h1, unsafe_allow_html=True)

    with sub_tab2:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Share / Growth Hierarchy Matrix (LM, MTD, Diff)</h3>", unsafe_allow_html=True)
        html_h2 = generate_hierarchy_table_2(filtered_df)
        st.write(html_h2, unsafe_allow_html=True)

    with sub_tab3:
        st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>Unique Billing Outlet Count Comparison (LM vs MTD)</h3>", unsafe_allow_html=True)
        html_h3 = generate_hierarchy_table_3(filtered_df)
        st.write(html_h3, unsafe_allow_html=True)

with main_tab4:
    st.markdown("<h3 style='color: #f8fafc; font-size: 18px;'>🤖 Smart Sales & Outlet Query Assistant</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 13px;'>Select a common query or type your own question below to analyze your data.</p>", unsafe_allow_html=True)

    query_type = st.selectbox(
        "Choose a common question:",
        [
            "-- Select a Query --",
            "Outlets that haven't billed IBDC this month",
            "Top 10 performing outlets by Volume (This Month)",
            "Outlets with Zero Volume (This Month)",
            "Brands with negative growth compared to Last Month"
        ]
    )

    custom_query = st.text_input("Or type your own question / search term:")
    active_query = custom_query if custom_query else query_type

    if "haven't billed ibdc" in active_query.lower() or query_type == "Outlets that haven't billed IBDC this month":
        st.markdown("#### Outlets in your filter scope with 0 IBDC volume this month:")
        if "Brand" in filtered_df.columns and "Outlet Name" in filtered_df.columns:
            all_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates()
            ibdc_billed = filtered_df[(filtered_df["Brand"] == "IBDC") & (filtered_df["This Month"] > 0)]["LIC No"].unique()
            not_billed_df = all_outlets[~all_outlets["LIC No"].isin(ibdc_billed)]
            
            if not not_billed_df.empty:
                st.dataframe(not_billed_df, use_container_width=True)
                st.download_button("📥 Download Unbilled Outlets CSV", data=not_billed_df.to_csv(index=False).encode('utf-8'), file_name="unbilled_ibdc_outlets.csv", mime="text/csv")
            else:
                st.success("🎉 All outlets in this filter scope have billed IBDC this month!")
        else:
            st.warning("Required columns not found.")

    elif "top 10" in active_query.lower() or query_type == "Top 10 performing outlets by Volume (This Month)":
        st.markdown("#### Top 10 Outlets by This Month Volume:")
        if "Outlet Name" in filtered_df.columns:
            top_outlets = filtered_df.groupby(["LIC No", "Outlet Name", "ASM", "Zone"], observed=False)["This Month"].sum().reset_index()
            top_outlets = top_outlets.sort_values(by="This Month", ascending=False).head(10)
            st.dataframe(top_outlets, use_container_width=True)

    elif "zero volume" in active_query.lower() or query_type == "Outlets with Zero Volume (This Month)":
        st.markdown("#### Outlets with 0 Total Volume This Month:")
        outlet_sums = filtered_df.groupby(["LIC No", "Outlet Name", "ASM"], observed=False)["This Month"].sum().reset_index()
        zero_vol = outlet_sums[outlet_sums["This Month"] == 0]
        st.dataframe(zero_vol, use_container_width=True)

    elif "negative growth" in active_query.lower() or query_type == "Brands with negative growth compared to Last Month":
        st.markdown("#### Brands experiencing a drop from Last Month to This Month:")
        brand_comp = filtered_df.groupby("Brand", observed=False)[["Last Month", "This Month"]].sum().reset_index()
        brand_comp["Difference"] = brand_comp["This Month"] - brand_comp["Last Month"]
        negative_brands = brand_comp[brand_comp["Difference"] < 0].sort_values(by="Difference")
        st.dataframe(negative_brands, use_container_width=True)

    elif custom_query:
        st.markdown(f"<h4>Search results for: '{custom_query}'</h4>", unsafe_allow_html=True)
        mask = filtered_df.astype(str).apply(lambda col: col.str.contains(custom_query, case=False, na=False)).any(axis=1)
        search_results = filtered_df[mask]
        
        if not search_results.empty:
            st.dataframe(search_results, use_container_width=True)
        else:
            st.info("ℹ️ No matching records found for your query in the current filter scope.")
