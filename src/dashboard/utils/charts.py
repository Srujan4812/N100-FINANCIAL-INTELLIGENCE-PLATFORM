import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

def plot_pnl_chart(df_pnl: pd.DataFrame) -> go.Figure:
    """Sales (bar) and Net Profit (bar/line) comparison over time."""
    fig = go.Figure()
    
    # Sort by year ascending
    df_sorted = df_pnl.sort_values(by='year')
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['sales'],
        name='Sales (Cr)',
        marker_color='#1f77b4',
        opacity=0.8
    ))
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['net_profit'],
        name='Net Profit (Cr)',
        marker_color='#2ca02c',
        opacity=0.9
    ))
    
    fig.update_layout(
        title="Revenue & Net Profit Trend",
        xaxis_title="Financial Year",
        yaxis_title="Amount (In Cr)",
        barmode='group',
        template='plotly_white',
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

def plot_bs_chart(df_bs: pd.DataFrame) -> go.Figure:
    """Stacked bar showing Balance Sheet composition (Liabilities side)."""
    fig = go.Figure()
    df_sorted = df_bs.sort_values(by='year')
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['equity_capital'] + df_sorted['reserves'].fillna(0.0),
        name='Net Worth',
        marker_color='#2ca02c'
    ))
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['borrowings'].fillna(0.0),
        name='Borrowings (Debt)',
        marker_color='#d62728'
    ))
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['other_liabilities'].fillna(0.0),
        name='Other Liabilities',
        marker_color='#bcbd22'
    ))
    
    fig.update_layout(
        title="Balance Sheet Funding Mix",
        xaxis_title="Financial Year",
        yaxis_title="Amount (In Cr)",
        barmode='stack',
        template='plotly_white',
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

def plot_cf_chart(df_cf: pd.DataFrame) -> go.Figure:
    """Grouped bar chart for Cash Flows (CFO, CFI, CFF)."""
    fig = go.Figure()
    df_sorted = df_cf.sort_values(by='year')
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['operating_activity'].fillna(0.0),
        name='CFO (Ops)',
        marker_color='#2ca02c'
    ))
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['investing_activity'].fillna(0.0),
        name='CFI (Invest)',
        marker_color='#d62728'
    ))
    
    fig.add_trace(go.Bar(
        x=df_sorted['year'],
        y=df_sorted['financing_activity'].fillna(0.0),
        name='CFF (Finance)',
        marker_color='#1f77b4'
    ))
    
    fig.update_layout(
        title="Cash Flow Breakdown",
        xaxis_title="Financial Year",
        yaxis_title="Amount (In Cr)",
        barmode='group',
        template='plotly_white',
        legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.7)'),
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

def plot_sector_bubble_chart(df_sector: pd.DataFrame) -> go.Figure:
    """Bubble chart: X=ROE, Y=Sales, size=Market Cap, color=Broad Sector."""
    # Handle negative ROE or missing caps gracefully
    df_clean = df_sector[df_sector['return_on_equity_pct'].notnull() & df_sector['sales'].notnull()].copy()
    df_clean['market_cap_crore'] = df_clean['market_cap_crore'].fillna(100.0)
    
    fig = px.scatter(
        df_clean,
        x="return_on_equity_pct",
        y="sales",
        size="market_cap_crore",
        color="broad_sector",
        hover_name="company_name",
        title="Sector Landscape: Sales vs ROE (size = Market Cap)",
        labels={
            "return_on_equity_pct": "Return on Equity (ROE %)",
            "sales": "Revenue / Sales (Cr)",
            "broad_sector": "Sector"
        },
        template="plotly_white"
    )
    
    fig.update_layout(
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig
