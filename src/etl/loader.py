import os
import time
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Import normalisers and validator
from normaliser import normalize_ticker, normalize_year
from validator import DataValidator

# Load environment variables
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")
RAW_DIR = "data/raw"
SUPPORT_DIR = "data/supporting"
SCHEMA_SQL = "src/etl/schema.sql"
AUDIT_LOG_PATH = "load_audit.csv"

def init_db(conn: sqlite3.Connection):
    """Initialise SQLite database using schema.sql."""
    with open(SCHEMA_SQL, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()

def load_table(conn: sqlite3.Connection, df: pd.DataFrame, table_name: str) -> int:
    """Inserts a cleaned DataFrame into the SQLite database."""
    if df.empty:
        return 0
    # Write to SQL
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.commit()
    return len(df)

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean whitespaces and standardise column names to string lowercase."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def run_ingestion():
    """Main ETL pipeline ingestion runner."""
    start_time = time.time()
    
    # Establish connection
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # Remove existing DB file to guarantee clean loading
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception as e:
            print(f"Could not remove existing database: {e}")
            
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # Initialise validator
    validator = DataValidator("validation_failures.csv")

    audit_records = []
    
    # --- 1. Load Companies (Master table) ---
    print("Loading companies.xlsx...")
    co_start = time.time()
    co_file = os.path.join(RAW_DIR, "companies.xlsx")
    df_co = pd.read_excel(co_file, sheet_name=0, header=1)
    df_co = clean_column_names(df_co)
    rows_in = len(df_co)
    
    # Normalise ticker id
    df_co['id'] = df_co['id'].apply(normalize_ticker)
    # Filter out missing tickers
    df_co = df_co[df_co['id'] != 'MISSING'].copy()
    
    # Handle DQ-01/08 anomalies: fill null face_value
    df_co['face_value'] = df_co['face_value'].fillna(1.0)
    
    # Validate
    df_co = validator.validate_companies(df_co)
    rows_out = load_table(conn, df_co, "companies")
    rejected = rows_in - rows_out
    
    # Store set of valid tickers for foreign key checks
    valid_tickers = set(df_co['id'].tolist())
    
    audit_records.append({
        'table': 'companies',
        'rows_in': rows_in,
        'rows_out': rows_out,
        'rejected': rejected,
        'timestamp': datetime.now().isoformat(),
        'runtime_s': round(time.time() - co_start, 3)
    })

    # Helper function for core time-series tables (P&L, Balance Sheet, Cash Flow)
    def ingest_core_ts(file_name: str, table_name: str, validate_func):
        print(f"Loading {file_name}...")
        ts_start = time.time()
        file_path = os.path.join(RAW_DIR, file_name)
        df = pd.read_excel(file_path, sheet_name=0, header=1)
        df = clean_column_names(df)
        
        # Strip potential id columns from excel if they exist
        if 'id' in df.columns and table_name != 'prosandcons':
            df = df.drop(columns=['id'])
            
        r_in = len(df)
        
        # Normalise tickers and years
        df['company_id'] = df['company_id'].apply(normalize_ticker)
        df['year'] = df['year'].apply(normalize_year)
        
        # Drop rows where year or ticker is invalid
        df = df[(df['company_id'] != 'MISSING') & (df['year'] != 'PARSE_ERROR')].copy()
        
        # Handle specific table omissions before general validation
        if table_name == 'profitandloss':
            # Fill missing operating_profit and opm_percentage if null
            df['operating_profit'] = df['operating_profit'].fillna(df['sales'] - df['expenses'])
            df['opm_percentage'] = df['opm_percentage'].fillna((df['operating_profit'] / df['sales'] * 100).fillna(0))
            
        # Apply standard validator
        df = validator.validate_time_series(df, table_name, valid_tickers)
        # Apply table-specific validations
        df = validate_func(df)
        
        r_out = load_table(conn, df, table_name)
        rej = r_in - r_out
        
        audit_records.append({
            'table': table_name,
            'rows_in': r_in,
            'rows_out': r_out,
            'rejected': rej,
            'timestamp': datetime.now().isoformat(),
            'runtime_s': round(time.time() - ts_start, 3)
        })
        return df

    # --- 2. Load Profit and Loss ---
    df_pnl = ingest_core_ts("profitandloss.xlsx", "profitandloss", validator.validate_pnl)

    # --- 3. Load Balance Sheet ---
    df_bs = ingest_core_ts("balancesheet.xlsx", "balancesheet", validator.validate_balancesheet)

    # --- 4. Load Cash Flow ---
    df_cf = ingest_core_ts("cashflow.xlsx", "cashflow", validator.validate_cashflow)

    # Run coverage check
    validator.validate_coverage(df_pnl, df_bs, df_cf, valid_tickers)

    # --- 5. Load Analysis ---
    print("Loading analysis.xlsx...")
    an_start = time.time()
    df_an = pd.read_excel(os.path.join(RAW_DIR, "analysis.xlsx"), sheet_name=0, header=1)
    df_an = clean_column_names(df_an)
    r_in = len(df_an)
    df_an['company_id'] = df_an['company_id'].apply(normalize_ticker)
    df_an = df_an[(df_an['company_id'] != 'MISSING') & (df_an['company_id'].isin(valid_tickers))].copy()
    # No deduplication of company_id to keep multi-period records, but deduplicate on id for PK
    df_an = df_an.drop_duplicates(subset=['id'], keep='last').copy()
    r_out = load_table(conn, df_an, "analysis")
    audit_records.append({
        'table': 'analysis', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - an_start, 3)
    })

    # --- 6. Load Documents ---
    print("Loading documents.xlsx...")
    doc_start = time.time()
    df_doc = pd.read_excel(os.path.join(RAW_DIR, "documents.xlsx"), sheet_name=0, header=1)
    df_doc = clean_column_names(df_doc)
    if 'id' in df_doc.columns:
        df_doc = df_doc.drop(columns=['id'])
    r_in = len(df_doc)
    df_doc['company_id'] = df_doc['company_id'].apply(normalize_ticker)
    
    # Standardise year in documents (labeled 'Year' - capital Y)
    df_doc['Year'] = pd.to_numeric(df_doc['Year'], errors='coerce')
    df_doc = df_doc.dropna(subset=['Year'])
    df_doc['Year'] = df_doc['Year'].astype(int)
    
    df_doc = df_doc[(df_doc['company_id'] != 'MISSING') & (df_doc['company_id'].isin(valid_tickers))].copy()
    
    # Deduplicate annual report per company per year
    df_doc = df_doc.drop_duplicates(subset=['company_id', 'Year'], keep='last').copy()
    
    # Validate URLs (quick parallel check)
    df_doc = validator.validate_documents(df_doc)
    
    r_out = load_table(conn, df_doc, "documents")
    audit_records.append({
        'table': 'documents', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - doc_start, 3)
    })

    # --- 7. Load Pros and Cons ---
    print("Loading prosandcons.xlsx...")
    pc_start = time.time()
    df_pc = pd.read_excel(os.path.join(RAW_DIR, "prosandcons.xlsx"), sheet_name=0, header=1)
    df_pc = clean_column_names(df_pc)
    r_in = len(df_pc)
    df_pc['company_id'] = df_pc['company_id'].apply(normalize_ticker)
    df_pc = df_pc[(df_pc['company_id'] != 'MISSING') & (df_pc['company_id'].isin(valid_tickers))].copy()
    r_out = load_table(conn, df_pc, "prosandcons")
    audit_records.append({
        'table': 'prosandcons', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - pc_start, 3)
    })

    # --- 8. Load Sectors (supporting) ---
    print("Loading sectors.xlsx...")
    sec_start = time.time()
    df_sec = pd.read_excel(os.path.join(SUPPORT_DIR, "sectors.xlsx"), sheet_name=0, header=0)
    df_sec = clean_column_names(df_sec)
    if 'id' in df_sec.columns:
        df_sec = df_sec.drop(columns=['id'])
    r_in = len(df_sec)
    df_sec['company_id'] = df_sec['company_id'].apply(normalize_ticker)
    df_sec = df_sec[(df_sec['company_id'] != 'MISSING') & (df_sec['company_id'].isin(valid_tickers))].copy()
    df_sec = df_sec.drop_duplicates(subset=['company_id'], keep='last').copy()
    r_out = load_table(conn, df_sec, "sectors")
    audit_records.append({
        'table': 'sectors', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - sec_start, 3)
    })

    # --- 9. Load Stock Prices (supporting) ---
    print("Loading stock_prices.xlsx...")
    sp_start = time.time()
    df_sp = pd.read_excel(os.path.join(SUPPORT_DIR, "stock_prices.xlsx"), sheet_name=0, header=0)
    df_sp = clean_column_names(df_sp)
    if 'id' in df_sp.columns:
        df_sp = df_sp.drop(columns=['id'])
    r_in = len(df_sp)
    df_sp['company_id'] = df_sp['company_id'].apply(normalize_ticker)
    df_sp = df_sp[(df_sp['company_id'] != 'MISSING') & (df_sp['company_id'].isin(valid_tickers))].copy()
    
    # Date formatting verification
    df_sp['date'] = pd.to_datetime(df_sp['date'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_sp = df_sp.dropna(subset=['date']).copy()
    
    df_sp = df_sp.drop_duplicates(subset=['company_id', 'date'], keep='last').copy()
    r_out = load_table(conn, df_sp, "stock_prices")
    audit_records.append({
        'table': 'stock_prices', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - sp_start, 3)
    })

    # --- 10. Load Market Cap (supporting) ---
    print("Loading market_cap.xlsx...")
    mc_start = time.time()
    df_mc = pd.read_excel(os.path.join(SUPPORT_DIR, "market_cap.xlsx"), sheet_name=0, header=0)
    df_mc = clean_column_names(df_mc)
    if 'id' in df_mc.columns:
        df_mc = df_mc.drop(columns=['id'])
    r_in = len(df_mc)
    df_mc['company_id'] = df_mc['company_id'].apply(normalize_ticker)
    
    # Ensure year is integer
    df_mc['year'] = pd.to_numeric(df_mc['year'], errors='coerce')
    df_mc = df_mc.dropna(subset=['year'])
    df_mc['year'] = df_mc['year'].astype(int)
    
    df_mc = df_mc[(df_mc['company_id'] != 'MISSING') & (df_mc['company_id'].isin(valid_tickers))].copy()
    df_mc = df_mc.drop_duplicates(subset=['company_id', 'year'], keep='last').copy()
    r_out = load_table(conn, df_mc, "market_cap")
    audit_records.append({
        'table': 'market_cap', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - mc_start, 3)
    })

    # --- 11. Load Financial Ratios (supporting) ---
    print("Loading financial_ratios.xlsx...")
    fr_start = time.time()
    df_fr = pd.read_excel(os.path.join(SUPPORT_DIR, "financial_ratios.xlsx"), sheet_name=0, header=0)
    df_fr = clean_column_names(df_fr)
    if 'id' in df_fr.columns:
        df_fr = df_fr.drop(columns=['id'])
    r_in = len(df_fr)
    df_fr['company_id'] = df_fr['company_id'].apply(normalize_ticker)
    
    # Year normalise for financial_ratios to match YYYY-MM
    df_fr['year'] = df_fr['year'].apply(normalize_year)
    
    df_fr = df_fr[(df_fr['company_id'] != 'MISSING') & (df_fr['year'] != 'PARSE_ERROR') & (df_fr['company_id'].isin(valid_tickers))].copy()
    df_fr = df_fr.drop_duplicates(subset=['company_id', 'year'], keep='last').copy()
    r_out = load_table(conn, df_fr, "financial_ratios")
    audit_records.append({
        'table': 'financial_ratios', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'fr_start': fr_start
    })

    # --- 12. Load Peer Groups (supporting) ---
    print("Loading peer_groups.xlsx...")
    pg_start = time.time()
    df_pg = pd.read_excel(os.path.join(SUPPORT_DIR, "peer_groups.xlsx"), sheet_name=0, header=0)
    df_pg = clean_column_names(df_pg)
    if 'id' in df_pg.columns:
        df_pg = df_pg.drop(columns=['id'])
    
    r_in = len(df_pg)
    
    df_pg['company_id'] = df_pg['company_id'].apply(normalize_ticker)
    df_pg = df_pg[(df_pg['company_id'] != 'MISSING') & (df_pg['company_id'].isin(valid_tickers))].copy()
    
    # Cast is_benchmark to integer (0 or 1)
    df_pg['is_benchmark'] = df_pg['is_benchmark'].astype(int)
    
    df_pg = df_pg.drop_duplicates(subset=['peer_group_name', 'company_id'], keep='last').copy()
    
    r_out = load_table(conn, df_pg, "peer_groups")
        
    audit_records.append({
        'table': 'peer_groups', 'rows_in': r_in, 'rows_out': r_out, 'rejected': r_in - r_out,
        'timestamp': datetime.now().isoformat(), 'runtime_s': round(time.time() - pg_start, 3)
    })

    # Save failures list
    validator.save_failures()
    
    # Close connection
    conn.close()

    # Write audit log to CSV
    df_audit = pd.DataFrame(audit_records)
    # Re-calculate clean runtimes
    for i, rec in enumerate(audit_records):
        if 'fr_start' in rec:
            df_audit.at[i, 'runtime_s'] = round(time.time() - rec['fr_start'], 3)
    df_audit = df_audit.drop(columns=['fr_start'], errors='ignore')
    
    df_audit.to_csv(AUDIT_LOG_PATH, index=False)
    
    print(f"ETL Ingestion complete in {time.time() - start_time:.2f} seconds.")
    print(f"Database created at: {DB_PATH}")

if __name__ == "__main__":
    run_ingestion()
