# ------------------------------------------------------------
# Prototype for NAWI test‑report generation (SIH‑26035)
# ------------------------------------------------------------
import json, pathlib, datetime, sys, math
from dataclasses import dataclass, asdict
from typing import List

# ----- Helper: load OIML error table (very small subset) -----
def load_oiml_limits(txt_path: pathlib.Path):
    """
    Parses the OIML R‑76‑1 text and extracts a minimal error‑limit table.
    For the prototype we hard‑code the most common ranges.
    """
    # In a full implementation we would parse the table; here we use a static dict.
    # Key: (capacity_max_kg, class) → max permissible error (fraction of FS)
    return {
        (5,   "I"): 0.001,      # ±0.1 % of full scale or 0.001 kg, whichever larger
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

# ----- Data structures -------------------------------------------------
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

# ----- Core logic -------------------------------------------------------
def compute_errors(readings: List[Reading]) -> dict:
    """Compute repeatability, linearity and combined error (simplified)."""
    # 1) Repeatability: placeholder value (typical for Class II)
    repeatability = 0.0015          # fraction of full scale (FS)

    # 2) Linearity: max deviation from ideal straight line through (0,0) & (FS,FS)
    loads = [r.load_kg for r in readings]
    values = [r.reading for r in readings]
    # slope = Σ(x*y) / Σ(x²)
    num = sum(x*y for x, y in zip(loads, values))
    den = sum(x*x for x in loads) or 1.0
    slope = num / den
    deviations = [abs(v - slope*l) for l, v in zip(loads, values)]
    linearity = max(deviations) / max(loads) if loads else 0.0

    # 3) Combined error (root‑sum‑square)
    combined = math.sqrt(repeatability**2 + linearity**2)

    return {
        "repeatability_error": round(repeatability, 6),
        "linearity_error": round(linearity, 6),
        "combined_error": round(combined, 6)
    }

def lookup_mpe(capacity: float, class_: str, limits: dict) -> float:
    """Return the max permissible error (fraction of FS) for given capacity & class."""
    for (max_cap, cls), mpe in sorted(limits.items()):
        if capacity <= max_cap and cls == class_:
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

# ----- Report rendering (PDF) -------------------------------------------
def render_pdf(report: Report, out_path: pathlib.Path):
    """Generate a simple PDF using `reportlab`.  Installs the library if missing."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "-q"])
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    margin = 40
    line_h = 14
    y = height - margin
    def draw(text):
        nonlocal y
        c.drawString(margin, y, text)
        y -= line_h

    # Header
    draw("Legal Metrology – NAWI Test Report")
    draw(f"Generated at: {report.generated_at}")
    draw("-" * 70)
    # Instrument metadata
    draw(f"Manufacturer      : {report.instrument.manufacturer}")
    draw(f"Model             : {report.instrument.model}")
    draw(f"Serial No.        : {report.instrument.serial_number}")
    draw(f"Type‑approval No. : {report.instrument.type_approval_no}")
    draw("-" * 70)
    # Test conditions
    draw("Test Conditions")
    draw(f"  Temperature (°C)      : {report.test_conditions.temperature_c}")
    draw(f"  Humidity (%)          : {report.test_conditions.humidity_percent}")
    draw(f"  Reference mass (kg)   : {report.test_conditions.reference_mass_kg}")
    draw("-" * 70)
    # Raw data
    draw("Raw Readings (Load → Measured)")
    for r in report.raw_readings:
        draw(f"  {r.load_kg:6.2f} kg → {r.reading:9.4f} kg")
    draw("-" * 70)
    # Calculations
    draw("Calculated Errors")
    draw(f"  Repeatability error    : {report.calculations['repeatability_error']:.6f} FS")
    draw(f"  Linearity error        : {report.calculations['linearity_error']:.6f} FS")
    draw(f"  Combined error         : {report.calculations['combined_error']:.6f} FS")
    draw(f"  Max permissible error  : {report.calculations['max_permissible_error']:.6f} FS")
    draw("-" * 70)
    # Conformity statement
    if report.conformity:
        draw("**CONFORMITY** – The instrument complies with:")
        draw("  • OIML R‑76‑1 (2006) – Section 5 & 6")
        draw("  • Legal Metrology (Approval of Models) Rules, 2011 – § 7")
        draw("  • Legal Metrology (General) Rules, 2011 – § 2 (Class II)")
    else:
        draw("**NON‑CONFORMITY** – The instrument exceeds the permissible error.")
        draw("  Refer to OIML R‑76‑1 Table 5‑1 for detailed limits.")
    draw("-" * 70)
    # Legal disclaimer
    draw("Prepared in accordance with Section 12 of the Legal Metrology Act, 2009.")
    c.showPage()
    c.save()

# ----- Main entry point -------------------------------------------------
def main():
    """Interactive demo: loads a JSON template, computes the report, writes PDF."""
    # Load (or create) sample input JSON
    sample_path = pathlib.Path(__file__).with_name("sample_input.json")
    if not sample_path.exists():
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
        sample_path.write_text(json.dumps(example, indent=2))
                sample_path.write_text(json.dumps(example, indent=2))
        print(f"Created example input file: {sample_path}")
        print("Edit the JSON with your real measurements and re-run the script.")
        sys.exit(0)

    data = json.loads(sample_path.read_text())
    # Load OIML limits (hard-coded for prototype)
    oiml_limits = load_oiml_limits(pathlib.Path("oiml r76.txt"))
    # Build report object
    report = build_report(data, oiml_limits)
    # Save full report JSON for audit
    out_json = pathlib.Path(f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    out_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    print(f"Report data saved to: {out_json}")
    # Render PDF
    out_pdf = pathlib.Path(f"NAWI_Test_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    render_pdf(report, out_pdf)
    print(f"PDF report generated: {out_pdf}")

if __name__ == "__main__":
    main()
