import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🖥️ PAGE CONFIGURATION
# ============================================
st.set_page_config(page_title="EstateLedger | Command Center", layout="wide", page_icon="🏛️")

# Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# 🔐 SECURE ACCESS CONTROL
# ============================================
ADMIN_PASSWORDS = ["Admin123", "Partner456"] 

def check_access():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    with st.sidebar:
        st.title("🔑 Partner Portal")
        if not st.session_state.authenticated:
            pwd = st.text_input("Enter Admin Key", type="password")
            if st.button("Unlock Management"):
                if pwd in ADMIN_PASSWORDS:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Key")
        else:
            st.success("Editor Access Active")
            if st.button("Lock Console"):
                st.session_state.authenticated = False
                st.rerun()

check_access()
is_editor = st.session_state.authenticated

# ============================================
# 🔗 DATABASE CONNECTION
# ============================================
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Missing Supabase Secrets configuration.")
    st.stop()

# ============================================
# 📊 CRASH-PROOF DATA ENGINE
# ============================================
@st.cache_data(ttl=30)
def fetch_all_data():
    try:
        # Fetching raw data
        p_raw = supabase.table("properties").select("*").execute()
        u_raw = supabase.table("profit_usage").select("*").execute()
        prof_raw = supabase.table("property_profits").select("*").execute()
        
        df_p = pd.DataFrame(p_raw.data)
        df_u = pd.DataFrame(u_raw.data)
        df_prof = pd.DataFrame(prof_raw.data)

        # 🛡️ DEFENSIVE COLUMN MAPPING (Prevents KeyErrors)
        p_cols = ["id", "property_name", "location", "buying_price", "construction_cost", "status", "total_profit", "purchase_date", "selling_date"]
        u_cols = ["id", "title", "amount", "created_at"]
        prof_cols = ["property_name", "total_profit", "jaffar_profit", "tehseen_profit", "dealer_profit"]

        # Ensure df_p has all columns
        if df_p.empty:
            df_p = pd.DataFrame(columns=p_cols)
        else:
            for col in p_cols:
                if col not in df_p.columns: df_p[col] = None
        
        # Ensure df_u has all columns
        if df_u.empty:
            df_u = pd.DataFrame(columns=u_cols)
        else:
            for col in u_cols:
                if col not in df_u.columns: df_u[col] = 0

        # Ensure df_prof has all columns
        if df_prof.empty:
            df_prof = pd.DataFrame(columns=prof_cols)
        else:
            for col in prof_cols:
                if col not in df_prof.columns: df_prof[col] = 0

        # Force numeric types for math
        num_fields = ["buying_price", "construction_cost", "total_profit", "amount", "jaffar_profit", "tehseen_profit", "dealer_profit"]
        for df in [df_p, df_u, df_prof]:
            for col in df.columns:
                if col in num_fields:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df_p, df_u, df_prof
    except Exception as e:
        st.error(f"Sync Failure: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_p, df_u, df_prof = fetch_all_data()

# ============================================
# 🏛️ PROFESSIONAL DASHBOARD LAYOUT
# ============================================
st.title("🏛️ EstateLedger Executive")
st.caption(f"Real-time Financial Position | {datetime.now().strftime('%d %B %Y')}")

# --- TOP METRICS BAR ---
if not df_p.empty:
    # Logic Calculations
    active_inv = df_p[df_p["status"] == "Unsold"]
    locked_cap = active_inv["buying_price"].sum() + active_inv["construction_cost"].sum()
    
    total_gains = df_p["total_profit"].sum()
    total_spent = df_u["amount"].sum()
    cash_on_hand = total_gains - total_spent
    
    net_worth = locked_cap + cash_on_hand

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Locked Capital", f"PKR {locked_cap:,.0f}", help="Cash invested in unsold properties")
    c2.metric("Available Profit", f"PKR {cash_on_hand:,.0f}", help="Total profit minus expenses")
    c3.metric("Net Business Value", f"PKR {net_worth:,.0f}", help="Combined value of inventory and cash")
    
    roi = (total_gains / (df_p["buying_price"].sum() + 1)) * 100
    c4.metric("ROI Efficiency", f"{roi:.1f}%", delta="Business Health")

st.divider()

# --- ANALYTICS & RECORDS TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance", "📁 Property Ledger", "👥 Partner Shares", "💸 Expense Log"])

with tab1:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Inventory Distribution")
        if not df_p[df_p["status"] == "Unsold"].empty:
            chart_data = df_p[df_p["status"] == "Unsold"][["property_name", "buying_price"]]
            st.bar_chart(chart_data.set_index("property_name"))
        else:
            st.info("No active inventory to graph.")
    
    with col_b:
        st.subheader("Deal Summary")
        st.write(f"**Properties Owned:** {len(df_p[df_p['status'] == 'Unsold'])}")
        st.write(f"**Deals Closed:** {len(df_p[df_p['status'] == 'Sold'])}")
        st.write(f"**Total Portfolio Items:** {len(df_p)}")

with tab2:
    st.subheader("Master Property Record")
    st.dataframe(df_p, use_container_width=True)

with tab3:
    st.subheader("Partner Profit Distributions")
    if not df_prof.empty:
        p1, p2, p3 = st.columns(3)
        p1.metric("Jaffar (50%)", f"PKR {df_prof['jaffar_profit'].sum():,.0f}")
        p2.metric("Tehseen (40%)", f"PKR {df_prof['tehseen_profit'].sum():,.0f}")
        p3.metric("Dealer Pool (10%)", f"PKR {df_prof['dealer_profit'].sum():,.0f}")
        st.divider()
        st.table(df_prof)
    else:
        st.info("No profits recorded yet.")

with tab4:
    st.subheader("Expense & Withdrawal Records")
    st.dataframe(df_u, use_container_width=True)

# ============================================
# ⚙️ MANAGEMENT CONSOLE (Sidebar Only)
# ============================================
if is_editor:
    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Admin Actions")
    task = st.sidebar.selectbox("Choose Task", ["Register Purchase", "Complete a Sale", "Log Expense"])
    
    if task == "Register Purchase":
        with st.sidebar.form("add_p"):
            n = st.text_input("Property Name")
            l = st.text_input("Location")
            b = st.number_input("Buying Price", min_value=0)
            c = st.number_input("Construction Cost", min_value=0)
            if st.form_submit_button("Save Purchase"):
                supabase.table("properties").insert({
                    "property_name": n, "location": l, "buying_price": b, 
                    "construction_cost": c, "status": "Unsold"
                }).execute()
                st.rerun()

    elif task == "Complete a Sale":
        active_list = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
        if active_list:
            target = st.sidebar.selectbox("Select Property", active_list)
            price = st.sidebar.number_input("Sale Price", min_value=0)
            if st.sidebar.button("Finalize Deal"):
                data = df_p[df_p["property_name"] == target].iloc[0]
                profit = price - (data["buying_price"] + data["construction_cost"])
                
                # Update Property
                supabase.table("properties").update({
                    "status": "Sold", "selling_price": price, 
                    "total_profit": profit, "selling_date": str(datetime.now())
                }).eq("id", data["id"]).execute()
                
                # Split Profits
                supabase.table("property_profits").insert({
                    "property_name": target, "total_profit": profit,
                    "jaffar_profit": profit * 0.5, "tehseen_profit": profit * 0.4, "dealer_profit": profit * 0.1
                }).execute()
                st.rerun()
        else:
            st.sidebar.warning("No properties to sell.")

    elif task == "Log Expense":
        with st.sidebar.form("exp"):
            t = st.text_input("Expense Title")
            a = st.number_input("Amount", min_value=0)
            if st.form_submit_button("Log Withdrawal"):
                supabase.table("profit_usage").insert({"title": t, "amount": a}).execute()
                st.rerun()
