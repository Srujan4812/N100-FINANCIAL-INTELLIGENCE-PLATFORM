import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from typing import Dict, Any, List, Optional

DB_PATH = "data/nifty100.db"
CLUSTER_CSV = "cluster_labels.csv"
OUTLIER_CSV = "outlier_report.csv"
STATS_CSV = "portfolio_stats.csv"
HEATMAP_PNG = "correlation_heatmap.png"

def run_clustering_and_stats():
    print("Running Statistical Analysis & Clustering Module...")
    conn = sqlite3.connect(DB_PATH)
    
    # Load latest year ratios joined with sectors and market cap
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    latest_mc_yr = int(latest_year[:4])
    
    query = """
        SELECT 
            r.company_id,
            s.broad_sector,
            r.return_on_equity_pct,
            r.roce_percentage,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.asset_turnover,
            r.free_cash_flow_cr,
            r.revenue_cagr_5yr,
            r.pat_cagr_5yr,
            m.pe_ratio
        FROM financial_ratios r
        JOIN sectors s ON r.company_id = s.company_id
        JOIN market_cap m ON r.company_id = m.company_id AND m.year = ?
        WHERE r.year = ?
    """
    df = pd.read_sql(query, conn, params=[latest_mc_yr, latest_year])
    conn.close()

    if df.empty:
        print("No ratio data available for statistical clustering.")
        return

    # Clean missing values for clustering features
    features = ['return_on_equity_pct', 'debt_to_equity', 'operating_profit_margin_pct', 'revenue_cagr_5yr', 'free_cash_flow_cr']
    df_clean = df.copy()
    for col in features:
        df_clean[col] = df_clean[col].fillna(df_clean[col].median() if not df_clean[col].empty else 0.0)

    # 1. KMeans Clustering (n=5)
    X = df_clean[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df_clean['cluster_id'] = kmeans.fit_predict(X_scaled)
    
    # Assign labels based on cluster feature profiles
    cluster_profiles = df_clean.groupby('cluster_id')[features].mean()
    print("Cluster Profiles:\n", cluster_profiles)
    
    cluster_names = {}
    for cid, row in cluster_profiles.iterrows():
        roe_val = row['return_on_equity_pct']
        de_val = row['debt_to_equity']
        opm_val = row['operating_profit_margin_pct']
        fcf_val = row['free_cash_flow_cr']
        
        if roe_val > 25.0 and de_val < 0.5:
            cluster_names[cid] = "High-Quality Growth"
        elif roe_val < 8.0 and de_val > 1.5:
            cluster_names[cid] = "Distressed / High Debt"
        elif fcf_val > 2000.0:
            cluster_names[cid] = "Cash Cow Giants"
        elif roe_val > 12.0 and de_val <= 1.0:
            cluster_names[cid] = "Defensive Value"
        else:
            cluster_names[cid] = "Cyclical / Moderate Growth"

    df_clean['cluster_name'] = df_clean['cluster_id'].map(cluster_names)
    
    # Export cluster labels
    df_clean[['company_id', 'cluster_id', 'cluster_name']].to_csv(CLUSTER_CSV, index=False)
    print(f"Generated {CLUSTER_CSV}.")

    # 2. Correlation Matrix Heatmap
    correlation_metrics = [
        'return_on_equity_pct', 'roce_percentage', 'net_profit_margin_pct',
        'operating_profit_margin_pct', 'debt_to_equity', 'interest_coverage',
        'asset_turnover', 'free_cash_flow_cr', 'revenue_cagr_5yr', 'pat_cagr_5yr'
    ]
    df_corr = df_clean[correlation_metrics].rename(columns={
        'return_on_equity_pct': 'ROE',
        'roce_percentage': 'ROCE',
        'net_profit_margin_pct': 'NPM',
        'operating_profit_margin_pct': 'OPM',
        'debt_to_equity': 'D/E',
        'interest_coverage': 'ICR',
        'asset_turnover': 'Asset Turn',
        'free_cash_flow_cr': 'FCF',
        'revenue_cagr_5yr': '5Y Rev CAGR',
        'pat_cagr_5yr': '5Y PAT CAGR'
    }).corr()

    # Plot Heatmap
    plt.figure(figsize=(8, 6))
    plt.imshow(df_corr.values, cmap='coolwarm', interpolation='nearest')
    plt.colorbar()
    # Labels
    tick_marks = [i for i in range(len(df_corr.columns))]
    plt.xticks(tick_marks, df_corr.columns, rotation=45, ha='right', size=8)
    plt.yticks(tick_marks, df_corr.columns, size=8)
    plt.title("KPI Pearson Correlation Matrix Heatmap", size=11, weight='bold')
    plt.tight_layout()
    plt.savefig(HEATMAP_PNG, dpi=120)
    plt.close()
    print(f"Generated {HEATMAP_PNG}.")

    # 3. Z-score Outlier Detection per Sector (Page 23, 10.4)
    # Z-score per metric per sector. |Z| > 3 -> Outlier
    outliers = []
    outlier_metrics = ['return_on_equity_pct', 'debt_to_equity', 'operating_profit_margin_pct', 'free_cash_flow_cr']
    
    for sector in df_clean['broad_sector'].unique():
        df_sec = df_clean[df_clean['broad_sector'] == sector].copy()
        if len(df_sec) < 3:  # Need minimum size to calculate standard deviations
            continue
            
        for metric in outlier_metrics:
            mean = df_sec[metric].mean()
            std = df_sec[metric].std()
            if std > 0:
                for _, row in df_sec.iterrows():
                    val = row[metric]
                    z = (val - mean) / std
                    if abs(z) > 2.5: # 2.5 standard dev is a strong statistical outlier
                        outliers.append({
                            'company_id': row['company_id'],
                            'broad_sector': sector,
                            'metric': metric,
                            'value': val,
                            'sector_mean': round(mean, 2),
                            'sector_std': round(std, 2),
                            'z_score': round(z, 2)
                        })
                        
    df_outliers = pd.DataFrame(outliers)
    df_outliers.to_csv(OUTLIER_CSV, index=False)
    print(f"Generated {OUTLIER_CSV}. Found {len(df_outliers)} sector-level outliers.")

    # 4. Portfolio Statistics (P10, P25, P50, P75, P90)
    stats_metrics = ['return_on_equity_pct', 'debt_to_equity', 'pe_ratio', 'operating_profit_margin_pct', 'free_cash_flow_cr']
    stats_records = []
    
    for metric in stats_metrics:
        series = df_clean[metric].dropna()
        if not series.empty:
            stats_records.append({
                'metric': metric,
                'P10': round(np.percentile(series, 10), 2),
                'P25': round(np.percentile(series, 25), 2),
                'P50': round(np.percentile(series, 50), 2),
                'P75': round(np.percentile(series, 75), 2),
                'P90': round(np.percentile(series, 90), 2),
                'Mean': round(series.mean(), 2),
                'Std': round(series.std(), 2)
            })
            
    df_stats = pd.DataFrame(stats_records)
    df_stats.to_csv(STATS_CSV, index=False)
    print(f"Generated {STATS_CSV}.")

if __name__ == "__main__":
    run_clustering_and_stats()
