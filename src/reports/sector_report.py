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

OUTPUT_DIR = "reports/sector"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_sector_reports():
    print("Generating Sector Reports for all sectors...")
    start_time = time.time()
    
    conn = get_connection()
    
    # Fetch latest year financial ratios
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(year) FROM financial_ratios")
    latest_year = cursor.fetchone()[0]
    
    # Query companies in sectors
    query = """
        SELECT 
            c.id as ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.composite_quality_score,
            r.return_on_equity_pct,
            r.debt_to_equity,
            r.net_profit_margin_pct,
            r.free_cash_flow_cr,
            r.capital_allocation_pattern,
            p.is_benchmark
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        LEFT JOIN financial_ratios r ON c.id = r.company_id AND r.year = ?
        LEFT JOIN peer_groups p ON s.broad_sector = p.peer_group_name AND c.id = p.company_id
        ORDER BY s.broad_sector ASC, r.composite_quality_score DESC
    """
    df = pd.read_sql(query, conn, params=[latest_year])
    conn.close()

    if df.empty:
        print("No sector data to generate reports.")
        return
        
    styles = getSampleStyleSheet()
    
    # Custom styles
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

    table_cell_left = ParagraphStyle(
        'TableCellLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#1e293b'),
        alignment=0 # Left
    )

    sectors = df['broad_sector'].unique()
    
    for sector in sectors:
        df_sec = df[df['broad_sector'] == sector].copy()
        
        # Sanitize filename
        sec_filename = sector.replace(" ", "_").replace("/", "_").replace("&", "and")
        pdf_path = os.path.join(OUTPUT_DIR, f"{sec_filename}_sector_report.pdf")
        
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        story = []
        
        # --- HEADER SECTION ---
        header_data = [
            [
                Paragraph(f"<b>{sector.upper()} SECTOR REPORT</b>", title_style),
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
        
        # --- SECTOR METRICS CARD ---
        total_cos = len(df_sec)
        valid_qs = df_sec[df_sec['composite_quality_score'].notnull()]
        avg_score = valid_qs['composite_quality_score'].mean() if not valid_qs.empty else 0.0
        best_co = df_sec.iloc[0]['company_name'] if not df_sec.empty else "N/A"
        best_score = df_sec.iloc[0]['composite_quality_score'] if not df_sec.empty else 0.0
        
        # Benchmark company
        benchmark_row = df_sec[df_sec['is_benchmark'] == 1]
        benchmark_name = benchmark_row.iloc[0]['company_name'] if not benchmark_row.empty else "N/A"
        benchmark_score = benchmark_row.iloc[0]['composite_quality_score'] if not benchmark_row.empty else 0.0
        
        summary_data = [
            [
                Paragraph(f"<b>Sector Size:</b> {total_cos} Companies", body_style),
                Paragraph(f"<b>Avg Quality Score:</b> {avg_score:.1f}/100", body_style),
                Paragraph(f"<b>Best-in-Class:</b> {best_co} ({best_score:.1f})", body_style)
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
        
        # --- PEER COMPARISON TABLE ---
        col_widths = [55, 120, 120, 50, 48, 45, 45, 40]
        
        headers = [
            Paragraph("<b>Ticker</b>", table_header_style),
            Paragraph("<b>Company Name</b>", table_header_style),
            Paragraph("<b>Sub Sector</b>", table_header_style),
            Paragraph("<b>Quality Score</b>", table_header_style),
            Paragraph("<b>ROE %</b>", table_header_style),
            Paragraph("<b>D/E</b>", table_header_style),
            Paragraph("<b>NPM %</b>", table_header_style),
            Paragraph("<b>Benchmark</b>", table_header_style)
        ]
        
        table_rows = [headers]
        
        for _, row in df_sec.iterrows():
            qs_val = f"{row['composite_quality_score']:.1f}" if pd.notnull(row['composite_quality_score']) else "N/A"
            roe_val = f"{row['return_on_equity_pct']:.1f}%" if pd.notnull(row['return_on_equity_pct']) else "N/A"
            de_val = f"{row['debt_to_equity']:.2f}x" if pd.notnull(row['debt_to_equity']) else "N/A"
            npm_val = f"{row['net_profit_margin_pct']:.1f}%" if pd.notnull(row['net_profit_margin_pct']) else "N/A"
            is_bench = "Yes" if row['is_benchmark'] == 1 else "No"
            
            table_rows.append([
                Paragraph(f"<b>{row['ticker']}</b>", table_cell_style),
                Paragraph(row['company_name'][:25], table_cell_left),
                Paragraph(row['sub_sector'][:25], table_cell_left),
                Paragraph(qs_val, table_cell_style),
                Paragraph(roe_val, table_cell_style),
                Paragraph(de_val, table_cell_style),
                Paragraph(npm_val, table_cell_style),
                Paragraph(is_bench, table_cell_style)
            ])
            
        sector_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        
        t_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]
        
        # Add zebra striping
        for idx in range(1, len(table_rows)):
            if idx % 2 == 0:
                t_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
            # Highlight benchmark row
            is_b = table_rows[idx][-1].text
            if is_b == "Yes":
                t_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#e0f2fe'))) # light blue highlight
                
        sector_table.setStyle(TableStyle(t_style))
        story.append(sector_table)
        
        # Page footer builder
        def add_page_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#64748b'))
            canvas.drawString(36, 18, f"CONFIDENTIAL · SECTOR REPORT: {sector.upper()}")
            canvas.drawRightString(A4[0] - 36, 18, f"Page {doc.page}")
            canvas.restoreState()
            
        doc.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
        
    print(f"Generated {len(sectors)} Sector PDF Reports in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    import pandas as pd
    generate_sector_reports()
