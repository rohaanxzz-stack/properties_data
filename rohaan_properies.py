import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# 🛡️ ACCESS CONTROL (2 Editors vs Viewers)
# ============================================
ADMIN_PASSWORDS = ["Admin1", "Admin2"]  # Replace with your actual passwords

def check_access():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    with st.sidebar:
        st.title("🔑 Access Control")
        if not st.session_state.authenticated:
            pwd = st.text_input("Enter Admin Password", type="password")
            if st.button("Unlock Editor Mode"):
                if pwd in ADMIN_PASSWORDS:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Password")
        else:
            st.success("🔓 Editor Mode Active")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.rerun()

check_access()
is_editor = st.session_state.authenticated

# ============================================
# 🔗 SUPABASE CONNECTION
# ============================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Missing Supabase Secrets! Please check your settings.")
    st.stop()

# ============================================
# 📊 CALCULATIONS & DASHBOARD
# ============================================
def load_data():
    prop_res = supabase.table("properties").select("*").execute()
    usage_res = supabase.table("profit_usage").select("*").execute()
    return pd.DataFrame(prop_res.data), pd.DataFrame(usage_res.data)

df_p, df_u = load_data()

st.title("🏠 EstateLedger")
st.caption("Real Estate Historical Record & Profit Management")

if not df_p.empty:
    # Capital Locked (Cost of Unsold Properties)
    unsold = df_p[df_p["status"] == "Unsold"]
    capital_locked = unsold["buying_price"].sum() + unsold["construction_cost"].sum()
    
    # Total Profit Earned from Sales
    total_earned_profit = df_p["total_profit"].sum()
    
    # Total Profit Spent/Used
    total_spent = df_u["amount"].sum() if not df_u.empty else 0
    
    # Financial Standing
    cash_in_hand = total_earned_profit - total_spent
    current_net_worth = capital_locked + cash_in_hand

    col1, col2, col3 = st.columns(3)
    col1.metric("Capital in Houses", f"PKR {capital_locked:,.0f}")
    col2.metric("Cash Balance (Profit)", f"PKR {cash_in_hand:,.0f}")
    col3.metric("Current Net Worth", f"PKR {current_net_worth:,.0f}")
    st.divider()

# ============================================
# 📂 MENU NAVIGATION
# ============================================
menu = st.sidebar.selectbox(
    "Select Menu",
    ["Active Inventory", "Sold Records", "Partner Profits", "Profit Usage"]
)

# --- VIEW 1: ACTIVE INVENTORY ---
if menu == "Active Inventory":
    st.header("🏢 Current Property Inventory")
    
    if is_editor:
        with st.expander("➕ Add New Purchase"):
            with st.form("add_property"):
                name = st.text_input("Property Name")
                loc = st.text_input("Location")
                dlr = st.text_input("Dealer Name")
                b_price = st.number_input("Buying Price", min_value=0.0)
                c_price = st.number_input("Construction Cost", min_value=0.0)
                if st.form_submit_button("Record Purchase"):
                    # Note: Purchase Date is handled automatically by SQL NOW()
                    supabase.table("properties").insert({
                        "property_name": name, "location": loc, "dealer_name": dlr,
                        "buying_price": b_price, "construction_cost": c_price, "status": "Unsold"
                    }).execute()
                    st.success(f"Added {name}")
                    st.rerun()

    if not df_p.empty:
        active_view = df_p[df_p["status"] == "Unsold"][["purchase_date", "property_name", "location", "buying_price", "construction_cost"]]
        st.dataframe(active_view, use_container_width=True)

# --- VIEW 2: SOLD RECORDS ---
elif menu == "Sold Records":
    st.header("💰 Closed Deals & Sales History")
    
    if is_editor:
        with st.expander("🤝 Mark Property as Sold"):
            unsold_names = df_p[df_p["status"] == "Unsold"]["property_name"].tolist()
            if unsold_names:
                sel_p = st.selectbox("Select Property", unsold_names)
                sell_p = st.number_input("Final Selling Price", min_value=0.0)
                
                if st.button("Finalize Sale"):
                    target = df_p[df_p["property_name"] == sel_p].iloc[0]
                    total_inv = target["buying_price"] + target["construction_cost"]
                    net_profit = sell_p - total_inv
                    
                    # Update Property
                    supabase.table("properties").update({
                        "status": "Sold", "selling_price": sell_p, 
                        "selling_date": str(datetime.now()), "total_profit": net_profit
                    }).eq("id", target["id"]).execute()
                    
                    # Distribute to Partners (50/40/10)
                    supabase.table("property_profits").insert({
                        "property_id": target["id"], "property_name": sel_p,
                        "total_profit": net_profit,
                        "jaffar_profit": net_profit * 0.50,
                        "tehseen_profit": net_profit * 0.40,
                        "dealer_profit": net_profit * 0.10
                    }).execute()
                    st.success("Sale Recorded!")
                    st.rerun()
            else:
                st.info("No unsold properties available.")

    if not df_p.empty:
        sold_view = df_p[df_p["status"] == "Sold"][["property_name", "purchase_date", "selling_date", "total_profit"]]
        st.dataframe(sold_view, use_container_width=True)

# --- VIEW 3: PARTNER PROFITS ---
elif menu == "Partner Profits":
    st.header("👥 Partner Income Split")
    prof_res = supabase.table("property_profits").select("*").execute()
    
    if prof_res.data:
        pdf = pd.DataFrame(prof_res.data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Jaffar (50%)", f"PKR {pdf['jaffar_profit'].sum():,.0f}")
        col2.metric("Tehseen (40%)", f"PKR {pdf['tehseen_profit'].sum():,.0f}")
        col3.metric("Dealer (10%)", f"PKR {pdf['dealer_profit'].sum():,.0f}")
        
        st.divider()
        st.subheader("Profit Distribution Table")
        st.dataframe(pdf[["property_name", "total_profit", "jaffar_profit", "tehseen_profit", "dealer_profit"]], use_container_width=True)
    else:
        st.info("No profits to display yet.")

# --- VIEW 4: PROFIT USAGE ---
elif menu == "Profit Usage":
    st.header("💸 Record Profit Usage/Expenses")
    
    if is_editor:
        with st.form("usage_form"):
            title = st.text_input("Title (e.g., Office Rent, Partner Withdrawal)")
            amt = st.number_input("Amount", min_value=0.0)
            desc = st.text_area("Description")
            if st.form_submit_button("Log Expense"):
                supabase.table("profit_usage").insert({"title": title, "amount": amt, "description": desc}).execute()
                st.rerun()

    if not df_u.empty:
        st.dataframe(df_u[["created_at", "title", "amount", "description"]], use_container_width=True)
