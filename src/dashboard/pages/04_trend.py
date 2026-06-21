import streamlit as st
import sqlite3
import pandas as pd
import sys
import os
import plotly.express as px

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))

from db import get_connection

st.set_page_config(page_title="Trend Analysis", page_icon="📈", layout="wide")

st.title("Historical Trend & Growth Analytics")

st.markdown("""
Plot multi-year trends for any core statement items or computed ratios. Select up to 3 metrics to see overlaid line trends.
""")

try:
    conn = get_connection()
    df_co = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
    
    # Selection autocomplete
    options = [f"{row['id']} - {row['company_name']}" for _, row in df_co.iterrows()]
    selected_option = st.selectbox("Select Company Ticker/Name", options)
    
    if selected_option:
        ticker = selected_option.split(" - ")[0]
        
        # Load ratios and statement data
        query = """
            SELECT 
                r.year,
                r.return_on_equity_pct as ROE_pct,
                r.roce_percentage as ROCE_pct,
                r.net_profit_margin_pct as NPM_pct,
                r.debt_to_equity as DE_ratio,
                r.free_cash_flow_cr as FCF_Cr,
                r.composite_quality_score as Quality_Score,
                p.sales as Revenue_Cr,
                p.net_profit as Net_Profit_Cr,
                p.eps as EPS
            FROM financial_ratios r
            JOIN profitandloss p ON r.company_id = p.company_id AND r.year = p.year
            WHERE r.company_id = ?
            ORDER BY r.year ASC
        """
        df_trend = pd.read_sql(query, conn, params=[ticker])
        
        if df_trend.empty:
            st.warning("No time-series data found for this company.")
        else:
            # Multi-select columns for trend chart
            metric_cols = {
                'Revenue (Cr)': 'Revenue_Cr',
                'Net Profit (Cr)': 'Net_Profit_Cr',
                'ROE (%)': 'ROE_pct',
                'ROCE (%)': 'ROCE_pct',
                'Net Profit Margin (%)': 'NPM_pct',
                'Debt to Equity (x)': 'DE_ratio',
                'Free Cash Flow (Cr)': 'FCF_Cr',
                'EPS': 'EPS',
                'Composite Quality Score': 'Quality_Score'
            }
            
            selected_labels = st.multiselect(
                "Select up to 3 metrics to overlay",
                list(metric_cols.keys()),
                default=['Revenue (Cr)', 'Net Profit (Cr)']
            )
            
            if len(selected_labels) > 3:
                st.error("Please select a maximum of 3 metrics to prevent chart crowding.")
            elif len(selected_labels) == 0:
                st.info("Select at least one metric to display the line chart.")
            else:
                # Map select labels to columns
                selected_cols = [metric_cols[lbl] for lbl in selected_labels]
                
                # Plotly line chart
                fig = px.line(
                    df_trend, 
                    x='year', 
                    y=selected_cols, 
                    title=f"Historical Trends for {ticker}",
                    labels={'value': 'Value', 'year': 'Financial Year', 'variable': 'Metric'},
                    template='plotly_white'
                )
                fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabular trend & YoY growth calculation
                st.subheader("Time-Series Tabular Breakdown & YoY Growth")
                
                # For each selected metric, compute YoY change
                df_tab = df_trend[['year'] + selected_cols].copy()
                for col in selected_cols:
                    # Calculate percentage YoY growth
                    df_tab[f'{col} YoY %'] = df_tab[col].pct_change() * 100
                    
                # Format YoY columns to display as +12.3% or -5.2%
                for col in selected_cols:
                    df_tab[f'{col} YoY %'] = df_tab[f'{col} YoY %'].apply(
                        lambda val: f"{val:+.1f}%" if pd.notnull(val) else "—"
                    )
                
                st.dataframe(df_tab, hide_index=True, use_container_width=True)
                
    conn.close()
except Exception as e:
    st.error(f"Error loading trend analytics: {e}")
