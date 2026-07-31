import streamlit as st
import pandas as pd
import requests
import io

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="WB Sale Data", page_icon="logo.png", layout="wide")

# --- CUSTOM ATTRACTIVE LOGIN & UI STYLING ---
st.markdown("""
    <style>
    /* Main Background & Font Styling */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Login Card Container Styling */
    .login-card {
        background: #ffffff;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        text-align: center;
    }

    /* Form input fields */
    .stTextInput input {
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
        padding: 10px 12px !important;
    }

    /* Login Button Styling */
    .stButton button {
        width: 100%;
        background-color: #1e3a8a;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        padding: 10px;
        border: none;
        transition: background 0.3s ease;
    }
    .stButton button:hover {
        background-color: #1d4ed8;
        color: white;
    }

    /* Tables */
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
            
        return dfs, None
    except Exception as e:
        return None, str(e)

with st.spinner("Connecting to database..."):
    dfs, error = load_data_from_url(RAW_SHAREPOINT_URL)

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
    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""
                <div style='background: white; padding: 35px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); text-align: center;'>
            """, unsafe_allow_html=True)
            
            try:
                st.image("logo.png", width=90)
            except Exception:
                pass
                
            st.markdown("<h2 style='color: #1e3a8a; margin-bottom: 5px; font-size: 24px;'>Welcome Back</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #6b7280; font-size: 14px; margin-bottom: 25px;'>Sign in to access WB Sale Data Dashboard</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
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
                        st.rerun()
                    else:
                        st.error("❌ Invalid User ID or Password")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- CUSTOM TITLE WITH LOGO & LOGOUT ---
col_logo, col_title, col_logout = st.columns([1, 5, 2])
with col_logo:
    try:
        st.image("logo.png", width=60)
    except Exception:
        st.warning("logo.png missing")
with col_title:
    st.markdown("<h3 style='margin-top: 10px; font-size: 22px;'>WB Sale Data</h3>", unsafe_allow_html=True)
with col_logout:
    st.markdown(f"<p style='text-align: right; margin-top: 15px; font-size: 13px;'>👤 <b>{st.session_state['user_name']}</b></p>", unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["user_name"] = ""
        st.rerun()

st.sidebar.header("📁 Data Source")

# --- NAVIGATION LINK IN SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.markdown("🔗 **[Go to Payment & KYC](https://wbpaymentkyc.streamlit.app/)**")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Fetching newest data...")

# --- 4. FETCH DATA INDIVIDUALLY FROM SHEETS ---
required_sheets = ["This Month", "Last Month", "Target Data"]
for sheet in required_sheets:
    if sheet not in dfs:
        st.error(f"❌ Could not find the sheet named '{sheet}' in your Excel file.")
        st.stop()

df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()

for d in [df_this, df_last, df_target]:
    d.columns = d.columns.astype(str).str.strip()
    d.rename(columns={"Outlet Nan": "Outlet Name", "Asm": "ASM", "Volume": "Value"}, inplace=True)
    
    if "Segment" in d.columns:
        d["Segment"] = d["Segment"].replace({"Deluxe Plus-Whisky": "Deluxe-Whisky"})
    
    if "Brand" in d.columns:
        d["Brand"] = d["Brand"].replace({"IBW": "IBDC"})

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
st.subheader("🔍 Filters")
col1, col2, col3, col4 = st.columns(4)

temp_df = df_raw.copy()

with col1:
    asm_options = ["All"] + sorted(temp_df["ASM"].dropna().astype(str).unique().tolist()) if "ASM" in temp_df.columns else ["All"]
    selected_asm = st.selectbox("ASM Filter", asm_options)
    if selected_asm != "All":
        temp_df = temp_df[temp_df["ASM"].astype(str) == selected_asm]

with col2:
    tse_options = ["All"] + sorted(temp_df["TSE"].dropna().astype(str).unique().tolist()) if "TSE" in temp_df.columns else ["All"]
    selected_tse = st.selectbox("TSE Filter", tse_options)
    if selected_tse != "All":
        temp_df = temp_df[temp_df["TSE"].astype(str) == selected_tse]

with col3:
    lic_options = ["All"] + sorted(temp_df["LIC No"].dropna().astype(str).unique().tolist()) if "LIC No" in temp_df.columns else ["All"]
    selected_lic = st.selectbox("LIC No Filter", lic_options)
    if selected_lic != "All":
        temp_df = temp_df[temp_df["LIC No"].astype(str) == selected_lic]

with col4:
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

# --- 7. HTML TABLE GENERATORS ---
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
                
                bal_str = f"{int(row['Target'] - row['This Month']):,}" if is_marked else ""
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td style="white-space:nowrap;">{int(row["Last Month"]):,}</td><td style="white-space:nowrap;">{int(row["Target"]):,}</td><td style="white-space:nowrap;">{int(row["This Month"]):,}</td><td style="white-space:nowrap;">{bal_str}</td></tr>'

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
                
                growth_str = f"{b_growth:,.1f}%"
                html += f'<tr class="brand-row"><td class="brand-col-text" style="{bg_style}">{b_name}</td><td style="white-space:nowrap;">{b_last_pct:,.1f}%</td><td style="white-space:nowrap;">{b_this_pct:,.1f}%</td><td style="white-space:nowrap;">{growth_str}</td></tr>'

    if metric_type == "Volume":
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td style="white-space:nowrap;">{int(gt_last_vol):,}</td><td style="white-space:nowrap;">{int(gt_target_vol):,}</td><td style="white-space:nowrap;">{int(gt_this_vol):,}</td><td style="white-space:nowrap;">{int(gt_bal_vol):,}</td></tr>'
    else:
        html += f'<tr class="grand-total-row"><td class="seg-col-text">Grand Total</td><td style="white-space:nowrap;">100.0%</td><td style="white-space:nowrap;">100.0%</td><td></td></tr>'
        
    html += '</tbody></table></div>'
    return html

# --- 8. DISPLAY DASHBOARD IN TABS ---
st.markdown("---")

tab1, tab2 = st.tabs(["📦 Volume", "📈 Ms%"])

with tab1:
    html_vol = generate_html_table(filtered_df, metric_type="Volume")
    st.write(html_vol, unsafe_allow_html=True)

with tab2:
    html_ms = generate_html_table(filtered_df, metric_type="Ms%")
    st.write(html_ms, unsafe_allow_html=True)
