import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="EstateLedger",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 EstateLedger")
st.caption("Real Estate Record Management System")

# ============================================
# SUPABASE CONNECTION (Safe Handling)
# ============================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Missing Supabase Secrets! Please check your secrets.toml or Streamlit Cloud settings.")
    st.stop()

# ============================================
# SIDEBAR MENU
# ============================================
menu = st.sidebar.selectbox(
    "Select Menu",
    ["Dashboard", "Add Property", "Sell Property", "Property Records", "Partner Profits", "Profit Usage"]
)

# ============================================
# DASHBOARD
# ============================================
if menu == "Dashboard":
    st.header("📊 Dashboard")

    response = supabase.table("properties").select("*").execute()
    properties = response.data

    if properties:
        df = pd.DataFrame(properties)
        
        # Ensure numeric columns are treated as floats to prevent math errors
        df["buying_price"] = pd.to_numeric(df["buying_price"], errors='coerce').fillna(0)
        df["construction_cost"] = pd.to_numeric(df["construction_cost"], errors='coerce').fillna(0)
        df["total_profit"] = pd.to_numeric(df["total_profit"], errors='coerce').fillna(0)

        total_investment = df["buying_price"].sum() + df["construction_cost"].sum()
        total_profit = df["total_profit"].sum()
        net_worth = total_investment + total_profit

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Investment", f"PKR {total_investment:,.0f}")
        col2.metric("Total Profit", f"PKR {total_profit:,.0f}")
        col3.metric("Net Worth", f"PKR {net_worth:,.0f}")
        col4.metric("Status", "Profit" if total_profit >= 0 else "Loss")

        st.divider()
        st.subheader("Quick View: Current Inventory")
        st.dataframe(df[["property_name", "location", "status", "total_profit"]], use_container_width=True)
    else:
        st.info("No properties found. Go to 'Add Property' to begin.")

# ============================================
# ADD PROPERTY
# ============================================
elif menu == "Add Property":
    st.header("➕ Add Property")
    
    with st.form("property_form"):
        col1, col2 = st.columns(2)
        with col1:
            property_name = st.text_input("Property Name")
            location = st.text_input("Location")
            dealer_name = st.text_input("Dealer Name")
        with col2:
            buying_price = st.number_input("Buying Price", min_value=0.0, step=1000.0)
            construction_cost = st.number_input("Construction Cost", min_value=0.0, step=1000.0)
            purchase_date = st.date_input("Purchase Date", datetime.now())

        notes = st.text_area("Notes")
        submit = st.form_submit_button("Save Property")

        if submit:
            if property_name and location:
                data = {
                    "property_name": property_name,
                    "location": location,
                    "buying_price": buying_price,
                    "construction_cost": construction_cost,
                    "dealer_name": dealer_name,
                    "notes": notes,
                    "purchase_date": str(purchase_date),
                    "status": "Unsold",
                    "selling_price": 0,
                    "total_profit": 0
                }
                supabase.table("properties").insert(data).execute()
                st.success(f"✅ {property_name} saved successfully!")
            else:
                st.error("Property Name and Location are required.")

# ============================================
# SELL PROPERTY
# ============================================
# ============================================
# SELL PROPERTY (Improved Error Handling)
# ============================================
elif menu == "Sell Property":
    st.header("💰 Sell Property")

    try:
        response = supabase.table("properties").select("*").eq("status", "Unsold").execute()
        properties = response.data
        
        if properties:
            # ... (rest of your selling logic)
            st.write("Properties loaded successfully.")
        else:
            st.warning("No unsold properties found.")
            
    except Exception as e:
        st.error("🔌 Connection Error: Could not reach the database.")
        st.info("Check if your Supabase project is paused or if your internet is stable.")
        # This prevents the traceback from scaring the user# ============================================
# PROPERTY RECORDS & DELETE
# ============================================
elif menu == "Property Records":
    st.header("📁 All Property Records")
    response = supabase.table("properties").select("*").execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🗑️ Delete a Record")
        to_delete = st.selectbox("Select ID to delete", df["id"].tolist())
        if st.button("Delete Permanently", type="primary"):
            supabase.table("properties").delete().eq("id", to_delete).execute()
            st.rerun()
    else:
        st.info("No records found.")

# ============================================
# PARTNER PROFITS
# ============================================
elif menu == "Partner Profits":
    st.header("👥 Partner Profit Splits")
    response = supabase.table("property_profits").select("*").execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Jaffar (50%)", f"PKR {df['jaffar_profit'].sum():,.0f}")
        col2.metric("Tehseen (40%)", f"PKR {df['tehseen_profit'].sum():,.0f}")
        col3.metric("Dealer (10%)", f"PKR {df['dealer_profit'].sum():,.0f}")
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No sales records available to calculate profits.")

# ============================================
# PROFIT USAGE
# ============================================
elif menu == "Profit Usage":
    st.header("💸 Record Expense/Usage")
    
    with st.form("usage_form"):
        title = st.text_input("Expense Title")
        amount = st.number_input("Amount", min_value=0.0)
        desc = st.text_area("Description")
        if st.form_submit_button("Save Expense"):
            supabase.table("profit_usage").insert({
                "title": title, "amount": amount, "description": desc, "created_at": str(datetime.now())
            }).execute()
            st.success("Expense Recorded")
            st.rerun()

    res = supabase.table("profit_usage").select("*").execute()
    if res.data:
        st.table(pd.DataFrame(res.data))
