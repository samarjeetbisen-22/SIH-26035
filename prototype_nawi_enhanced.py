# ------------------------------------------------------------
# Enhanced NAWI test‑report prototype (SIH‑26035)
# ------------------------------------------------------------
import json, pathlib, datetime, sys, math, argparse, hashlib
from dataclasses import dataclass, asdict
from typing import List

# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------
@dataclass
class Reading:
    load_kg: float
    reading: float

@dataclass
class Instrument:
    manufacturer: str
    model: str
    serial_number: str
    type_approval_no: str

@dataclass
class TestConditions:
    temperature_c: float
    humidity_percent: float
    reference_mass_kg: float

@dataclass
class Report:
    instrument: Instrument
    test_conditions: TestConditions
    capacity_kg: float
    class_: str               # "I" or "II"
    raw_readings: List[Reading]
    calculations: dict
    conformity: bool
    generated_at: str

# ------------------------------------------------------------------
# OIML error‑limit handling – tries to parse the official PDF‑converted text
# ------------------------------------------------------------------
def parse_oiml_limits_from_txt(txt_path: pathlib.Path) -> dict:
    """Parse the OIML R‑76‑1 error‑limit tables from the extracted text.
    The official recommendation contains rows that look like one of the
    following (spacing may vary):
        "0‑5   0.001   0.0015"
        "5‑20  0.001   0.0015"
        "≥1000 0.005   0.006"
    where the first column is the capacity range (kg), the second column is the
    permissible error for Class I, and the third column for Class II.  The function
    extracts the **maximum** capacity of each range and stores the two errors in a
    dictionary keyed by ``(max_capacity, class)``.
    It tolerates an en‑dash, hyphen, leading/trailing spaces, and ignores noisy
    lines.
    """
    import re
    limits = {}
    if not txt_path.exists():
        return limits
    # Regex captures range (may include ≥ or ≤), then two floats
    pattern = re.compile(r"(?P<range>(?:[≥≤]?\s*\d+(?:[\s‑-]+\d+)?))\s+(?P<classI>\d*\.\d+)\s+(?P<classII>\d*\.\d+)")
    for raw_line in txt_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace('‑', '-')
        m = pattern.search(line)
        if not m:
            continue
        range_part = m.group('range').replace(' ', '')
        # Determine max capacity
        if range_part.startswith('≥'):
            max_cap = float(range_part[1:])
        elif '-' in range_part:
            try:
                max_cap = float(range_part.split('-')[-1])
            except ValueError:
                continue
        else:
            try:
                max_cap = float(range_part)
            except ValueError:
                continue
        try:
            class_i = float(m.group('classI'))
            class_ii = float(m.group('classII'))
        except ValueError:
            continue
        limits[(max_cap, "I")] = class_i
        limits[(max_cap, "II")] = class_ii
    return limits

def get_oiml_limits(txt_path: pathlib.Path) -> dict:
    parsed = parse_oiml_limits_from_txt(txt_path)
    if parsed:
        return parsed
    # Fallback static table (same as original prototype)
    return {
        (5,   "I"): 0.001,
        (5,   "II"): 0.0015,
        (20,  "I"): 0.001,
        (20,  "II"): 0.0015,
        (100, "I"): 0.002,
        (100, "II"): 0.003,
        (500, "I"): 0.003,
        (500, "II"): 0.004,
        (9999,"I"): 0.004,
        (9999,"II"): 0.005,
    }

# ------------------------------------------------------------------
# Core calculations
# ------------------------------------------------------------------
def compute_errors(readings: List[Reading], capacity: float) -> dict:
    """Compute repeatability, linearity and combined error.

    * **Repeatability** – derived from the spread of repeated measurements at the same load.
      For each distinct load we compute the standard deviation of its readings; the
      worst (maximum) standard deviation across all loads is taken and expressed as a
      fraction of the full‑scale capacity.
    * **Linearity** – same as before (max deviation from ideal slope, expressed as
      a fraction of full scale).
    * **Combined error** – sqrt(repeatability² + linearity²).

    If a load appears only once (i.e., no repeats), we fall back to the original
    placeholder of 0.0015 FS.
    """
    # ---- Repeatability ---------------------------------------------------
    from collections import defaultdict
    import statistics

    # Group readings by load value (tolerance for floating‑point equality)
    groups = defaultdict(list)
    for r in readings:
        groups[round(r.load_kg, 6)].append(r.reading)

    # Compute std‑dev for each group; if a group has a single value, ignore it.
    std_devs = [statistics.stdev(vals) for vals in groups.values() if len(vals) > 1]
    if std_devs:
        repeatability = max(std_devs) / capacity  # fraction of full scale
    else:
        # No repeats available – use historic placeholder (0.0015 FS)
        repeatability = 0.0015

    # ---- Linearity -------------------------------------------------------
    loads = [r.load_kg for r in readings]
    vals = [r.reading for r in readings]
    # Linear regression through origin (ideal slope = 1)
    num = sum(l * v for l, v in zip(loads, vals))
    den = sum(l * l for l in loads) or 1.0
    slope = num / den
    deviations = [abs(v - slope * l) for l, v in zip(loads, vals)]
    linearity = max(deviations) / max(loads) if loads else 0.0

    # ---- Combined error ---------------------------------------------------
    combined = (repeatability ** 2 + linearity ** 2) ** 0.5
    return {
        "repeatability_error": round(repeatability, 6),
        "linearity_error": round(linearity, 6),
        "combined_error": round(combined, 6),
    }
    """Compute repeatability, linearity and combined error (simplified)."""
    # Placeholder repeatability for Class II – in a real app this would be derived from repeats
    repeatability = 0.0015  # fraction of full scale (FS)
    loads = [r.load_kg for r in readings]
    vals = [r.reading for r in readings]
    # Linear regression through origin (ideal slope)
    num = sum(l * v for l, v in zip(loads, vals))
    den = sum(l * l for l in loads) or 1.0
    slope = num / den
    deviations = [abs(v - slope * l) for l, v in zip(loads, vals)]
    linearity = max(deviations) / max(loads) if loads else 0.0
    combined = math.sqrt(repeatability ** 2 + linearity ** 2)
    return {
        "repeatability_error": round(repeatability, 6),
        "linearity_error": round(linearity, 6),
        "combined_error": round(combined, 6),
    }

def lookup_mpe(capacity: float, cls: str, limits: dict) -> float:
    for (max_cap, c), mpe in sorted(limits.items()):
        if capacity <= max_cap and c == cls:
            return mpe
    return max(limits.values())

def build_report(data: dict, limits: dict) -> Report:
    instrument = Instrument(**data["instrument"])
    conditions = TestConditions(**data["test_conditions"])
    readings = [Reading(**r) for r in data["raw_readings"]]
    calc = compute_errors(readings)
    mpe = lookup_mpe(data["capacity_kg"], data["class"], limits)
    conformity = calc["combined_error"] <= mpe
    calc["max_permissible_error"] = round(mpe, 6)
    return Report(
        instrument=instrument,
        test_conditions=conditions,
        capacity_kg=data["capacity_kg"],
        class_=data["class"],
        raw_readings=readings,
        calculations=calc,
        conformity=conformity,
        generated_at=datetime.datetime.now().isoformat()
    )

# ------------------------------------------------------------------
# PDF generation (ReportLab – installed on‑demand)
# ------------------------------------------------------------------
def render_pdf(report: Report, out_path: pathlib.Path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "-q"])
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(out_path), pagesize=A4)
    margin, line_h = 40, 14
    y = A4[1] - margin
    def draw(txt: str):
        nonlocal y
        c.drawString(margin, y, txt)
        y -= line_h
    # Header & metadata
    draw("Legal Metrology – NAWI Test Report")
    draw(f"Generated at: {report.generated_at}")
    draw("-" * 70)
    draw(f"Manufacturer      : {report.instrument.manufacturer}")
    draw(f"Model             : {report.instrument.model}")
    draw(f"Serial No.        : {report.instrument.serial_number}")
    draw(f"Type‑approval No. : {report.instrument.type_approval_no}")
    draw("-" * 70)
    draw("Test Conditions")
    draw(f"  Temperature (°C)      : {report.test_conditions.temperature_c}")
    draw(f"  Humidity (%)          : {report.test_conditions.humidity_percent}")
    draw(f"  Reference mass (kg)   : {report.test_conditions.reference_mass_kg}")
    draw("-" * 70)
    draw("Raw Readings (Load → Measured)")
    for r in report.raw_readings:
        draw(f"  {r.load_kg:6.2f} kg → {r.reading:9.4f} kg")
    draw("-" * 70)
    draw("Calculated Errors")
    draw(f"  Repeatability error    : {report.calculations['repeatability_error']:.6f} FS")
    draw(f"  Linearity error        : {report.calculations['linearity_error']:.6f} FS")
    draw(f"  Combined error         : {report.calculations['combined_error']:.6f} FS")
    draw(f"  Max permissible error  : {report.calculations['max_permissible_error']:.6f} FS")
    draw("-" * 70)
    if report.conformity:
        draw("**CONFORMITY** – The instrument complies with:")
        draw("  • OIML R‑76‑1 (2006) – Section 5 & 6")
        draw("  • Legal Metrology (Approval of Models) Rules, 2011 – § 7")
        draw("  • Legal Metrology (General) Rules, 2011 – § 2 (Class II)")
    else:
        draw("**NON‑CONFORMITY** – The instrument exceeds the permissible error.")
        draw("  Refer to OIML R‑76‑1 Table 5‑1 for detailed limits.")
    draw("-" * 70)
    draw("Prepared in accordance with Section 12 of the Legal Metrology Act, 2009.")
    c.showPage()
    c.save()

# ------------------------------------------------------------------
# Optional HTML rendering (lightweight)
# ------------------------------------------------------------------
def render_html(report: Report, out_path: pathlib.Path):
    html = f"""
    <html><head><meta charset='utf-8'><title>NAWI Test Report</title>
    <style>body{{font-family:Arial, sans-serif; margin:40px;}}
    h1{{border-bottom:2px solid #333;}}
    table{{border-collapse:collapse;width:100%;margin-top:10px;}}
    th,td{{border:1px solid #ccc;padding:5px;text-align:left;}}</style></head>
    <body>
    <h1>Legal Metrology – NAWI Test Report</h1>
    <p><strong>Generated at:</strong> {report.generated_at}</p>
    <h2>Instrument</h2>
    <ul>
        <li>Manufacturer: {report.instrument.manufacturer}</li>
        <li>Model: {report.instrument.model}</li>
        <li>Serial No.: {report.instrument.serial_number}</li>
        <li>Type‑approval No.: {report.instrument.type_approval_no}</li>
    </ul>
    <h2>Test Conditions</h2>
    <ul>
        <li>Temperature (°C): {report.test_conditions.temperature_c}</li>
        <li>Humidity (%): {report.test_conditions.humidity_percent}</li>
        <li>Reference mass (kg): {report.test_conditions.reference_mass_kg}</li>
    </ul>
    <h2>Raw Readings</h2>
    <table><tr><th>Load (kg)</th><th>Reading (kg)</th></tr>
    {''.join(f'<tr><td>{r.load_kg:.2f}</td><td>{r.reading:.4f}</td></tr>' for r in report.raw_readings)}
    </table>
    <h2>Calculated Errors</h2>
    <ul>
        <li>Repeatability error: {report.calculations['repeatability_error']:.6f} FS</li>
        <li>Linearity error: {report.calculations['linearity_error']:.6f} FS</li>
        <li>Combined error: {report.calculations['combined_error']:.6f} FS</li>
        <li>Max permissible error: {report.calculations['max_permissible_error']:.6f} FS</li>
    </ul>
    <h2>Conformity</h2>
    <p>{'✔️ Conforms' if report.conformity else '❌ Does not conform'} to required standards.</p>
    <p>Prepared in accordance with Section 12 of the Legal Metrology Act, 2009.</p>
    </body></html>
    """
    out_path.write_text(html, encoding='utf-8')
    return out_path

# ------------------------------------------------------------------
# Helper: SHA‑256 hash for integrity verification
# ------------------------------------------------------------------
def write_hash_file(pdf_path: pathlib.Path) -> pathlib.Path:
    sha = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    hash_path = pdf_path.with_suffix('.sha256')
    hash_path.write_text(sha.hexdigest())
    return hash_path

# ------------------------------------------------------------------
# CLI handling
# ------------------------------------------------------------------
def parse_cli_args():
    parser = argparse.ArgumentParser(description="Generate NAWI test report (SIH‑26035)")
    parser.add_argument("-i", "--input", type=str, default="sample_input.json",
                        help="Path to JSON input file containing test data")
    parser.add_argument("-o", "--output-dir", type=str, default=".",
                        help="Directory where PDF/JSON/HTML/Hash files will be written")
    parser.add_argument("--html", action="store_true",
                        help="Also produce an HTML version of the report")
    return parser.parse_args()

# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------
def main():
    args = parse_cli_args()
    out_dir = pathlib.Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        example = {
            "instrument": {
                "manufacturer": "Acme Instruments Ltd.",
                "model": "NAWI‑500",
                "serial_number": "NAWI‑500‑00123",
                "type_approval_no": "TP‑2024‑001"
            },
            "test_conditions": {
                "temperature_c": 22.0,
                "humidity_percent": 45.0,
                "reference_mass_kg": 5.0
            },
            "capacity_kg": 100,
            "class": "II",
            "raw_readings": [
                {"load_kg": 0,   "reading": 0.001},
                {"load_kg": 10,  "reading": 10.004},
                {"load_kg": 20,  "reading": 20.009},
                {"load_kg": 50,  "reading": 50.018},
                {"load_kg": 100, "reading": 100.032}
            ]
        }
        input_path.write_text(json.dumps(example, indent=2))
        print(f"Created example input file: {input_path}")
        print("Edit the JSON with your real measurements and re‑run the script.")
        sys.exit(0)
    data = json.loads(input_path.read_text())
    # Load OIML limits from the extracted clean table (oiml_limits.txt). If not present, fall back to static table.
    oiml_limits = get_oiml_limits(pathlib.Path("oiml_limits.txt"))
    report = build_report(data, oiml_limits)
    # Persist JSON report
    json_path = out_dir / f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    print(f"Report data saved to: {json_path}")
    # PDF
    pdf_path = out_dir / f"NAWI_Test_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    render_pdf(report, pdf_path)
    print(f"PDF report generated: {pdf_path}")
    # SHA‑256 hash file
    hash_path = write_hash_file(pdf_path)
    print(f"SHA‑256 hash saved to: {hash_path}")
    # Optional HTML
    if args.html:
        html_path = out_dir / f"NAWI_Test_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        render_html(report, html_path)
        print(f"HTML report generated: {html_path}")

if __name__ == "__main__":
    main()
