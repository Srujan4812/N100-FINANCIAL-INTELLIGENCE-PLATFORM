import streamlit as st
import sqlite3
import pandas as pd
import sys
import os
import plotly.express as px
import plotly.graph_objects as go

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))

from db import get_connection
from charts import plot_sector_bubble_chart

st.set_page_config(page_title="Sector Analytics", page_icon="🗂️", layout="wide")

st.title("Sector Analytics & Benchmarks")

st.markdown("""
Compare companies across different macro-sectors. The bubble chart plots Sales vs ROE, with bubble sizes representing market cap and colors representing broad sectors.
""")

try:
    conn = get_connection()
    
    # Query all sector mappings joined with latest ratios and valuations
    query_all = """
        SELECT 
            c.id as company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.year,
            r.return_on_equity_pct,
            r.roce_percentage,
            r.debt_to_equity,
            r.free_cash_flow_cr,
            r.composite_quality_score,
            p.sales,
            m.market_cap_crore,
            m.pe_ratio
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        JOIN financial_ratios r ON s.company_id = r.company_id
        JOIN profitandloss p ON s.company_id = p.company_id AND r.year = p.year
        JOIN market_cap m ON s.company_id = m.company_id 
             AND CAST(substr(r.year, 1, 4) AS INTEGER) = m.year
        WHERE r.year = (SELECT MAX(year) FROM financial_ratios)
    """
    df_all = pd.read_sql(query_all, conn)
    
    if df_all.empty:
        st.warning("No data loaded. Ensure both Loader and Ratios are run.")
    else:
        # Display index bubble chart
        st.plotly_chart(plot_sector_bubble_chart(df_all), use_container_width=True)
        
        # Sector selector dropdown
        sectors = sorted(df_all['broad_sector'].unique().tolist())
        selected_sec = st.selectbox("Select Target Sector for Benchmarking", sectors)
        
        # Sector specific sub-dataframe
        df_sec = df_all[df_all['broad_sector'] == selected_sec].copy()
        
        # Show sector median benchmarks
        st.subheader(f"{selected_sec} Sector Median Benchmarks")
        
        # Median calculations across sector
        sec_median_pe = df_sec['pe_ratio'].median()
        sec_median_roe = df_sec['return_on_equity_pct'].median()
        sec_median_roce = df_sec['roce_percentage'].median()
        sec_median_de = df_sec['debt_to_equity'].median()
        
        # Universe median calculations for comparison
        univ_median_pe = df_all['pe_ratio'].median()
        univ_median_roe = df_all['return_on_equity_pct'].median()
        univ_median_roce = df_all['roce_percentage'].median()
        univ_median_de = df_all['debt_to_equity'].median()
        
        # Benchmarks comparison table
        bench_records = [
            {"Benchmark KPI": "Price-to-Earnings (P/E)", "Sector Median": f"{sec_median_pe:.1f}x", "Universe Median": f"{univ_median_pe:.1f}x"},
            {"Benchmark KPI": "Return on Equity (ROE %)", "Sector Median": f"{sec_median_roe:.1f}%", "Universe Median": f"{univ_median_roe:.1f}%"},
            {"Benchmark KPI": "Return on Capital (ROCE %)", "Sector Median": f"{sec_median_roce:.1f}%", "Universe Median": f"{univ_median_roce:.1f}%"},
            {"Benchmark KPI": "Debt to Equity (D/E)", "Sector Median": f"{sec_median_de:.2f}x", "Universe Median": f"{univ_median_de:.2f}x"}
        ]
        
        col_stats, col_table = st.columns([1, 2])
        
        with col_stats:
            # Highlight median stats in boxes
            st.metric(label="Sector Median P/E", value=f"{sec_median_pe:.1f}x", delta=f"{sec_median_pe - univ_median_pe:+.1f}x vs Universe")
            st.metric(label="Sector Median ROE", value=f"{sec_median_roe:.1f}%", delta=f"{sec_median_roe - univ_median_roe:+.1f}% vs Universe")
            
        with col_table:
            st.dataframe(pd.DataFrame(bench_records), hide_index=True, use_container_width=True)

        # Sector constituents lists ranked by Quality Score
        st.subheader(f"Top Performers in {selected_sec} (Ranked by Quality Score)")
        df_sec_ranked = df_sec.sort_values(by='composite_quality_score', ascending=False)
        st.dataframe(
            df_sec_ranked[['company_id', 'company_name', 'sub_sector', 'sales', 'return_on_equity_pct', 'debt_to_equity', 'composite_quality_score']].rename(columns={
                'company_id': 'Ticker',
                'company_name': 'Company Name',
                'sub_sector': 'Sub-Sector',
                'sales': 'Sales (Cr)',
                'return_on_equity_pct': 'ROE %',
                'debt_to_equity': 'D/E',
                'composite_quality_score': 'Quality Score'
            }),
            hide_index=True,
            use_container_width=True
        )

    conn.close()
except Exception as e:
    st.error(f"Error loading sector analysis page: {e}")
