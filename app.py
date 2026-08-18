import streamlit as st
import pandas as pd
import requests, io, datetime, re, base64
import extra_streamlit_components as stx
import gspread
from google.oauth2.service_account import Credentials

# --- 1. PAGE SETUP & CSS ---
st.set_page_config(page_title="WB Sale Data", page_icon="logo.png", layout="wide")
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
[data-testid="stSidebar"] {background-color: #0f172a !important; border-right: 1px solid rgba(255,255,255,0.1) !important;}
[data-testid="stSidebar"] * {color: #f8fafc !important;}
[data-testid="stSidebar"] .stButton button, [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {background-color: #1e293b !important; color: #fff !important; border: 1px solid rgba(255,255,255,0.25) !important; border-radius: 8px !important; width: 100% !important;}
.stApp {background-color: #0f172a !important;}
.table-wrapper {width: 100%; overflow-x: auto; margin-bottom: 20px; display: block; touch-action: pan-x pan-y pinch-zoom !important;}
.custom-dashboard-table {width: 100%; border-collapse: collapse !important; font-family: sans-serif; background-color: #fff; color: #000; font-size: 8.5px; border: 1px solid #d3d3d3 !important;}
.custom-dashboard-table th, .custom-dashboard-table td {border: 1px solid #d3d3d3 !important; padding: 4px 3px !important; text-align: center; white-space: nowrap !important;}
.custom-dashboard-table th {background-color: #D9E1F2; font-weight: bold; border-bottom: 2px solid #b0b0b0 !important; font-size: 8px;}
.table-wrapper th:first-child, .table-wrapper td:first-child {position: sticky !important; left: 0 !important; z-index: 2 !important; background-color: #F2F2F2 !important; border-right: 1px solid #d3d3d3 !important;}
.table-wrapper th:first-child {background-color: #D9E1F2 !important; z-index: 3 !important;}
.subtotal-row {font-weight: bold; background-color: #F2F2F2; font-size: 8px;}
.brand-row {background-color: #FFF;}
.grand-total-row {background-color: #D9E1F2; font-weight: bold; font-size: 9px; border-top: 2px solid #b0b0b0 !important;}
.brand-col-text, .seg-col-text {text-align: left !important; padding-left: 4px !important; font-size: 8px;}
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH & SECRETS HANDLERS ---
SHEET_ID = "1iEBhkOnErBiWiXgl74dYV3fYxLJvCKnff8ptkxHZ8eo"
cookie_manager = stx.CookieManager()

def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict.get("private_key", "").replace("\\n", "\n")
    return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])).open_by_key(SHEET_ID).sheet1

def to_excel_bytes(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
    return out.getvalue()

@st.cache_data(ttl=300)
def load_excel(url):
    try:
        r = requests.get(url.split("?")[0] + "?download=1", headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        for eng in ["pyxlsb", "openpyxl", None]:
            try: return pd.read_excel(io.BytesIO(r.content), sheet_name=None, engine=eng), None
            except Exception: pass
    except Exception as e: return None, str(e)

dfs, error = load_excel(st.secrets["SHAREPOINT_URL"])
if error or not dfs: st.error(f"⚠️ Error loading data: {error}"); st.stop()

# --- 3. DYNAMIC F2 DATE & USER AUTH ---
raw_users = dfs.get("Users", pd.DataFrame()).copy()

def get_f2_date(df_u):
    val = df_u.get("Date", df_u.iloc[:, 5] if df_u.shape[1] >= 6 else pd.Series()).iloc[0] if len(df_u) > 0 else None
    if pd.notna(val) and str(val).strip():
        if isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)): return int(val.day), val.strftime("%d %b %Y")
        try:
            n = float(str(val).strip())
            if n > 30000: dt = pd.to_datetime(n, unit='D', origin='1899-12-30'); return int(dt.day), dt.strftime("%d %b %Y")
        except Exception: pass
        p = pd.to_datetime(str(val).strip(), errors='coerce', dayfirst=True)
        if pd.notna(p): return int(p.day), p.strftime("%d %b %Y")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, 30)))
    return now.day, now.strftime("%d %b %Y")

days_elapsed, f2_display_date = get_f2_date(raw_users)

# Auth state check
df_u_norm = raw_users.rename(columns={c: next((k for k in ["Name", "user_id", "password", "role"] if k.lower() in c.lower()), c) for c in raw_users.columns.astype(str)})
cached_user = cookie_manager.get("wb_sale_user")

if "authenticated" not in st.session_state:
    st.session_state.update({"authenticated": bool(cached_user), "user_name": cached_user or "", "is_admin": False})

if not st.session_state["authenticated"]:
    with st.form("login"):
        st.subheader("Welcome Back")
        uid, pwd = st.text_input("User ID"), st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            match = df_u_norm[(df_u_norm["user_id"].astype(str).str.strip() == uid.strip()) & (df_u_norm["password"].astype(str).str.strip() == pwd.strip())]
            if not match.empty:
                st.session_state.update({"authenticated": True, "user_name": match.iloc[0]["Name"], "is_admin": str(match.iloc[0].get("role", "")).lower() in ["admin", "true", "1"]})
                try: cookie_manager.set("wb_sale_user", st.session_state["user_name"], max_age=30*86400)
                except Exception: pass
                st.rerun()
            else: st.error("❌ Invalid Credentials")
    st.stop()

# --- 4. DATA PIPELINE & STANDARDIZATION ---
df_outlet = dfs["Outlet Master"].rename(columns={"Outlet Nan": "Outlet Name"})
mappings = {k: dict(zip(df_outlet["LIC No"].astype(str).str.strip(), df_outlet[c].astype(str).str.strip())) for k, c in [("Group", df_outlet.columns[7] if len(df_outlet.columns) > 7 else "Group"), ("Zone", next((c for c in df_outlet.columns if "zone" in c.lower()), None)), ("ASM", next((c for c in df_outlet.columns if c.lower() in ["asm", "manager"]), None)), ("TSE", df_outlet.columns[14] if len(df_outlet.columns) > 14 else next((c for c in df_outlet.columns if "tse" in c.lower()), None))] if c}

def clean_df(df, metric=None):
    d = df.rename(columns={"Outlet Nan": "Outlet Name", "Volume": "Value", "volume": "Value", "val": "Value"}).copy()
    if "Segment" in d: d["Segment"] = d["Segment"].replace({"Deluxe Plus-Whisky": "Deluxe-Whisky"})
    if "Brand" in d: d["Brand"] = d["Brand"].replace({"IBW": "IBDC"})
    if "LIC No" in d:
        for k, m in mappings.items(): d[k] = d["LIC No"].astype(str).str.strip().map(m).fillna("West Bengal" if k == "Zone" else "Unassigned")
    if metric: d["Metric"] = metric
    return d

df_this, df_last, df_target = clean_df(dfs["This Month"], "This Month"), clean_df(dfs["Last Month"], "Last Month"), clean_df(dfs["Target Data"], "Target")
df_raw = pd.pivot_table(pd.concat([df_this, df_last, df_target], ignore_index=True), values="Value", index=[c for c in df_this.columns if c not in ["Metric", "Value"]], columns="Metric", aggfunc="sum").reset_index().fillna(0)

# --- 5. SIDEBAR & FILTERS ---
col_logo, col_title, col_logout = st.columns([1, 5, 2])
with col_title: st.markdown("<h3 style='color: #f8fafc;'>WB Sale Data</h3>", unsafe_allow_html=True)
with col_logout:
    if st.button("Logout"):
        try: cookie_manager.delete("wb_sale_user")
        except Exception: pass
        st.session_state.update({"authenticated": False, "user_name": "", "is_admin": False}); st.rerun()

st.sidebar.caption(f"🕒 **Last Synced:** {f2_display_date}")
if st.sidebar.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()

filter_cols = [c for c in ["Group", "ASM", "TSE", "LIC No", "Outlet Name"] if c in df_raw.columns]
filters = {}
c_boxes = st.columns(len(filter_cols))
for i, col in enumerate(filter_cols):
    with c_boxes[i]: filters[col] = st.selectbox(f"{col} Filter", ["All"] + sorted(df_raw[col].dropna().astype(str).unique().tolist()))

def filter_data(d):
    for k, v in filters.items():
        if v != "All" and k in d: d = d[d[k].astype(str) == v]
    return d

filtered_df = filter_data(df_raw)
f_this, f_last = filter_data(df_this), filter_data(df_last)

def render_table(html):
    st.markdown(f'<div style="overflow-x: auto;">{html}</div>', unsafe_allow_html=True)

# --- 6. ORIGINAL METRIC TABLES ---
def generate_metric_table(df, metric="Volume"):
    grp = df.groupby(["Segment", "Brand"], as_index=False, observed=False)[["Last Month", "Target", "This Month"]].sum()
    html = '<div class="table-wrapper"><table class="custom-dashboard-table"><thead><tr><th class="seg-col-text">Brand</th>' + ('<th>LM</th><th>TGT</th><th>TM</th><th>BAL</th>' if metric=="Volume" else '<th>LM</th><th>TM</th><th>GRW</th>') + '</tr></thead><tbody>'
    for seg, sdata in grp.groupby("Segment", sort=False, observed=False):
        html += f'<tr class="subtotal-row"><td class="seg-col-text">{seg}</td><td>{int(sdata["Last Month"].sum()):,}</td><td>{int(sdata["Target"].sum()):,}</td><td>{int(sdata["This Month"].sum()):,}</td><td></td></tr>'
        for _, r in sdata.iterrows():
            bal = f"{int(r['Target'] - r['This Month']):,}"
            html += f'<tr class="brand-row"><td class="brand-col-text">{r["Brand"]}</td><td>{int(r["Last Month"]):,}</td><td>{int(r["Target"]):,}</td><td>{int(r["This Month"]):,}</td><td>{bal}</td></tr>'
    html += '</tbody></table></div>'
    return html

# --- 7. TABS SETUP ---
t1, t2, t3, t4 = st.tabs(["📦 Volume", "📈 Ms%", "📊 Dashboard", "💬 Ask Assistant"])
with t1: render_table(generate_metric_table(filtered_df, "Volume"))
with t2: render_table(generate_metric_table(filtered_df, "MS%"))
with t3: st.info("Hierarchy reports available in Assistant / Master dashboards.")

# --- 8. ASK ASSISTANT TAB ---
with t4:
    col_q1, col_q2, col_q3 = st.columns([1.2, 1, 1.8])
    with col_q1: basis_period = st.selectbox("Basis on Period:", ["This Month (TM)", "Last Month (LM)", "Last 2 Months (LM + M2)", "Last 3 Months (LM + M2 + M3)", "Last 4 Months (LM + M2 + M3 + M4)"])
    with col_q2: target_brand = st.selectbox("Target Brand Focus:", ["IBDC", "MHW", "MHFB", "BLGLM+BLGOR", "SMG+SMGP", "SIW", "Monarch"])
    
    GAP_MAP = {
        "MMV / MMFLV Billed but BLGLM / BLGOR Not Billed": (["MMV", "MMFLV"], ["BLGLM", "BLGOR"]),
        "MCD Lux Billed but IBDC Not Billed": (["MCD Lux"], ["IBDC"]),
        "IQ Billed but IBDC Not Billed": (["IQ"], ["IBDC"]),
        "RSW Billed but MHW Not Billed": (["RSW"], ["MHW"]),
        "RGW Billed but MHW Not Billed": (["RGW"], ["MHW"]),
        "SRB7 Billed but MHW Not Billed": (["SRB7"], ["MHW"]),
        "RCW Billed but MHW Not Billed": (["RCW"], ["MHW"]),
        "All Season Billed but MHW Not Billed": (["All Season"], ["MHW"]),
    }
    
    query_type = st.selectbox("Choose a Query / Analysis:", ["-- Select a Query --", "Non Billing Outlets"] + list(GAP_MAP.keys()) + [
        "Deluxe Industry > 30 CS but IBDC Not Billed",
        "Semi Premium Whisky Industry > 50 CS but MHW Not Billed",
        "SMG + SMGP Lapsed Outlets (Not Repeated)", "SIW Lapsed Outlets (Not Repeated)",
        "Brand-wise L3M Daily Run vs Current Month Daily Run",
        "Deluxe Industry - MS% Trend (5 Months)", "Semi Premium Whisky Industry - MS% Trend (5 Months)",
        "Deluxe Industry - Volume Trend (5 Months)", "Semi Premium Whisky Industry - Volume Trend (5 Months)",
        "Deluxe Industry - Unique Billed Outlets Trend (5 Months)", "Semi Premium Whisky Industry - Unique Billed Outlets Trend (5 Months)"
    ])

    # Lazy-load historical dataset
    hist_dfs = {}
    if any(k in basis_period for k in ["2", "3", "4"]) or any(k in query_type for k in ["L3M", "Trend", "Lapsed"]):
        h_data, _ = load_excel(st.secrets.get("HISTORICAL_SHAREPOINT_URL", st.secrets["SHAREPOINT_URL"]))
        if h_data: hist_dfs = {k: filter_data(clean_df(h_data[k], k)) for k in ["M2", "M3", "M4"] if k in h_data}

    basis_list = [f_this] if "This Month" in basis_period else [f_last] + [hist_dfs.get(k, pd.DataFrame()) for k in ["M2", "M3", "M4"] if k in basis_period and k in hist_dfs]
    basis_df = pd.concat([d for d in basis_list if not d.empty], ignore_index=True) if basis_list else f_this
    base_outlets = filtered_df[["LIC No", "Outlet Name", "ASM", "TSE", "Group"]].drop_duplicates() if "LIC No" in filtered_df else pd.DataFrame()

    def show_results(df_res, title, filename):
        st.markdown(f"#### 🔍 {title} (Total: {len(df_res):,} Outlets):")
        if not df_res.empty:
            st.dataframe(df_res, use_container_width=True)
            st.download_button("📥 Download in Excel", data=to_excel_bytes(df_res), file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.success("🎉 No matching gap outlets found!")

    # Route query calculations
    if query_type == "Non Billing Outlets":
        b_list = [target_brand] if "+" not in target_brand else target_brand.split("+")
        active = basis_df[basis_df["Value"] > 0]["LIC No"].unique()
        tm_b = f_this[(f_this["Brand"].isin(b_list)) & (f_this["Value"] > 0)]["LIC No"].unique()
        show_results(base_outlets[(base_outlets["LIC No"].isin(active)) & (~base_outlets["LIC No"].isin(tm_b))], f"Outlets Active in {basis_period} but NOT Billing {target_brand} this Month", f"non_billing_{target_brand}.xlsx")

    elif query_type in GAP_MAP:
        src_b, tgt_b = GAP_MAP[query_type]
        src_out = basis_df[(basis_df["Brand"].isin(src_b)) & (basis_df["Value"] > 0)]["LIC No"].unique()
        tgt_out = f_this[(f_this["Brand"].isin(tgt_b)) & (f_this["Value"] > 0)]["LIC No"].unique()
        show_results(base_outlets[base_outlets["LIC No"].isin(set(src_out) - set(tgt_out))], f"Outlets Billing {'/'.join(src_b)} in {basis_period} but NOT {'/'.join(tgt_b)} this Month", "gap_outlets.xlsx")

    elif "Industry >" in query_type:
        is_dlx = "Deluxe" in query_type
        cutoff = 30 if is_dlx else 50
        seg = ["Deluxe-Whisky", "Deluxe Plus-Whisky"] if is_dlx else ["Semi Premium-Whisky"]
        tgt = "IBDC" if is_dlx else "MHW"
        ind_vol = basis_df[basis_df["Segment"].isin(seg)].groupby("LIC No")["Value"].sum()
        heavy = ind_vol[ind_vol > cutoff].index
        tm_billed = f_this[(f_this["Brand"] == tgt) & (f_this["Value"] > 0)]["LIC No"].unique()
        res = base_outlets[base_outlets["LIC No"].isin(set(heavy) - set(tm_billed))].copy()
        res["Industry Volume"] = res["LIC No"].map(ind_vol)
        show_results(res, f"Outlets with Industry Volume > {cutoff} CS in {basis_period} but {tgt} Not Billed", f"industry_gap_{tgt}.xlsx")

    elif "Lapsed" in query_type:
        t_b = ["SMG", "SMGP"] if "SMG" in query_type else ["SIW"]
        all_hist = pd.concat([f_this, f_last] + list(hist_dfs.values()), ignore_index=True)
        ever = all_hist[(all_hist["Brand"].isin(t_b)) & (all_hist["Value"] > 0)]["LIC No"].unique()
        b_billed = basis_df[(basis_df["Brand"].isin(t_b)) & (basis_df["Value"] > 0)]["LIC No"].unique()
        tm_b = f_this[(f_this["Brand"].isin(t_b)) & (f_this["Value"] > 0)]["LIC No"].unique()
        show_results(base_outlets[base_outlets["LIC No"].isin(set(ever) - set(b_billed) - set(tm_b))], f"Lapsed Outlets for {'+'.join(t_b)}", "lapsed_outlets.xlsx")

    elif query_type == "Brand-wise L3M Daily Run vs Current Month Daily Run":
        l3m = pd.concat([f_last, hist_dfs.get("M2", pd.DataFrame()), hist_dfs.get("M3", pd.DataFrame())], ignore_index=True).groupby("Brand", observed=False)["Value"].sum()
        tm_b = f_this.groupby("Brand", observed=False)["Value"].sum()
        rr = []
        for b in sorted(set(l3m.index).union(tm_b.index)):
            l_d, t_d = round(l3m.get(b, 0) / 90.0, 1), round(tm_brand := tm_b.get(b, 0) / float(days_elapsed), 1)
            rr.append({"Brand": b, "L3M Total": int(l3m.get(b,0)), "L3M Daily": l_d, "TM Total": int(tm_b.get(b,0)), f"TM Daily (/{days_elapsed}D)": t_d, "Growth (CS)": round(t_d - l_d, 1), "Growth %": f"{round(((t_d - l_d)/l_d)*100, 1) if l_d > 0 else 0.0:+,.1f}%"})
        st.dataframe(df_rr := pd.DataFrame(rr), use_container_width=True)
        st.download_button("📥 Download in Excel", data=to_excel_bytes(df_rr), file_name="run_rate.xlsx")

    elif "Trend (5 Months)" in query_type:
        is_dlx, is_ms, is_vol = "Deluxe" in query_type, "MS%" in query_type, "Volume" in query_type
        b_list = ["IBDC", "N1WSUP", "OCBL", "GGSW", "Green Label", "IQ", "MCD Lux", "Mountain Oak"] if is_dlx else ["MHW", "All Season", "Brothers", "GRAYSON'S Maxx", "OakInt", "RCW", "RGW", "ROCKFORD", "RSBS", "RSDD", "RSW", "SRB7", "Whiskots", "GRR"]
        segs = ["Deluxe-Whisky", "Deluxe Plus-Whisky"] if is_dlx else ["Semi Premium-Whisky"]
        m_dict = {"TM": f_this, "LM": f_last, **hist_dfs}
        html = '<div class="table-wrapper"><table class="custom-dashboard-table"><thead><tr><th class="seg-col-text">Brand</th>' + ''.join([f'<th>{k}</th>' for k in ["TM", "LM", "M2", "M3", "M4"]]) + '</tr></thead><tbody>'
        for b in b_list:
            html += f'<tr class="brand-row"><td class="brand-col-text">{b}</td>'
            for k in ["TM", "LM", "M2", "M3", "M4"]:
                sub = m_dict.get(k, pd.DataFrame())
                if sub.empty: html += '<td>-</td>'; continue
                b_val = sub[(sub["Segment"].isin(segs)) & (sub["Brand"] == b)]["Value"].sum()
                tot_val = sub[sub["Segment"].isin(segs)]["Value"].sum()
                html += f'<td>{b_val/tot_val*100:.1f}%</td>' if is_ms else (f'<td>{int(b_val):,}</td>' if is_vol else f'<td>{sub[(sub["Brand"]==b) & (sub["Value"]>0)]["LIC No"].nunique():,}</td>')
            html += '</tr>'
        html += '</tbody></table></div>'
        render_table(html)
