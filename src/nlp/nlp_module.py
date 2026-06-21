import os
import re
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

DB_PATH = "data/nifty100.db"
PARSED_CSV = "analysis_parsed.csv"
PROS_CONS_CSV = "pros_cons_generated.csv"
CROSS_VAL_CSV = "cross_validation.csv"

def parse_analysis_text():
    """
    Rule 9.1: Regex parser for analysis.xlsx text fields.
    Extracts CAGR numbers using r'(\d+)\s*Years?:?\s*([\d.]+)%'
    """
    print("Parsing analysis.xlsx qualitative text fields...")
    conn = sqlite3.connect(DB_PATH)
    df_an = pd.read_sql("SELECT * FROM analysis", conn)
    conn.close()

    parsed_records = []
    
    pattern = r'(\d+)\s*Years?:?\s*([\d.]+)%'
    
    fields = [
        ('compounded_sales_growth', 'Sales Growth'),
        ('compounded_profit_growth', 'Profit Growth'),
        ('stock_price_cagr', 'Stock Price CAGR'),
        ('roe', 'ROE')
    ]

    for _, row in df_an.iterrows():
        ticker = row['company_id']
        for field, metric_type in fields:
            text = row.get(field)
            if pd.notnull(text):
                # Search for all matches in text (e.g. "10 Years: 15% \n 5 Years: 12%")
                matches = re.findall(pattern, str(text), re.IGNORECASE)
                for period, val in matches:
                    parsed_records.append({
                        'company_id': ticker,
                        'metric_type': metric_type,
                        'period_years': int(period),
                        'value_pct': float(val)
                    })

    df_parsed = pd.DataFrame(parsed_records)
    df_parsed.to_csv(PARSED_CSV, index=False)
    print(f"Generated {PARSED_CSV}.")
    return df_parsed

def generate_rule_based_pros_cons():
    """
    Rule 9.2: Rule engine with 12 Pro rules + 12 Con rules to generate qualitative highlights
    and auto-fill gaps for 84 companies in prosandcons SQLite table.
    """
    print("Generating rule-based Pros & Cons...")
    conn = sqlite3.connect(DB_PATH)
    
    # Load all ratios and sectors
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    df_sec = pd.read_sql("SELECT * FROM sectors", conn)
    df_co = pd.read_sql("SELECT id FROM companies", conn)
    
    conn.close()

    if df_ratios.empty:
        print("No ratio data available for generating pros/cons.")
        return

    # Sort ratios by year to evaluate trends
    df_ratios = df_ratios.sort_values(by=['company_id', 'year'])
    
    generated_list = []

    for ticker in df_co['id'].tolist():
        comp_df = df_ratios[df_ratios['company_id'] == ticker]
        if comp_df.empty:
            continue
            
        latest_row = comp_df.iloc[-1]
        yr = latest_row['year']
        
        # Helper metrics
        roe = latest_row['return_on_equity_pct']
        roce = latest_row['roce_percentage']
        npm = latest_row['net_profit_margin_pct']
        opm = latest_row['operating_profit_margin_pct']
        de = latest_row['debt_to_equity']
        icr = latest_row['interest_coverage']
        fcf = latest_row['free_cash_flow_cr']
        sales = latest_row['net_profit_margin_pct'] # Sales/Revenue from P&L, let's just grab from ratio
        cfo_qual = latest_row['cfo_quality_score']
        fcf_conv = latest_row['fcf_conversion_pct']
        capex_int = latest_row['capex_intensity_pct']
        alloc = latest_row['capital_allocation_pattern']
        
        rev_cagr_5 = latest_row['revenue_cagr_5yr']
        pat_cagr_5 = latest_row['pat_cagr_5yr']
        eps_cagr_5 = latest_row['eps_cagr_5yr']
        
        # Historical arrays for trends
        fcfs = comp_df['free_cash_flow_cr'].tolist()
        opms = comp_df['operating_profit_margin_pct'].tolist()

        pros = []
        cons = []

        # --- 12 PRO RULES ---
        if roe is not None and roe > 20.0:
            pros.append("High latest return on equity (ROE > 20%)")
        if roce is not None and roce > 20.0:
            pros.append("High latest return on capital employed (ROCE > 20%)")
        if de is not None and de == 0:
            pros.append("Company is debt-free")
        if rev_cagr_5 is not None and rev_cagr_5 > 15.0:
            pros.append("Strong 5-year revenue growth (> 15% CAGR)")
        if pat_cagr_5 is not None and pat_cagr_5 > 15.0:
            pros.append("Strong 5-year net profit growth (> 15% CAGR)")
        if icr is not None and icr > 5.0:
            pros.append("Healthy interest coverage ratio (> 5x)")
        if len(fcfs) >= 3 and all(x > 0 for x in fcfs[-3:]):
            pros.append("Consistent positive Free Cash Flow generation over last 3 years")
        if npm is not None and npm > 15.0:
            pros.append("High net profit margin (> 15%) indicating pricing power")
        if alloc == "Reinvestor":
            pros.append("Efficient capital allocation: reinvesting cash flows into capital expansion")
        elif alloc == "Shareholder Returns":
            pros.append("Generous shareholder returns: returning cash to shareholders via dividends/buybacks")
        if fcf_conv is not None and fcf_conv > 60.0:
            pros.append("Efficient cash conversion: FCF/EBITDA > 60%")
        if cfo_qual is not None and cfo_qual > 1.0:
            pros.append("High earnings quality: Cash from Operations exceeds Net Profit")
        if eps_cagr_5 is not None and eps_cagr_5 > 12.0:
            pros.append("Consistent EPS growth (> 12% CAGR)")

        # --- 12 CON RULES ---
        if de is not None and de > 2.0:
            cons.append("High leverage: Debt to Equity > 2.0x")
        if len(fcfs) >= 3 and all(x < 0 for x in fcfs[-3:]):
            cons.append("Negative Free Cash Flow for 3 consecutive years")
        if rev_cagr_5 is not None and rev_cagr_5 < 5.0:
            cons.append("Low 5-year revenue growth (< 5% CAGR)")
        if icr is not None and icr < 1.5:
            cons.append("Poor interest coverage ratio (< 1.5x), potential debt servicing risk")
        if cfo_qual is not None and cfo_qual < 0.5:
            cons.append("Accrual risk: Cash from Operations is less than 50% of Net Profit")
        if len(opms) >= 3 and opms[-1] < opms[-2] < opms[-3]:
            cons.append("Operating profit margins are on a declining trend YoY")
        if roe is not None and roe < 10.0:
            cons.append("Low return on equity (ROE < 10%)")
        if fcf_conv is not None and fcf_conv < 30.0:
            cons.append("Poor cash conversion: FCF/EBITDA < 30%")
        if pat_cagr_5 is not None and pat_cagr_5 < 5.0:
            cons.append("Stagnant or declining 5-year profit growth (< 5% CAGR)")
        if capex_int is not None and capex_int > 15.0:
            cons.append("High capital expenditure intensity (> 15% of sales) eating into returns")
        # Check if asset turn is low
        if latest_row['asset_turnover'] is not None and latest_row['asset_turnover'] < 0.5:
            cons.append("Low asset turnover (< 0.5x), indicating poor asset utilisation efficiency")
        if alloc == "Distress":
            cons.append("Distress cash flow pattern: operating cash burn funded by financing inflows")

        # Save to list
        for pro in pros:
            generated_list.append({
                'company_id': ticker,
                'type': 'PRO',
                'text': pro,
                'confidence_pct': 90.0
            })
        for con in cons:
            generated_list.append({
                'company_id': ticker,
                'type': 'CON',
                'text': con,
                'confidence_pct': 90.0
            })

    df_gen = pd.DataFrame(generated_list)
    df_gen.to_csv(PROS_CONS_CSV, index=False)
    print(f"Generated {PROS_CONS_CSV}.")

    # Load into prosandcons SQLite table (only for companies with missing records)
    # Check companies currently in DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT company_id FROM prosandcons")
    existing_companies = {r[0] for r in cursor.fetchall()}
    
    # Insert new rules for companies not currently populated
    insert_records = []
    # Assign unique IDs manually starting from MAX(id)+1
    cursor.execute("SELECT IFNULL(MAX(id), 0) FROM prosandcons")
    next_id = cursor.fetchone()[0] + 1
    
    for ticker in df_co['id'].tolist():
        if ticker not in existing_companies:
            co_pros = [x['text'] for x in generated_list if x['company_id'] == ticker and x['type'] == 'PRO']
            co_cons = [x['text'] for x in generated_list if x['company_id'] == ticker and x['type'] == 'CON']
            
            # Combine into list of pros and list of cons
            max_len = max(len(co_pros), len(co_cons))
            for i in range(max_len):
                pro_text = co_pros[i] if i < len(co_pros) else None
                con_text = co_cons[i] if i < len(co_cons) else None
                
                insert_records.append((next_id, ticker, pro_text, con_text))
                next_id += 1
                
    if insert_records:
        cursor.executemany(
            "INSERT INTO prosandcons (id, company_id, pros, cons) VALUES (?, ?, ?, ?)",
            insert_records
        )
        conn.commit()
        print(f"Auto-filled gaps for {len(existing_companies)} to {len(df_co)} companies. Loaded {len(insert_records)} qualitative rows into prosandcons SQLite table.")
    
    conn.close()

def cross_validate_cagrs(df_parsed: pd.DataFrame):
    """
    Rule 9.5: Compare parsed CAGR vs computed CAGR in financial_ratios table.
    Flags >5% absolute divergence.
    """
    print("Cross-validating CAGR values...")
    conn = sqlite3.connect(DB_PATH)
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    conn.close()

    if df_ratios.empty or df_parsed.empty:
        print("CAGR cross-validation skipped due to empty datasets.")
        return

    # Filter ratios for latest year
    latest_year = df_ratios['year'].max()
    df_latest = df_ratios[df_ratios['year'] == latest_year]
    
    validation_failures = []

    for _, row in df_parsed.iterrows():
        ticker = row['company_id']
        metric = row['metric_type']
        period = row['period_years']
        parsed_val = row['value_pct']

        # Only check 5-year or 10-year CAGR
        if period not in [3, 5, 10]:
            continue

        # Map metric type to ratio column
        ratio_col = None
        if metric == 'Sales Growth':
            ratio_col = f'revenue_cagr_{period}yr'
        elif metric == 'Profit Growth':
            ratio_col = f'pat_cagr_{period}yr'
        elif metric == 'ROE' and period == 10:
            # ROE 10Y check is not CAGR but average, we can skip or check
            continue

        if ratio_col:
            # Get ratio engine value
            co_row = df_latest[df_latest['company_id'] == ticker]
            if not co_row.empty:
                computed_val = co_row.iloc[0][ratio_col]
                if pd.notnull(computed_val):
                    divergence = abs(parsed_val - computed_val)
                    if divergence > 5.0:
                        validation_failures.append({
                            'company_id': ticker,
                            'metric': f"{metric} {period}Yr",
                            'parsed_value': parsed_val,
                            'computed_value': computed_val,
                            'divergence_pct': round(divergence, 2)
                        })

    df_cross = pd.DataFrame(validation_failures)
    df_cross.to_csv(CROSS_VAL_CSV, index=False)
    print(f"Generated {CROSS_VAL_CSV}. Logged {len(df_cross)} CAGR validation divergences.")

def main():
    df_parsed = parse_analysis_text()
    generate_rule_based_pros_cons()
    cross_validate_cagrs(df_parsed)

if __name__ == "__main__":
    main()
