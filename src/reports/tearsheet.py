import os
import sys
import sqlite3
import time
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ReportLab imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../dashboard/utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../analytics')))

from db import get_connection

OUTPUT_DIR = "reports/tearsheets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define PDF Page size and Usable Width (in points)
# A4 width = 595.27 points. With 1.5 cm margins (total 3.0 cm = 85.0 points)
# Usable Width (UW) = 510.0 points
UW = 510.0

def build_charts_for_ticker(ticker: str, df_pnl: pd.DataFrame, df_bs: pd.DataFrame, df_cf: pd.DataFrame) -> Tuple[str, str, str, str]:
    """Generates 4 temporary charts for the tearsheet and returns their file paths."""
    pnl_path = f"temp_{ticker}_pnl.png"
    ret_path = f"temp_{ticker}_returns.png"
    funding_path = f"temp_{ticker}_funding.png"
    cf_path = f"temp_{ticker}_cf.png"
    
    # 1. P&L Chart
    fig, ax = plt.subplots(figsize=(4, 2.5))
    df_pnl_sorted = df_pnl.sort_values(by='year')
    x = range(len(df_pnl_sorted))
    width = 0.35
    ax.bar([i - width/2 for i in x], df_pnl_sorted['sales'], width, label='Sales', color='#1f77b4')
    ax.bar([i + width/2 for i in x], df_pnl_sorted['net_profit'], width, label='Net Profit', color='#2ca02c')
    ax.set_xticks(x)
    ax.set_xticklabels(df_pnl_sorted['year'].apply(lambda s: s[-2:]), size=7)
    ax.set_title("Sales & Net Profit Trend (Cr)", size=8, weight='bold')
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(prop={'size': 6})
    plt.tight_layout()
    plt.savefig(pnl_path, dpi=120)
    plt.close()
    
    # 2. Returns Chart (ROE / ROCE)
    fig, ax = plt.subplots(figsize=(4, 2.5))
    df_pnl_sorted = df_pnl_sorted.fillna(0.0) # check roce/roe values
    
    # We join with ratios if needed, but we can compute them directly
    # Wait, we can fetch from financial_ratios table
    # So we'll pass df_ratios in instead of computing them here
    pass
    
def draw_company_pdf_tearsheet(ticker: str, company: pd.Series, sector: pd.Series, pnl: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame, ratios: pd.DataFrame, pros_cons: pd.DataFrame):
    """Generates the 2-page Tearsheet PDF for a single company."""
    pdf_path = os.path.join(OUTPUT_DIR, f"{ticker}_tearsheet.pdf")
    
    # Page setup
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=42, # approx 1.5 cm
        rightMargin=42,
        topMargin=42,
        bottomMargin=42
    )
    
    styles = getSampleStyleSheet()
    
    # Custom text styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#334155'),
        leading=11
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.white,
        alignment=1 # Center
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#1e293b'),
        alignment=1 # Center
    )

    pro_style = ParagraphStyle(
        'ProStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#065f46'),
        leading=10
    )

    con_style = ParagraphStyle(
        'ConStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#991b1b'),
        leading=10
    )

    story = []

    # --- PAGE 1 HEADER ---
    header_data = [
        [
            Paragraph(f"<b>{company['company_name']}</b> ({ticker})", title_style),
            Paragraph(f"<b>Sector:</b> {sector.iloc[0]['broad_sector']} | {sector.iloc[0]['sub_sector']}" if not sector.empty else "", body_style)
        ]
    ]
    # Header columns sum to UW: 300 + 210 = 510
    header_table = Table(header_data, colWidths=[300, 210])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#3b82f6')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Business Profile description
    story.append(Paragraph("<b>Business Overview:</b>", body_style))
    story.append(Paragraph(str(company['about_company']), body_style))
    story.append(Spacer(1, 12))

    # --- KPI SUMMARY TABLE (Page 22, 8.1) ---
    latest_ratio = ratios.iloc[0] if not ratios.empty else {}
    
    # 2x3 KPI grid data
    roe_val = f"{latest_ratio['return_on_equity_pct']:.1f}%" if pd.notnull(latest_ratio.get('return_on_equity_pct')) else "N/A"
    roce_val = f"{latest_ratio['roce_percentage']:.1f}%" if pd.notnull(latest_ratio.get('roce_percentage')) else "N/A"
    npm_val = f"{latest_ratio['net_profit_margin_pct']:.1f}%" if pd.notnull(latest_ratio.get('net_profit_margin_pct')) else "N/A"
    de_val = f"{latest_ratio['debt_to_equity']:.2f}x" if pd.notnull(latest_ratio.get('debt_to_equity')) else "N/A"
    fcf_val = f"{latest_ratio['free_cash_flow_cr']:.1f} Cr" if pd.notnull(latest_ratio.get('free_cash_flow_cr')) else "N/A"
    qs_val = f"{latest_ratio['composite_quality_score']:.1f}/100" if pd.notnull(latest_ratio.get('composite_quality_score')) else "N/A"

    kpi_data = [
        [
            Paragraph("<b>ROE</b>", table_header_style), 
            Paragraph("<b>ROCE</b>", table_header_style), 
            Paragraph("<b>NPM</b>", table_header_style)
        ],
        [
            Paragraph(roe_val, table_cell_style), 
            Paragraph(roce_val, table_cell_style), 
            Paragraph(npm_val, table_cell_style)
        ],
        [
            Paragraph("<b>Debt to Equity</b>", table_header_style), 
            Paragraph("<b>Free Cash Flow</b>", table_header_style), 
            Paragraph("<b>Quality Score</b>", table_header_style)
        ],
        [
            Paragraph(de_val, table_cell_style), 
            Paragraph(fcf_val, table_cell_style), 
            Paragraph(qs_val, table_cell_style)
        ]
    ]
    # KPI Columns sum to UW: 170 * 3 = 510
    kpi_table = Table(kpi_data, colWidths=[170, 170, 170])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#f8fafc')),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # --- MATPLOTLIB CHARTS PAGE 1 ---
    # Create matplotlib charts for embedding
    # We will generate P&L chart and ROE/ROCE line chart
    df_pnl_sorted = pnl.sort_values(by='year')
    x = range(len(df_pnl_sorted))
    
    # Chart 1: P&L
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    width = 0.35
    ax.bar([i - width/2 for i in x], df_pnl_sorted['sales'], width, label='Sales', color='#1f77b4')
    ax.bar([i + width/2 for i in x], df_pnl_sorted['net_profit'], width, label='PAT', color='#2ca02c')
    ax.set_xticks(x)
    ax.set_xticklabels(df_pnl_sorted['year'].apply(lambda s: s[-2:]), size=7)
    ax.set_title("Sales & Net Profit (Cr)", size=8, weight='bold')
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(prop={'size': 6})
    plt.tight_layout()
    chart1_path = f"temp_{ticker}_pnl.png"
    plt.savefig(chart1_path, dpi=120)
    plt.close()

    # Chart 2: Returns (ROE / ROCE)
    df_ratios_sorted = ratios.sort_values(by='year')
    x_r = range(len(df_ratios_sorted))
    
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    ax.plot(x_r, df_ratios_sorted['return_on_equity_pct'], marker='o', linewidth=1.5, label='ROE %', color='#2ca02c')
    ax.plot(x_r, df_ratios_sorted['roce_percentage'], marker='x', linewidth=1.5, label='ROCE %', color='#ff7f0e')
    ax.set_xticks(x_r)
    ax.set_xticklabels(df_ratios_sorted['year'].apply(lambda s: s[-2:]), size=7)
    ax.set_title("ROE & ROCE Trend (%)", size=8, weight='bold')
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(prop={'size': 6})
    plt.tight_layout()
    chart2_path = f"temp_{ticker}_returns.png"
    plt.savefig(chart2_path, dpi=120)
    plt.close()

    # Embed charts side-by-side in 1x2 table: width = 250 + 250 = 500
    charts_table1 = Table([
        [Image(chart1_path, width=245, height=155), Image(chart2_path, width=245, height=155)]
    ], colWidths=[255, 255])
    charts_table1.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(charts_table1)
    
    # Page Break
    story.append(PageBreak())

    # --- PAGE 2 HEADER ---
    story.append(header_table)
    story.append(Spacer(1, 10))

    # --- MATPLOTLIB CHARTS PAGE 2 ---
    # Chart 3: Balance Sheetstacked funding mix
    df_bs_sorted = bs.sort_values(by='year')
    x_b = range(len(df_bs_sorted))
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    ax.bar(x_b, df_bs_sorted['equity_capital'] + df_bs_sorted['reserves'].fillna(0.0), label='Net Worth', color='#2ca02c')
    ax.bar(x_b, df_bs_sorted['borrowings'].fillna(0.0), bottom=df_bs_sorted['equity_capital'] + df_bs_sorted['reserves'].fillna(0.0), label='Debt', color='#d62728')
    ax.set_xticks(x_b)
    ax.set_xticklabels(df_bs_sorted['year'].apply(lambda s: s[-2:]), size=7)
    ax.set_title("Balance Sheet Funding Mix (Cr)", size=8, weight='bold')
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(prop={'size': 6})
    plt.tight_layout()
    chart3_path = f"temp_{ticker}_funding.png"
    plt.savefig(chart3_path, dpi=120)
    plt.close()

    # Chart 4: Cash Flow
    df_cf_sorted = cf.sort_values(by='year')
    x_c = range(len(df_cf_sorted))
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    ax.bar([i - 0.2 for i in x_c], df_cf_sorted['operating_activity'].fillna(0.0), 0.2, label='CFO', color='#2ca02c')
    ax.bar(x_c, df_cf_sorted['investing_activity'].fillna(0.0), 0.2, label='CFI', color='#d62728')
    ax.bar([i + 0.2 for i in x_c], df_cf_sorted['financing_activity'].fillna(0.0), 0.2, label='CFF', color='#1f77b4')
    ax.set_xticks(x_c)
    ax.set_xticklabels(df_cf_sorted['year'].apply(lambda s: s[-2:]), size=7)
    ax.set_title("Cash Flow Trends (Cr)", size=8, weight='bold')
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(prop={'size': 6})
    plt.tight_layout()
    chart4_path = f"temp_{ticker}_cf.png"
    plt.savefig(chart4_path, dpi=120)
    plt.close()

    # Embed charts side-by-side
    charts_table2 = Table([
        [Image(chart3_path, width=245, height=155), Image(chart4_path, width=245, height=155)]
    ], colWidths=[255, 255])
    charts_table2.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(charts_table2)
    story.append(Spacer(1, 15))

    # --- QUALITATIVE ANALYSIS SECTION ---
    # Fetch pros and cons
    pros_list = pros_cons[pros_cons['pros'].notnull()]['pros'].tolist()
    cons_list = pros_cons[pros_cons['cons'].notnull()]['cons'].tolist()
    
    # Re-map lists to paragraphs
    pro_paragraphs = [Paragraph(f"• {p}", pro_style) for p in pros_list]
    con_paragraphs = [Paragraph(f"• {c}", con_style) for c in cons_list]
    
    # Capital Allocation Pattern Callout
    alloc_pattern = latest_ratio.get('capital_allocation_pattern', 'Other')
    alloc_desc = f"<b>Capital Allocation Strategy:</b> {alloc_pattern}"
    
    # Table layout for Pros and Cons (UW: 250 + 250 = 500, plus spacer)
    qual_table_data = [
        [Paragraph("<b>Positives & Strengths (Pros)</b>", body_style), Paragraph("<b>Key Risks & Concerns (Cons)</b>", body_style)],
        [pro_paragraphs if pro_paragraphs else Paragraph("None logged.", body_style), con_paragraphs if con_paragraphs else Paragraph("None logged.", body_style)]
    ]
    
    qual_table = Table(qual_table_data, colWidths=[250, 250])
    qual_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#e6f4ea')), # light green
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#fce8e6')), # light red
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    story.append(Paragraph(alloc_desc, body_style))
    story.append(Spacer(1, 8))
    story.append(qual_table)
    
    # Build Document
    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(42, 20, "CONFIDENTIAL · INTERNAL USE ONLY · DATA ANALYTICS DIVISION")
        canvas.drawRightString(A4[0] - 42, 20, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    
    # Cleanup temporary charts
    for path in [chart1_path, chart2_path, chart3_path, chart4_path]:
        if os.path.exists(path):
            os.remove(path)

def generate_all_tearsheets():
    """Loops over all companies in the SQLite database and generates tearsheets."""
    print("Generating Tearsheets for all Nifty 100 constituents...")
    start_time = time.time()
    
    conn = get_connection()
    df_companies = pd.read_sql("SELECT * FROM companies", conn)
    df_pnl = pd.read_sql("SELECT * FROM profitandloss", conn)
    df_bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    df_cf = pd.read_sql("SELECT * FROM cashflow", conn)
    df_ratios = pd.read_sql("SELECT * FROM financial_ratios", conn)
    df_sec = pd.read_sql("SELECT * FROM sectors", conn)
    df_pc = pd.read_sql("SELECT * FROM prosandcons", conn)
    conn.close()

    count = 0
    total_cos = len(df_companies)
    for idx, row in df_companies.iterrows():
        ticker = row['id']
        co_pnl = df_pnl[df_pnl['company_id'] == ticker]
        co_bs = df_bs[df_bs['company_id'] == ticker]
        co_cf = df_cf[df_cf['company_id'] == ticker]
        co_ratios = df_ratios[df_ratios['company_id'] == ticker]
        co_sec = df_sec[df_sec['company_id'] == ticker]
        co_pc = df_pc[df_pc['company_id'] == ticker]
        
        # Check if company has sufficient data to draw trends
        if len(co_pnl) >= 2 and len(co_bs) >= 2:
            try:
                print(f"[{idx+1}/{total_cos}] Generating tearsheet for {ticker}...")
                draw_company_pdf_tearsheet(ticker, row, co_sec, co_pnl, co_bs, co_cf, co_ratios, co_pc)
                count += 1
            except Exception as e:
                print(f"Error generating tearsheet for {ticker}: {e}")

    print(f"Successfully generated {count} Tearsheet PDFs in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    generate_all_tearsheets()
