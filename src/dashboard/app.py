import streamlit as st
import sqlite3
import pandas as pd
import sys
import os

# Add src/dashboard/utils and src/analytics to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../analytics')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../analytics/screener')))

from db import get_connection

# Page Config
st.set_page_config(
    page_title="Nifty 100 Financial Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main container styling */
    .reportview-container {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* KPI Card styling */
    .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: #3b82f6;
        margin-bottom: 4px;
    }
    .kpi-subtitle {
        font-size: 0.75rem;
        color: #10b981;
        font-weight: 500;
    }
    
    /* Banner styling */
    .banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        border-left: 5px solid #3b82f6;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Branding
st.sidebar.markdown("""
<div style="text-align: center; padding-bottom: 20px;">
    <h2 style="color: #3b82f6; margin-bottom: 0px; font-weight: 700;">NIFTY 100</h2>
    <p style="color: #94a3b8; font-size: 0.8rem; letter-spacing: 0.1em; text-transform: uppercase;">Financial Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Main Title Header
st.title("Nifty 100 Financial Intelligence Platform")

st.markdown("""
<div class="banner">
    <h4 style="margin: 0px 0px 8px 0px; color: #f8fafc; font-weight: 600;">System Overview</h4>
    <p style="margin: 0px; color: #cbd5e1; font-size: 0.9rem;">
        Welcome to the Nifty 100 fundamental research workspace. This self-contained platform aggregates 14 years of P&L, Balance Sheet, and Cash Flow filings for 92 key constituents, calculating computed KPIs, growth rates, and health scores instantly. Use the sidebar to navigate between screens.
    </p>
</div>
""", unsafe_allow_html=True)

# Load macro statistics from DB
try:
    conn = get_connection()
    df_companies = pd.read_sql("SELECT * FROM companies", conn)
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    df_sec = pd.read_sql("SELECT * FROM sectors", conn)
    df_mc = pd.read_sql("SELECT * FROM market_cap", conn)
    conn.close()
    
    latest_year = df_ratios['year'].max()
    df_latest_ratios = df_ratios[df_ratios['year'] == latest_year]
    
    # Calculate statistics
    avg_roe = df_latest_ratios['return_on_equity_pct'].mean()
    avg_roce = df_latest_ratios['roce_percentage'].mean()
    median_pe = df_mc[df_mc['year'] == int(latest_year[:4])]['pe_ratio'].median()
    total_companies = len(df_companies)
    
    # Columns for Key Macro Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Universe Size</div>
            <div class="kpi-value">{total_companies}</div>
            <div class="kpi-subtitle">Active Constituents</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Avg ROE ({latest_year})</div>
            <div class="kpi-value">{avg_roe:.1f}%</div>
            <div class="kpi-subtitle">Profitability Metric</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Avg ROCE ({latest_year})</div>
            <div class="kpi-value">{avg_roce:.1f}%</div>
            <div class="kpi-subtitle">Capital Return Rate</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Median PE</div>
            <div class="kpi-value">{median_pe:.1f}x</div>
            <div class="kpi-subtitle">Index Valuation Multiple</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Industry & Sector Allocation")
    
    # Sector aggregation
    df_sec_grouped = df_sec.groupby('broad_sector').size().reset_index(name='count').sort_values(by='count', ascending=False)
    
    import plotly.express as px
    fig_sec = px.pie(
        df_sec_grouped, 
        values='count', 
        names='broad_sector', 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Plotly,
        title="Index Sector Composition"
    )
    fig_sec.update_layout(template='plotly_white', margin=dict(t=50, b=20, l=20, r=20))
    
    col_chart, col_tbl = st.columns([2, 1])
    with col_chart:
        st.plotly_chart(fig_sec, use_container_width=True)
    with col_tbl:
        st.dataframe(
            df_sec_grouped.rename(columns={'broad_sector': 'Broad Sector', 'count': 'Company Count'}),
            hide_index=True,
            use_container_width=True
        )

except Exception as e:
    st.error(f"Error loading database: {e}. Please ensure the database is loaded by running Sprint 1.")
