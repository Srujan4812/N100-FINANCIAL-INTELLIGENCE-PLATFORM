# Nifty 100 Financial Intelligence Platform

> 🔴 **Live Deployments:**
> - 📊 **Streamlit Dashboard**: [https://nifty100-dashboard-9y7s.onrender.com/](https://nifty100-dashboard-9y7s.onrender.com/)
> - 🔌 **FastAPI Backend / Swagger Docs**: [https://nifty100-api-6u65.onrender.com/docs](https://nifty100-api-6u65.onrender.com/docs)

A self-contained, production-grade fundamental research workspace enabling analysts to query, screen, score, and compare constituent companies of the Nifty 100 index. Built on a local SQLite storage model, statistical engine, FastAPI endpoints, and a multi-page interactive Streamlit dashboard.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: 3.12.x or higher
- All required packages are listed in `requirements.txt`.

### 2. Installation
Clone the repository and set up a virtual environment:
```powershell
# Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Ingestion & Database Population (ETL)
Populate the SQLite database by running the ETL ingestion pipeline. 
> [!TIP]
> To run the ingestion quickly without requesting HTTP headers for 1,580 document URLs over the network, set `SKIP_URL_VALIDATION=TRUE` in your `.env` file (or environment). The platform utilizes a local JSON cache at `data/url_cache.json` to prevent duplicate network calls.
```powershell
# Run database initialization & data ingestion
python src/etl/loader.py
```

### 4. Running the Platform
Launch the FastAPI server and the Streamlit dashboard:
```powershell
# Launch FastAPI server (runs on localhost:8000)
.\.venv\Scripts\uvicorn src.api.main:app --port 8000

# Launch Streamlit dashboard (runs on localhost:8501)
.\.venv\Scripts\streamlit run src/dashboard/app.py
```

---

## 📊 Feature Highlights & Module Architecture

### 1. Data Quality & ETL Ingestion (Module 1)
- Implements 16 strict validation rules (DQ-01 to DQ-16) checking primary keys, foreign key constraints, year formatting (`YYYY-MM`), tax rates (0-60%), balance sheet integrity (within 1% tolerance), cash flow cross-checks, and document URL connectivity.
- Generates a validation failure report at `validation_failures.csv` and ingestion audit log at `load_audit.csv`.

### 2. Financial Ratio Engine (Module 2)
- Automatically computes 50+ profitability, leverage, cash flow quality, returns, growth CAGR (3Y, 5Y, 10Y), and capital allocation patterns.
- Addresses divide-by-zero, negative equity (computes ROE as `None`), bank-specific debt structures, and CAGR turnaround logic (base value negative set as `None` with warning flags).

### 3. Investment Screener & Composite Quality Score (Modules 3-5)
- Includes 6 preset screener templates: *Quality Compounder*, *Value Pick*, *Growth Accelerator*, *Dividend Champion*, *Debt-Free Blue Chip*, and *Turnaround Watch*.
- Scores companies out of 100 based on: Profitability (35%), Cash Quality (30%), Growth (20%), and Leverage (15%).
- Customizable screens can be defined in `config/screener_config.yaml`.

### 4. Peer Comparison & Sector Analytics (Modules 6 & 9)
- Compares companies within their peer groups (e.g. Private Banks, IT Services) and calculates intra-group percentile ranks and gap analysis against benchmarks.
- Plots 8-axis polar radar charts comparing companies to the peer group averages.
- Detects best-in-class badging (>=75th percentile on >=6 metrics) and watch-list flags (<=25th percentile on >=4 metrics).

### 5. Cash Flow Intelligence & Statistical Clustering (Modules 7 & 10)
- Classifies Capex intensity (light vs. heavy) and capital allocation styles.
- Performs KMeans (n=5) profile clustering, Pearson correlation heatmaps, and sector Z-score outlier detection.

### 6. Automated PDF Tearsheet & Report Generator (Module 8)
- **Company Tearsheet**: 2-page PDF overview with KPI metrics, P&L bar graphs, Return trends, Balance Sheet funding mix stacked bars, Cash Flow waterfalls, pros/cons, and capital allocation badges.
- **Portfolio Summary**: Standardized PDF report listing all 92 companies with their sector and key metrics.
- **Sector Report**: 10 sector PDFs detailing benchmarks, peer rankings, and best-in-class listings.
- **Screener Output**: Formatted PDF of companies matching the 6 screening templates.

---

## 🔌 REST API Specification (16 Endpoints)

FastAPI serves JSON data at `http://127.0.0.1:8000/` and auto-generates interactive Swagger UI docs at `/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Uptime status and database row counts |
| `/api/v1/companies` | GET | List all 92 companies with ticker, name, and sector |
| `/api/v1/companies/{ticker}` | GET | Get company profile, sector, latest ratios, and pros/cons |
| `/api/v1/companies/{ticker}/pl` | GET | Get P&L statement history (supports `from_year` / `to_year` filters) |
| `/api/v1/companies/{ticker}/bs` | GET | Get Balance Sheet history (supports year filters) |
| `/api/v1/companies/{ticker}/cashflow` | GET | Get Cash Flow history (supports year filters) |
| `/api/v1/companies/{ticker}/ratios` | GET | Get all pre-computed KPI ratios |
| `/api/v1/companies/{ticker}/tearsheet` | GET | Binary download of the pre-generated 2-page Tearsheet PDF |
| `/api/v1/screener` | GET | Run custom screens (filters: `min_roe`, `max_de`, `min_cagr`, `sector`) |
| `/api/v1/sectors` | GET | List all 11 sectors with company counts and median KPIs |
| `/api/v1/sectors/{sector}/companies` | GET | List all companies in a sector with KPI summary |
| `/api/v1/peers/{group_name}` | GET | Get peer group constituents and KPI rankings |
| `/api/v1/companies/{ticker}/peers/compare`| GET | Get radar comparison data (company vs. peer average) |
| `/api/v1/market-cap/{ticker}` | GET | Historical multiples (P/E, P/B, EV/EBITDA) |
| `/api/v1/portfolio/stats` | GET | Index percentile statistics (P10, P25, P50, P75, P90, Mean, Std) |
| `/api/v1/companies/{ticker}/documents` | GET | Return links to annual report PDF documents |

---

## 🧪 Testing & Quality Assurance

A suite of **62 pytest test cases** validates ETL pipelines, year/ticker normalizers, ratio math, edge cases, and all 16 REST endpoints:
```powershell
# Run the entire test suite and generate an HTML report
pytest tests/ --html=reports/pytest_report.html --self-contained-html
```
The generated test report is located at [pytest_report.html](file:///C:/N100-FINANCIAL-INTELLIGENCE-PLATFORM/reports/pytest_report.html).

## & Deployment on Render

This project includes a 
ender.yaml Blueprint to easily deploy the platform as two web services (API and Dashboard) on Render.

1. Create a [Render](https://render.com/) account and connect your GitHub repository.
2. In the Render Dashboard, click **New +** and select **Blueprint**.
3. Select this repository and click **Connect**.
4. Render will automatically detect the 
ender.yaml file and provision both the **FastAPI Server** and the **Streamlit Dashboard** as separate web services.
5. The SQLite database is pre-populated and committed, so the platform will work out of the box.

---

## ☁️ Deployment on Render

This project includes a `render.yaml` Blueprint to easily deploy the platform as two web services (API and Dashboard) on Render.

1. Create a [Render](https://render.com/) account and connect your GitHub repository.
2. In the Render Dashboard, click **New +** and select **Blueprint**.
3. Select this repository and click **Connect**.
4. Render will automatically detect the `render.yaml` file and provision both the **FastAPI Server** and the **Streamlit Dashboard** as separate web services.
5. The SQLite database is pre-populated and committed, so the platform will work out of the box.
