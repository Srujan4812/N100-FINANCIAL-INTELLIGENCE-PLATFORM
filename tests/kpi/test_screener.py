import sys
import os
# Adjust path to import from src/analytics
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/analytics')))
# For config files
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/analytics/screener')))

import pytest
import pandas as pd
from engine import load_screener_config, run_screener

def test_load_config():
    config = load_screener_config()
    assert "presets" in config
    assert "Quality Compounder" in config["presets"]
    assert "Value Pick" in config["presets"]
def test_run_screener_preset():
    df, desc = run_screener(preset_name="Quality Compounder")
    assert isinstance(df, pd.DataFrame)
    assert "High return" in desc or "No records found" in desc
def test_run_screener_custom():
    custom_filters = {
        'min_roe': 15.0,
        'max_de': 1.0
    }
    df, desc = run_screener(custom_filters=custom_filters)
    assert isinstance(df, pd.DataFrame)
    assert desc == "Custom Search" or "No records found" in desc
    if not df.empty:
        assert (df['return_on_equity_pct'] >= 15.0).all()
        assert (df['debt_to_equity'] <= 1.0).all()
