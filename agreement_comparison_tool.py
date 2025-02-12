import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# =============================================================================
# Function to generate monthly projection DataFrame for an agreement.
# =============================================================================
def generate_agreement_projection(
    initial_users, growth_rate, months,
    pricing_model, flat_cost, tier_limits, tier_prices, tier_final_price,
    platform_fee, platform_users_included,
    base_syncs, sync_growth_rate, sync_cost,
    extra_sync_pricing  # Dictionary mapping month -> extra one-time sync pricing
):
    data = []
    cumulative_total = 0.0
    users = initial_users
    for month in range(0, months + 1):
        # Update projected users (month 0 uses the initial count)
        if month == 0:
            users = initial_users
        else:
            users = int(users * (1 + growth_rate / 100))
        
        # --- Calculate User Pricing ---
        if pricing_model == "Flat":
            user_pricing = users * flat_cost
        else:
            remaining = users
            tier_pricings = []
            # For each defined tier:
            for limit, price in zip(tier_limits, tier_prices):
                if remaining > limit:
                    pricing_here = limit * price
                    remaining -= limit
                else:
                    pricing_here = remaining * price
                    remaining = 0
                tier_pricings.append(pricing_here)
            # Final (unbounded) tier:
            final_pricing = remaining * tier_final_price if remaining > 0 else 0.0
            tier_pricings.append(final_pricing)
            user_pricing = sum(tier_pricings)
        
        # --- Platform Pricing (fixed monthly fee) ---
        fee = platform_fee
        
        # --- Calculate Sync Pricing ---
        # Compute compounding syncs per user:
        syncs_per_user = base_syncs * ((1 + sync_growth_rate / 100) ** month)
        base_sync_pricing = users * syncs_per_user * sync_cost
        extra_pricing = extra_sync_pricing.get(month, 0.0)
        total_sync_pricing = base_sync_pricing + extra_pricing
        
        # --- Total Agreement Pricing ---
        monthly_total = user_pricing + fee + total_sync_pricing
        cumulative_total += monthly_total
        
        # --- Build Row Data ---
        row = {
            "Month": month,
            "Projected Users": users,
        }
        if pricing_model == "Flat":
            row["User Pricing ($)"] = user_pricing
        else:
            # Add detailed tier breakdown columns:
            for i, pricing_val in enumerate(tier_pricings[:-1]):  # Defined tiers
                row[f"Tier {i+1} Pricing ($)"] = pricing_val
            row["Final Tier Pricing ($)"] = tier_pricings[-1]
            row["Total User Pricing ($)"] = user_pricing
        
        row["Platform Fee ($)"] = fee
        row["Sync Pricing ($)"] = total_sync_pricing
        row["Total Agreement Pricing ($)"] = monthly_total
        row["Cumulative Agreement Pricing ($)"] = cumulative_total
        
        data.append(row)
    
    df = pd.DataFrame(data)
    return df

# =============================================================================
# Function to plot cumulative agreement pricing comparison.
# =============================================================================
def plot_agreement_comparison(df_current, df_proposed):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(df_current["Month"], df_current["Cumulative Agreement Pricing ($)"].astype(float),
            marker='o', linestyle='-', color='blue', label='Current Agreement')
    ax.plot(df_proposed["Month"], df_proposed["Cumulative Agreement Pricing ($)"].astype(float),
            marker='o', linestyle='--', color='red', label='Proposed Agreement')
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative Agreement Pricing ($)")
    ax.set_title("Cumulative Agreement Pricing Comparison")
    ax.legend()
    return fig

# =============================================================================
# Main Streamlit App
# =============================================================================
def main():
    st.title("Agreement Comparison & Projection Tool")
    
    # ----- Global Projection Period -----
    projection_months = st.sidebar.radio("Projection Period (months)", [12, 24], index=0)
    
    st.header("Enter Agreement Details")
    # Create two columns for side-by-side inputs
    col_current, col_proposed = st.columns(2)
    
    # -----------------------
    # Current Agreement Inputs
    # -----------------------
    with col_current:
        st.subheader("Current Agreement")
        initial_users_current = st.number_input("Initial Users", value=10000, min_value=1, step=1, key="init_users_current")
        growth_rate_current = st.number_input("User Growth Rate (%)", value=5.0, min_value=0.0, step=0.1, key="growth_rate_current")
        pricing_model_current = st.selectbox("Pricing Model", ["Flat", "Tiered"], key="pricing_model_current")
        if pricing_model_current == "Flat":
            flat_cost_current = st.number_input("Flat Pricing per User ($)", value=1.0, min_value=0.0, step=0.1, key="flat_cost_current")
            tier_limits_current = []
            tier_prices_current = []
            tier_final_current = None
        else:
            num_tiers_current = st.number_input(
                "Number of Defined Tiers",
                min_value=1,
                max_value=3,
                value=2,
                step=1,
                key="num_tiers_current",
                help="Defined tiers are the tiers excluding the final unbounded tier. For example, if you want 3 tiers total (including the final unbounded tier), specify 2 defined tiers."
            )
            tier_limits_current = []
            tier_prices_current = []
            for i in range(int(num_tiers_current)):
                limit = st.number_input(f"Tier {i+1} Limit", value=(i+1)*5000, min_value=1, step=1, key=f"tier_limit_current_{i}")
                price = st.number_input(f"Tier {i+1} Pricing ($)", value=1.0, min_value=0.0, step=0.1, key=f"tier_price_current_{i}")
                tier_limits_current.append(limit)
                tier_prices_current.append(price)
            tier_final_current = st.number_input("Final Tier Pricing ($) (for remaining users)", value=0.80, min_value=0.0, step=0.1, key="tier_final_current")
            flat_cost_current = None
        
        platform_fee_current = st.number_input("Platform Fee ($)", value=500.0, min_value=0.0, step=1.0, key="platform_fee_current")
        platform_users_included_current = st.number_input("Users Included in Platform Fee", value=500, min_value=1, step=1, key="platform_users_included_current")
        
        # ----- Sync Pricing Toggle & Inputs for Current Agreement -----
        include_sync_current = st.checkbox("Include Sync Pricing?", value=False, key="include_sync_current")
        if include_sync_current:
            base_syncs_current = st.number_input(
                "Base Syncs per User", value=0.10, min_value=0.0, step=0.01,
                key="base_syncs_current", help="Set to 0 to eliminate sync pricing from the calculations."
            )
            sync_growth_current = st.number_input("Sync Growth Rate (%)", value=0.0, min_value=0.0, step=0.1, key="sync_growth_current")
            sync_cost_current = st.number_input("Sync Pricing per Sync ($)", value=0.05, min_value=0.0, step=0.01, key="sync_cost_current")
            extra_syncs_current_str = st.text_input(
                "Extra One-Time Sync Pricing (optional)",
                value="",
                key="extra_syncs_current",
                help=("Enter additional pricing for syncs if a custom amount of syncs is anticipated in a given month. "
                      "Format: Month:Pricing (e.g., 3:200,6:150)")
            )
            extra_syncs_current = {}
            if extra_syncs_current_str:
                try:
                    for pair in extra_syncs_current_str.split(","):
                        if pair.strip():
                            month_str, pricing_str = pair.split(":")
                            extra_syncs_current[int(month_str.strip())] = float(pricing_str.strip())
                except Exception as e:
                    st.error("Error parsing Extra One-Time Sync Pricing for Current Agreement. Please use the format Month:Pricing, e.g., 3:200,6:150")
        else:
            base_syncs_current = 0.0
            sync_growth_current = 0.0
            sync_cost_current = 0.0
            extra_syncs_current = {}
    
    # -----------------------
    # Proposed Agreement Inputs
    # -----------------------
    with col_proposed:
        st.subheader("Proposed Agreement")
        initial_users_proposed = st.number_input("Initial Users", value=10000, min_value=1, step=1, key="init_users_proposed")
        growth_rate_proposed = st.number_input("User Growth Rate (%)", value=5.0, min_value=0.0, step=0.1, key="growth_rate_proposed")
        pricing_model_proposed = st.selectbox("Pricing Model", ["Flat", "Tiered"], key="pricing_model_proposed")
        if pricing_model_proposed == "Flat":
            flat_cost_proposed = st.number_input("Flat Pricing per User ($)", value=1.0, min_value=0.0, step=0.1, key="flat_cost_proposed")
            tier_limits_proposed = []
            tier_prices_proposed = []
            tier_final_proposed = None
        else:
            num_tiers_proposed = st.number_input(
                "Number of Defined Tiers",
                min_value=1,
                max_value=3,
                value=2,
                step=1,
                key="num_tiers_proposed",
                help="Defined tiers are the tiers excluding the final unbounded tier. For example, if you want 3 tiers total (including the final unbounded tier), specify 2 defined tiers."
            )
            tier_limits_proposed = []
            tier_prices_proposed = []
            for i in range(int(num_tiers_proposed)):
                limit = st.number_input(f"Tier {i+1} Limit", value=(i+1)*5000, min_value=1, step=1, key=f"tier_limit_proposed_{i}")
                price = st.number_input(f"Tier {i+1} Pricing ($)", value=1.0, min_value=0.0, step=0.1, key=f"tier_price_proposed_{i}")
                tier_limits_proposed.append(limit)
                tier_prices_proposed.append(price)
            tier_final_proposed = st.number_input("Final Tier Pricing ($) (for remaining users)", value=0.80, min_value=0.0, step=0.1, key="tier_final_proposed")
            flat_cost_proposed = None
        
        platform_fee_proposed = st.number_input("Platform Fee ($)", value=1000.0, min_value=0.0, step=1.0, key="platform_fee_proposed")
        platform_users_included_proposed = st.number_input("Users Included in Platform Fee", value=1000, min_value=1, step=1, key="platform_users_included_proposed")
        
        # ----- Sync Pricing Toggle & Inputs for Proposed Agreement -----
        include_sync_proposed = st.checkbox("Include Sync Pricing?", value=False, key="include_sync_proposed")
        if include_sync_proposed:
            base_syncs_proposed = st.number_input(
                "Base Syncs per User", value=0.25, min_value=0.0, step=0.01,
                key="base_syncs_proposed", help="Set to 0 to eliminate sync pricing from the calculations."
            )
            sync_growth_proposed = st.number_input("Sync Growth Rate (%)", value=0.0, min_value=0.0, step=0.1, key="sync_growth_proposed")
            sync_cost_proposed = st.number_input("Sync Pricing per Sync ($)", value=0.05, min_value=0.0, step=0.01, key="sync_cost_proposed")
            extra_syncs_proposed_str = st.text_input(
                "Extra One-Time Sync Pricing (optional)",
                value="",
                key="extra_syncs_proposed",
                help=("Enter additional pricing for syncs if a custom amount of syncs is anticipated in a given month. "
                      "Format: Month:Pricing (e.g., 3:200,6:150)")
            )
            extra_syncs_proposed = {}
            if extra_syncs_proposed_str:
                try:
                    for pair in extra_syncs_proposed_str.split(","):
                        if pair.strip():
                            month_str, pricing_str = pair.split(":")
                            extra_syncs_proposed[int(month_str.strip())] = float(pricing_str.strip())
                except Exception as e:
                    st.error("Error parsing Extra One-Time Sync Pricing for Proposed Agreement. Please use the format Month:Pricing, e.g., 3:200,6:150")
        else:
            base_syncs_proposed = 0.0
            sync_growth_proposed = 0.0
            sync_cost_proposed = 0.0
            extra_syncs_proposed = {}
    
    # =============================================================================
    # Generate Projections for Each Agreement
    # =============================================================================
    df_current = generate_agreement_projection(
        initial_users_current, growth_rate_current, projection_months,
        pricing_model_current,
        flat_cost_current if pricing_model_current == "Flat" else None,
        tier_limits_current, tier_prices_current, tier_final_current if pricing_model_current == "Tiered" else None,
        platform_fee_current, platform_users_included_current,
        base_syncs_current, sync_growth_current, sync_cost_current,
        extra_syncs_current
    )
    
    df_proposed = generate_agreement_projection(
        initial_users_proposed, growth_rate_proposed, projection_months,
        pricing_model_proposed,
        flat_cost_proposed if pricing_model_proposed == "Flat" else None,
        tier_limits_proposed, tier_prices_proposed, tier_final_proposed if pricing_model_proposed == "Tiered" else None,
        platform_fee_proposed, platform_users_included_proposed,
        base_syncs_proposed, sync_growth_proposed, sync_cost_proposed,
        extra_syncs_proposed
    )
    
    # =============================================================================
    # Display Side-by-Side Projection Tables with CSV Downloads
    # =============================================================================
    st.markdown("---")
    st.subheader("Projection Tables")
    table_col1, table_col2 = st.columns(2)
    
    with table_col1:
        st.write("### Current Agreement Projection")
        df_display_current = df_current.copy()
        numeric_cols = df_display_current.select_dtypes(include=["float", "int"]).columns
        df_display_current[numeric_cols] = df_display_current[numeric_cols].applymap(lambda x: f"{x:.2f}")
        st.dataframe(df_display_current)
        csv_current = df_current.to_csv(index=False).encode("utf-8")
        st.download_button("Download Current CSV", csv_current, "current_projection.csv", "text/csv")
    
    with table_col2:
        st.write("### Proposed Agreement Projection")
        df_display_proposed = df_proposed.copy()
        numeric_cols = df_display_proposed.select_dtypes(include=["float", "int"]).columns
        df_display_proposed[numeric_cols] = df_display_proposed[numeric_cols].applymap(lambda x: f"{x:.2f}")
        st.dataframe(df_display_proposed)
        csv_proposed = df_proposed.to_csv(index=False).encode("utf-8")
        st.download_button("Download Proposed CSV", csv_proposed, "proposed_projection.csv", "text/csv")
    
    # =============================================================================
    # Display Cumulative Pricing Comparison Graph with PNG Download
    # =============================================================================
    st.markdown("---")
    st.subheader("Cumulative Agreement Pricing Comparison")
    fig = plot_agreement_comparison(df_current, df_proposed)
    st.pyplot(fig)
    
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Graph as PNG", buf, "agreement_comparison.png", "image/png")

if __name__ == "__main__":
    main()