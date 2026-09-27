"""
SIH-26035: Legal Metrology NAWI Compliance Prototype
====================================================
Comprehensive prototype for assessing Non-Automatic Weighing Instruments (NAWI)
against OIML R 76-1 limits.

Features:
- OIML Limit Parsing
- Core error calculations (Repeatability, Linearity, Eccentricity, Hysteresis, Combined Uncertainty)
- SQLite Audit Trail Database
- QR Code generation
- Professional PDF Reports (using reportlab)
- Rich HTML Dashboard Reports
- Excel/CSV Exports
- Batch Processing
- CLI functionality
"""

import os
import sys
import json
import uuid
import math
import hashlib
import sqlite3
import argparse
import subprocess
import datetime
from collections import defaultdict
from pathlib import Path
import csv
import statistics as stats_module
import http.server
import socketserver

# --- AUTO INSTALLER ---
def install_packages():
    required = {"reportlab", "qrcode", "matplotlib", "Pillow"}
    try:
        import pkg_resources
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = required - installed
    except ImportError:
        missing = required
        
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing, '-q'])
        except Exception as e:
            print(f"Failed to auto-install packages: {e}")

install_packages()

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

# --- OIML PARSING ---
def parse_oiml_limits_from_txt(content):
    limits = {"I": [], "II": [], "III": [], "IIII": []}
    lines = content.split('\n')
    current_class = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('Class'):
            current_class = line.split(' ')[1]
        elif current_class and ',' in line:
            parts = line.split(',')
            if len(parts) == 3:
                try:
                    mpe = float(parts[0])
                    min_load = float(parts[1]) if parts[1].strip() != 'None' else 0.0
                    max_load = float(parts[2]) if parts[2].strip() != 'None' else float('inf')
                    limits[current_class].append({'mpe': mpe, 'min': min_load, 'max': max_load})
                except ValueError:
                    pass
    return limits

def get_oiml_limits(accuracy_class):
    # Static fallback table if txt parsing isn't used
    fallback = {
        "I": [
            {"mpe": 0.5, "min": 0, "max": 50000},
            {"mpe": 1.0, "min": 50000, "max": 200000},
            {"mpe": 1.5, "min": 200000, "max": float('inf')}
        ],
        "II": [
            {"mpe": 0.5, "min": 0, "max": 5000},
            {"mpe": 1.0, "min": 5000, "max": 20000},
            {"mpe": 1.5, "min": 20000, "max": 100000}
        ],
        "III": [
            {"mpe": 0.5, "min": 0, "max": 500},
            {"mpe": 1.0, "min": 500, "max": 2000},
            {"mpe": 1.5, "min": 2000, "max": 10000}
        ],
        "IIII": [
            {"mpe": 0.5, "min": 0, "max": 50},
            {"mpe": 1.0, "min": 50, "max": 200},
            {"mpe": 1.5, "min": 200, "max": 1000}
        ]
    }
    
    oiml_file = Path("oiml_limits.txt")
    if oiml_file.exists():
        parsed = parse_oiml_limits_from_txt(oiml_file.read_text(encoding='utf-8'))
        if accuracy_class in parsed and parsed[accuracy_class]:
            return parsed[accuracy_class]
    return fallback.get(accuracy_class, fallback["III"])

def calculate_mpe(load_e, accuracy_class):
    limits = get_oiml_limits(accuracy_class)
    for limit in limits:
        if limit["min"] <= load_e <= limit["max"]:
            return limit["mpe"]
    return limits[-1]["mpe"] if limits else 1.5

# --- CORE CALCULATIONS ---
def compute_errors(instrument, readings):
    capacity = instrument.get('max_capacity', 1.0)
    e = instrument.get('verification_scale_interval_e', 0.001)
    acc_class = instrument.get('accuracy_class', 'III')
    
    # Organize readings
    grouped_by_load = defaultdict(list)
    for r in readings:
        grouped_by_load[r['load_kg']].append(r)
        
    # Repeatability
    repeatability = 0.0015 # default fallback
    max_repeatability_err = 0.0
    for load, r_list in grouped_by_load.items():
        inc_readings = [r['reading'] for r in r_list if r['direction'] == 'increasing']
        if len(inc_readings) > 1:
            mean = sum(inc_readings) / len(inc_readings)
            variance = sum((x - mean) ** 2 for x in inc_readings) / (len(inc_readings) - 1)
            stdev = math.sqrt(variance)
            err = stdev / capacity
            if err > max_repeatability_err:
                max_repeatability_err = err
    if max_repeatability_err > 0:
        repeatability = max_repeatability_err

    # Linearity
    linearity = 0.0
    # simple max deviation from ideal (reading == load)
    for r in readings:
        dev = abs(r['reading'] - r['load_kg']) / capacity
        if dev > linearity:
            linearity = dev

    # Hysteresis
    hysteresis = 0.0
    for load, r_list in grouped_by_load.items():
        inc = [r['reading'] for r in r_list if r['direction'] == 'increasing']
        dec = [r['reading'] for r in r_list if r['direction'] == 'decreasing']
        if inc and dec:
            diff = abs(sum(inc)/len(inc) - sum(dec)/len(dec)) / capacity
            if diff > hysteresis:
                hysteresis = diff
                
    # Eccentricity
    eccentricity = 0.0
    for load, r_list in grouped_by_load.items():
        positions = defaultdict(list)
        for r in r_list:
            positions[r.get('position', 'center')].append(r['reading'])
        if len(positions) > 1:
            means = {p: sum(v)/len(v) for p, v in positions.items()}
            diff = (max(means.values()) - min(means.values())) / capacity
            if diff > eccentricity:
                eccentricity = diff

    combined_uncertainty = math.sqrt(repeatability**2 + linearity**2 + eccentricity**2 + hysteresis**2)
    
    # Per-point evaluation
    results = []
    overall_pass = True
    
    for r in readings:
        load_e = r['load_kg'] / e
        mpe_e = calculate_mpe(load_e, acc_class)
        mpe_kg = mpe_e * e
        error_kg = r['reading'] - r['load_kg']
        passed = abs(error_kg) <= mpe_kg
        if not passed:
            overall_pass = False
            
        results.append({
            'load_kg': r['load_kg'],
            'reading': r['reading'],
            'direction': r['direction'],
            'error_kg': error_kg,
            'mpe_kg': mpe_kg,
            'passed': passed
        })

    # Compliance score (0-100): weighted average across all load points
    # Reflects overall instrument health, not just the single worst point
    if results:
        ratios = [abs(pt['error_kg']) / pt['mpe_kg'] if pt['mpe_kg'] > 0 else 0 for pt in results]
        avg_ratio = sum(ratios) / len(ratios)
        worst_ratio = max(ratios)
        # Blend: 70% average performance + 30% worst-case
        blended_ratio = 0.7 * avg_ratio + 0.3 * worst_ratio
        score = max(0.0, min(100.0, 100.0 * (1.0 - blended_ratio)))
    else:
        score = 100.0
    
    if score >= 90: risk_level = "LOW"
    elif score >= 70: risk_level = "MEDIUM"
    elif score >= 50: risk_level = "HIGH"
    else: risk_level = "CRITICAL"

    if not overall_pass:
        if risk_level in ["LOW", "MEDIUM"]: risk_level = "HIGH"

    return {
        'repeatability': repeatability,
        'linearity': linearity,
        'hysteresis': hysteresis,
        'eccentricity': eccentricity,
        'combined_uncertainty': combined_uncertainty,
        'point_results': results,
        'overall_pass': overall_pass,
        'compliance_score': score,
        'risk_level': risk_level
    }

# --- DATABASE ---
def init_db(db_path="nawi_audit.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        report_id TEXT PRIMARY KEY,
        instrument_serial TEXT,
        instrument_model TEXT,
        capacity REAL,
        class TEXT,
        combined_error REAL,
        mpe REAL,
        conformity INTEGER,
        compliance_score REAL,
        risk_level TEXT,
        created_at TEXT,
        inspector_name TEXT,
        inspector_id TEXT,
        json_data BLOB
    )''')
    conn.commit()
    conn.close()

def save_to_db(report_data, db_path="nawi_audit.db"):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO reports 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (
                  report_data['report_id'],
                  report_data['instrument']['serial_number'],
                  report_data['instrument']['model'],
                  report_data['instrument']['max_capacity'],
                  report_data['instrument']['accuracy_class'],
                  report_data['calculations']['combined_uncertainty'],
                  0.0, # fallback mpe col
                  1 if report_data['conformity'] else 0,
                  report_data['calculations']['compliance_score'],
                  report_data['calculations']['risk_level'],
                  report_data['generated_at'],
                  report_data['test_conditions']['inspector_name'],
                  report_data['test_conditions']['inspector_id'],
                  json.dumps(report_data).encode('utf-8')
              ))
    conn.commit()
    conn.close()

def get_instrument_history(serial_number, db_path="nawi_audit.db"):
    if not os.path.exists(db_path): return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM reports WHERE instrument_serial = ? ORDER BY created_at DESC', (serial_number,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_statistics(db_path="nawi_audit.db"):
    if not os.path.exists(db_path): return {}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*), SUM(conformity), AVG(compliance_score) FROM reports')
    total, passed, avg_score = c.fetchone()
    
    c.execute('SELECT risk_level, COUNT(*) FROM reports GROUP BY risk_level')
    risks = dict(c.fetchall())
    conn.close()
    
    total = total or 0
    passed = passed or 0
    return {
        'total_tests': total,
        'pass_rate': (passed / total * 100) if total > 0 else 0,
        'avg_compliance_score': avg_score or 0.0,
        'risk_distribution': risks
    }

# --- GENERATION ---
def generate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def generate_qr(report_data, output_path):
    qr_data = f"ReportID:{report_data['report_id']}|Serial:{report_data['instrument']['serial_number']}|Pass:{report_data['conformity']}|Hash:{report_data['hash'][:10]}"
    img = qrcode.make(qr_data)
    img.save(output_path)
    return output_path

def generate_pdf_report(report_data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph("GOVERNMENT OF INDIA", styles['Title']))
    story.append(Paragraph("LEGAL METROLOGY DEPARTMENT", styles['Heading1']))
    story.append(Paragraph("NAWI Compliance Verification Report", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(f"<b>Report ID:</b> {report_data['report_id']}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {report_data['generated_at']}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Instrument Info
    story.append(Paragraph("<b>Instrument Information:</b>", styles['Heading3']))
    inst = report_data['instrument']
    inst_data = [
        ["Manufacturer", inst['manufacturer'], "Model", inst['model']],
        ["Serial Number", inst['serial_number'], "Class", inst['accuracy_class']],
        ["Max Capacity", f"{inst['max_capacity']} kg", "Min Capacity", f"{inst['min_capacity']} kg"],
        ["Verification Scale Int (e)", f"{inst['verification_scale_interval_e']} kg", "", ""]
    ]
    t = Table(inst_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    # Results summary
    story.append(Paragraph("<b>Test Results Summary:</b>", styles['Heading3']))
    calc = report_data['calculations']
    status_color = colors.green if report_data['conformity'] else colors.red
    status_text = "PASS" if report_data['conformity'] else "FAIL"
    
    res_data = [
        ["Overall Status", status_text],
        ["Compliance Score", f"{calc['compliance_score']:.2f}%"],
        ["Risk Level", calc['risk_level']],
        ["Combined Uncertainty", f"{calc['combined_uncertainty']:.6f}"]
    ]
    t2 = Table(res_data, colWidths=[2.5*inch, 2.5*inch])
    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('TEXTCOLOR', (1,0), (1,0), status_color),
        ('FONTNAME', (1,0), (1,0), 'Helvetica-Bold'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.2*inch))
    
    # Readings table
    story.append(Paragraph("<b>Detailed Load Point Errors:</b>", styles['Heading3']))
    readings_data = [["Load (kg)", "Reading (kg)", "Direction", "Error (kg)", "MPE (kg)", "Result"]]
    for pt in calc['point_results']:
        readings_data.append([
            f"{pt['load_kg']:.3f}", f"{pt['reading']:.3f}", pt['direction'],
            f"{pt['error_kg']:.4f}", f"{pt['mpe_kg']:.4f}", "PASS" if pt['passed'] else "FAIL"
        ])
    t3 = Table(readings_data)
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t3)
    story.append(Spacer(1, 0.4*inch))

    # QR Code
    qr_path = report_data['report_id'] + "_qr.png"
    generate_qr(report_data, qr_path)
    story.append(RLImage(qr_path, width=1.5*inch, height=1.5*inch))
    story.append(Spacer(1, 0.2*inch))
    
    # Error breakdown table
    story.append(Paragraph("<b>Error Analysis Breakdown:</b>", styles['Heading3']))
    err_data = [
        ["Metric", "Value", "Description"],
        ["Repeatability", f"{calc['repeatability']:.6f}", "Max stdev of repeated readings / capacity"],
        ["Linearity", f"{calc['linearity']:.6f}", "Max deviation from ideal / capacity"],
        ["Hysteresis", f"{calc['hysteresis']:.6f}", "Max inc/dec difference / capacity"],
        ["Eccentricity", f"{calc['eccentricity']:.6f}", "Max positional difference / capacity"],
        ["Combined", f"{calc['combined_uncertainty']:.6f}", "Root sum of squares"],
    ]
    t4 = Table(err_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.Color(0.2, 0.2, 0.5)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t4)
    story.append(Spacer(1, 0.2*inch))
    
    # Legal citations
    story.append(Paragraph("<b>Legal Framework and Citations:</b>", styles['Heading3']))
    citations = [
        ["Reference", "Applicable Section"],
        ["OIML R 76-1 (2006)", "Sections 3, 5, 6 - Metrological requirements and MPE"],
        ["The Legal Metrology Act, 2009", "Section 12 - Approval of models"],
        ["LM (Approval of Models) Rules, 2011", "Rule 7 - Tests for approval"],
        ["LM (General) Rules, 2011", "Rule 2 - Classification"],
        ["IS 9281:2002 / ISO 76:2017", "Indian Standard for electronic weighing instruments"],
    ]
    t5 = Table(citations, colWidths=[3*inch, 3.5*inch])
    t5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.Color(0.1, 0.3, 0.1)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t5)
    story.append(Spacer(1, 0.3*inch))
    
    # Next calibration
    next_cal = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    story.append(Paragraph(f"<b>Validity Period:</b> 12 months | <b>Next Calibration Due:</b> {next_cal}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Inspector signature block
    story.append(Paragraph("___________________________", styles['Normal']))
    story.append(Paragraph(f"Inspector: {report_data['test_conditions']['inspector_name']} (ID: {report_data['test_conditions']['inspector_id']})", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    # Footer info
    story.append(Paragraph(f"<b>SHA-256 Hash:</b> {report_data['hash']}", styles['Normal']))
    story.append(Paragraph("Prepared in accordance with Section 12 of the Legal Metrology Act, 2009.", styles['Normal']))
    
    doc.build(story)
    if os.path.exists(qr_path):
        os.remove(qr_path)
    print(f"PDF generated: {output_path}")

def generate_html_report(report_data, output_path):
    calc = report_data['calculations']
    status_color = "#28a745" if report_data['conformity'] else "#dc3545"
    status_text = "PASS (CONFORMING)" if report_data['conformity'] else "FAIL (NON-CONFORMING)"
    
    risk_colors = {"LOW": "#28a745", "MEDIUM": "#ffc107", "HIGH": "#fd7e14", "CRITICAL": "#dc3545"}
    risk_color = risk_colors.get(calc['risk_level'], "#6c757d")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NAWI Compliance Report - {report_data['report_id']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        h1, h2, h3 {{ color: #0056b3; }}
        .header {{ text-align: center; border-bottom: 2px solid #0056b3; padding-bottom: 10px; margin-bottom: 20px; }}
        .badge {{ display: inline-block; padding: 10px 20px; font-size: 18px; font-weight: bold; color: white; border-radius: 5px; }}
        .card {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; background: #f9f9f9; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #0056b3; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .progress-bar {{ width: 100%; background-color: #e0e0e0; border-radius: 5px; overflow: hidden; }}
        .progress {{ height: 24px; background-color: {status_color}; text-align: center; color: white; line-height: 24px; }}
        @media print {{ body {{ margin: 0; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GOVERNMENT OF INDIA</h1>
        <h2>LEGAL METROLOGY DEPARTMENT</h2>
        <h3>NAWI Compliance Verification Report</h3>
    </div>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <div class="badge" style="background-color: {status_color};">{status_text}</div>
    </div>
    
    <div class="card">
        <h3>Compliance Score: {calc['compliance_score']:.2f}%</h3>
        <div class="progress-bar">
            <div class="progress" style="width: {calc['compliance_score']}%;">{calc['compliance_score']:.2f}%</div>
        </div>
        <p><b>Risk Level:</b> <span style="color: {risk_color}; font-weight: bold;">{calc['risk_level']}</span></p>
    </div>

    <div class="card">
        <h3>Instrument Details</h3>
        <table>
            <tr><th>Manufacturer</th><td>{report_data['instrument']['manufacturer']}</td><th>Model</th><td>{report_data['instrument']['model']}</td></tr>
            <tr><th>Serial Number</th><td>{report_data['instrument']['serial_number']}</td><th>Accuracy Class</th><td>{report_data['instrument']['accuracy_class']}</td></tr>
            <tr><th>Max Capacity</th><td>{report_data['instrument']['max_capacity']} kg</td><th>Min Capacity</th><td>{report_data['instrument']['min_capacity']} kg</td></tr>
            <tr><th>Verification Interval (e)</th><td>{report_data['instrument']['verification_scale_interval_e']} kg</td><th>Approval No</th><td>{report_data['instrument'].get('type_approval_no', 'N/A')}</td></tr>
        </table>
    </div>

    <div class="card">
        <h3>Test Conditions & Metadata</h3>
        <p><b>Report ID:</b> {report_data['report_id']}</p>
        <p><b>Date:</b> {report_data['generated_at']}</p>
        <p><b>Inspector:</b> {report_data['test_conditions']['inspector_name']} (ID: {report_data['test_conditions']['inspector_id']})</p>
        <p><b>Location:</b> {report_data['test_conditions']['test_location']}</p>
    </div>
    
    <h3>Load Point Analysis</h3>
    <table>
        <tr><th>Load (kg)</th><th>Reading (kg)</th><th>Direction</th><th>Error (kg)</th><th>MPE (kg)</th><th>Result</th></tr>"""
    
    for pt in calc['point_results']:
        pt_status_color = "green" if pt['passed'] else "red"
        html += f"<tr><td>{pt['load_kg']:.3f}</td><td>{pt['reading']:.3f}</td><td>{pt['direction']}</td><td>{pt['error_kg']:.4f}</td><td>{pt['mpe_kg']:.4f}</td><td style='color: {pt_status_color}; font-weight: bold;'>{'PASS' if pt['passed'] else 'FAIL'}</td></tr>"
        
    html += f"""
    </table>
    
    <div class="card">
        <h3>Error Breakdown</h3>
        <table>
            <tr><th>Metric</th><th>Value</th><th>Description</th></tr>
            <tr><td>Repeatability</td><td>{calc['repeatability']:.6f}</td><td>Max stdev of repeated readings / capacity</td></tr>
            <tr><td>Linearity</td><td>{calc['linearity']:.6f}</td><td>Max deviation from ideal response / capacity</td></tr>
            <tr><td>Hysteresis</td><td>{calc['hysteresis']:.6f}</td><td>Max diff between increasing and decreasing / capacity</td></tr>
            <tr><td>Eccentricity</td><td>{calc['eccentricity']:.6f}</td><td>Max diff across loading positions / capacity</td></tr>
            <tr><td><b>Combined Uncertainty</b></td><td><b>{calc['combined_uncertainty']:.6f}</b></td><td>Root sum of squares of all errors</td></tr>
        </table>
    </div>

    <div class="card">
        <h3>Per-Load Error Visualization</h3>
        <svg width="100%" height="200" viewBox="0 0 600 200">
            <rect width="600" height="200" fill="#f9f9f9" stroke="#ddd"/>"""
    
    # Build SVG bar chart for per-point errors
    point_results = calc['point_results']
    if point_results:
        max_err = max(abs(pt['error_kg']) for pt in point_results) or 0.001
        max_mpe = max(pt['mpe_kg'] for pt in point_results) or 0.001
        chart_max = max(max_err, max_mpe) * 1.2
        bar_width = min(40, 550 // max(len(point_results), 1))
        spacing = 5
        
        for i, pt in enumerate(point_results):
            x = 30 + i * (bar_width + spacing)
            err_height = abs(pt['error_kg']) / chart_max * 150
            mpe_height = pt['mpe_kg'] / chart_max * 150
            bar_color = "#28a745" if pt['passed'] else "#dc3545"
            
            # MPE limit line (grey)
            html += f'<rect x="{x}" y="{180 - mpe_height}" width="{bar_width}" height="2" fill="#999" opacity="0.7"/>'
            # Error bar
            html += f'<rect x="{x}" y="{180 - err_height}" width="{bar_width}" height="{err_height}" fill="{bar_color}" opacity="0.8"/>'
            # Label
            html += f'<text x="{x + bar_width//2}" y="195" text-anchor="middle" font-size="9">{pt["load_kg"]:.0f}kg</text>'
    
    html += """
            <text x="5" y="15" font-size="10" fill="#666">Error bars (green=pass, red=fail). Grey line = MPE limit.</text>
        </svg>
    </div>"""
    
    # Instrument history (from database)
    history = get_instrument_history(report_data['instrument']['serial_number'])
    if len(history) > 1:
        html += """
    <div class="card">
        <h3>Instrument History &amp; Trend</h3>
        <table>
            <tr><th>Date</th><th>Score</th><th>Result</th><th>Risk</th></tr>"""
        for h in history[:10]:
            h_color = "#28a745" if h['conformity'] else "#dc3545"
            html += f"<tr><td>{h['created_at'][:10]}</td><td>{h['compliance_score']:.1f}%</td>"
            html += f"<td style='color:{h_color};font-weight:bold;'>{'PASS' if h['conformity'] else 'FAIL'}</td>"
            html += f"<td>{h['risk_level']}</td></tr>"
        html += """
        </table>
    </div>"""
    
    # Next calibration date
    next_cal = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    
    html += f"""
    <div class="card">
        <h3>Calibration Schedule</h3>
        <p><b>Validity Period:</b> {report_data.get('validity_period_months', 12)} months</p>
        <p><b>Next Calibration Due:</b> {next_cal}</p>
    </div>

    <div class="card">
        <h3>Legal Framework &amp; Citations</h3>
        <table>
            <tr><th>Reference</th><th>Applicable Section</th></tr>
            <tr><td>OIML R 76-1 (2006)</td><td>Sections 3, 5, 6 - Metrological requirements &amp; MPE for NAWI</td></tr>
            <tr><td>The Legal Metrology Act, 2009</td><td>Section 12 - Approval of models of weights and measures</td></tr>
            <tr><td>Legal Metrology (Approval of Models) Rules, 2011</td><td>Rule 7 - Tests for approval; Rule 3 - Definitions</td></tr>
            <tr><td>Legal Metrology (General) Rules, 2011</td><td>Rule 2 - Classification of weighing instruments</td></tr>
            <tr><td>IS 9281:2002 / ISO 76:2017</td><td>Indian Standard for electronic weighing instruments</td></tr>
        </table>
    </div>

    <div style="margin-top:20px; padding:15px; border:2px solid #0056b3; border-radius:5px;">
        <h3 style="color:#0056b3;">Inspector Certification</h3>
        <p>I certify that the above test was conducted in accordance with the applicable standards
        and the results accurately reflect the performance of the instrument.</p>
        <br/>
        <table style="border:none; width:100%;">
            <tr style="border:none;">
                <td style="border:none; width:50%;"><b>Inspector Signature:</b> ___________________________</td>
                <td style="border:none; width:50%;"><b>Date:</b> {report_data['generated_at'][:10]}</td>
            </tr>
            <tr style="border:none;">
                <td style="border:none;"><b>Name:</b> {report_data['test_conditions']['inspector_name']}</td>
                <td style="border:none;"><b>ID:</b> {report_data['test_conditions']['inspector_id']}</td>
            </tr>
        </table>
    </div>

    <div style="font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 10px; margin-top:20px;">
        <p><b>SHA-256 Hash:</b> {report_data['hash']}</p>
        <p>This report is electronically generated and hashed for integrity verification.</p>
        <p>Prepared in accordance with Section 12 of the Legal Metrology Act, 2009.</p>
    </div>
</body>
</html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML generated: {output_path}")

def generate_csv_report(report_data, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Report ID", report_data['report_id']])
        writer.writerow(["Date", report_data['generated_at']])
        writer.writerow(["Serial Number", report_data['instrument']['serial_number']])
        writer.writerow(["Conformity", "PASS" if report_data['conformity'] else "FAIL"])
        writer.writerow([])
        writer.writerow(["Load (kg)", "Reading (kg)", "Direction", "Error (kg)", "MPE (kg)", "Result"])
        for pt in report_data['calculations']['point_results']:
            writer.writerow([pt['load_kg'], pt['reading'], pt['direction'], pt['error_kg'], pt['mpe_kg'], "PASS" if pt['passed'] else "FAIL"])
    print(f"CSV generated: {output_path}")

def process_file(file_path, output_dir, no_db, html_flag, csv_flag):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    instrument = data.get('instrument', {})
    readings = data.get('readings', [])
    test_conditions = data.get('test_conditions', {})
    
    calc_results = compute_errors(instrument, readings)
    
    report_data = {
        'report_id': str(uuid.uuid4()),
        'generated_at': datetime.datetime.now().isoformat(),
        'instrument': instrument,
        'test_conditions': test_conditions,
        'readings': readings,
        'calculations': calc_results,
        'conformity': calc_results['overall_pass'],
        'validity_period_months': 12
    }
    
    report_str = json.dumps(report_data, sort_keys=True)
    report_data['hash'] = generate_hash(report_str)
    
    if not no_db:
        save_to_db(report_data)
        
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pdf_path = os.path.join(output_dir, f"{base_name}_report.pdf")
    generate_pdf_report(report_data, pdf_path)
    
    if html_flag:
        html_path = os.path.join(output_dir, f"{base_name}_report.html")
        generate_html_report(report_data, html_path)
        
    if csv_flag:
        csv_path = os.path.join(output_dir, f"{base_name}_report.csv")
        generate_csv_report(report_data, csv_path)

def generate_sample_input(output_path):
    sample = {
        "instrument": {
            "manufacturer": "Essae Teraoka Pvt. Ltd.",
            "model": "DS-852",
            "serial_number": "ET-DS852-2026-0471",
            "type_approval_no": "IND/LM/09/2026/0471",
            "max_capacity": 15.0,
            "min_capacity": 0.04,
            "verification_scale_interval_e": 0.005,
            "accuracy_class": "III"
        },
        "test_conditions": {
            "temperature_c": 25.2,
            "humidity_percent": 58,
            "barometric_pressure_hpa": 1012.5,
            "reference_mass_kg": 15.0,
            "test_location": "Regional Reference Standards Laboratory, New Delhi",
            "inspector_name": "Rajesh Kumar Sharma",
            "inspector_id": "INS-DL-2024-0087"
        },
        "readings": [
            # --- Increasing direction, Repeat 1 (center) ---
            {"load_kg": 0.0,  "reading": 0.000,  "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 1.0,  "reading": 1.002,  "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 3.0,  "reading": 3.003,  "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 5.0,  "reading": 5.004,  "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 7.5,  "reading": 7.503,  "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 10.0, "reading": 10.005, "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 12.0, "reading": 12.004, "direction": "increasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 15.0, "reading": 15.006, "direction": "increasing", "repeat_number": 1, "position": "center"},
            # --- Increasing direction, Repeat 2 (center) ---
            {"load_kg": 0.0,  "reading": 0.000,  "direction": "increasing", "repeat_number": 2, "position": "center"},
            {"load_kg": 1.0,  "reading": 1.001,  "direction": "increasing", "repeat_number": 2, "position": "center"},
            {"load_kg": 5.0,  "reading": 5.003,  "direction": "increasing", "repeat_number": 2, "position": "center"},
            {"load_kg": 10.0, "reading": 10.004, "direction": "increasing", "repeat_number": 2, "position": "center"},
            {"load_kg": 15.0, "reading": 15.007, "direction": "increasing", "repeat_number": 2, "position": "center"},
            # --- Increasing direction, Repeat 3 (center) ---
            {"load_kg": 0.0,  "reading": 0.000,  "direction": "increasing", "repeat_number": 3, "position": "center"},
            {"load_kg": 5.0,  "reading": 5.005,  "direction": "increasing", "repeat_number": 3, "position": "center"},
            {"load_kg": 10.0, "reading": 10.006, "direction": "increasing", "repeat_number": 3, "position": "center"},
            {"load_kg": 15.0, "reading": 15.005, "direction": "increasing", "repeat_number": 3, "position": "center"},
            # --- Decreasing direction (hysteresis test) ---
            {"load_kg": 15.0, "reading": 15.007, "direction": "decreasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 10.0, "reading": 10.006, "direction": "decreasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 5.0,  "reading": 5.005,  "direction": "decreasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 1.0,  "reading": 1.002,  "direction": "decreasing", "repeat_number": 1, "position": "center"},
            {"load_kg": 0.0,  "reading": 0.001,  "direction": "decreasing", "repeat_number": 1, "position": "center"},
            # --- Eccentricity test (different positions at 5 kg) ---
            {"load_kg": 5.0,  "reading": 5.004,  "direction": "increasing", "repeat_number": 1, "position": "front-left"},
            {"load_kg": 5.0,  "reading": 5.003,  "direction": "increasing", "repeat_number": 1, "position": "front-right"},
            {"load_kg": 5.0,  "reading": 5.006,  "direction": "increasing", "repeat_number": 1, "position": "back-left"},
            {"load_kg": 5.0,  "reading": 5.002,  "direction": "increasing", "repeat_number": 1, "position": "back-right"}
        ]
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample, f, indent=4)
    print(f"Sample input generated at {output_path}")

def run_dashboard():
    port = 8000
    print(f"Starting dashboard on http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down.")

def print_banner():
    banner = """
 +===============================================================+
 |        SIH-26035: LEGAL METROLOGY NAWI COMPLIANCE             |
 |            Smart India Hackathon 2026 Prototype                |
 +===============================================================+
 |  FEATURES:                                                     |
 |   [1] OIML R 76-1 Compliance Testing (Classes I-IIII)         |
 |   [2] Repeatability | Linearity | Hysteresis | Eccentricity   |
 |   [3] Combined Uncertainty & Compliance Scoring (0-100%)      |
 |   [4] Risk Assessment (LOW / MEDIUM / HIGH / CRITICAL)        |
 |   [5] Professional PDF Reports with QR Code                   |
 |   [6] Interactive HTML Dashboard with SVG Charts              |
 |   [7] SQLite Audit Trail & Instrument History                 |
 |   [8] Batch Processing & CSV Export                           |
 |   [9] SHA-256 Tamper-Evident Hashing                          |
 |  [10] Legal Citations (LM Act 2009, OIML, IS Standards)       |
 +===============================================================+
    """
    print(banner)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Legal Metrology NAWI Compliance Prototype")
    parser.add_argument('-i', '--input', help="Input JSON file or directory")
    parser.add_argument('-o', '--output-dir', default="reports", help="Output directory")
    parser.add_argument('--html', action='store_true', help="Generate HTML report")
    parser.add_argument('--csv', action='store_true', help="Generate CSV export")
    parser.add_argument('--batch', action='store_true', help="Enable batch processing (treat input as directory)")
    parser.add_argument('--history', metavar='SERIAL', help="Show test history for an instrument")
    parser.add_argument('--stats', action='store_true', help="Show overall statistics from the database")
    parser.add_argument('--dashboard', action='store_true', help="Launch local web server dashboard")
    parser.add_argument('--no-db', action='store_true', help="Skip database storage")

    args = parser.parse_args()

    if args.dashboard:
        run_dashboard()
        return

    if args.stats:
        stats = get_statistics()
        print("--- DATABASE STATISTICS ---")
        for k, v in stats.items():
            print(f"{k}: {v}")
        return

    if args.history:
        history = get_instrument_history(args.history)
        print(f"--- HISTORY FOR {args.history} ---")
        for r in history:
            print(f"Date: {r['created_at']}, Score: {r['compliance_score']}, Conformity: {r['conformity']}, Risk: {r['risk_level']}")
        return

    if not args.input:
        if not os.path.exists('sample_input.json'):
            generate_sample_input('sample_input.json')
        args.input = 'sample_input.json'

    os.makedirs(args.output_dir, exist_ok=True)

    if args.batch:
        if not os.path.isdir(args.input):
            print("Error: For batch mode, input must be a directory.")
            return
        for file in os.listdir(args.input):
            if file.endswith('.json'):
                process_file(os.path.join(args.input, file), args.output_dir, args.no_db, args.html, args.csv)
    else:
        if not os.path.exists(args.input):
            generate_sample_input(args.input)
        process_file(args.input, args.output_dir, args.no_db, args.html, args.csv)

if __name__ == "__main__":
    main()
