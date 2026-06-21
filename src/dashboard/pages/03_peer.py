import streamlit as st
import sqlite3
import pandas as pd
import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../analytics')))

from db import get_connection

st.set_page_config(page_title="Peer Comparison", page_icon="👥", layout="wide")

st.title("Peer Comparison Engine")

st.markdown("""
Use this module to compare companies within pre-defined peer groups (from `peer_groups.xlsx`) and check their relative percentile performance and benchmark gaps.
""")

try:
    conn = get_connection()
    
    # Load unique peer groups
    df_pg = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups", conn)
    peer_groups = df_pg['peer_group_name'].tolist()
    
    if not peer_groups:
        st.warning("No peer groups found in the database. Ensure peer_groups.xlsx is loaded.")
    else:
        # Dropdown selection
        selected_pg = st.selectbox("Select Peer Group Name", peer_groups)
        
        # Load years
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT year FROM financial_ratios ORDER BY year DESC")
        years = [y[0] for y in cursor.fetchall()]
        selected_year = st.selectbox("Select Year", years)
        
        # Fetch group details
        query = """
            SELECT 
                pg.company_id,
                c.company_name,
                pg.is_benchmark,
                r.return_on_equity_pct as ROE,
                r.roce_percentage as ROCE,
                r.net_profit_margin_pct as NPM,
                r.debt_to_equity as DE,
                r.interest_coverage as ICR,
                r.free_cash_flow_cr as FCF,
                r.revenue_cagr_5yr as Sales_CAGR_5Y,
                r.pat_cagr_5yr as PAT_CAGR_5Y,
                r.composite_quality_score as Quality_Score
            FROM peer_groups pg
            JOIN companies c ON pg.company_id = c.id
            JOIN financial_ratios r ON pg.company_id = r.company_id
            WHERE pg.peer_group_name = ? AND r.year = ?
        """
        df_members = pd.read_sql(query, conn, params=[selected_pg, selected_year])
        
        if df_members.empty:
            st.warning(f"No records found for peer group '{selected_pg}' in year {selected_year}.")
        else:
            # Display best-in-class and watch lists info
            st.markdown(f"Comparing **{len(df_members)}** companies in **{selected_pg}**:")
            
            # Find benchmark company
            bench_row = df_members[df_members['is_benchmark'] == 1]
            benchmark_ticker = bench_row.iloc[0]['company_id'] if not bench_row.empty else None
            benchmark_name = bench_row.iloc[0]['company_name'] if not bench_row.empty else "N/A"
            
            st.markdown(f"**Peer Group Benchmark Company:** `{benchmark_ticker}` ({benchmark_name})")
            
            # Show comparison dataframe
            df_disp = df_members.copy()
            df_disp['is_benchmark'] = df_disp['is_benchmark'].apply(lambda x: "⭐ Benchmark" if x == 1 else "")
            st.dataframe(df_disp.rename(columns={
                'company_id': 'Ticker',
                'company_name': 'Company Name',
                'is_benchmark': 'Type',
                'DE': 'D/E',
                'ICR': 'Interest Coverage',
                'FCF': 'FCF (Cr)',
                'Sales_CAGR_5Y': '5Y Sales CAGR %',
                'PAT_CAGR_5Y': '5Y PAT CAGR %',
                'Quality_Score': 'Quality Score'
            }), hide_index=True, use_container_width=True)
            
            # Benchmark Gap Analysis Section
            st.subheader("Benchmark Gap Analysis")
            
            selected_comp = st.selectbox("Select Company to Compare vs Benchmark", df_members['company_id'].tolist())
            
            if selected_comp and benchmark_ticker:
                comp_row = df_members[df_members['company_id'] == selected_comp].iloc[0]
                bench_data = bench_row.iloc[0]
                
                # Metrics to compare
                compare_metrics = ['ROE', 'ROCE', 'NPM', 'DE', 'ICR', 'FCF', 'Sales_CAGR_5Y', 'PAT_CAGR_5Y', 'Quality_Score']
                
                gap_records = []
                for metric in compare_metrics:
                    val_comp = comp_row[metric]
                    val_bench = bench_data[metric]
                    
                    if pd.notnull(val_comp) and pd.notnull(val_bench):
                        gap_abs = val_comp - val_bench
                        gap_pct = (gap_abs / val_bench * 100) if val_bench != 0 else 0
                        status = "🟢 Above" if gap_abs >= 0 else "🔴 Below"
                        # For D/E, lower is better, so flip status
                        if metric == 'DE':
                            status = "🟢 Lower (Better)" if gap_abs <= 0 else "🔴 Higher (Worse)"
                            
                        gap_records.append({
                            'Metric': metric,
                            'Company Value': f"{val_comp:.2f}",
                            'Benchmark Value': f"{val_bench:.2f}",
                            'Absolute Gap': f"{gap_abs:+.2f}",
                            'Percentage Gap': f"{gap_pct:+.1f}%",
                            'Status': status
                        })
                    else:
                        gap_records.append({
                            'Metric': metric,
                            'Company Value': str(val_comp),
                            'Benchmark Value': str(val_bench),
                            'Absolute Gap': 'N/A',
                            'Percentage Gap': 'N/A',
                            'Status': 'N/A'
                        })
                        
                st.dataframe(pd.DataFrame(gap_records), hide_index=True, use_container_width=True)
                
                # Radar Chart view
                st.subheader(f"{selected_comp} Performance Radar Chart")
                radar_png = f"reports/radar_charts/{selected_comp}_radar.png"
                if os.path.exists(radar_png):
                    st.image(radar_png, caption=f"Percentile overlay vs peer group limits", width=550)
                else:
                    st.info("Radar chart not generated yet. Ensure Sprint 3 is run.")
                    
    conn.close()
except Exception as e:
    st.error(f"Error loading peer comparison screen: {e}")
