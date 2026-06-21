import os
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = "data/nifty100.db"
PEER_EXPORT_PATH = "peer_comparison.xlsx"

def run_peer_analysis(year_val: Optional[str] = None) -> pd.DataFrame:
    """
    Runs peer group percentile analysis and gap checks.
    Saves formatted worksheets to peer_comparison.xlsx.
    """
    conn = sqlite3.connect(DB_PATH)
    
    if year_val is None:
        # Get latest year in ratios table
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(year) FROM financial_ratios")
        res = cursor.fetchone()
        year_val = res[0] if res and res[0] else "2024-03"

    # Load peer mappings and financial ratios
    df_pg = pd.read_sql("SELECT * FROM peer_groups", conn)
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios WHERE year = ?", conn, params=[year_val])
    df_companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
    
    conn.close()

    if df_pg.empty or df_ratios.empty:
        print("No peer groups or financial ratios available for peer analysis.")
        return pd.DataFrame()

    # Join datasets
    df = df_pg.merge(df_ratios, on='company_id', how='inner')
    df = df.merge(df_companies, left_on='company_id', right_on='id', how='inner')
    
    metrics = [
        'net_profit_margin_pct', 'operating_profit_margin_pct', 'return_on_equity_pct',
        'roce_percentage', 'debt_to_equity', 'interest_coverage', 'asset_turnover',
        'free_cash_flow_cr', 'capex_cr', 'earnings_per_share', 'book_value_per_share',
        'dividend_payout_ratio_pct', 'cfo_quality_score', 'fcf_conversion_pct',
        'revenue_cagr_5yr', 'pat_cagr_5yr', 'eps_cagr_5yr'
    ]

    # Compute percentiles within peer groups
    # Note: lower D/E is better, so we rank D/E in reverse
    percentiles_dict = {}
    for metric in metrics:
        if metric not in df.columns:
            continue
            
        # Reverse rank for D/E (lower is better, so lower D/E gets higher percentile)
        ascending = False if metric == 'debt_to_equity' else True
        
        # Calculate rank as percentile (0.0 to 1.0)
        df[f'{metric}_percentile'] = df.groupby('peer_group_name')[metric].rank(
            pct=True, ascending=ascending, method='min'
        )

    # Best-in-class / Weak detection (Page 20, 4.5 and 4.6)
    # 10 core metrics for classification:
    core_metrics = [
        'return_on_equity_pct', 'roce_percentage', 'net_profit_margin_pct',
        'debt_to_equity', 'free_cash_flow_cr', 'pat_cagr_5yr', 'revenue_cagr_5yr',
        'eps_cagr_5yr', 'cfo_quality_score', 'fcf_conversion_pct'
    ]

    df['best_in_class_count'] = 0
    df['weak_count'] = 0
    df['class_tag'] = "Normal"

    for idx, row in df.iterrows():
        bic = 0
        weak = 0
        for metric in core_metrics:
            pct_col = f'{metric}_percentile'
            if pct_col in df.columns:
                pct_val = row[pct_col]
                if pd.notnull(pct_val):
                    if pct_val >= 0.75:  # Top quartile
                        bic += 1
                    elif pct_val <= 0.25:  # Bottom quartile
                        weak += 1
        df.at[idx, 'best_in_class_count'] = bic
        df.at[idx, 'weak_count'] = weak
        if bic >= 6:
            df.at[idx, 'class_tag'] = "Best in Class"
        elif weak >= 4:
            df.at[idx, 'class_tag'] = "Watch List"

    # Export to Excel: One sheet per peer group
    unique_groups = df['peer_group_name'].unique()
    
    with pd.ExcelWriter(PEER_EXPORT_PATH, engine='openpyxl') as writer:
        for pg in unique_groups:
            df_group = df[df['peer_group_name'] == pg].copy()
            
            # Find benchmark row
            bench_rows = df_group[df_group['is_benchmark'] == 1]
            benchmark_company = bench_rows.iloc[0]['company_id'] if not bench_rows.empty else None
            
            # Side-by-side comparison output columns
            disp_cols = ['company_id', 'company_name', 'class_tag', 'is_benchmark'] + metrics
            df_disp = df_group[disp_cols].copy()
            
            # Write to excel sheet
            df_disp.to_excel(writer, sheet_name=pg[:30], index=False)
            
            # Formatting details can be loaded by openpyxl inside reporting engine
            
    print(f"Peer comparison analysis completed and exported to {PEER_EXPORT_PATH}.")
    return df
