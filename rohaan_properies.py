import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🛡️ ACCESS CONTROL (2 Editors vs Viewers)
# ============================================
# Only these passwords allow "Edit" access
ADMIN_PASSWORDS = ["Jaffar123", "Tehseen456"] 

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
    st.error("Supabase credentials missing! Set them in Streamlit Cloud Secrets.")
    st.stop()

# ============================================
# 📊 DATA LOADING & CALCULATIONS
# ============================================
def load_all_data():
    p_res = supabase.table("properties").select("*").execute()
    u_res = supabase.table("profit_usage").select("*").execute()
    prof_res = supabase.table("property_profits").select("*").execute()
    return pd.DataFrame(p_res.data), pd.DataFrame(u_res.data), pd.DataFrame(prof_res.data)

df_p, df_u, df_profits = load_all_data()

st.title("🏛️ EstateLedger")
st.caption("Official Partner Income & Property Ledger")

if not df_p.empty:
    # 1. Capital Locked (Inventory Cost)
    unsold = df_p[df_p["status"] == "Unsold"]
    capital_locked = unsold["buying_price"].sum() + unsold["construction_cost"].sum()
    
    # 2. Total Earned Profit (After Sales)
    total_earned = df_p["total_profit"].sum()
    
    # 3. Expenses (Profit used)
    total_spent = df_u["amount"].sum() if not df_u.empty else 0
    
    # 4. Net Worth & Cash
    cash_in_hand = total_earned - total_spent
    current_net_worth = capital_locked + cash_in_hand

    # Dashboard Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Capital in Houses", f"PKR {capital_locked:,.0f}")
    m2.metric("Cash Balance (Profit)", f"PKR {cash_in_hand:,.0f}")
    m3.metric("Total Net Worth", f"PKR {current_net_worth:,.0f}")
    st.divider()

# ============================================
# 📂 NAVIGATION
# ============================================
menu = st.sidebar.radio("Go To", ["Active Inventory", "Sold Records", "Partner Profit Shares", "Expense Tracker"])

# --- VIEW 1: ACTIVE INVENTORY ---
if menu == "Active Inventory":
    st.header("🏠 Current Property Inventory")
    
    if is_editor:
        with st.expander("➕ Add New Purchase"):
            with st.form("add_prop"):
                name = st.text_input("Property/Project Name")
                loc = st.text_input("Location")
                dlr = st.text_input("Sourced from Dealer")
                b_price = st.number_input("Buying Price", min_value=0.0)
                c_price = st.number_input("Construction/renovation Cost", min_value=0.0)
                if st.form_submit_button("Record Purchase"):
                    # purchase_date is handled automatically by SQL NOW()
                    supabase.table("properties").insert({
                        "property_name": name, "location": loc, "dealer_name": dlr,
                        "buying_price": b_price, "construction_cost": c_price, "status": "Unsold"
                    }).execute()
                    st.rerun()

    if not df_p.empty:
        active = df_p[df_p["status"] == "Unsold"][["purchase_date", "property_name", "location", "buying_price", "construction_cost"]]
        st.dataframe(active, use_container_width=True)

# --- VIEW 2: SOLD RECORDS ---
elif menu == "Sold Records":
    st.header("💰 History of Sold Properties")
    
    if is_editor:
        with st.expander("🤝 Finalize a Sale"):
            unsold_list = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
            if unsold_list:
                sel_p = st.selectbox("Select Property", unsold_list)
                final_s = st.number_input("Final Selling Price", min_value=0.0)
                if st.button("Confirm Sale & Calculate Profits"):
                    # Get data of the selected property
                    p_data = df_p[df_p["property_name"] == sel_p].iloc[0]
                    total_inv = p_data["buying_price"] + p_data["construction_cost"]
                    net_profit = final_s - total_inv
                    
                    # Update Main Table
                    supabase.table("properties").update({
                        "status": "Sold", "selling_price": final_s, 
                        "selling_date": str(datetime.now()), "total_profit": net_profit
                    }).eq("id", p_data["id"]).execute()
                    
                    # Distribute to Partners Table
                    supabase.table("property_profits").insert({
                        "property_id": p_data["id"], "property_name": sel_p,
                        "total_profit": net_profit,
                        "jaffar_profit": net_profit * 0.50,
                        "tehseen_profit": net_profit * 0.40,
                        "dealer_profit": net_profit * 0.10
                    }).execute()
                    st.rerun()
            else:
                st.write("No unsold properties to sell.")

    if not df_p.empty:
        sold = df_p[df_p["status"] == "Sold"][["property_name", "purchase_date", "selling_date", "total_profit"]]
        st.dataframe(sold, use_container_width=True)

# --- VIEW 3: PARTNER SHARES ---
elif menu == "Partner Profit Shares":
    st.header("👥 Individual Partner Ledgers")
    
    if not df_profits.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jaffar (50%)", f"PKR {df_profits['jaffar_profit'].sum():,.0f}")
        c2.metric("Tehseen (40%)", f"PKR {df_profits['tehseen_profit'].sum():,.0f}")
        c3.metric("Dealer Pool (10%)", f"PKR {df_profits['dealer_profit'].sum():,.0f}")
        
        st.subheader("Detailed Breakdown per House")
        st.table(df_profits[["property_name", "jaffar_profit", "tehseen_profit", "dealer_profit"]])
    else:
        st.info("No profits recorded yet.")

# --- VIEW 4: EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.header("💸 Where the Profit Went")
    if is_editor:
        with st.form("usage_form"):
            t = st.text_input("Expense Title (e.g., Office Rent, New Plot Deposit)")
            a = st.number_input("Amount", min_value=0.0)
            if st.form_submit_button("Log Expense"):
                supabase.table("profit_usage").insert({"title": t, "amount": a}).execute()
                st.rerun()

    if not df_u.empty:
        st.dataframe(df_u[["created_at", "title", "amount"]], use_container_width=True)
