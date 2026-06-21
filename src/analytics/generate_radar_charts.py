import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional

DB_PATH = "data/nifty100.db"
OUTPUT_DIR = "reports/radar_charts"

def generate_all_radar_charts(year_val: Optional[str] = None):
    """
    Generates radar charts for all 92 companies.
    Saves them as reports/radar_charts/<ticker>_radar.png
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    
    if year_val is None:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(year) FROM financial_ratios")
        res = cursor.fetchone()
        year_val = res[0] if res and res[0] else "2024-03"
        
    df_pg = pd.read_sql("SELECT * FROM peer_groups", conn)
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios WHERE year = ?", conn, params=[year_val])
    df_companies = pd.read_sql("SELECT id, company_name FROM companies", conn)
    
    conn.close()
    
    if df_ratios.empty:
        print("No ratio data available to generate radar charts.")
        return
        
    # Join ratios with companies to get names
    df_ratios = df_ratios.merge(df_companies, left_on='company_id', right_on='id')

    # Radar metrics to plot
    metrics = [
        'return_on_equity_pct', 'roce_percentage', 'net_profit_margin_pct',
        'debt_to_equity', 'free_cash_flow_cr', 'pat_cagr_5yr', 'revenue_cagr_5yr', 'eps_cagr_5yr'
    ]
    
    labels = ['ROE', 'ROCE', 'NPM', 'D/E', 'FCF', 'PAT CAGR 5Y', 'Rev CAGR 5Y', 'EPS CAGR 5Y']
    num_vars = len(labels)

    # Compute angles for the radar chart
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    # Close the loop
    angles += angles[:1]
    
    # We will generate a chart for each company
    for _, row in df_ratios.iterrows():
        ticker = row['company_id']
        co_name = row['company_name']
        
        # Check if the company belongs to any peer group
        pg_membership = df_pg[df_pg['company_id'] == ticker]
        if pg_membership.empty:
            # If no peer group, we skip or use all companies average
            pg_name = "All Nifty 100"
            group_tickers = df_ratios['company_id'].tolist()
        else:
            pg_name = pg_membership.iloc[0]['peer_group_name']
            group_tickers = df_pg[df_pg['peer_group_name'] == pg_name]['company_id'].tolist()
            
        # Get peer group dataframe
        df_group = df_ratios[df_ratios['company_id'].isin(group_tickers)].copy()
        
        # Fill missing values with 0 for scaling
        df_group = df_group.fillna(0.0)
        
        # Scale values between 0 and 100 for visual comparison
        # (For D/E, invert the scaling: lower is better -> gets 100, higher gets 0)
        co_values = []
        group_avg_values = []
        
        for metric in metrics:
            val_min = df_group[metric].min()
            val_max = df_group[metric].max()
            val_avg = df_group[metric].mean()
            val_co = row.get(metric, 0.0)
            if pd.isnull(val_co):
                val_co = 0.0
                
            # If min == max, set scaled to 100
            if val_max == val_min:
                scaled_co = 100.0
                scaled_avg = 100.0
            else:
                if metric == 'debt_to_equity':
                    scaled_co = 100.0 * (val_max - val_co) / (val_max - val_min)
                    scaled_avg = 100.0 * (val_max - val_avg) / (val_max - val_min)
                else:
                    scaled_co = 100.0 * (val_co - val_min) / (val_max - val_min)
                    scaled_avg = 100.0 * (val_avg - val_min) / (val_max - val_min)
                    
            co_values.append(scaled_co)
            group_avg_values.append(scaled_avg)
            
        # Close the loop for values
        co_values += co_values[:1]
        group_avg_values += group_avg_values[:1]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # Draw one axe per variable and add labels
        plt.xticks(angles[:-1], labels, color='grey', size=8)
        
        # Draw ylabels
        ax.set_rlabel_position(0)
        plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="grey", size=7)
        plt.ylim(0, 110)
        
        # Plot Company values
        ax.plot(angles, co_values, linewidth=2, linestyle='solid', label=ticker, color='#1f77b4')
        ax.fill(angles, co_values, color='#1f77b4', alpha=0.25)
        
        # Plot Peer Group Average values
        ax.plot(angles, group_avg_values, linewidth=1.5, linestyle='dashed', label=f"{pg_name} Avg", color='#ff7f0e')
        ax.fill(angles, group_avg_values, color='#ff7f0e', alpha=0.1)
        # Add legend and title
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), fontsize=8)
        plt.title(f"{ticker} vs Peer Group ({pg_name})", size=11, color='#333333', y=1.1, weight='bold')
        
        # Save figure
        fig_path = os.path.join(OUTPUT_DIR, f"{ticker}_radar.png")
        plt.savefig(fig_path, dpi=120, bbox_inches='tight')
        plt.close()
        
    print(f"Generated {len(df_ratios)} radar chart images in {OUTPUT_DIR}.")

if __name__ == "__main__":
    from typing import Optional
    generate_all_radar_charts()
