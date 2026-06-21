import os
import sys
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Any

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../dashboard/utils')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../analytics')))

from db import get_connection

OUTPUT_DIR = "reports/portfolio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_portfolio_report():
    print("Generating Portfolio Summary Report PDF...")
    start_time = time.time()
    
    # Establish connection
    conn = get_connection()
    
    # Fetch latest year financial ratios
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    query = """
        SELECT 
            c.id as ticker,
            c.company_name,
            s.broad_sector,
            r.composite_quality_score,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.net_profit_margin_pct,
            r.free_cash_flow_cr,
            r.capital_allocation_pattern
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios r ON c.id = r.company_id AND r.year = ?
        ORDER BY r.composite_quality_score DESC, c.id ASC
    """
    df = pd.read_sql(query, conn, params=[latest_year])
    conn.close()

    # Determine filename with date
    date_str = datetime.now().strftime("%Y%m%d")
    pdf_path = os.path.join(OUTPUT_DIR, f"portfolio_summary_{date_str}.pdf")
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#2563eb'),
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
        fontSize=7,
        textColor=colors.white,
        alignment=1 # Center
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        textColor=colors.HexColor('#1e293b'),
        alignment=1 # Center
    )

    table_cell_left = ParagraphStyle(
        'TableCellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        textColor=colors.HexColor('#1e293b'),
        alignment=0 # Left
    )

    story = []
    
    # --- HEADER SECTION ---
    header_data = [
        [
            Paragraph("<b>NIFTY 100 PORTFOLIO SUMMARY REPORT</b>", title_style),
            Paragraph(f"<b>Run Date:</b> {datetime.now().strftime('%Y-%m-%d')}<br/><b>Analyzed Year:</b> {latest_year}", body_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[370, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#2563eb')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # --- SUMMARY METRICS CARD ---
    total_companies = len(df)
    valid_qs = df[df['composite_quality_score'].notnull()]
    avg_score = valid_qs['composite_quality_score'].mean() if not valid_qs.empty else 0.0
    top_performer = df.iloc[0]['company_name'] if not df.empty else "N/A"
    top_score = df.iloc[0]['composite_quality_score'] if not df.empty else 0.0
    
    summary_data = [
        [
            Paragraph(f"<b>Total Universe Size:</b> {total_companies} Companies", body_style),
            Paragraph(f"<b>Average Quality Score:</b> {avg_score:.1f}/100", body_style),
            Paragraph(f"<b>Top Ranked:</b> {top_performer} ({top_score:.1f})", body_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[170, 170, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))
    
    # --- TABLE HEADER COLS ---
    # Width of A4 page = 595. With 36pt margins, usable width = 523pt
    col_widths = [50, 115, 90, 48, 40, 40, 50, 50, 40]
    
    headers = [
        Paragraph("<b>Ticker</b>", table_header_style),
        Paragraph("<b>Company Name</b>", table_header_style),
        Paragraph("<b>Broad Sector</b>", table_header_style),
        Paragraph("<b>Quality Score</b>", table_header_style),
        Paragraph("<b>ROE %</b>", table_header_style),
        Paragraph("<b>D/E</b>", table_header_style),
        Paragraph("<b>NPM %</b>", table_header_style),
        Paragraph("<b>FCF (Cr)</b>", table_header_style),
        Paragraph("<b>Pattern</b>", table_header_style)
    ]
    
    table_rows = [headers]
    
    for _, row in df.iterrows():
        qs_val = f"{row['composite_quality_score']:.1f}" if pd.notnull(row['composite_quality_score']) else "N/A"
        roe_val = f"{row['return_on_equity_pct']:.1f}%" if pd.notnull(row['return_on_equity_pct']) else "N/A"
        de_val = f"{row['debt_to_equity']:.2f}x" if pd.notnull(row['debt_to_equity']) else "N/A"
        npm_val = f"{row['net_profit_margin_pct']:.1f}%" if pd.notnull(row['net_profit_margin_pct']) else "N/A"
        fcf_val = f"{row['free_cash_flow_cr']:.1f}" if pd.notnull(row['free_cash_flow_cr']) else "N/A"
        alloc_val = str(row['capital_allocation_pattern']) if pd.notnull(row['capital_allocation_pattern']) else "N/A"
        
        table_rows.append([
            Paragraph(f"<b>{row['ticker']}</b>", table_cell_style),
            Paragraph(row['company_name'][:25], table_cell_left),
            Paragraph(row['broad_sector'], table_cell_left),
            Paragraph(qs_val, table_cell_style),
            Paragraph(roe_val, table_cell_style),
            Paragraph(de_val, table_cell_style),
            Paragraph(npm_val, table_cell_style),
            Paragraph(fcf_val, table_cell_style),
            Paragraph(alloc_val, table_cell_style)
        ])
        
    portfolio_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]
    
    # Add zebra striping
    for idx in range(1, len(table_rows)):
        if idx % 2 == 0:
            t_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
            
    portfolio_table.setStyle(TableStyle(t_style))
    story.append(portfolio_table)
    
    # Page footer builder
    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(36, 18, "CONFIDENTIAL · INTERNAL USE ONLY · DATA ANALYTICS DIVISION")
        canvas.drawRightString(A4[0] - 36, 18, f"Page {doc.page}")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    print(f"Portfolio report generated at: {pdf_path} in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    import pandas as pd
    generate_portfolio_report()
