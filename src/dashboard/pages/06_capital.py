import streamlit as st
import sqlite3
import pandas as pd
import sys
import os
import plotly.express as px

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))

from db import get_connection

st.set_page_config(page_title="Capital Allocation Map", page_icon="🗺️", layout="wide")

st.title("Capital Allocation Map")

st.markdown("""
Understand how companies distribute operating cash flows. The Treemap groups companies by their capital allocation label (computed from the sign patterns of CFO, CFI, and CFF), with tile sizes scaled by sales.
""")

try:
    conn = get_connection()
    
    # Load unique years
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT year FROM financial_ratios ORDER BY year DESC")
    years = [y[0] for y in cursor.fetchall()]
    selected_year = st.selectbox("Select Financial Year", years)
    
    # Fetch ratios and sales
    query = """
        SELECT 
            r.company_id,
            c.company_name,
            r.capital_allocation_pattern,
            r.free_cash_flow_cr,
            r.cash_from_operations_cr,
            p.sales,
            s.broad_sector
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        JOIN sectors s ON r.company_id = s.company_id
        JOIN profitandloss p ON r.company_id = p.company_id AND r.year = p.year
        WHERE r.year = ?
    """
    df_map = pd.read_sql(query, conn, params=[selected_year])
    
    if df_map.empty:
        st.warning("No data found for the selected year.")
    else:
        # Pre-process null patterns
        df_map['capital_allocation_pattern'] = df_map['capital_allocation_pattern'].fillna("Other")
        df_map['sales'] = df_map['sales'].fillna(1.0)
        
        # Interactive Plotly Treemap
        fig_tree = px.treemap(
            df_map, 
            path=['capital_allocation_pattern', 'company_id'], 
            values='sales',
            color='capital_allocation_pattern',
            hover_data=['company_name', 'sales', 'free_cash_flow_cr'],
            color_discrete_sequence=px.colors.qualitative.Safe,
            title=f"Capital Allocation Distribution ({selected_year})"
        )
        fig_tree.update_layout(margin=dict(t=50, b=20, l=10, r=10))
        st.plotly_chart(fig_tree, use_container_width=True)
        
        # Pattern drilldown selection
        st.subheader("Filter Constituents by Capital Strategy Pattern")
        patterns = sorted(df_map['capital_allocation_pattern'].unique().tolist())
        selected_pattern = st.selectbox("Select Allocation Pattern for Drilldown List", patterns)
        
        # Drilldown dataframe
        df_drill = df_map[df_map['capital_allocation_pattern'] == selected_pattern].copy()
        st.write(f"Found **{len(df_drill)}** companies employing **{selected_pattern}** strategy:")
        
        st.dataframe(
            df_drill[['company_id', 'company_name', 'broad_sector', 'sales', 'cash_from_operations_cr', 'free_cash_flow_cr']].rename(columns={
                'company_id': 'Ticker',
                'company_name': 'Company Name',
                'broad_sector': 'Broad Sector',
                'sales': 'Sales (Cr)',
                'cash_from_operations_cr': 'CFO (Cr)',
                'free_cash_flow_cr': 'FCF (Cr)'
            }),
            hide_index=True,
            use_container_width=True
        )
        
    conn.close()
except Exception as e:
    st.error(f"Error loading capital allocation map: {e}")
