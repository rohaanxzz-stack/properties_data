import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🛡️ ACCESS CONTROL (2 Editors vs Viewers)
# ============================================
ADMIN_PASSWORDS = ["Admin1", "Admin2"] 

def check_access():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    with st.sidebar:
        st.title("🔐 Access Control")
        if not st.session_state.authenticated:
            pwd = st.text_input("Enter Admin Password", type="password")
            if st.button("Unlock Editor Mode"):
                if pwd in ADMIN_PASSWORDS:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Access Denied")
        else:
            st.success("🔓 Editor Mode Active")
            if st.button("Switch to Read-Only"):
                st.session_state.authenticated = False
                st.rerun()

check_access()
is_editor = st.session_state.authenticated

# ============================================
# 🔗 SUPABASE CONNECTION
# ============================================
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception:
    st.error("Supabase credentials missing! Check Streamlit Secrets.")
    st.stop()

# ============================================
# 📊 DATA LOADING & INITIALIZATION
# ============================================
def load_all_data():
    try:
        p_res = supabase.table("properties").select("*").execute()
        u_res = supabase.table("profit_usage").select("*").execute()
        prof_res = supabase.table("property_profits").select("*").execute()
        
        df_p = pd.DataFrame(p_res.data)
        df_u = pd.DataFrame(u_res.data)
        df_profits = pd.DataFrame(prof_res.data)

        # Force column creation if DB is empty to prevent KeyError
        if df_p.empty:
            df_p = pd.DataFrame(columns=["id", "property_name", "buying_price", "construction_cost", "status", "total_profit", "purchase_date"])
        if df_u.empty:
            df_u = pd.DataFrame(columns=["amount", "title"])
            
        # Clean numeric data
        for col in ["buying_price", "construction_cost", "total_profit"]:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        
        return df_p, df_u, df_profits
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_p, df_u, df_profits = load_all_data()

# ============================================
# 🏗️ VISUAL DASHBOARD SECTION
# ============================================
st.title("🏛️ EstateLedger Pro")
st.subheader("Financial Overview")

if not df_p.empty:
    # Logic for calculations
    unsold = df_p[df_p["status"] == "Unsold"]
    capital_locked = unsold["buying_price"].sum() + unsold["construction_cost"].sum()
    
    total_earned_profit = df_p["total_profit"].sum()
    total_spent_profit = pd.to_numeric(df_u["amount"], errors='coerce').sum() if not df_u.empty else 0
    
    cash_balance = total_earned_profit - total_spent_profit
    net_worth = capital_locked + cash_balance

    # Dashboard Cards
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Capital in Houses", f"PKR {capital_locked:,.0f}")
    col2.metric("Profit Cash (Avail)", f"PKR {cash_balance:,.0f}")
    col3.metric("Net Worth", f"PKR {net_worth:,.0f}")
    
    # Status Indicator
    if total_earned_profit > 0:
        col4.success("🟢 IN PROFIT")
    elif total_earned_profit < 0:
        col4.error("🔴 IN LOSS")
    else:
        col4.info("⚪ NO SALES YET")
        
    st.divider()

# ============================================
# 📂 MENU NAVIGATION
# ============================================
menu = st.sidebar.radio("Navigation", ["Active Inventory", "Sold Records", "Partner Ledger", "Expense Tracker"])

# --- VIEW 1: ACTIVE INVENTORY ---
if menu == "Active Inventory":
    st.header("🏠 Unsold Properties")
    if is_editor:
        with st.expander("➕ Add New Purchase"):
            with st.form("add"):
                name = st.text_input("Property Name")
                b_price = st.number_input("Buying Price", min_value=0.0)
                c_price = st.number_input("Construction Cost", min_value=0.0)
                if st.form_submit_button("Save"):
                    supabase.table("properties").insert({
                        "property_name": name, "buying_price": b_price, 
                        "construction_cost": c_price, "status": "Unsold"
                    }).execute()
                    st.rerun()

    active = df_p[df_p["status"] == "Unsold"]
    st.dataframe(active[["purchase_date", "property_name", "buying_price", "construction_cost"]], use_container_width=True)

# --- VIEW 2: SOLD RECORDS ---
elif menu == "Sold Records":
    st.header("💰 History of Sales")
    if is_editor:
        with st.expander("🤝 Record a Sale"):
            unsold_list = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
            if unsold_list:
                sel = st.selectbox("Select House", unsold_list)
                price = st.number_input("Sold Price", min_value=0.0)
                if st.button("Confirm Sale"):
                    p_data = df_p[df_p["property_name"] == sel].iloc[0]
                    profit = price - (p_data["buying_price"] + p_data["construction_cost"])
                    
                    # Update DB
                    supabase.table("properties").update({
                        "status": "Sold", "selling_price": price, 
                        "total_profit": profit, "selling_date": str(datetime.now())
                    }).eq("id", p_data["id"]).execute()
                    
                    # Partner Split (50/40/10)
                    supabase.table("property_profits").insert({
                        "property_name": sel, "total_profit": profit,
                        "jaffar_profit": profit * 0.5, "tehseen_profit": profit * 0.4, "dealer_profit": profit * 0.1
                    }).execute()
                    st.rerun()

    sold = df_p[df_p["status"] == "Sold"]
    st.dataframe(sold[["property_name", "purchase_date", "selling_date", "total_profit"]], use_container_width=True)

# --- VIEW 3: PARTNER LEDGER ---
elif menu == "Partner Ledger":
    st.header("👥 Partner Shares")
    if not df_profits.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jaffar (50%)", f"PKR {df_profits['jaffar_profit'].sum():,.0f}")
        c2.metric("Tehseen (40%)", f"PKR {df_profits['tehseen_profit'].sum():,.0f}")
        c3.metric("Dealer (10%)", f"PKR {df_profits['dealer_profit'].sum():,.0f}")
        st.dataframe(df_profits, use_container_width=True)

# --- VIEW 4: EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.header("💸 Profit Withdrawals")
    if is_editor:
        with st.form("usage"):
            t = st.text_input("Expense Title")
            a = st.number_input("Amount", min_value=0.0)
            if st.form_submit_button("Record Expense"):
                supabase.table("profit_usage").insert({"title": t, "amount": a}).execute()
                st.rerun()
    st.dataframe(df_u, use_container_width=True)
