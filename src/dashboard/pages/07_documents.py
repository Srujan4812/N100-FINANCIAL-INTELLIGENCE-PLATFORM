import streamlit as st
import sqlite3
import pandas as pd
import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))

from db import get_connection

st.set_page_config(page_title="Annual Reports Repository", page_icon="📁", layout="wide")

st.title("Annual Reports Repository")

st.markdown("""
Browse and download historical annual report PDFs. Tickers query directly from BSE/NSE primary document mappings.
""")

try:
    conn = get_connection()
    df_co = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
    
    # Selection autocomplete
    options = [f"{row['id']} - {row['company_name']}" for _, row in df_co.iterrows()]
    selected_option = st.selectbox("Select Company to View Filings", options)
    
    if selected_option:
        ticker = selected_option.split(" - ")[0]
        
        # Load reports for selected company
        query = "SELECT year, Annual_Report FROM documents WHERE company_id = ? ORDER BY year DESC"
        df_docs = pd.read_sql(query, conn, params=[ticker])
        
        if df_docs.empty:
            st.warning("No report filings found for this company in the database.")
        else:
            # Prepare interactive dataframe showing clickable markdown links
            report_records = []
            for _, row in df_docs.iterrows():
                yr = row['year']
                url = row['Annual_Report']
                
                if pd.notnull(url) and str(url).startswith('http'):
                    link_val = url
                    status = "✅ Available Link"
                else:
                    link_val = None
                    status = "⚠️ No Link"
                    
                report_records.append({
                    "Year": yr,
                    "Link": link_val,
                    "Filing Status": status,
                    "Raw URL": url if pd.notnull(url) else "N/A"
                })
                
            df_display = pd.DataFrame(report_records)
            st.markdown(f"Displaying **{len(df_display)}** filings for **{ticker}**:")
            
            # Using column config to render links correctly
            st.dataframe(
                df_display, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Report Link", display_text="Open PDF")
                }
            )
            
    conn.close()
except Exception as e:
    st.error(f"Error loading reports: {e}")
