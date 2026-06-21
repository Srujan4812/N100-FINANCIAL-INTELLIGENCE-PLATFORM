import os
import sys
import pytest
import pandas as pd
from typing import Set

# Add src/etl to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/etl')))

from validator import DataValidator

@pytest.fixture
def validator():
    # Write test failures to a temp file to avoid corrupting main failures list
    val = DataValidator("tests/dq/test_failures.csv")
    val.failures = [] # clear any existing
    yield val
    # Clean up temp failures file if exists
    if os.path.exists("tests/dq/test_failures.csv"):
        os.remove("tests/dq/test_failures.csv")

def test_dq_01_duplicate_company_ticker(validator):
    # DQ-01: Company PK Uniqueness
    df = pd.DataFrame([
        {"id": "INFY", "company_name": "Infosys Ltd", "face_value": 5.0},
        {"id": "INFY", "company_name": "Infosys Duplicate", "face_value": 5.0}
    ])
    with pytest.raises(ValueError) as excinfo:
        validator.validate_companies(df)
    assert "DQ-01" in str(excinfo.value) or "Duplicate" in str(excinfo.value)
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-01"

def test_dq_08_invalid_ticker_format_companies(validator):
    # DQ-08: Ticker Format (2-12 chars)
    df = pd.DataFrame([
        {"id": "I", "company_name": "Short Ticker", "face_value": 1.0},
        {"id": "VERYLONGTICKERNAME", "company_name": "Long Ticker", "face_value": 1.0},
        {"id": "TCS", "company_name": "Valid Ticker", "face_value": 1.0}
    ])
    res = validator.validate_companies(df)
    assert len(res) == 1
    assert res.iloc[0]["id"] == "TCS"
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-08"

def test_dq_02_duplicate_year_composite_pk(validator):
    # DQ-02: Composite PK in time-series
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100},
        {"company_id": "TCS", "year": "2023-03", "sales": 120}
    ])
    res = validator.validate_time_series(df, "profitandloss", {"TCS"})
    # Checks deduplication (keep last)
    assert len(res) == 1
    assert res.iloc[0]["sales"] == 120
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-02"

def test_dq_03_foreign_key_integrity(validator):
    # DQ-03: Company must exist in companies_set
    df = pd.DataFrame([
        {"company_id": "ORPHAN", "year": "2023-03"},
        {"company_id": "TCS", "year": "2023-03"}
    ])
    res = validator.validate_time_series(df, "profitandloss", {"TCS"})
    assert len(res) == 1
    assert res.iloc[0]["company_id"] == "TCS"
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-03"

def test_dq_07_invalid_year_format(validator):
    # DQ-07: Year format matching YYYY-MM
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023"},
        {"company_id": "TCS", "year": "FY24"},
        {"company_id": "TCS", "year": "2023-03"}
    ])
    res = validator.validate_time_series(df, "profitandloss", {"TCS"})
    assert len(res) == 1
    assert res.iloc[0]["year"] == "2023-03"
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-07"

def test_dq_05_opm_cross_check(validator):
    # DQ-05: OPM Mismatch (Warning)
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100.0, "expenses": 80.0, "operating_profit": 20.0, "opm_percentage": 50.0}
    ])
    res = validator.validate_pnl(df)
    assert len(res) == 1
    # Check that warning is logged for mismatch
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-05"

def test_dq_06_non_bank_positive_sales(validator):
    # DQ-06: Sales <= 0 for non-banks
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 0.0}
    ])
    res = validator.validate_pnl(df)
    assert len(res) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-06"

def test_dq_11_tax_rate_range(validator):
    # DQ-11: Tax rate between 0 and 60
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100.0, "tax_percentage": -5.0},
        {"company_id": "TCS", "year": "2024-03", "sales": 100.0, "tax_percentage": 75.0}
    ])
    res = validator.validate_pnl(df)
    assert len(res) == 2
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-11"

def test_dq_12_dividend_payout_cap(validator):
    # DQ-12: Dividend payout <= 200%
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100.0, "dividend_payout": 250.0}
    ])
    res = validator.validate_pnl(df)
    assert len(res) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-12"

def test_dq_14_eps_sign_consistency(validator):
    # DQ-14: Positive net profit with negative EPS
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100.0, "net_profit": 500.0, "eps": -2.0}
    ])
    res = validator.validate_pnl(df)
    assert len(res) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-14"

def test_dq_04_balance_sheet_balance(validator):
    # DQ-04: Assets and liabilities mismatch (1% tolerance)
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "total_assets": 100.0, "total_liabilities": 105.0}
    ])
    res = validator.validate_balancesheet(df)
    assert len(res) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-04"

def test_dq_10_negative_fixed_assets(validator):
    # DQ-10: Coerce negative fixed assets to 0
    df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "fixed_assets": -50.0}
    ])
    res = validator.validate_balancesheet(df)
    assert len(res) == 1
    assert res.iloc[0]["fixed_assets"] == 0.0
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-10"

def test_dq_09_net_cash_flow_check(validator):
    # DQ-09: Cash flow net check (10 Cr tolerance)
    df = pd.DataFrame([
        {
            "company_id": "TCS", "year": "2023-03", 
            "operating_activity": 100.0, 
            "investing_activity": -80.0, 
            "financing_activity": -10.0, 
            "net_cash_flow": 30.0 # reported is 30, computed is 10
        }
    ])
    res = validator.validate_cashflow(df)
    assert len(res) == 1
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-09"

def test_dq_16_coverage_check(validator):
    # DQ-16: Coverage Check (< 5 years)
    pnl = pd.DataFrame([{"company_id": "TCS", "year": "2023-03"}])
    bs = pd.DataFrame([{"company_id": "TCS", "year": "2023-03"}])
    cf = pd.DataFrame([{"company_id": "TCS", "year": "2023-03"}])
    
    validator.validate_coverage(pnl, bs, cf, {"TCS"})
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-16"
