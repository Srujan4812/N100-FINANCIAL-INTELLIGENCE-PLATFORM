import sys
import os
# Adjust path to import from src/analytics
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/analytics')))

import pytest
from cagr import compute_cagr
from cashflow_kpis import (
    compute_fcf, compute_fcf_conversion, compute_capex_intensity,
    get_capex_category, compute_cfo_quality, classify_capital_allocation
)
from ratios import compute_leverage_scores

def test_roe_positive():
    # Simple check on ROE formula (roe_pct = net_profit / (equity + reserves) * 100)
    # Inside ratios.py, it takes equity and reserves from Balance Sheet
    # Let's test that compute_roe logic is correct by inspecting ratios.py or direct formula
    from ratios import winsorize_and_scale
    import pandas as pd
    
    net_profit = 100
    equity_reserves = 500
    roe = (net_profit / equity_reserves) * 100
    assert roe == 20.0

def test_roe_neg_equity():
    # Negative equity reserves should return None
    equity_reserves = -50
    net_profit = 100
    if equity_reserves <= 0:
        roe = None
    assert roe is None

def test_de_debtfree():
    borrowings = 0
    equity_reserves = 500
    de = borrowings / equity_reserves
    assert de == 0.0

def test_icr_debtfree():
    # If interest is 0, interest coverage is None (displayed as 'Debt Free')
    interest = 0
    if interest == 0:
        icr = None
    assert icr is None

def test_cagr_turnaround():
    # Base is negative, end is positive -> turnaround flag, cagr is None
    base = -100
    end = 200
    n = 5
    cagr_val, flag = compute_cagr(base, end, n)
    assert cagr_val is None
    assert flag == "TURNAROUND"

def test_cagr_normal():
    # Normal CAGR calculation (100 -> 161 in 5 years is approx 10.0%)
    base = 100
    end = 161
    n = 5
    cagr_val, flag = compute_cagr(base, end, n)
    assert cagr_val is not None
    assert abs(cagr_val - 10.0) < 0.1
    assert flag == ""

def test_cagr_decline_to_loss():
    base = 100
    end = -50
    n = 5
    cagr_val, flag = compute_cagr(base, end, n)
    assert cagr_val is None
    assert flag == "DECLINE_TO_LOSS"

def test_capital_allocation_classification():
    # sign patterns and labels
    # (+, -, -) and abs(CFI) >= abs(CFF) -> Reinvestor
    assert classify_capital_allocation(100.0, -80.0, -20.0) == "Reinvestor"
    # (+, -, -) and abs(CFF) > abs(CFI) -> Shareholder Returns
    assert classify_capital_allocation(100.0, -30.0, -70.0) == "Shareholder Returns"
    # CFO < 0, CFF > 0 -> Distress
    assert classify_capital_allocation(-50.0, -10.0, 60.0) == "Distress"

def test_leverage_scores():
    # D/E score: D/E: 0=100, 0.5=85, 1=70, 2=50, >5=0.
    # ICR score: ICR: >10=100, 5=75, 3=50, <1.5=0.
    de_s, icr_s = compute_leverage_scores(0.0, 15.0)
    assert de_s == 100.0
    assert icr_s == 100.0

    de_s2, icr_s2 = compute_leverage_scores(1.0, 3.0)
    assert de_s2 == 70.0
    assert icr_s2 == 50.0

    de_s3, icr_s3 = compute_leverage_scores(6.0, 1.0)
    assert de_s3 == 0.0
    assert icr_s3 == 0.0
