import re
import os
import pandas as pd
from datetime import datetime
from typing import Any, List, Dict, Tuple, Set

class DataValidator:
    def __init__(self, output_path: str = "validation_failures.csv"):
        self.output_path = output_path
        self.failures: List[Dict[str, Any]] = []

    def log_failure(self, rule_id: str, company_id: str, year: str, field: str, value: Any, issue: str, severity: str, action: str):
        """Log a validation failure with timestamp, severity, and action taken."""
        self.failures.append({
            'timestamp': datetime.now().isoformat(),
            'rule_id': rule_id,
            'company_id': company_id,
            'year': year,
            'field': field,
            'value': str(value),
            'issue': issue,
            'severity': severity,
            'action_taken': action
        })

    def save_failures(self):
        """Append or write all logged failures to validation_failures.csv."""
        if not self.failures:
            # If empty, create an empty file if it doesn't exist to satisfy AC
            if not os.path.exists(self.output_path):
                pd.DataFrame(columns=[
                    'timestamp', 'rule_id', 'company_id', 'year', 'field', 
                    'value', 'issue', 'severity', 'action_taken'
                ]).to_csv(self.output_path, index=False)
            return

        df_new = pd.DataFrame(self.failures)
        if os.path.exists(self.output_path):
            try:
                df_old = pd.read_csv(self.output_path)
                df_combined = pd.concat([df_old, df_new], ignore_index=True)
                df_combined.to_csv(self.output_path, index=False)
            except Exception:
                df_new.to_csv(self.output_path, index=False)
        else:
            df_new.to_csv(self.output_path, index=False)
        # Clear local failure list after saving
        self.failures = []

    def validate_companies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate companies master reference table.
        Rule DQ-01 (Critical): Company PK Uniqueness
        Rule DQ-08 (Critical): Ticker Format (2-12 chars)
        """
        if df.empty:
            return df
        
        # DQ-01: Company PK Uniqueness
        if df['id'].duplicated().any():
            dups = df['id'][df['id'].duplicated()].unique().tolist()
            for dup in dups:
                self.log_failure("DQ-01", str(dup), "N/A", "id", dup, "Duplicate company ticker in companies table", "CRITICAL", "Halt load")
            raise ValueError(f"CRITICAL DQ-01: Duplicate tickers found in companies table: {dups}")

        valid_rows = []
        for idx, row in df.iterrows():
            ticker = row['id']
            # DQ-08: Ticker Format
            if not isinstance(ticker, str) or len(ticker) < 2 or len(ticker) > 12:
                self.log_failure("DQ-08", str(ticker), "N/A", "id", ticker, f"Invalid ticker length ({len(str(ticker)) if ticker else 0}), must be 2-12 chars", "CRITICAL", "Reject row")
                continue
            valid_rows.append(row)
            
        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_time_series(self, df: pd.DataFrame, table_name: str, companies_set: Set[str]) -> pd.DataFrame:
        """
        Validates basic PK and FK rules for P&L, BS, Cash Flow tables.
        Rule DQ-02 (Critical): Annual PK Uniqueness (company_id, year)
        Rule DQ-03 (Critical): FK Integrity (company_id must exist in companies)
        Rule DQ-07 (Critical): Year Format YYYY-MM
        Rule DQ-08 (Critical): Ticker Format (2-12 chars)
        """
        if df.empty:
            return df

        # DQ-02: Annual PK Uniqueness (Deduplicate keeping last)
        duplicates = df.duplicated(subset=['company_id', 'year'], keep='last')
        if duplicates.any():
            dup_rows = df[df.duplicated(subset=['company_id', 'year'], keep=False)]
            for _, row in dup_rows.iterrows():
                self.log_failure("DQ-02", str(row['company_id']), str(row['year']), "company_id,year", f"{row['company_id']},{row['year']}", f"Duplicate composite key in {table_name}", "CRITICAL", "Deduplicate: keep last occurrence")
            df = df.drop_duplicates(subset=['company_id', 'year'], keep='last').copy()

        valid_rows = []
        for idx, row in df.iterrows():
            co_id = row['company_id']
            yr = row['year']

            # DQ-08: Ticker Format
            if not isinstance(co_id, str) or len(co_id) < 2 or len(co_id) > 12:
                self.log_failure("DQ-08", str(co_id), str(yr), "company_id", co_id, f"Invalid ticker length in {table_name}", "CRITICAL", "Reject row")
                continue

            # DQ-07: Year Format check
            if not isinstance(yr, str) or not re.match(r'^\d{4}-\d{2}$', yr):
                self.log_failure("DQ-07", str(co_id), str(yr), "year", yr, f"Invalid year format in {table_name}, must match YYYY-MM", "CRITICAL", "Reject row")
                continue

            # DQ-03: FK Integrity
            if co_id not in companies_set:
                self.log_failure("DQ-03", str(co_id), str(yr), "company_id", co_id, f"Orphan company ticker in {table_name} (FK constraint failed)", "CRITICAL", "Reject row")
                continue

            valid_rows.append(row)

        return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

    def validate_pnl(self, df: pd.DataFrame, sectors_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Validate P&L specific rules.
        Rule DQ-05 (Warning): OPM Cross-Check
        Rule DQ-06 (Warning): Positive Sales (for non-banks)
        Rule DQ-11 (Warning): Tax Rate Range (0 to 60)
        Rule DQ-12 (Warning): Dividend Payout Cap (<= 200%)
        Rule DQ-14 (Warning): EPS Sign Consistency
        """
        if df.empty:
            return df

        # Build bank list for DQ-06
        bank_tickers = set()
        if sectors_df is not None and not sectors_df.empty:
            # check sub_sector or broad_sector
            banks = sectors_df[sectors_df['broad_sector'].str.contains('Financial', case=False, na=False)]
            bank_tickers = set(banks['company_id'].tolist())

        for idx, row in df.iterrows():
            co_id = row['company_id']
            yr = row['year']
            sales = row.get('sales', 0)
            op_profit = row.get('operating_profit', 0)
            opm_pct = row.get('opm_percentage', 0)
            tax_pct = row.get('tax_percentage', 0)
            div_payout = row.get('dividend_payout', 0)
            net_profit = row.get('net_profit', 0)
            eps = row.get('eps', 0)

            # DQ-05: OPM Cross-Check
            if sales > 0:
                calc_opm = (op_profit / sales) * 100
                if abs(opm_pct - calc_opm) >= 1.0:
                    self.log_failure(
                        "DQ-05", co_id, yr, "opm_percentage", opm_pct,
                        f"OPM mismatch: reported {opm_pct}%, computed {calc_opm:.2f}%", 
                        "WARNING", "Flagged row. Will use computed OPM in ratios."
                    )

            # DQ-06: Positive Sales (Non-Banks)
            if co_id not in bank_tickers:
                if sales <= 0:
                    self.log_failure(
                        "DQ-06", co_id, yr, "sales", sales,
                        f"Sales <= 0 ({sales}) for non-bank company", 
                        "WARNING", "Flagged row. Exclude from growth CAGR."
                    )

            # DQ-11: Tax Rate Range
            if tax_pct is not None and (tax_pct < 0 or tax_pct > 60):
                self.log_failure(
                    "DQ-11", co_id, yr, "tax_percentage", tax_pct,
                    f"Tax rate out of bounds: {tax_pct}% (expected 0-60%)", 
                    "WARNING", "Flagged row."
                )

            # DQ-12: Dividend Payout Cap
            if div_payout is not None and div_payout > 200:
                self.log_failure(
                    "DQ-12", co_id, yr, "dividend_payout", div_payout,
                    f"Dividend payout exceeds cap: {div_payout}% (expected <= 200%)", 
                    "WARNING", "Flagged row. Suspected data entry error."
                )

            # DQ-14: EPS Sign Consistency
            if net_profit > 0 and (eps is not None and eps <= 0):
                self.log_failure(
                    "DQ-14", co_id, yr, "eps", eps,
                    f"Positive net profit ({net_profit}) but non-positive EPS ({eps})", 
                    "WARNING", "Flagged row."
                )

        return df

    def validate_balancesheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate Balance Sheet specific rules.
        Rule DQ-04 (Warning): Balance Sheet Balance (within 1% tolerance)
        Rule DQ-10 (Warning): Non-Negative Fixed Assets (coerce negative fixed assets to 0)
        Rule DQ-15 (Info): BSE/ASE Balance (strict equality)
        """
        if df.empty:
            return df

        for idx, row in df.iterrows():
            co_id = row['company_id']
            yr = row['year']
            total_assets = row.get('total_assets', 0)
            total_liab = row.get('total_liabilities', 0)
            fixed_assets = row.get('fixed_assets', 0)

            # DQ-04: Balance Sheet Balance
            if total_assets > 0:
                pct_diff = abs(total_assets - total_liab) / total_assets
                if pct_diff >= 0.01:
                    self.log_failure(
                        "DQ-04", co_id, yr, "total_assets,total_liabilities", 
                        f"{total_assets},{total_liab}",
                        f"Assets and liabilities mismatch: {total_assets} vs {total_liab} ({pct_diff*100:.2f}% diff)",
                        "WARNING", "Flagged row. Do not reject. Analyst review required."
                    )
                elif total_assets != total_liab:
                    # DQ-15: Info strict equality check
                    self.log_failure(
                        "DQ-15", co_id, yr, "total_assets,total_liabilities",
                        f"{total_assets},{total_liab}",
                        "Strict balance sheet assets & liabilities differ but within 1% tolerance",
                        "INFO", "Logged count for audit"
                    )

            # DQ-10: Non-Negative Fixed Assets
            if fixed_assets is not None and fixed_assets < 0:
                self.log_failure(
                    "DQ-10", co_id, yr, "fixed_assets", fixed_assets,
                    f"Negative fixed assets ({fixed_assets})", 
                    "WARNING", "Coerced fixed_assets to 0"
                )
                df.at[idx, 'fixed_assets'] = 0.0

        return df

    def validate_cashflow(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate Cash Flow specific rules.
        Rule DQ-09 (Warning): Net Cash Check (within 10 Cr tolerance)
        """
        if df.empty:
            return df

        for idx, row in df.iterrows():
            co_id = row['company_id']
            yr = row['year']
            cfo = row.get('operating_activity', 0)
            cfi = row.get('investing_activity', 0)
            cff = row.get('financing_activity', 0)
            net_cf = row.get('net_cash_flow', 0)

            # Check if any cash flow value is null, coerce to 0 for checks
            cfo_val = cfo if pd.notnull(cfo) else 0.0
            cfi_val = cfi if pd.notnull(cfi) else 0.0
            cff_val = cff if pd.notnull(cff) else 0.0
            net_cf_val = net_cf if pd.notnull(net_cf) else 0.0

            # DQ-09: Net Cash Check
            computed_net_cf = cfo_val + cfi_val + cff_val
            if abs(net_cf_val - computed_net_cf) > 10.0:  # 10 Crore tolerance
                self.log_failure(
                    "DQ-09", co_id, yr, "net_cash_flow", net_cf,
                    f"Net cash flow mismatch: reported {net_cf_val}, computed {computed_net_cf}",
                    "WARNING", "Flagged row. Will use computed net cash flow in analytics if needed."
                )

        return df

    def validate_documents(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate documents URLs (DQ-13) in parallel using ThreadPoolExecutor.
        Checks if requests can fetch URL headers. If it returns 404, flags it.
        Uses a local JSON cache to prevent redundant network requests and checks env.
        """
        import os
        import json
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if df.empty:
            return df

        if os.getenv("SKIP_URL_VALIDATION", "FALSE").strip().upper() == "TRUE":
            print("Skipping document URL validation (SKIP_URL_VALIDATION=TRUE).")
            return df

        cache_path = "data/url_cache.json"
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        # Load URL cache
        url_cache = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    url_cache = json.load(f)
            except Exception:
                pass

        urls_to_check = []
        for idx, row in df.iterrows():
            co_id = row['company_id']
            yr = row.get('Year')  # capital Y in documents.xlsx
            url = row.get('Annual_Report')

            if pd.isnull(url) or not str(url).startswith('http'):
                self.log_failure(
                    "DQ-13", co_id, str(yr), "Annual_Report", url,
                    "Missing or invalid URL structure", "WARNING", "Logged URL issue"
                )
                continue
            
            url_str = str(url)
            if url_str in url_cache:
                issue = url_cache[url_str]
                if issue:
                    self.log_failure("DQ-13", co_id, str(yr), "Annual_Report", url_str, issue, "WARNING", "Logged URL issue (from cache)")
                continue

            urls_to_check.append((idx, co_id, yr, url_str))

        if not urls_to_check:
            return df

        print(f"Checking {len(urls_to_check)} document URLs (not found in cache)...")

        def check_single_url(item):
            idx, co_id, yr, url = item
            try:
                # Use a quick HEAD check with a 1.0s timeout
                resp = requests.head(url, timeout=1.0, allow_redirects=True)
                if resp.status_code == 404:
                    return (idx, co_id, yr, url, "Annual Report PDF URL returned 404")
            except Exception as e:
                # Timeout/connection errors are logged as warnings but rows are kept
                return (idx, co_id, yr, url, f"URL check failed (timeout/error): {str(e)[:60]}")
            return (idx, co_id, yr, url, None)

        # Execute parallel requests using a pool of threads
        cache_updated = False
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_single_url, item) for item in urls_to_check]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    idx, co_id, yr, url, issue = res
                    # Cache result
                    url_cache[url] = issue
                    cache_updated = True
                    if issue:
                        self.log_failure("DQ-13", co_id, str(yr), "Annual_Report", url, issue, "WARNING", "Logged URL issue")

        # Save cache if updated
        if cache_updated:
            try:
                with open(cache_path, "w") as f:
                    json.dump(url_cache, f, indent=2)
            except Exception:
                pass

        return df

    def validate_coverage(self, pnl_df: pd.DataFrame, bs_df: pd.DataFrame, cf_df: pd.DataFrame, companies_set: Set[str]):
        """
        Rule DQ-16 (Warning): Coverage Check
        Flag companies that have < 5 years of historical financial records.
        """
        for ticker in companies_set:
            pnl_yrs = len(pnl_df[pnl_df['company_id'] == ticker])
            bs_yrs = len(bs_df[bs_df['company_id'] == ticker])
            cf_yrs = len(cf_df[cf_df['company_id'] == ticker])
            
            min_yrs = min(pnl_yrs, bs_yrs, cf_yrs)
            if min_yrs < 5:
                self.log_failure(
                    "DQ-16", ticker, "N/A", "P&L/BS/CF counts", min_yrs,
                    f"Insufficient history: only {min_yrs} years of coverage (expected >= 5)",
                    "WARNING", "Flagged company. Exclude from CAGR if < 3 years."
                )
