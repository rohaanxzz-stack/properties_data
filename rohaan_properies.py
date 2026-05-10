import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🛡️ ACCESS CONTROL
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
    st.error("Supabase credentials missing in Secrets!")
    st.stop()

# ============================================
# 📊 DATA LOADING (Safe against KeyErrors)
# ============================================
def load_all_data():
    try:
        p_res = supabase.table("properties").select("*").execute()
        u_res = supabase.table("profit_usage").select("*").execute()
        prof_res = supabase.table("property_profits").select("*").execute()
        
        df_p = pd.DataFrame(p_res.data)
        df_u = pd.DataFrame(u_res.data)
        df_profits = pd.DataFrame(prof_res.data)

        # FIX FOR KEYERROR: If table is empty, initialize columns manually
        if df_p.empty:
            df_p = pd.DataFrame(columns=[
                "id", "property_name", "location", "dealer_name", 
                "buying_price", "construction_cost", "status", 
                "total_profit", "purchase_date", "selling_price"
            ])
        if df_u.empty:
            df_u = pd.DataFrame(columns=["id", "title", "amount", "created_at"])
        if df_profits.empty:
            df_profits = pd.DataFrame(columns=[
                "property_name", "total_profit", "jaffar_profit", 
                "tehseen_profit", "dealer_profit"
            ])
            
        return df_p, df_u, df_profits
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_p, df_u, df_profits = load_all_data()

st.title("🏛️ EstateLedger")
st.caption("Official Partner Income & Property Ledger")

# ============================================
# 📈 FINANCIAL DASHBOARD
# ============================================
if not df_p.empty:
    # Ensure numeric types
    df_p["buying_price"] = pd.to_numeric(df_p["buying_price"], errors='coerce').fillna(0)
    df_p["construction_cost"] = pd.to_numeric(df_p["construction_cost"], errors='coerce').fillna(0)
    df_p["total_profit"] = pd.to_numeric(df_p["total_profit"], errors='coerce').fillna(0)

    unsold = df_p[df_p["status"] == "Unsold"]
    capital_locked = unsold["buying_price"].sum() + unsold["construction_cost"].sum()
    total_earned = df_p["total_profit"].sum()
    total_spent = pd.to_numeric(df_u["amount"], errors='coerce').sum() if not df_u.empty else 0
    
    cash_in_hand = total_earned - total_spent
    current_net_worth = capital_locked + cash_in_hand

    m1, m2, m3 = st.columns(3)
    m1.metric("Capital in Houses", f"PKR {capital_locked:,.0f}")
    m2.metric("Cash Balance (Profit)", f"PKR {cash_in_hand:,.0f}")
    m3.metric("Total Net Worth", f"PKR {current_net_worth:,.0f}")
    st.divider()

# ============================================
# 📂 NAVIGATION
# ============================================
menu = st.sidebar.radio("Go To", ["Active Inventory", "Sold Records", "Partner Profit Shares", "Expense Tracker"])

# --- ACTIVE INVENTORY ---
if menu == "Active Inventory":
    st.header("🏠 Current Property Inventory")
    if is_editor:
        with st.expander("➕ Add New Purchase"):
            with st.form("add_prop"):
                name = st.text_input("Property Name")
                loc = st.text_input("Location")
                dlr = st.text_input("Dealer Name")
                b_price = st.number_input("Buying Price", min_value=0.0)
                c_price = st.number_input("Construction Cost", min_value=0.0)
                if st.form_submit_button("Record Purchase"):
                    supabase.table("properties").insert({
                        "property_name": name, "location": loc, "dealer_name": dlr,
                        "buying_price": b_price, "construction_cost": c_price, "status": "Unsold"
                    }).execute()
                    st.rerun()

    active = df_p[df_p["status"] == "Unsold"]
    st.dataframe(active[["purchase_date", "property_name", "location", "buying_price", "construction_cost"]], use_container_width=True)

# --- SOLD RECORDS ---
elif menu == "Sold Records":
    st.header("💰 Sales History")
    if is_editor:
        with st.expander("🤝 Finalize a Sale"):
            unsold_list = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
            if unsold_list:
                sel_p = st.selectbox("Select Property", unsold_list)
                final_s = st.number_input("Final Selling Price", min_value=0.0)
                if st.button("Confirm Sale"):
                    p_data = df_p[df_p["property_name"] == sel_p].iloc[0]
                    total_inv = p_data["buying_price"] + p_data["construction_cost"]
                    net_profit = final_s - total_inv
                    
                    supabase.table("properties").update({
                        "status": "Sold", "selling_price": final_s, 
                        "selling_date": str(datetime.now()), "total_profit": net_profit
                    }).eq("id", p_data["id"]).execute()
                    
                    supabase.table("property_profits").insert({
                        "property_id": p_data["id"], "property_name": sel_p,
                        "total_profit": net_profit,
                        "jaffar_profit": net_profit * 0.50,
                        "tehseen_profit": net_profit * 0.40,
                        "dealer_profit": net_profit * 0.10
                    }).execute()
                    st.rerun()
            else:
                st.info("No unsold properties available.")

    sold = df_p[df_p["status"] == "Sold"]
    st.dataframe(sold[["property_name", "purchase_date", "selling_date", "total_profit"]], use_container_width=True)

# --- PARTNER SHARES ---
elif menu == "Partner Profit Shares":
    st.header("👥 Partner Shares")
    if not df_profits.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jaffar (50%)", f"PKR {df_profits['jaffar_profit'].sum():,.0f}")
        c2.metric("Tehseen (40%)", f"PKR {df_profits['tehseen_profit'].sum():,.0f}")
        c3.metric("Dealer (10%)", f"PKR {df_profits['dealer_profit'].sum():,.0f}")
        st.dataframe(df_profits, use_container_width=True)

# --- EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.header("💸 Profit Usage")
    if is_editor:
        with st.form("usage"):
            t = st.text_input("Expense Title")
            a = st.number_input("Amount", min_value=0.0)
            if st.form_submit_button("Log Expense"):
                supabase.table("profit_usage").insert({"title": t, "amount": a}).execute()
                st.rerun()
    st.dataframe(df_u, use_container_width=True)
