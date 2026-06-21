import os
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional

DB_PATH = "data/nifty100.db"
CF_INTELLIGENCE_PATH = "cashflow_intelligence.xlsx"
ALERTS_PATH = "distress_alerts.csv"

def run_cashflow_analysis():
    print("Running Cash Flow Intelligence Module...")
    conn = sqlite3.connect(DB_PATH)
    
    # Query ratios, cashflow, balancesheet and companies
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    df_bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    df_companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
    
    conn.close()

    if df_ratios.empty:
        print("No ratio data available for cash flow intelligence.")
        return

    # Sort ratios by company and year to calculate YoY debt trends
    df_ratios = df_ratios.sort_values(by=['company_id', 'year'])
    df_bs = df_bs.sort_values(by=['company_id', 'year'])

    records = []
    distress_alerts = []

    # Map time series for each company
    for ticker in df_companies['id']:
        comp_ratios = df_ratios[df_ratios['company_id'] == ticker].copy()
        comp_bs = df_bs[df_bs['company_id'] == ticker].copy()
        
        # Merge ratios and bs to get borrowings YoY
        comp_data = comp_ratios.merge(
            comp_bs[['year', 'borrowings']], 
            on='year', 
            how='left'
        )
        
        if comp_data.empty:
            continue
            
        # Shift borrowings to compute YoY changes
        comp_data['prev_borrowings'] = comp_data['borrowings'].shift(1)
        
        for idx, row in comp_data.iterrows():
            yr = row['year']
            cfo = row['cash_from_operations_cr']
            cfi = row['capex_cr']  # Absolute proxy for capex
            cff = row['free_cash_flow_cr'] - row['cash_from_operations_cr'] # backout CFF sign from cashflow table if needed, or join cashflow table
            
            # Fetch actual cashflow signs from cashflow table
            # (In loader.py, cashflow table stores operating_activity, investing_activity, financing_activity)
            # Let's get them from SQLite cashflow table directly for exact signs
            # (But we can also query the database or calculate it)
            
            # Let's write a database fetch inside the loop for simplicity, or we could have queried cashflow table initially.
            # Querying the database cashflow table directly inside is clean
            conn = sqlite3.connect(DB_PATH)
            cf_row = pd.read_sql("SELECT * FROM cashflow WHERE company_id = ? AND year = ?", conn, params=[ticker, yr])
            conn.close()
            
            if not cf_row.empty:
                cff_actual = cf_row.iloc[0]['financing_activity']
                cfo_actual = cf_row.iloc[0]['operating_activity']
            else:
                cff_actual = 0.0
                cfo_actual = 0.0
                
            borrowings_curr = row['borrowings']
            borrowings_prev = row['prev_borrowings']
            
            # Debt Repayment Detection: CFF < 0 and borrowings declining YoY
            deleveraging = "No"
            if cff_actual is not None and cff_actual < 0:
                if borrowings_curr is not None and borrowings_prev is not None:
                    if borrowings_curr < borrowings_prev:
                        deleveraging = "Deleveraging"

            # Distress Pattern: CFO < 0 and CFF > 0 (funding operations via debt/equity)
            distress_signal = "Healthy"
            if cfo_actual is not None and cff_actual is not None:
                if cfo_actual < 0 and cff_actual > 0:
                    distress_signal = "Distress Signal"
                    distress_alerts.append({
                        'company_id': ticker,
                        'year': yr,
                        'cfo': cfo_actual,
                        'cff': cff_actual,
                        'issue': "Operational cash burn funded by financing inflows (debt/equity)"
                    })

            # CapEx Intensity Label (Page 22, 7.2)
            intensity = row['capex_intensity_pct']
            capex_label = get_capex_category(intensity)

            records.append({
                'company_id': ticker,
                'year': yr,
                'cfo_quality_score': row['cfo_quality_score'],
                'capex_intensity_pct': intensity,
                'capex_intensity_label': capex_label,
                'fcf_conversion_pct': row['fcf_conversion_pct'],
                'deleveraging_status': deleveraging,
                'distress_status': distress_signal,
                'capital_allocation_pattern': row['capital_allocation_pattern']
            })

    # Save Cash Flow Intelligence Excel
    df_intel = pd.DataFrame(records)
    df_intel.to_excel(CF_INTELLIGENCE_PATH, index=False)
    print(f"Generated {CF_INTELLIGENCE_PATH}.")

    # Save Alerts CSV
    df_alerts = pd.DataFrame(distress_alerts)
    df_alerts.to_csv(ALERTS_PATH, index=False)
    print(f"Generated {ALERTS_PATH}.")

def get_capex_category(intensity: Optional[float]) -> str:
    if intensity is None:
        return "medium"
    if intensity < 3.0:
        return "asset-light"
    elif intensity > 8.0:
        return "capital intensive"
    else:
        return "medium"

if __name__ == "__main__":
    run_cashflow_analysis()
