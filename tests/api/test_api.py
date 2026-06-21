import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add src/api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/api')))

from main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert "db_row_counts" in json_data
    assert json_data["db_row_counts"]["companies"] == 92

def test_api_get_companies():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 92
    assert data[0]["id"] is not None
    assert data[0]["company_name"] is not None

def test_api_get_companies_filter():
    response = client.get("/api/v1/companies?sector=Information Technology")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for company in data:
        assert "Information Technology" in company["sector"]

def test_api_company_profile_valid():
    response = client.get("/api/v1/companies/INFY")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "INFY"
    assert "company_name" in data
    assert "latest_ratios" in data

def test_api_company_profile_invalid():
    response = client.get("/api/v1/companies/XYZ_INVALID_TICKER")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_api_company_pl():
    response = client.get("/api/v1/companies/INFY/pl")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "sales" in data[0]

def test_api_company_bs():
    response = client.get("/api/v1/companies/INFY/bs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "total_assets" in data[0]

def test_api_company_cashflow():
    response = client.get("/api/v1/companies/INFY/cashflow")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "operating_activity" in data[0]

def test_api_company_ratios():
    response = client.get("/api/v1/companies/INFY/ratios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "composite_quality_score" in data[0]

def test_api_screener():
    response = client.get("/api/v1/screener?min_roe=15&max_de=0.5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for row in data:
        assert row["return_on_equity_pct"] >= 15
        assert row["debt_to_equity"] <= 0.5

def test_api_sectors():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "sector" in data[0]
    assert "company_count" in data[0]

def test_api_sector_companies():
    response = client.get("/api/v1/sectors/Information Technology/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "ticker" in data[0]

def test_api_peer_group_valid():
    # Peer group name from DB, we know they are named after broad sectors
    response = client.get("/api/v1/peers/IT Services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_api_peer_group_invalid():
    response = client.get("/api/v1/peers/Nonexistent_Group_XYZ")
    assert response.status_code == 404

def test_api_peer_compare():
    response = client.get("/api/v1/companies/INFY/peers/compare")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "INFY"
    assert "company_values" in data
    assert "peer_average_values" in data

def test_api_market_cap():
    response = client.get("/api/v1/market-cap/INFY")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "pe_ratio" in data[0]

def test_api_portfolio_stats():
    response = client.get("/api/v1/portfolio/stats")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "metric" in data[0]

def test_api_company_documents():
    response = client.get("/api/v1/companies/INFY/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "annual_report_url" in data[0]

def test_api_tearsheet_download_valid():
    response = client.get("/api/v1/companies/INFY/tearsheet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

def test_api_tearsheet_download_invalid():
    response = client.get("/api/v1/companies/XYZ_INVALID_TICKER/tearsheet")
    assert response.status_code == 404
