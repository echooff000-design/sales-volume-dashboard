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
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label { color: #f8fafc !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab-list"] button div p, 
    .stTabs [data-baseweb="tab-list"] button span,
    .stTabs [data-baseweb="tab"] p { color: #ef4444 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] div p, 
    .stTabs [data-baseweb="tab"][aria-selected="true"] span,
    .stTabs [data-baseweb="tab"][aria-selected="true"] p { color: #ef4444 !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #ef4444 !important; }
    .table-wrapper { width: 100%; overflow-x: auto; margin-bottom: 20px; }
    .custom-dashboard-table { width: 100%; border-collapse: collapse; font-family: sans-serif; background-color: #ffffff; color: #000000; font-size: 8.5px; }
    .custom-dashboard-table th, .custom-dashboard-table td { border: 1px solid #D9D9D9; padding: 3px 2px; text-align: center; white-space: nowrap !important; }
    .custom-dashboard-table th { background-color: #D9E1F2; font-weight: bold; font-size: 8px; }
    .subtotal-row { font-weight: bold; background-color: #F2F2F2; }
    .grand-total-row { background-color: #D9E1F2; font-weight: bold; font-size: 9px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. COOKIE MANAGER & LOGIN ---
cookie_manager = stx.CookieManager()

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=300)
def load_data():
    try:
        url = st.secrets["SHAREPOINT_URL"].split("?")[0] + "?download=1"
        response = requests.get(url, timeout=20)
        dfs = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
        return dfs, None, datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    except Exception as e:
        return None, str(e), None

dfs, error, last_update = load_data()
if error: st.error(f"⚠️ {error}"); st.stop()

# --- 4. AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = bool(cookie_manager.get(cookie="wb_sale_user"))
    st.session_state["user_name"] = cookie_manager.get(cookie="wb_sale_user") or ""

if not st.session_state["authenticated"]:
    # (Insert your login form logic here as you had it previously)
    st.warning("Please log in.")
    st.stop()

# --- 5. DATA PROCESSING ---
df_this = dfs["This Month"].copy()
df_last = dfs["Last Month"].copy()
df_target = dfs["Target Data"].copy()
df_outlet = dfs["Outlet Master"].copy()

# ... (Insert your data mapping and pivot logic here) ...
# Ensure 'filtered_df' is created here after applying sidebar filters
filtered_df = df_raw.copy() # Placeholder for your actual filtered dataframe

# --- 6. DISPLAY TABS ---
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Dashboard", "💬 Ask Assistant"])

# ... (Insert generate_html_table and hierarchy functions) ...

with main_tab4:
    st.markdown("### 🤖 Smart Sales Query Assistant")
    query_type = st.selectbox("Choose a common question:", [
        "-- Select a Query --",
        "Outlets that haven't billed IBDC this month",
        "Top 10 performing outlets by Volume (This Month)",
        "Outlets with Zero Volume (This Month)"
    ])
    custom_query = st.text_input("Or type your own question (e.g., 'IBDC sales in Kol'):")

    active_query = custom_query if custom_query else query_type

    if "haven't billed ibdc" in active_query.lower() or query_type == "Outlets that haven't billed IBDC this month":
        all_outlets = filtered_df[["LIC No", "Outlet Name", "ASM"]].drop_duplicates()
        ibdc_billed = filtered_df[(filtered_df["Brand"] == "IBDC") & (filtered_df["This Month"] > 0)]["LIC No"].unique()
        res = all_outlets[~all_outlets["LIC No"].isin(ibdc_billed)]
        st.dataframe(res, use_container_width=True)

    elif custom_query:
        mask = filtered_df.astype(str).apply(lambda col: col.str.contains(custom_query, case=False, na=False)).any(axis=1)
        st.dataframe(filtered_df[mask], use_container_width=True)
