import os
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "data/nifty100.db"
SUMMARY_PATH = "valuation_summary.xlsx"
FLAGS_PATH = "valuation_flags.csv"

def run_valuation_analysis():
    print("Running Valuation & Market Data Module...")
    conn = sqlite3.connect(DB_PATH)
    
    # Get latest year in ratios
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_ratio_yr = cursor.fetchone()[0]
    latest_mc_yr = int(latest_ratio_yr[:4])
    
    # Query datasets
    query = """
        SELECT 
            r.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.free_cash_flow_cr,
            r.roce_percentage,
            m.market_cap_crore,
            m.enterprise_value_crore,
            m.pe_ratio,
            m.pb_ratio,
            m.ev_ebitda,
            m.dividend_yield_pct
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        JOIN sectors s ON r.company_id = s.company_id
        JOIN market_cap m ON r.company_id = m.company_id AND m.year = ?
        WHERE r.year = ?
    """
    df = pd.read_sql(query, conn, params=[latest_mc_yr, latest_ratio_yr])
    conn.close()

    if df.empty:
        print("No records available to analyze valuations.")
        return

    # Calculate FCF Yield
    df['fcf_yield_pct'] = df.apply(
        lambda row: (row['free_cash_flow_cr'] / row['market_cap_crore'] * 100)
        if pd.notnull(row['free_cash_flow_cr']) and pd.notnull(row['market_cap_crore']) and row['market_cap_crore'] > 0
        else 0.0,
        axis=1
    )

    # Group by broad sector to get PE and EV/EBITDA medians
    sector_medians = df.groupby('broad_sector')[['pe_ratio', 'ev_ebitda']].median().rename(columns={
        'pe_ratio': 'sector_median_pe',
        'ev_ebitda': 'sector_median_ev_ebitda'
    })
    
    df = df.merge(sector_medians, on='broad_sector', how='left')

    # Apply Over/Under Valuation Flags (Page 21, 6.6)
    df['valuation_flag'] = "Fair Value"
    df['flag_rationale'] = ""

    flags_records = []

    for idx, row in df.iterrows():
        ticker = row['company_id']
        pe = row['pe_ratio']
        sec_pe = row['sector_median_pe']
        
        # Overvaluation check
        if pd.notnull(pe) and pd.notnull(sec_pe):
            if pe > (sec_pe * 1.5):
                df.at[idx, 'valuation_flag'] = "Caution"
                df.at[idx, 'flag_rationale'] = f"P/E ({pe:.1f}x) is > 1.5x sector median ({sec_pe:.1f}x)"
                flags_records.append({
                    'company_id': ticker,
                    'valuation_flag': 'Caution',
                    'rationale': df.at[idx, 'flag_rationale'],
                    'pe_ratio': pe,
                    'sector_median_pe': sec_pe
                })
            # Undervaluation check
            elif pe < (sec_pe * 0.7):
                df.at[idx, 'valuation_flag'] = "Discount"
                df.at[idx, 'flag_rationale'] = f"P/E ({pe:.1f}x) is < 0.7x sector median ({sec_pe:.1f}x)"
                flags_records.append({
                    'company_id': ticker,
                    'valuation_flag': 'Discount',
                    'rationale': df.at[idx, 'flag_rationale'],
                    'pe_ratio': pe,
                    'sector_median_pe': sec_pe
                })
                
    # Save Valuation Summary Excel
    df.to_excel(SUMMARY_PATH, index=False)
    print(f"Generated {SUMMARY_PATH}.")

    # Save Flags CSV
    df_flags = pd.DataFrame(flags_records)
    df_flags.to_csv(FLAGS_PATH, index=False)
    print(f"Generated {FLAGS_PATH}.")

if __name__ == "__main__":
    run_valuation_analysis()
