import streamlit as st
import sqlite3
import pandas as pd
import sys
import os

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../analytics')))

from db import get_connection
from charts import plot_pnl_chart, plot_bs_chart, plot_cf_chart

st.set_page_config(page_title="Company Profile", page_icon="🏢", layout="wide")

# Custom Card CSS
st.markdown("""
<style>
    .metric-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    .metric-box {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px;
        flex: 1;
        margin: 0 8px;
        text-align: center;
    }
    .metric-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #3b82f6;
    }
    .profile-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
    }
    .pro-badge {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 6px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        border-left: 3px solid #10b981;
    }
    .con-badge {
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        padding: 6px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        border-left: 3px solid #ef4444;
    }
</style>
""", unsafe_allow_html=True)

st.title("Company Intelligence Profile")

try:
    conn = get_connection()
    df_co = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
    
    # Autocomplete ticker/name lookup
    options = [f"{row['id']} - {row['company_name']}" for _, row in df_co.iterrows()]
    selected_option = st.selectbox("Search Company by Ticker or Name", options)
    
    if selected_option:
        ticker = selected_option.split(" - ")[0]
        
        # Load details
        company = pd.read_sql("SELECT * FROM companies WHERE id = ?", conn, params=[ticker]).iloc[0]
        sector = pd.read_sql("SELECT * FROM sectors WHERE company_id = ?", conn, params=[ticker])
        pnl = pd.read_sql("SELECT * FROM profitandloss WHERE company_id = ?", conn, params=[ticker])
        bs = pd.read_sql("SELECT * FROM balancesheet WHERE company_id = ?", conn, params=[ticker])
        cf = pd.read_sql("SELECT * FROM cashflow WHERE company_id = ?", conn, params=[ticker])
        ratios = pd.read_sql("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year DESC", conn, params=[ticker])
        mc = pd.read_sql("SELECT * FROM market_cap WHERE company_id = ? ORDER BY year DESC", conn, params=[ticker])
        prosandcons = pd.read_sql("SELECT * FROM prosandcons WHERE company_id = ?", conn, params=[ticker])
        
        # Details layout
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        col_logo, col_desc = st.columns([1, 4])
        
        with col_logo:
            # Fallback placeholder if logo returns 404
            logo_url = company['company_logo']
            if pd.isnull(logo_url) or not str(logo_url).startswith('http'):
                st.markdown(f"<div style='width: 100px; height: 100px; border-radius: 50%; background-color: #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; font-weight: 700; color: white;'>{ticker[:2]}</div>", unsafe_allow_html=True)
            else:
                st.image(logo_url, width=110, use_container_width=False)
                
        with col_desc:
            st.subheader(f"{company['company_name']} ({ticker})")
            sec_lbl = f"**Sector:** {sector.iloc[0]['broad_sector']} | **Sub-Sector:** {sector.iloc[0]['sub_sector']}" if not sector.empty else ""
            st.markdown(sec_lbl)
            st.write(company['about_company'])
            
            links = []
            if pd.notnull(company['website']):
                links.append(f"[Website]({company['website']})")
            if pd.notnull(company['chart_link']):
                links.append(f"[TradingView Chart]({company['chart_link']})")
            if pd.notnull(company['nse_profile']):
                links.append(f"[NSE Profile]({company['nse_profile']})")
            if links:
                st.markdown(" | ".join(links))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Ratios calculations
        if not ratios.empty:
            latest_ratio = ratios.iloc[0]
            latest_mc = mc.iloc[0] if not mc.empty else None
            
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            
            # Displays cards side-by-side
            metrics_display = [
                ("ROE", f"{latest_ratio['return_on_equity_pct']:.1f}%" if pd.notnull(latest_ratio['return_on_equity_pct']) else "N/A"),
                ("ROCE", f"{latest_ratio['roce_percentage']:.1f}%" if pd.notnull(latest_ratio['roce_percentage']) else "N/A"),
                ("OPM", f"{latest_ratio['operating_profit_margin_pct']:.1f}%" if pd.notnull(latest_ratio['operating_profit_margin_pct']) else "N/A"),
                ("NPM", f"{latest_ratio['net_profit_margin_pct']:.1f}%" if pd.notnull(latest_ratio['net_profit_margin_pct']) else "N/A"),
                ("Debt to Equity", f"{latest_ratio['debt_to_equity']:.2f}x" if pd.notnull(latest_ratio['debt_to_equity']) else "N/A"),
                ("P/E Ratio", f"{latest_mc['pe_ratio']:.1f}x" if latest_mc is not None and pd.notnull(latest_mc.get('pe_ratio')) else "N/A")
            ]
            
            col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
            cols = [col_m1, col_m2, col_m3, col_m4, col_m5, col_m6]
            for i, (lbl, val) in enumerate(metrics_display):
                with cols[i]:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-lbl">{lbl}</div>
                        <div class="metric-val">{val}</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Plot charts
        st.subheader("Financial Statements Visualization")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if not pnl.empty:
                st.plotly_chart(plot_pnl_chart(pnl), use_container_width=True)
        with col_c2:
            if not bs.empty:
                st.plotly_chart(plot_bs_chart(bs), use_container_width=True)
                
        col_c3, col_c4 = st.columns(2)
        with col_c3:
            if not cf.empty:
                st.plotly_chart(plot_cf_chart(cf), use_container_width=True)
        with col_c4:
            # Display pre-generated Radar Chart
            radar_png = f"reports/radar_charts/{ticker}_radar.png"
            if os.path.exists(radar_png):
                st.image(radar_png, caption=f"Valuation & Metric Percentiles vs Peer Group", use_container_width=True)
            else:
                st.info("Radar chart not generated. Run Sprint 3 to compute comparison radar overlays.")

        # Qualitative Section (Pros and Cons)
        st.subheader("Investment Thesis (Qualitative Highlights)")
        col_pros, col_cons = st.columns(2)
        
        with col_pros:
            st.markdown("**Strengths & Positives (Pros)**")
            pros_list = prosandcons[prosandcons['pros'].notnull()]['pros'].tolist()
            if pros_list:
                for pro in pros_list:
                    st.markdown(f"<div class='pro-badge'>👍 {pro}</div>", unsafe_allow_html=True)
            else:
                st.write("No positive qualitative signals logged.")
                
        with col_cons:
            st.markdown("**Risks & Concerns (Cons)**")
            cons_list = prosandcons[prosandcons['cons'].notnull()]['cons'].tolist()
            if cons_list:
                for con in cons_list:
                    st.markdown(f"<div class='con-badge'>⚠️ {con}</div>", unsafe_allow_html=True)
            else:
                st.write("No risk observations logged.")
                
        # Clickable Tearsheet PDF download link
        pdf_path = f"reports/tearsheets/{ticker}_tearsheet.pdf"
        st.subheader("Automated Tearsheet Report")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label=f"Download {ticker} 2-Page tearsheet PDF",
                    data=pdf_file,
                    file_name=f"{ticker}_tearsheet.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("Tearsheet PDF has not been generated yet. You will be able to download tearsheets once PDF Reporting (Sprint 5) is completed.")

    conn.close()
except Exception as e:
    st.error(f"Error loading profile: {e}")
