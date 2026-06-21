import os
import sqlite3
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = "data/nifty100.db"
START_TIME = datetime.now()

app = FastAPI(
    title="Nifty 100 Financial Intelligence REST API",
    description="Backend API exposing fundamental financial data, screener, and reports for Nifty 100 companies.",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get DB connection
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Nifty 100 Financial Intelligence REST API. Navigate to /docs for the interactive Swagger documentation.",
        "docs_url": "/docs",
        "api_prefix": "/api/v1"
    }

# 1. health endpoint
@app.get("/api/v1/health")
def get_health():
    """Server health check. Returns DB row counts and server uptime."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        counts = {}
        tables = [
            'companies', 'profitandloss', 'balancesheet', 'cashflow', 'analysis',
            'documents', 'prosandcons', 'sectors', 'stock_prices', 'market_cap',
            'financial_ratios', 'peer_groups'
        ]
        for t in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cursor.fetchone()[0]
            except Exception:
                counts[t] = 0
        conn.close()
        
        uptime = str(datetime.now() - START_TIME)
        return {
            "status": "healthy",
            "uptime": uptime,
            "db_row_counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# 2. companies endpoint
@app.get("/api/v1/companies")
def get_companies(sector: Optional[str] = None):
    """List all 92 companies with id, name, sector. Supports ?sector= filter."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    if sector:
        query = """
            SELECT c.id, c.company_name, s.broad_sector as sector 
            FROM companies c 
            JOIN sectors s ON c.id = s.company_id 
            WHERE s.broad_sector LIKE ?
            ORDER BY c.id
        """
        cursor.execute(query, (f"%{sector}%",))
    else:
        query = """
            SELECT c.id, c.company_name, s.broad_sector as sector 
            FROM companies c 
            JOIN sectors s ON c.id = s.company_id 
            ORDER BY c.id
        """
        cursor.execute(query)
        
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 3. company profile endpoint
@app.get("/api/v1/companies/{ticker}")
def get_company_profile(ticker: str):
    """Full company profile: KPIs, pros/cons, sector, description."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check if company exists
    cursor.execute("SELECT * FROM companies WHERE id = ?", (ticker_upper,))
    co = cursor.fetchone()
    if not co:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker_upper}' not found.")
        
    cursor.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker_upper,))
    sec = cursor.fetchone()
    
    cursor.execute("SELECT pros, cons FROM prosandcons WHERE company_id = ?", (ticker_upper,))
    pc_rows = cursor.fetchall()
    pros = [r['pros'] for r in pc_rows if r['pros']]
    cons = [r['cons'] for r in pc_rows if r['cons']]
    
    # Get latest year ratios
    cursor.execute("""
        SELECT * FROM financial_ratios 
        WHERE company_id = ? 
        ORDER BY year DESC LIMIT 1
    """, (ticker_upper,))
    latest_ratios = cursor.fetchone()
    
    conn.close()
    
    return {
        "ticker": co["id"],
        "company_name": co["company_name"],
        "about_company": co["about_company"],
        "industry": None,
        "face_value": co["face_value"],
        "sector": dict(sec) if sec else None,
        "pros": pros,
        "cons": cons,
        "latest_ratios": dict(latest_ratios) if latest_ratios else None
    }

# 4. P&L history endpoint
@app.get("/api/v1/companies/{ticker}/pl")
def get_company_pl(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """P&L history for a company. Supports ?from_year= ?to_year= filters."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    query = "SELECT * FROM profitandloss WHERE company_id = ?"
    params = [ticker_upper]
    
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
        
    query += " ORDER BY year ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 5. Balance Sheet history endpoint
@app.get("/api/v1/companies/{ticker}/bs")
def get_company_bs(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """Balance sheet history. Same year filters."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    query = "SELECT * FROM balancesheet WHERE company_id = ?"
    params = [ticker_upper]
    
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
        
    query += " ORDER BY year ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 6. Cash Flow history endpoint
@app.get("/api/v1/companies/{ticker}/cashflow")
def get_company_cashflow(ticker: str, from_year: Optional[str] = None, to_year: Optional[str] = None):
    """Cash flow history. Same year filters."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    query = "SELECT * FROM cashflow WHERE company_id = ?"
    params = [ticker_upper]
    
    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)
        
    query += " ORDER BY year ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 7. Pre-computed KPIs endpoint
@app.get("/api/v1/companies/{ticker}/ratios")
def get_company_ratios(ticker: str):
    """All pre-computed KPIs per year for one company."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    cursor.execute("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC", (ticker_upper,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 8. Pre-generated tearsheet PDF endpoint (binary download)
@app.get("/api/v1/companies/{ticker}/tearsheet")
def get_company_tearsheet(ticker: str):
    """Returns pre-generated tearsheet PDF (binary download)."""
    ticker_upper = ticker.strip().upper()
    pdf_path = f"reports/tearsheets/{ticker_upper}_tearsheet.pdf"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Tearsheet PDF for '{ticker_upper}' not found. Please pre-generate it first."
        )
        
    return FileResponse(
        pdf_path, 
        media_type="application/pdf", 
        filename=f"{ticker_upper}_tearsheet.pdf"
    )

# 9. Screener endpoint
@app.get("/api/v1/screener")
def get_screener_results(
    min_roe: Optional[float] = None,
    max_de: Optional[float] = None,
    sector: Optional[str] = None,
    min_cagr: Optional[float] = None
):
    """Screener: ?min_roe=&max_de=&sector=&min_cagr= -> ranked list."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    latest_mc_yr = int(latest_year[:4])
    
    query = """
        SELECT 
            r.company_id,
            c.company_name,
            s.broad_sector,
            r.composite_quality_score,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.net_profit_margin_pct,
            r.revenue_cagr_5yr,
            m.pe_ratio
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        JOIN sectors s ON r.company_id = s.company_id
        JOIN market_cap m ON r.company_id = m.company_id AND m.year = ?
        WHERE r.year = ?
    """
    cursor.execute(query, (latest_mc_yr, latest_year))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    # Filter python side for ease and flexibility
    filtered = []
    for r in rows:
        if min_roe is not None and (r['return_on_equity_pct'] is None or r['return_on_equity_pct'] < min_roe):
            continue
        if max_de is not None and (r['debt_to_equity'] is None or r['debt_to_equity'] > max_de):
            continue
        if min_cagr is not None and (r['revenue_cagr_5yr'] is None or r['revenue_cagr_5yr'] < min_cagr):
            continue
        if sector and (r['broad_sector'] is None or sector.strip().lower() not in r['broad_sector'].strip().lower()):
            continue
        filtered.append(r)
        
    # Sort by quality score descending
    filtered.sort(key=lambda x: x.get('composite_quality_score') or 0, reverse=True)
    return filtered

# 10. Sectors summary endpoint
@app.get("/api/v1/sectors")
def get_sectors_summary():
    """List all 11 sectors with company count and median KPIs."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    query = """
        SELECT 
            s.broad_sector as sector,
            COUNT(c.id) as company_count
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        GROUP BY s.broad_sector
    """
    cursor.execute(query)
    sector_counts = {r['sector']: r['company_count'] for r in cursor.fetchall()}
    
    # Get all ratios to compute median side
    query_all = """
        SELECT s.broad_sector as sector, r.return_on_equity_pct, r.debt_to_equity, r.net_profit_margin_pct
        FROM financial_ratios r
        JOIN sectors s ON r.company_id = s.company_id
        WHERE r.year = ?
    """
    cursor.execute(query_all, (latest_year,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    import pandas as pd
    df = pd.DataFrame(rows)
    
    res = []
    for sec, count in sector_counts.items():
        df_sec = df[df['sector'] == sec]
        if not df_sec.empty:
            median_roe = df_sec['return_on_equity_pct'].median()
            median_de = df_sec['debt_to_equity'].median()
            median_npm = df_sec['net_profit_margin_pct'].median()
        else:
            median_roe = median_de = median_npm = None
            
        res.append({
            "sector": sec,
            "company_count": count,
            "median_roe": float(median_roe) if pd.notnull(median_roe) else None,
            "median_de": float(median_de) if pd.notnull(median_de) else None,
            "median_npm": float(median_npm) if pd.notnull(median_npm) else None
        })
    return res

# 11. Sector companies endpoint
@app.get("/api/v1/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    """All companies in a sector with KPI summary."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    query = """
        SELECT 
            c.id as ticker,
            c.company_name,
            s.sub_sector,
            r.composite_quality_score,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.net_profit_margin_pct
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios r ON c.id = r.company_id AND r.year = ?
        WHERE s.broad_sector LIKE ?
        ORDER BY r.composite_quality_score DESC
    """
    cursor.execute(query, (latest_year, f"%{sector}%"))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 12. Peer group endpoint
@app.get("/api/v1/peers/{group_name}")
def get_peer_group(group_name: str):
    """All companies in a peer group with percentile ranks."""
    conn = get_db_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    # We load peers matching the group name
    query = """
        SELECT 
            p.company_id as ticker,
            c.company_name,
            p.is_benchmark,
            r.composite_quality_score,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.net_profit_margin_pct
        FROM peer_groups p
        JOIN companies c ON p.company_id = c.id
        LEFT JOIN financial_ratios r ON p.company_id = r.company_id AND r.year = ?
        WHERE p.peer_group_name LIKE ?
        ORDER BY r.composite_quality_score DESC
    """
    cursor.execute(query, (latest_year, f"%{group_name}%"))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Peer group '{group_name}' not found.")
        
    return rows

# 13. Peer radar comparison data endpoint
@app.get("/api/v1/companies/{ticker}/peers/compare")
def get_peer_comparison_radar(ticker: str):
    """Radar data: company vs peer group average for 8 metrics."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Find company's peer group
    cursor.execute("SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (ticker_upper,))
    pg_row = cursor.fetchone()
    if not pg_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No peer group mapping found for company '{ticker_upper}'.")
        
    group_name = pg_row['peer_group_name']
    
    # Fetch all companies in that peer group
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    query = """
        SELECT 
            r.company_id,
            r.return_on_equity_pct as roe,
            r.roce_percentage as roce,
            r.net_profit_margin_pct as npm,
            r.debt_to_equity as de,
            r.free_cash_flow_cr as fcf,
            r.pat_cagr_5yr as pat_cagr,
            r.revenue_cagr_5yr as rev_cagr,
            r.eps_cagr_5yr as eps_cagr
        FROM financial_ratios r
        JOIN peer_groups p ON r.company_id = p.company_id
        WHERE p.peer_group_name = ? AND r.year = ?
    """
    cursor.execute(query, (group_name, latest_year))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    import pandas as pd
    df = pd.DataFrame(rows)
    if df.empty:
        raise HTTPException(status_code=404, detail="No ratio data for peer comparison.")
        
    # Get company values
    co_row = df[df['company_id'] == ticker_upper]
    if co_row.empty:
        raise HTTPException(status_code=404, detail="Company metrics not found.")
        
    co_metrics = co_row.iloc[0].to_dict()
    
    # Compute peer average
    peer_avg = df.mean(numeric_only=True).to_dict()
    
    return {
        "ticker": ticker_upper,
        "peer_group": group_name,
        "metrics_keys": ["roe", "roce", "npm", "de", "fcf", "pat_cagr", "rev_cagr", "eps_cagr"],
        "company_values": co_metrics,
        "peer_average_values": peer_avg
    }

# 14. Historical valuation multiples endpoint
@app.get("/api/v1/market-cap/{ticker}")
def get_historical_valuation(ticker: str):
    """Historical valuation multiples (P/E, P/B, EV/EBITDA) 2019-2024."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    cursor.execute("""
        SELECT year, market_cap_crore, enterprise_value_crore, pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct
        FROM market_cap 
        WHERE company_id = ? 
        ORDER BY year ASC
    """, (ticker_upper,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# 15. Portfolio-level stats endpoint
@app.get("/api/v1/portfolio/stats")
def get_portfolio_stats():
    """Portfolio-level statistics: P10-P90 for core KPIs."""
    csv_path = "portfolio_stats.csv"
    if not os.path.exists(csv_path):
        try:
            from clustering_analysis import run_clustering_and_stats
            run_clustering_and_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate portfolio stats: {str(e)}")
            
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="portfolio_stats.csv file not found.")
        
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read portfolio stats: {str(e)}")

# 16. Annual report documents links endpoint
@app.get("/api/v1/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    """Annual report links for a company."""
    ticker_upper = ticker.strip().upper()
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Check company
    cursor.execute("SELECT 1 FROM companies WHERE id = ?", (ticker_upper,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Company '{ticker_upper}' not found.")
        
    cursor.execute("""
        SELECT Year as year, Annual_Report as annual_report_url
        FROM documents 
        WHERE company_id = ? 
        ORDER BY Year DESC
    """, (ticker_upper,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
