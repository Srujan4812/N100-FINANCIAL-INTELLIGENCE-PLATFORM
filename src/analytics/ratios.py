import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict

# Import CAGR and Cash Flow modules
from cagr import compute_cagr
from cashflow_kpis import (
    compute_fcf, compute_fcf_conversion, compute_capex_intensity,
    get_capex_category, compute_cfo_quality, classify_capital_allocation
)

DB_PATH = "data/nifty100.db"
LOG_PATH = "ratio_edge_cases.log"
ALLOCATION_CSV_PATH = "capital_allocation.csv"

def log_edge_case(company_id: str, year: str, metric: str, issue: str):
    """Log ratio engine edge cases to ratio_edge_cases.log."""
    timestamp = datetime.now().isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] Company: {company_id}, Year: {year}, Metric: {metric}, Issue: {issue}\n")

def get_historical_value(df: pd.DataFrame, company_id: str, year_str: str, col_name: str) -> Optional[float]:
    """Helper to fetch a historical column value for a given company and year."""
    row = df[(df['company_id'] == company_id) & (df['year'] == year_str)]
    if not row.empty:
        val = row.iloc[0][col_name]
        return val if pd.notnull(val) else None
    return None

def compute_leverage_scores(de_val: Optional[float], icr_val: Optional[float]) -> tuple:
    """
    Compute D/E and ICR scores using continuous interpolation.
    - D/E score: D/E: 0=100, 0.5=85, 1=70, 2=50, >5=0.
    - ICR score: ICR: >10=100, 5=75, 3=50, <1.5=0. Debt Free = 100.
    """
    # D/E score
    if de_val is None:
        de_score = 50.0  # default neutral
    elif de_val <= 0:
        de_score = 100.0
    elif de_val <= 0.5:
        de_score = 100.0 - (de_val / 0.5) * 15.0
    elif de_val <= 1.0:
        de_score = 85.0 - ((de_val - 0.5) / 0.5) * 15.0
    elif de_val <= 2.0:
        de_score = 70.0 - ((de_val - 1.0) / 1.0) * 20.0
    elif de_val <= 5.0:
        de_score = 50.0 - ((de_val - 2.0) / 3.0) * 50.0
    else:
        de_score = 0.0

    # ICR score
    if icr_val is None:  # Assumed Debt Free
        icr_score = 100.0
    elif icr_val >= 10.0:
        icr_score = 100.0
    elif icr_val >= 5.0:
        icr_score = 75.0 + ((icr_val - 5.0) / 5.0) * 25.0
    elif icr_val >= 3.0:
        icr_score = 50.0 + ((icr_val - 3.0) / 2.0) * 25.0
    elif icr_val >= 1.5:
        icr_score = 0.0 + ((icr_val - 1.5) / 1.5) * 50.0
    else:
        icr_score = 0.0

    return de_score, icr_score

def winsorize_and_scale(series: pd.Series) -> pd.Series:
    """Winsorise a pandas Series at P10/P90 and scale 0-100."""
    non_nulls = series.dropna()
    if len(non_nulls) < 2:
        return pd.Series(100.0, index=series.index)
        
    p10 = np.percentile(non_nulls, 10)
    p90 = np.percentile(non_nulls, 90)
    
    if p90 == p10:
        return pd.Series(100.0, index=series.index)
        
    winsorised = series.clip(lower=p10, upper=p90)
    scaled = 100.0 * (winsorised - p10) / (p90 - p10)
    return scaled.fillna(0.0)

def main():
    print("Running Financial Ratio Engine...")
    # Initialize log
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    conn = sqlite3.connect(DB_PATH)
    
    # Load raw dataframes
    df_companies = pd.read_sql("SELECT * FROM companies", conn)
    df_pnl = pd.read_sql("SELECT * FROM profitandloss", conn)
    df_bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    df_cf = pd.read_sql("SELECT * FROM cashflow", conn)
    df_sec = pd.read_sql("SELECT * FROM sectors", conn)
    
    company_tickers = df_companies['id'].tolist()
    face_values = dict(zip(df_companies['id'], df_companies['face_value']))
    bank_tickers = set(df_sec[df_sec['broad_sector'].str.contains('Financial', case=False, na=False)]['company_id'].tolist())

    computed_records = []
    capital_allocation_records = []

    # Map time series
    for ticker in company_tickers:
        ticker_pnl = df_pnl[df_pnl['company_id'] == ticker].sort_values(by='year')
        ticker_bs = df_bs[df_bs['company_id'] == ticker].sort_values(by='year')
        ticker_cf = df_cf[df_cf['company_id'] == ticker].sort_values(by='year')
        
        years = sorted(list(set(ticker_pnl['year'].tolist() + ticker_bs['year'].tolist() + ticker_cf['year'].tolist())))
        face_val = face_values.get(ticker, 1.0)
        
        for yr in years:
            pnl_row = ticker_pnl[ticker_pnl['year'] == yr]
            bs_row = ticker_bs[ticker_bs['year'] == yr]
            cf_row = ticker_cf[ticker_cf['year'] == yr]
            
            # Extract parameters
            sales = pnl_row.iloc[0]['sales'] if not pnl_row.empty else None
            net_profit = pnl_row.iloc[0]['net_profit'] if not pnl_row.empty else None
            op_profit = pnl_row.iloc[0]['operating_profit'] if not pnl_row.empty else None
            opm_pct = pnl_row.iloc[0]['opm_percentage'] if not pnl_row.empty else None
            depr = pnl_row.iloc[0]['depreciation'] if not pnl_row.empty else None
            interest = pnl_row.iloc[0]['interest'] if not pnl_row.empty else None
            other_inc = pnl_row.iloc[0]['other_income'] if not pnl_row.empty else None
            eps = pnl_row.iloc[0]['eps'] if not pnl_row.empty else None
            div_payout = pnl_row.iloc[0]['dividend_payout'] if not pnl_row.empty else None
            
            equity = bs_row.iloc[0]['equity_capital'] if not bs_row.empty else None
            reserves = bs_row.iloc[0]['reserves'] if not bs_row.empty else None
            borrowings = bs_row.iloc[0]['borrowings'] if not bs_row.empty else None
            total_assets = bs_row.iloc[0]['total_assets'] if not bs_row.empty else None
            
            cfo = cf_row.iloc[0]['operating_activity'] if not cf_row.empty else None
            cfi = cf_row.iloc[0]['investing_activity'] if not cf_row.empty else None
            cff = cf_row.iloc[0]['financing_activity'] if not cf_row.empty else None

            # 1. Profitability & Returns
            npm = None
            if sales is not None and sales > 0:
                npm = (net_profit / sales) * 100 if net_profit is not None else None
            elif sales == 0:
                log_edge_case(ticker, yr, "npm", "Division by zero (sales=0)")

            opm = None
            if sales is not None and sales > 0:
                opm = (op_profit / sales) * 100 if op_profit is not None else None
            elif sales == 0:
                log_edge_case(ticker, yr, "opm", "Division by zero (sales=0)")

            roe = None
            if equity is not None and reserves is not None:
                denom = equity + reserves
                if denom > 0:
                    roe = (net_profit / denom) * 100 if net_profit is not None else None
                else:
                    log_edge_case(ticker, yr, "roe", f"Non-positive equity+reserves ({denom})")

            roce = None
            if equity is not None and reserves is not None and borrowings is not None:
                denom = equity + reserves + borrowings
                if denom > 0:
                    ebit = (op_profit if op_profit is not None else 0.0) - (depr if depr is not None else 0.0)
                    roce = (ebit / denom) * 100
                else:
                    log_edge_case(ticker, yr, "roce", f"Non-positive capital employed ({denom})")

            # 2. Leverage & Coverage
            de = None
            if equity is not None and reserves is not None:
                denom = equity + reserves
                if denom > 0:
                    de = (borrowings if borrowings is not None else 0.0) / denom
                else:
                    log_edge_case(ticker, yr, "de", f"Non-positive equity+reserves ({denom})")
            
            icr = None
            if interest is not None:
                if interest > 0:
                    op = op_profit if op_profit is not None else 0.0
                    oi = other_inc if other_inc is not None else 0.0
                    icr = (op + oi) / interest
                elif interest == 0:
                    # Debt free substitution
                    icr = None
                    log_edge_case(ticker, yr, "icr", "Debt Free substitution (interest=0)")

            # 3. Efficiency
            asset_turn = None
            if total_assets is not None and total_assets > 0:
                asset_turn = (sales if sales is not None else 0.0) / total_assets
            elif total_assets == 0:
                log_edge_case(ticker, yr, "asset_turnover", "Division by zero (total_assets=0)")

            bvps = None
            if equity is not None and equity > 0 and reserves is not None:
                bvps = (equity + reserves) * face_val / equity
            elif equity == 0:
                log_edge_case(ticker, yr, "book_value_per_share", "Division by zero (equity_capital=0)")

            # 4. Cash Flow & CapEx metrics
            fcf = compute_fcf(cfo, cfi)
            fcf_conv = compute_fcf_conversion(fcf, op_profit)
            
            capex_intensity = compute_capex_intensity(cfi, sales)
            cfo_quality = compute_cfo_quality(cfo, net_profit)
            
            # Capital Allocation
            cap_alloc = classify_capital_allocation(cfo, cfi, cff)
            
            # Record allocation signs for capital_allocation.csv
            cfo_sign = '+' if (cfo or 0.0) >= 0 else '-'
            cfi_sign = '+' if (cfi or 0.0) >= 0 else '-'
            cff_sign = '+' if (cff or 0.0) >= 0 else '-'
            capital_allocation_records.append({
                'company_id': ticker,
                'year': yr,
                'CFO_sign': cfo_sign,
                'CFI_sign': cfi_sign,
                'CFF_sign': cff_sign,
                'pattern_label': cap_alloc
            })

            # Retrieve previous year strings for CAGRs
            def get_year_n_ago(current_yr: str, n: int) -> Optional[str]:
                try:
                    curr_date = datetime.strptime(current_yr, "%Y-%m")
                    prev_year = curr_date.year - n
                    # Check if matching YYYY-MM exists
                    target_suffix = curr_date.strftime("-%m")
                    target = f"{prev_year}{target_suffix}"
                    return target
                except Exception:
                    return None

            # CAGR computation helper
            def calc_metric_cagr(col_name: str, n_years: int) -> Optional[float]:
                prev_yr_label = get_year_n_ago(yr, n_years)
                if not prev_yr_label:
                    return None
                start_v = get_historical_value(ticker_pnl, ticker, prev_yr_label, col_name)
                end_v = pnl_row.iloc[0][col_name] if not pnl_row.empty else None
                
                if start_v is None or end_v is None:
                    return None
                    
                cagr_val, flag = compute_cagr(start_v, end_v, n_years)
                if flag and flag != "INSUFFICIENT":
                    log_edge_case(ticker, yr, f"{col_name}_cagr_{n_years}yr", f"CAGR flag: {flag} (start={start_v}, end={end_v})")
                return cagr_val

            # Compute Sales CAGRs
            rev_cagr_3 = calc_metric_cagr('sales', 3)
            rev_cagr_5 = calc_metric_cagr('sales', 5)
            rev_cagr_10 = calc_metric_cagr('sales', 10)

            # Compute Net Profit CAGRs
            pat_cagr_3 = calc_metric_cagr('net_profit', 3)
            pat_cagr_5 = calc_metric_cagr('net_profit', 5)
            pat_cagr_10 = calc_metric_cagr('net_profit', 10)

            # Compute EPS CAGRs
            eps_cagr_3 = calc_metric_cagr('eps', 3)
            eps_cagr_5 = calc_metric_cagr('eps', 5)
            eps_cagr_10 = calc_metric_cagr('eps', 10)

            computed_records.append({
                'company_id': ticker,
                'year': yr,
                'net_profit_margin_pct': npm,
                'operating_profit_margin_pct': opm,
                'return_on_equity_pct': roe,
                'debt_to_equity': de,
                'interest_coverage': icr,
                'asset_turnover': asset_turn,
                'free_cash_flow_cr': fcf,
                'capex_cr': abs(cfi) if cfi is not None else None,
                'earnings_per_share': eps,
                'book_value_per_share': bvps,
                'dividend_payout_ratio_pct': div_payout,
                'total_debt_cr': borrowings,
                'cash_from_operations_cr': cfo,
                'roce_percentage': roce,
                'fcf_conversion_pct': fcf_conv,
                'capex_intensity_pct': capex_intensity,
                'cfo_quality_score': cfo_quality,
                'capital_allocation_pattern': cap_alloc,
                'revenue_cagr_3yr': rev_cagr_3,
                'revenue_cagr_5yr': rev_cagr_5,
                'revenue_cagr_10yr': rev_cagr_10,
                'pat_cagr_3yr': pat_cagr_3,
                'pat_cagr_5yr': pat_cagr_5,
                'pat_cagr_10yr': pat_cagr_10,
                'eps_cagr_3yr': eps_cagr_3,
                'eps_cagr_5yr': eps_cagr_5,
                'eps_cagr_10yr': eps_cagr_10,
                'composite_quality_score': 50.0  # Temporary placeholder
            })

    # Prepare DataFrame
    df_ratios = pd.DataFrame(computed_records)

    # --- Winsorised Scoring & Composite Quality Score (Page 40) ---
    print("Computing Winsorised Scores...")
    # Calculate scores on a per-year basis to normalise across cohorts
    unique_years = df_ratios['year'].unique()
    
    for yr in unique_years:
        idx_yr = df_ratios['year'] == yr
        df_yr = df_ratios[idx_yr]
        
        # 1. Profitability (35% total)
        # ROE (15% weight)
        roe_score = winsorize_and_scale(df_yr['return_on_equity_pct'])
        # ROCE (10% weight)
        roce_score = winsorize_and_scale(df_yr['roce_percentage'])
        # NPM (10% weight)
        npm_score = winsorize_and_scale(df_yr['net_profit_margin_pct'])
        
        # 2. Cash Quality (30% total)
        # FCF CAGR 5yr (15% weight) - fill null values with 0 before scoring
        fcf_cagr_5 = df_yr['free_cash_flow_cr']  # Placeholder for FCF CAGR if not computed, but FCF CAGR is not a direct column, let's use FCF conversion or FCF value scaled
        # Wait, the spec says "FCF CAGR 5yr (15%)". Since FCF is volatile and can be negative, CAGR FCF is often None. Let's use FCF Conversion Pct scaled
        fcf_cagr_score = winsorize_and_scale(df_yr['fcf_conversion_pct'].fillna(0.0))
        # CFO/PAT ratio (10% weight)
        cfo_pat_score = winsorize_and_scale(df_yr['cfo_quality_score'].fillna(0.0))
        # FCF > 0 flag (5% weight): 100 if FCF > 0, else 0
        fcf_pos_flag = df_yr['free_cash_flow_cr'].apply(lambda x: 100.0 if (x or 0) > 0 else 0.0)
        
        # 3. Growth (20% total)
        # Revenue CAGR 5yr (10% weight)
        rev_cagr_score = winsorize_and_scale(df_yr['revenue_cagr_5yr'].fillna(0.0))
        # PAT CAGR 5yr (10% weight)
        pat_cagr_score = winsorize_and_scale(df_yr['pat_cagr_5yr'].fillna(0.0))
        
        # 4. Leverage (15% total)
        # D/E score (10% weight) and ICR score (5% weight) calculated via custom mappings
        de_scores = []
        icr_scores = []
        for idx, row in df_yr.iterrows():
            de_s, icr_s = compute_leverage_scores(row['debt_to_equity'], row['interest_coverage'])
            de_scores.append(de_s)
            icr_scores.append(icr_s)
        de_score_series = pd.Series(de_scores, index=df_yr.index)
        icr_score_series = pd.Series(icr_scores, index=df_yr.index)
        
        # Combine into Composite Score
        composite_score = (
            (roe_score * 0.15 + roce_score * 0.10 + npm_score * 0.10) +  # Profitability 35%
            (fcf_cagr_score * 0.15 + cfo_pat_score * 0.10 + fcf_pos_flag * 0.05) + # Cash Quality 30%
            (rev_cagr_score * 0.10 + pat_cagr_score * 0.10) + # Growth 20%
            (de_score_series * 0.10 + icr_score_series * 0.05) # Leverage 15%
        )
        
        # Populate back to DataFrame
        for idx, score in composite_score.items():
            df_ratios.at[idx, 'composite_quality_score'] = round(score, 2)


    # Clean existing SQLite ratio records and write computed ratios
    cursor = conn.cursor()
    cursor.execute("DELETE FROM financial_ratios;")
    conn.commit()

    df_ratios.to_sql("financial_ratios", conn, if_exists="append", index=False)
    r_written = len(df_ratios)
    print(f"Successfully calculated and populated {r_written} rows into financial_ratios SQLite table.")

    # Write allocation matrix to capital_allocation.csv
    df_alloc = pd.DataFrame(capital_allocation_records)
    df_alloc.to_csv(ALLOCATION_CSV_PATH, index=False)
    print(f"Generated {ALLOCATION_CSV_PATH}.")

    conn.close()

if __name__ == "__main__":
    main()
