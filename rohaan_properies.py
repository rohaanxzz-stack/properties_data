# ============================================
# ESTATELEDGER
# STREAMLIT + SUPABASE + PARTNER PROFITS
# FULL GITHUB READY CODE
# ============================================

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="EstateLedger",
    layout="wide"
)

st.title("🏠 EstateLedger")
st.caption("Real Estate Record Management System")

# ============================================
# SUPABASE CONNECTION
# ============================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ============================================
# SIDEBAR MENU
# ============================================

menu = st.sidebar.selectbox(
    "Select Menu",
    [
        "Dashboard",
        "Add Property",
        "Sell Property",
        "Property Records",
        "Partner Profits",
        "Profit Usage"
    ]
)

# ============================================
# DASHBOARD
# ============================================

if menu == "Dashboard":

    st.header("📊 Dashboard")

    response = supabase.table(
        "properties"
    ).select("*").execute()

    properties = response.data

    df = pd.DataFrame(properties)

    if not df.empty:

        total_investment = (
            df["buying_price"].sum()
            + df["construction_cost"].sum()
        )

        total_profit = (
            df["total_profit"].sum()
        )

        net_worth = (
            total_investment
            + total_profit
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Investment",
            f"PKR {total_investment:,.0f}"
        )

        col2.metric(
            "Total Profit",
            f"PKR {total_profit:,.0f}"
        )

        col3.metric(
            "Net Worth",
            f"PKR {net_worth:,.0f}"
        )

        col4.metric(
            "Status",
            "Profit"
            if total_profit >= 0
            else "Loss"
        )

        st.divider()

        st.subheader("Property Records")

        st.dataframe(df)

    else:
        st.warning("No Properties Found")

# ============================================
# ADD PROPERTY
# ============================================

elif menu == "Add Property":

    st.header("➕ Add Property")

    property_name = st.text_input(
        "Property Name"
    )

    location = st.text_input(
        "Location"
    )

    buying_price = st.number_input(
        "Buying Price",
        min_value=0.0
    )

    construction_cost = st.number_input(
        "Construction Cost",
        min_value=0.0
    )

    dealer_name = st.text_input(
        "Dealer Name"
    )

    notes = st.text_area(
        "Notes"
    )

    if st.button("Save Property"):

        data = {

            "property_name": property_name,

            "location": location,

            "buying_price": buying_price,

            "construction_cost": construction_cost,

            "dealer_name": dealer_name,

            "notes": notes,

            "purchase_date": str(
                datetime.now()
            ),

            "status": "Unsold",

            "selling_price": 0,

            "total_profit": 0
        }

        supabase.table(
            "properties"
        ).insert(data).execute()

        st.success(
            "✅ Property Added Successfully"
        )

# ============================================
# SELL PROPERTY
# ============================================

elif menu == "Sell Property":

    st.header("💰 Sell Property")

    response = supabase.table(
        "properties"
    ).select("*").eq(
        "status",
        "Unsold"
    ).execute()

    properties = response.data

    if properties:

        property_options = {
            p["property_name"]: p["id"]
            for p in properties
        }

        selected_property = st.selectbox(
            "Select Property",
            list(property_options.keys())
        )

        selling_price = st.number_input(
            "Selling Price",
            min_value=0.0
        )

        if st.button("Mark As Sold"):

            property_id = property_options[
                selected_property
            ]

            property_data = next(
                p for p in properties
                if p["id"] == property_id
            )

            total_expense = (
                property_data["buying_price"]
                + property_data["construction_cost"]
            )

            total_profit = (
                selling_price
                - total_expense
            )

            # =====================================
            # PARTNER PROFIT DISTRIBUTION
            # =====================================

            jaffar_profit = total_profit * 0.50
            tehseen_profit = total_profit * 0.40
            dealer_profit = total_profit * 0.10

            # =====================================
            # UPDATE PROPERTY
            # =====================================

            supabase.table(
                "properties"
            ).update({

                "status": "Sold",

                "selling_price": selling_price,

                "selling_date": str(
                    datetime.now()
                ),

                "total_profit": total_profit

            }).eq(
                "id",
                property_id
            ).execute()

            # =====================================
            # SAVE PARTNER PROFITS
            # =====================================

            profit_data = {

                "property_id": property_id,

                "property_name":
                selected_property,

                "total_profit":
                total_profit,

                "jaffar_profit":
                jaffar_profit,

                "tehseen_profit":
                tehseen_profit,

                "dealer_profit":
                dealer_profit
            }

            supabase.table(
                "property_profits"
            ).insert(
                profit_data
            ).execute()

            st.success(
                "✅ Property Sold & Profits Distributed"
            )

            st.info(
                f"""
                Jaffar Profit: PKR {jaffar_profit:,.0f}

                Tehseen Profit: PKR {tehseen_profit:,.0f}

                Dealer Profit: PKR {dealer_profit:,.0f}
                """
            )

    else:
        st.warning(
            "No Unsold Properties Found"
        )

# ============================================
# PROPERTY RECORDS
# ============================================

elif menu == "Property Records":

    st.header("📁 Property Records")

    response = supabase.table(
        "properties"
    ).select("*").execute()

    properties = response.data

    if properties:

        df = pd.DataFrame(properties)

        st.dataframe(
            df,
            use_container_width=True
        )

    else:
        st.warning(
            "No Records Found"
        )

# ============================================
# PARTNER PROFITS
# ============================================

elif menu == "Partner Profits":

    st.header("👥 Partner Profits")

    response = supabase.table(
        "property_profits"
    ).select("*").execute()

    profits = response.data

    if profits:

        df = pd.DataFrame(profits)

        total_jaffar = (
            df["jaffar_profit"].sum()
        )

        total_tehseen = (
            df["tehseen_profit"].sum()
        )

        total_dealer = (
            df["dealer_profit"].sum()
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Jaffar Total Profit",
            f"PKR {total_jaffar:,.0f}"
        )

        col2.metric(
            "Tehseen Total Profit",
            f"PKR {total_tehseen:,.0f}"
        )

        col3.metric(
            "Dealer Total Profit",
            f"PKR {total_dealer:,.0f}"
        )

        st.divider()

        st.dataframe(df)

    else:
        st.warning(
            "No Profit Records Found"
        )

# ============================================
# PROFIT USAGE
# ============================================

elif menu == "Profit Usage":

    st.header("💸 Profit Usage")

    title = st.text_input(
        "Usage Title"
    )

    amount = st.number_input(
        "Amount",
        min_value=0.0
    )

    description = st.text_area(
        "Description"
    )

    if st.button("Save Usage"):

        usage_data = {

            "title": title,

            "amount": amount,

            "description": description,

            "created_at": str(
                datetime.now()
            )
        }

        supabase.table(
            "profit_usage"
        ).insert(
            usage_data
        ).execute()

        st.success(
            "✅ Profit Usage Saved"
        )

    response = supabase.table(
        "profit_usage"
    ).select("*").execute()

    usage = response.data

    if usage:

        usage_df = pd.DataFrame(usage)

        st.dataframe(usage_df)

# ============================================
# SUPABASE SQL
# RUN THIS IN SQL EDITOR
# ============================================

"""
CREATE TABLE properties (

    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    property_name TEXT,

    location TEXT,

    buying_price NUMERIC DEFAULT 0,

    construction_cost NUMERIC DEFAULT 0,

    dealer_name TEXT,

    notes TEXT,

    purchase_date TIMESTAMP DEFAULT NOW(),

    status TEXT DEFAULT 'Unsold',

    selling_price NUMERIC DEFAULT 0,

    selling_date TIMESTAMP,

    total_profit NUMERIC DEFAULT 0

);

CREATE TABLE property_profits (

    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    property_id BIGINT REFERENCES properties(id)
    ON DELETE CASCADE,

    property_name TEXT,

    total_profit NUMERIC DEFAULT 0,

    jaffar_profit NUMERIC DEFAULT 0,

    tehseen_profit NUMERIC DEFAULT 0,

    dealer_profit NUMERIC DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()

);

CREATE TABLE profit_usage (

    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    title TEXT,

    amount NUMERIC DEFAULT 0,

    description TEXT,

    created_at TIMESTAMP DEFAULT NOW()

);
"""

# ============================================
# .streamlit/secrets.toml
# ============================================

"""
SUPABASE_URL = "YOUR_SUPABASE_URL"

SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
"""

# ============================================
# requirements.txt
# ============================================

"""
streamlit
supabase
pandas
"""

# ============================================
# RUN COMMAND
# ============================================

"""
streamlit run app.py
"""