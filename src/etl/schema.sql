-- Schema for Nifty 100 Financial Intelligence Platform SQLite database
PRAGMA foreign_keys = ON;

-- 1. Master companies table
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR PRIMARY KEY,
    company_logo TEXT,
    company_name VARCHAR NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value NUMERIC NOT NULL,
    book_value NUMERIC,
    roce_percentage NUMERIC,
    roe_percentage NUMERIC
);

-- 2. Profit and Loss statement
CREATE TABLE IF NOT EXISTS profitandloss (
    company_id VARCHAR NOT NULL,
    year VARCHAR NOT NULL,
    sales NUMERIC NOT NULL,
    expenses NUMERIC NOT NULL,
    operating_profit NUMERIC NOT NULL,
    opm_percentage NUMERIC NOT NULL,
    other_income NUMERIC,
    interest NUMERIC,
    depreciation NUMERIC,
    profit_before_tax NUMERIC,
    tax_percentage NUMERIC,
    net_profit NUMERIC,
    eps NUMERIC,
    dividend_payout NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 3. Balance Sheet statement
CREATE TABLE IF NOT EXISTS balancesheet (
    company_id VARCHAR NOT NULL,
    year VARCHAR NOT NULL,
    equity_capital NUMERIC NOT NULL,
    reserves NUMERIC,
    borrowings NUMERIC,
    other_liabilities NUMERIC,
    total_liabilities NUMERIC NOT NULL,
    fixed_assets NUMERIC,
    cwip NUMERIC,
    investments NUMERIC,
    other_asset NUMERIC,
    total_assets NUMERIC NOT NULL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 4. Cash Flow statement
CREATE TABLE IF NOT EXISTS cashflow (
    company_id VARCHAR NOT NULL,
    year VARCHAR NOT NULL,
    operating_activity NUMERIC,
    investing_activity NUMERIC,
    financing_activity NUMERIC,
    net_cash_flow NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 5. Qualitative/growth metrics analysis
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 6. Annual Report documents links
CREATE TABLE IF NOT EXISTS documents (
    company_id VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    Annual_Report TEXT,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 7. Pros and Cons text (qualitative observations)
CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 8. Company sector mapping
CREATE TABLE IF NOT EXISTS sectors (
    company_id VARCHAR PRIMARY KEY,
    broad_sector VARCHAR NOT NULL,
    sub_sector VARCHAR NOT NULL,
    index_weight_pct NUMERIC,
    market_cap_category VARCHAR,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 9. Monthly simulated stock price history
CREATE TABLE IF NOT EXISTS stock_prices (
    company_id VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume INTEGER,
    adjusted_close NUMERIC,
    PRIMARY KEY (company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 10. Valuation parameters
CREATE TABLE IF NOT EXISTS market_cap (
    company_id VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    market_cap_crore NUMERIC,
    enterprise_value_crore NUMERIC,
    pe_ratio NUMERIC,
    pb_ratio NUMERIC,
    ev_ebitda NUMERIC,
    dividend_yield_pct NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 11. Calculated financial ratios
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id VARCHAR NOT NULL,
    year VARCHAR NOT NULL,
    net_profit_margin_pct NUMERIC,
    operating_profit_margin_pct NUMERIC,
    return_on_equity_pct NUMERIC,
    debt_to_equity NUMERIC,
    interest_coverage NUMERIC,
    asset_turnover NUMERIC,
    free_cash_flow_cr NUMERIC,
    capex_cr NUMERIC,
    earnings_per_share NUMERIC,
    book_value_per_share NUMERIC,
    dividend_payout_ratio_pct NUMERIC,
    total_debt_cr NUMERIC,
    cash_from_operations_cr NUMERIC,
    roce_percentage NUMERIC,
    fcf_conversion_pct NUMERIC,
    capex_intensity_pct NUMERIC,
    cfo_quality_score NUMERIC,
    capital_allocation_pattern VARCHAR,
    revenue_cagr_3yr NUMERIC,
    revenue_cagr_5yr NUMERIC,
    revenue_cagr_10yr NUMERIC,
    pat_cagr_3yr NUMERIC,
    pat_cagr_5yr NUMERIC,
    pat_cagr_10yr NUMERIC,
    eps_cagr_3yr NUMERIC,
    eps_cagr_5yr NUMERIC,
    eps_cagr_10yr NUMERIC,
    composite_quality_score NUMERIC,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);

-- 12. Peer comparison groups mapping
CREATE TABLE IF NOT EXISTS peer_groups (
    peer_group_name VARCHAR NOT NULL,
    company_id VARCHAR NOT NULL,
    is_benchmark INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (peer_group_name, company_id),
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);
