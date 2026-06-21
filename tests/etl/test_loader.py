import os
import sqlite3
import pytest

DB_PATH = "data/nifty100.db"

def test_db_exists():
    assert os.path.exists(DB_PATH)

def test_db_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()

    expected_tables = [
        'companies', 'profitandloss', 'balancesheet', 'cashflow', 'analysis',
        'documents', 'prosandcons', 'sectors', 'stock_prices', 'market_cap',
        'financial_ratios', 'peer_groups'
    ]
    for table in expected_tables:
        assert table in tables

def test_companies_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies;")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 92

def test_pnl_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM profitandloss;")
    count = cursor.fetchone()[0]
    conn.close()
    assert count > 1000

def test_balancesheet_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM balancesheet;")
    count = cursor.fetchone()[0]
    conn.close()
    assert count > 1000

def test_sectors_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sectors;")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 92
