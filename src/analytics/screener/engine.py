import os
import sqlite3
import yaml
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = "data/nifty100.db"
CONFIG_PATH = "config/screener_config.yaml"

def load_screener_config() -> Dict[str, Any]:
    """Load configurations from config/screener_config.yaml."""
    if not os.path.exists(CONFIG_PATH):
        return {"presets": {}}
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def get_latest_ratio_year(conn: sqlite3.Connection) -> str:
    """Helper to fetch the latest year present in financial_ratios table."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    res = cursor.fetchone()
    return res[0] if res and res[0] else "2024-03"

def run_screener(
    preset_name: Optional[str] = None, 
    custom_filters: Optional[Dict[str, Any]] = None,
    year_val: Optional[str] = None
) -> Tuple[pd.DataFrame, str]:
    """
    Executes stock screener query.
    If preset_name is provided, loads filters from YAML.
    Otherwise applies custom_filters.
    If year_val is None, defaults to the latest year in DB.
    """
    conn = sqlite3.connect(DB_PATH)
    
    if year_val is None:
        year_val = get_latest_ratio_year(conn)
        
    # Standard query joining ratios, companies, sectors, and valuation multiples
    query = """
        SELECT 
            r.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,
            r.year,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.return_on_equity_pct,
            r.roce_percentage,
            r.debt_to_equity,
            r.interest_coverage,
            r.asset_turnover,
            r.free_cash_flow_cr,
            r.capex_cr,
            r.earnings_per_share,
            r.book_value_per_share,
            r.dividend_payout_ratio_pct,
            r.revenue_cagr_3yr,
            r.revenue_cagr_5yr,
            r.revenue_cagr_10yr,
            r.pat_cagr_3yr,
            r.pat_cagr_5yr,
            r.pat_cagr_10yr,
            r.eps_cagr_3yr,
            r.eps_cagr_5yr,
            r.eps_cagr_10yr,
            r.composite_quality_score,
            m.market_cap_crore,
            m.enterprise_value_crore,
            m.pe_ratio,
            m.pb_ratio,
            m.ev_ebitda,
            m.dividend_yield_pct,
            p.sales,
            p.net_profit
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        JOIN sectors s ON r.company_id = s.company_id
        JOIN market_cap m ON r.company_id = m.company_id 
             AND CAST(substr(r.year, 1, 4) AS INTEGER) = m.year
        JOIN profitandloss p ON r.company_id = p.company_id 
             AND r.year = p.year
        WHERE r.year = ?
    """
    
    df = pd.read_sql(query, conn, params=[year_val])
    conn.close()
    
    if df.empty:
        return df, f"No records found for year {year_val}"
        
    # Calculate FCF Yield: FCF / Market_Cap * 100
    df['fcf_yield'] = df.apply(
        lambda row: (row['free_cash_flow_cr'] / row['market_cap_crore'] * 100)
        if pd.notnull(row['free_cash_flow_cr']) and pd.notnull(row['market_cap_crore']) and row['market_cap_crore'] > 0
        else 0.0,
        axis=1
    )

    filters = {}
    ranking_metric = "composite_quality_score"
    sort_ascending = False
    description = "Custom Search"

    if preset_name:
        config = load_screener_config()
        presets = config.get("presets", {})
        if preset_name in presets:
            preset_conf = presets[preset_name]
            filters = preset_conf.get("filters", {})
            ranking_metric = preset_conf.get("ranking_metric", "composite_quality_score")
            sort_ascending = preset_conf.get("sort_ascending", False)
            description = preset_conf.get("description", preset_name)
        else:
            return pd.DataFrame(), f"Preset '{preset_name}' not found in screener config."
    elif custom_filters:
        filters = custom_filters

    # Apply filters
    filtered_df = df.copy()
    
    # Map input keys to dataframe column names
    filter_mapping = {
        'min_roe': ('return_on_equity_pct', '>='),
        'max_de': ('debt_to_equity', '<='),
        'min_fcf': ('free_cash_flow_cr', '>='),
        'min_revenue_cagr_5yr': ('revenue_cagr_5yr', '>='),
        'min_revenue_cagr_3yr': ('revenue_cagr_3yr', '>='),
        'min_pat_cagr_5yr': ('pat_cagr_5yr', '>='),
        'max_pe': ('pe_ratio', '<='),
        'max_pb': ('pb_ratio', '<='),
        'min_dividend_yield': ('dividend_yield_pct', '>='),
        'max_dividend_payout': ('dividend_payout_ratio_pct', '<='),
        'min_sales': ('sales', '>='),
    }

    for key, threshold in filters.items():
        if threshold is None:
            continue
        if key in filter_mapping:
            col, op = filter_mapping[key]
            if col in filtered_df.columns:
                # Filter out null values for the column first
                filtered_df = filtered_df[filtered_df[col].notnull()]
                if op == '>=':
                    filtered_df = filtered_df[filtered_df[col] >= float(threshold)]
                elif op == '<=':
                    filtered_df = filtered_df[filtered_df[col] <= float(threshold)]
                    
    # Sort results
    if ranking_metric in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by=ranking_metric, ascending=not sort_ascending)
        
    return filtered_df, description
