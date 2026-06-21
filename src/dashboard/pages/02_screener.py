import streamlit as st
import pandas as pd
import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../analytics')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../analytics/screener')))

from engine import run_screener, load_screener_config
from db import get_connection

st.set_page_config(page_title="Investment Screener", page_icon="🔍", layout="wide")

st.title("Universe Investment Screener")

st.sidebar.subheader("Filter Configurations")

# 1. Preset Templates selection
config = load_screener_config()
presets = list(config.get("presets", {}).keys())

selected_preset = st.sidebar.selectbox("Choose Preset Template", ["None"] + presets)

st.sidebar.markdown("---")
st.sidebar.markdown("**Custom Criteria Sliders**")

# Default values
default_filters = {
    'min_roe': 0.0,
    'max_de': 5.0,
    'min_fcf': -1000.0,
    'min_revenue_cagr_5yr': -50.0,
    'min_pat_cagr_5yr': -50.0,
    'max_pe': 100.0,
    'max_pb': 20.0,
    'min_dividend_yield': 0.0,
    'max_dividend_payout': 150.0,
    'min_sales': 0.0
}

# If a preset is chosen, override sliders with preset defaults
preset_filters = {}
if selected_preset != "None":
    preset_filters = config["presets"][selected_preset].get("filters", {})
    st.info(f"Applying Preset: **{selected_preset}** - *{config['presets'][selected_preset].get('description')}*")

# Define sliders
min_roe = st.sidebar.slider("Min ROE (%)", -20.0, 80.0, float(preset_filters.get('min_roe', default_filters['min_roe'])), 1.0)
max_de = st.sidebar.slider("Max Debt to Equity (x)", 0.0, 10.0, float(preset_filters.get('max_de', default_filters['max_de'])), 0.1)
min_fcf = st.sidebar.slider("Min Free Cash Flow (Cr)", -5000.0, 20000.0, float(preset_filters.get('min_fcf', default_filters['min_fcf'])), 100.0)
min_rev_cagr = st.sidebar.slider("Min 5Y Revenue CAGR (%)", -30.0, 60.0, float(preset_filters.get('min_revenue_cagr_5yr', default_filters['min_revenue_cagr_5yr'])), 1.0)
min_pat_cagr = st.sidebar.slider("Min 5Y PAT CAGR (%)", -30.0, 60.0, float(preset_filters.get('min_pat_cagr_5yr', default_filters['min_pat_cagr_5yr'])), 1.0)
max_pe = st.sidebar.slider("Max PE Ratio (x)", 5.0, 150.0, float(preset_filters.get('max_pe', default_filters['max_pe'])), 1.0)
max_pb = st.sidebar.slider("Max PB Ratio (x)", 0.1, 30.0, float(preset_filters.get('max_pb', default_filters['max_pb'])), 0.5)
min_div_yield = st.sidebar.slider("Min Dividend Yield (%)", 0.0, 8.0, float(preset_filters.get('min_dividend_yield', default_filters['min_dividend_yield'])), 0.1)
max_div_payout = st.sidebar.slider("Max Dividend Payout (%)", 0.0, 200.0, float(preset_filters.get('max_dividend_payout', default_filters['max_dividend_payout'])), 5.0)
min_sales = st.sidebar.slider("Min Sales (Cr)", 0.0, 200000.0, float(preset_filters.get('min_sales', default_filters['min_sales'])), 1000.0)

# Build filter dictionary
active_filters = {
    'min_roe': min_roe,
    'max_de': max_de,
    'min_fcf': min_fcf,
    'min_revenue_cagr_5yr': min_rev_cagr,
    'min_pat_cagr_5yr': min_pat_cagr,
    'max_pe': max_pe,
    'max_pb': max_pb,
    'min_dividend_yield': min_div_yield,
    'max_dividend_payout': max_div_payout,
    'min_sales': min_sales
}

# Run screener
try:
    if selected_preset != "None":
        df_res, desc = run_screener(preset_name=selected_preset)
    else:
        df_res, desc = run_screener(custom_filters=active_filters)
        
    st.subheader(f"Screen Results: {desc}")
    
    if df_res.empty:
        st.warning("No companies in the database match the selected filters.")
    else:
        st.markdown(f"Found **{len(df_res)}** companies matching your criteria.")
        
        # Columns to display nicely
        display_columns = [
            'company_id', 'company_name', 'broad_sector', 'sales', 'return_on_equity_pct',
            'debt_to_equity', 'free_cash_flow_cr', 'pe_ratio', 'dividend_yield_pct',
            'revenue_cagr_5yr', 'composite_quality_score'
        ]
        
        # Format the numbers for display
        df_display = df_res[display_columns].rename(columns={
            'company_id': 'Ticker',
            'company_name': 'Company Name',
            'broad_sector': 'Sector',
            'sales': 'Sales (Cr)',
            'return_on_equity_pct': 'ROE %',
            'debt_to_equity': 'D/E',
            'free_cash_flow_cr': 'FCF (Cr)',
            'pe_ratio': 'P/E',
            'dividend_yield_pct': 'Div Yield %',
            'revenue_cagr_5yr': '5Y Rev CAGR',
            'composite_quality_score': 'Quality Score'
        })
        
        # Output DataFrame
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        # Export Actions
        st.markdown("---")
        csv_data = df_res.to_csv(index=False)
        st.download_button(
            label="Export Results as CSV",
            data=csv_data,
            file_name="screener_results.csv",
            mime="text/csv"
        )
        
except Exception as e:
    st.error(f"Error running screener: {e}")
