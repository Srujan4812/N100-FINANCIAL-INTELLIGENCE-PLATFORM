import sys
import os
# Adjust path to import from src/etl
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/etl')))

from normaliser import normalize_year, normalize_ticker

def test_year_mar23():
    assert normalize_year("Mar-23") == "2023-03"

def test_year_fy24():
    assert normalize_year("FY24") == "2024-03"

def test_year_dec22():
    assert normalize_year("Dec-22") == "2022-12"

def test_year_garbage():
    assert normalize_year("xyz") == "PARSE_ERROR"

def test_ticker_strip():
    assert normalize_ticker(" TCS ") == "TCS"

def test_ticker_lower():
    assert normalize_ticker("tcs") == "TCS"

def test_year_integer():
    assert normalize_year(2023) == "2023-03"

def test_year_march2023():
    assert normalize_year("March-2023") == "2023-03"

def test_ticker_special_chars():
    assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"
    assert normalize_ticker("M&M") == "M&M"

def test_ticker_missing():
    assert normalize_ticker(None) == "MISSING"
    assert normalize_ticker("") == "MISSING"
