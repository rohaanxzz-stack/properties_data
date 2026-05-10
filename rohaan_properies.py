import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🖥️ PAGE CONFIGURATION
# ============================================
st.set_page_config(page_title="EstateLedger | Analytics", layout="wide", page_icon="📈")

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 🔐 ACCESS CONTROL
# ============================================
ADMIN_PASSWORDS = ["Jaffar50", "Tehseen40"] 

def check_access():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    with st.sidebar:
        st.title("🛡️ Secure Access")
        if not st.session_state.authenticated:
            pwd = st.text_input("Admin Password", type="password")
            if st.button("Unlock Management Tools"):
                if pwd in ADMIN_PASSWORDS:
                    st.session_state.authenticated = True
                    st.rerun()
        else:
            st.success("Editor Mode Active")
            if st.button("Log Out"):
                st.session_state.authenticated = False
                st.rerun()

check_access()
is_editor = st.session_state.authenticated

# ============================================
# 🔗 DATABASE CONNECTION
# ============================================
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Connection Error: Check Supabase Credentials.")
    st.stop()

# ============================================
# 📊 DATA AGGREGATION ENGINE
# ============================================
@st.cache_data(ttl=60) # Refreshes every minute
def fetch_financials():
    try:
        p_res = supabase.table("properties").select("*").execute()
        u_res = supabase.table("profit_usage").select("*").execute()
        prof_res = supabase.table("property_profits").select("*").execute()
        
        df_p = pd.DataFrame(p_res.data)
        df_u = pd.DataFrame(u_res.data)
        df_profits = pd.DataFrame(prof_res.data)

        # Skeleton initialization for empty DB
        if df_p.empty:
            df_p = pd.DataFrame(columns=["status", "buying_price", "construction_cost", "total_profit", "property_name"])
        if df_u.empty:
            df_u = pd.DataFrame(columns=["amount"])
            
        # Clean data types
        for col in ["buying_price", "construction_cost", "total_profit"]:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        
        return df_p, df_u, df_profits
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_p, df_u, df_profits = fetch_financials()

# ============================================
# 🏛️ EXECUTIVE DASHBOARD
# ============================================
st.title("🏛️ Executive Real Estate Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- METRIC LAYER ---
if not df_p.empty:
    # Calculations
    unsold = df_p[df_p["status"] == "Unsold"]
    locked_capital = unsold["buying_price"].sum() + unsold["construction_cost"].sum()
    
    total_net_profit = df_p["total_profit"].sum()
    expenses = pd.to_numeric(df_u["amount"], errors='coerce').sum() if not df_u.empty else 0
    available_cash = total_net_profit - expenses
    
    business_value = locked_capital + available_cash

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inventory Value", f"PKR {locked_capital:,.0f}", help="Total cash currently invested in unsold houses")
    m2.metric("Available Profit", f"PKR {available_cash:,.0f}", help="Net profit remaining after expenses")
    m3.metric("Company Net Worth", f"PKR {business_value:,.0f}", help="Total Assets + Cash")
    
    performance = (total_net_profit / (df_p["buying_price"].sum() + 1)) * 100
    m4.metric("ROI Performance", f"{performance:.1f}%", delta="Business Health")

st.divider()

# --- ANALYTICS TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Analytics", "📑 Records", "👥 Partner Shares", "💸 Cash Flow"])

with tab1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Inventory Distribution")
        if not df_p.empty:
            # Simple Bar Chart of Property Values
            chart_data = df_p[df_p["status"] == "Unsold"][["property_name", "buying_price"]]
            st.bar_chart(chart_data.set_index("property_name"))
    with col_r:
        st.subheader("Market Summary")
        st.write(f"**Total Properties:** {len(df_p)}")
        st.write(f"**Active Projects:** {len(df_p[df_p['status'] == 'Unsold'])}")
        st.write(f"**Completed Sales:** {len(df_p[df_p['status'] == 'Sold'])}")

with tab2:
    st.subheader("Historical Property Ledger")
    st.dataframe(df_p, use_container_width=True)
    if is_editor:
        st.info("💡 Switch to 'Add Property' or 'Sell Property' in the sidebar to modify data.")

with tab3:
    st.subheader("Partner Profit Distributions")
    if not df_profits.empty:
        p1, p2, p3 = st.columns(3)
        p1.metric("Jaffar (50%)", f"PKR {df_profits['jaffar_profit'].sum():,.0f}")
        p2.metric("Tehseen (40%)", f"PKR {df_profits['tehseen_profit'].sum():,.0f}")
        p3.metric("Dealer (10%)", f"PKR {df_profits['dealer_profit'].sum():,.0f}")
        st.table(df_profits[["property_name", "total_profit", "jaffar_profit", "tehseen_profit"]])
    else:
        st.write("No profit data available.")

with tab4:
    st.subheader("Expense & Withdrawal Log")
    if not df_u.empty:
        st.dataframe(df_u, use_container_width=True)
    else:
        st.write("No expenses recorded.")

# ============================================
# ⚙️ MANAGEMENT SIDEBAR
# ============================================
if is_editor:
    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Management Tools")
    action = st.sidebar.selectbox("Action", ["Add Property", "Mark as Sold", "Record Expense"])
    
    if action == "Add Property":
        with st.sidebar.form("new_prop"):
            name = st.text_input("Property Name")
            buy = st.number_input("Buying Price", min_value=0)
            const = st.number_input("Construction Cost", min_value=0)
            if st.form_submit_button("Submit"):
                supabase.table("properties").insert({
                    "property_name": name, "buying_price": buy, 
                    "construction_cost": const, "status": "Unsold"
                }).execute()
                st.rerun()

    elif action == "Mark as Sold":
        unsold_list = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
        if unsold_list:
            sel = st.sidebar.selectbox("Property", unsold_list)
            price = st.sidebar.number_input("Sale Price", min_value=0)
            if st.sidebar.button("Finalize Sale"):
                p_data = df_p[df_p["property_name"] == sel].iloc[0]
                profit = price - (p_data["buying_price"] + p_data["construction_cost"])
                # Update tables
                supabase.table("properties").update({"status":"Sold", "total_profit": profit, "selling_price": price, "selling_date": str(datetime.now())}).eq("id", p_data["id"]).execute()
                supabase.table("property_profits").insert({"property_name": sel, "total_profit": profit, "jaffar_profit": profit*0.5, "tehseen_profit": profit*0.4, "dealer_profit": profit*0.1}).execute()
                st.rerun()
