import os
import sys
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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../analytics/screener')))

from engine import run_screener, load_screener_config

OUTPUT_DIR = "reports/screener"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_screener_reports():
    print("Generating Screener Reports...")
    start_time = time.time()
    
    pdf_path = os.path.join(OUTPUT_DIR, "screener_presets_report.pdf")
    
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
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#334155'),
        leading=12
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

    story = []
    
    # --- TITLE PAGE HEADER ---
    header_data = [
        [
            Paragraph("<b>NIFTY 100 SCREENER ANALYSIS REPORT</b>", title_style),
            Paragraph(f"<b>Run Date:</b> {datetime.now().strftime('%Y-%m-%d')}", body_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[370, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#2563eb')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    config = load_screener_config()
    presets = config.get("presets", {})
    
    for idx, preset_name in enumerate(presets.keys()):
        df_res, desc = run_screener(preset_name=preset_name)
        
        story.append(Paragraph(f"<b>Preset {idx+1}: {preset_name}</b>", section_style))
        story.append(Paragraph(f"<i>Description:</i> {desc}", body_style))
        story.append(Spacer(1, 6))
        
        if df_res.empty:
            story.append(Paragraph("No companies matched this screener's criteria.", body_style))
            story.append(Spacer(1, 15))
            continue
            
        # Display top 15 matches to keep report concise but comprehensive
        df_display = df_res.head(15)
        story.append(Paragraph(f"Showing top {len(df_display)} matches out of {len(df_res)} total matches.", body_style))
        story.append(Spacer(1, 8))
        
        # Build results table
        col_widths = [60, 150, 120, 60, 60, 73]
        
        headers = [
            Paragraph("<b>Ticker</b>", table_header_style),
            Paragraph("<b>Company Name</b>", table_header_style),
            Paragraph("<b>Sector</b>", table_header_style),
            Paragraph("<b>Quality Score</b>", table_header_style),
            Paragraph("<b>ROE %</b>", table_header_style),
            Paragraph("<b>PE Ratio</b>", table_header_style)
        ]
        
        table_rows = [headers]
        
        for _, row in df_display.iterrows():
            qs_val = f"{row['composite_quality_score']:.1f}" if pd.notnull(row['composite_quality_score']) else "N/A"
            roe_val = f"{row['return_on_equity_pct']:.1f}%" if pd.notnull(row['return_on_equity_pct']) else "N/A"
            pe_val = f"{row['pe_ratio']:.1f}x" if pd.notnull(row['pe_ratio']) else "N/A"
            
            table_rows.append([
                Paragraph(f"<b>{row['company_id']}</b>", table_cell_style),
                Paragraph(row['company_name'][:25], table_cell_left),
                Paragraph(row['broad_sector'], table_cell_left),
                Paragraph(qs_val, table_cell_style),
                Paragraph(roe_val, table_cell_style),
                Paragraph(pe_val, table_cell_style)
            ])
            
        res_table = Table(table_rows, colWidths=col_widths)
        
        t_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]
        
        # Add zebra striping
        for r_idx in range(1, len(table_rows)):
            if r_idx % 2 == 0:
                t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#f8fafc')))
                
        res_table.setStyle(TableStyle(t_style))
        story.append(res_table)
        story.append(Spacer(1, 20))
        
        # Add page break between presets to make it look premium
        if idx < len(presets) - 1:
            story.append(PageBreak())
            # Re-append header for subsequent pages
            story.append(header_table)
            story.append(Spacer(1, 15))
            
    # Page footer builder
    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(36, 18, "CONFIDENTIAL · SCREENER ANALYSIS REPORT")
        canvas.drawRightString(A4[0] - 36, 18, f"Page {doc.page}")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    print(f"Screener presets report generated at: {pdf_path} in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    import pandas as pd
    generate_screener_reports()
