"""
Metrolab Unified Server & API Bridge
Serves both the modern React Web Interface and the Python OIML R-76 backend on http://localhost:8000
"""

import os
import sys
import json
import sqlite3
import datetime
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Import calculation and report generation routines from prototype_sih26035
import prototype_sih26035 as proto

PORT = 8000
BASE_DIR = Path(__file__).parent.resolve()
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH = str(BASE_DIR / "nawi_audit.db")
SAMPLE_FILE = BASE_DIR / "sample_input.json"

os.makedirs(REPORTS_DIR, exist_ok=True)
proto.init_db(DB_PATH)

class MetrolabApiHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # ==========================================
        # 1. API ENDPOINTS (/api/...)
        # ==========================================
        if path == "/api/status":
            self._set_cors_headers()
            stats = proto.get_statistics(DB_PATH)
            resp = {
                "status": "online",
                "engine": "OIML R-76 SIH-26035 Backend",
                "database": DB_PATH,
                "reports_count": len(list(REPORTS_DIR.glob("*"))),
                "stats": stats
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        elif path == "/api/sample":
            self._set_cors_headers()
            if SAMPLE_FILE.exists():
                with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"error": "sample_input.json not found"}).encode("utf-8"))
            return

        elif path == "/api/history":
            self._set_cors_headers()
            serial = query.get("serial", [""])[0]
            if serial:
                history = proto.get_instrument_history(serial, DB_PATH)
            else:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT report_id, instrument_serial, instrument_model, capacity, class, conformity, compliance_score, risk_level, created_at, inspector_name FROM reports ORDER BY created_at DESC LIMIT 20")
                rows = c.fetchall()
                conn.close()
                history = [dict(r) for r in rows]
            self.wfile.write(json.dumps(history).encode("utf-8"))
            return

        elif path == "/api/stats":
            self._set_cors_headers()
            stats = proto.get_statistics(DB_PATH)
            self.wfile.write(json.dumps(stats).encode("utf-8"))
            return

        elif path.startswith("/api/reports/"):
            filename = os.path.basename(path)
            file_path = REPORTS_DIR / filename
            if file_path.exists():
                mime = "application/pdf" if filename.endswith(".pdf") else "text/html"
                self._set_cors_headers(content_type=mime)
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Report file not found")
            return

        # ==========================================
        # 2. STATIC FRONTEND SPA SERVING
        # ==========================================
        else:
            rel_path = path.lstrip("/")
            target_file = FRONTEND_DIST / rel_path

            if not rel_path or not target_file.exists() or target_file.is_dir():
                target_file = FRONTEND_DIST / "index.html"

            if target_file.exists():
                content_type, _ = mimetypes.guess_type(str(target_file))
                if content_type is None:
                    if str(target_file).endswith(".js"):
                        content_type = "application/javascript"
                    elif str(target_file).endswith(".css"):
                        content_type = "text/css"
                    elif str(target_file).endswith(".svg"):
                        content_type = "image/svg+xml"
                    else:
                        content_type = "text/html"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                with open(target_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Frontend build not found. Run 'npm run build' in frontend directory.")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/api/save_audit":
            self._set_cors_headers()
            report_id = payload.get("report_id", f"REP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            instrument = payload.get("instrument", {})
            test_conditions = payload.get("test_conditions", {})
            calculations = payload.get("calculations", {})
            conformity = payload.get("conformity", False)

            report_data = {
                "report_id": report_id,
                "instrument": instrument,
                "test_conditions": test_conditions,
                "calculations": calculations,
                "conformity": conformity,
                "generated_at": payload.get("generated_at", datetime.datetime.now().isoformat()),
                "hash": calculations.get("verification_hash", proto.generate_hash(report_id))
            }

            proto.save_to_db(report_data, DB_PATH)

            self.wfile.write(json.dumps({
                "success": True,
                "report_id": report_id,
                "message": "Saved to SQLite audit database nawi_audit.db",
                "database": DB_PATH
            }).encode("utf-8"))
            return

        elif path == "/api/generate_pdf":
            self._set_cors_headers()
            instrument = payload.get("instrument", {})
            readings = payload.get("readings", [])
            test_conditions = payload.get("test_conditions", {})

            proto_input = {
                "instrument": {
                    "manufacturer": instrument.get("manufacturer", "Essae"),
                    "model": instrument.get("model", "DS-852"),
                    "serial_number": instrument.get("serialNumber") or instrument.get("serial_number", "DS-001"),
                    "type_approval_no": instrument.get("typeApprovalNo") or instrument.get("type_approval_no", "IND/LM/01"),
                    "max_capacity": float(instrument.get("maxCapacity") or instrument.get("max_capacity", 15.0)),
                    "min_capacity": float(instrument.get("minCapacity") or instrument.get("min_capacity", 0.04)),
                    "verification_scale_interval_e": float(instrument.get("verificationScaleIntervalE") or instrument.get("verification_scale_interval_e", 0.005)),
                    "accuracy_class": instrument.get("accuracyClass") or instrument.get("accuracy_class", "III")
                },
                "test_conditions": {
                    "temperature_c": float(test_conditions.get("temperatureC") or test_conditions.get("temperature_c", 25.0)),
                    "humidity_percent": float(test_conditions.get("humidityPercent") or test_conditions.get("humidity_percent", 55.0)),
                    "barometric_pressure_hpa": float(test_conditions.get("barometricPressureHpa") or test_conditions.get("barometric_pressure_hpa", 1013.0)),
                    "reference_mass_kg": float(instrument.get("maxCapacity") or 15.0),
                    "test_location": test_conditions.get("testLocation") or test_conditions.get("test_location", "RRSL"),
                    "inspector_name": test_conditions.get("inspectorName") or test_conditions.get("inspector_name", "Inspector"),
                    "inspector_id": test_conditions.get("inspectorId") or test_conditions.get("inspector_id", "INS-001")
                },
                "readings": [
                    {
                        "load_kg": float(r.get("load") or r.get("load_kg", 0)),
                        "reading": float(r.get("reading", 0)),
                        "direction": r.get("direction", "increasing"),
                        "repeat_number": int(r.get("repeatNumber") or r.get("repeat_number", 1)),
                        "position": r.get("position", "center")
                    }
                    for r in readings
                ]
            }

            serial_clean = proto_input["instrument"]["serial_number"].replace("/", "_").replace(" ", "_")
            temp_json_path = REPORTS_DIR / f"temp_{serial_clean}.json"
            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(proto_input, f, indent=2)

            try:
                proto.process_file(str(temp_json_path), str(REPORTS_DIR), no_db=False, gen_html=True, gen_csv=True)
                pdf_name = f"temp_{serial_clean}_report.pdf"
                html_name = f"temp_{serial_clean}_report.html"

                self.wfile.write(json.dumps({
                    "success": True,
                    "pdf_filename": pdf_name,
                    "html_filename": html_name,
                    "pdf_url": f"/api/reports/{pdf_name}",
                    "html_url": f"/api/reports/{html_name}",
                    "message": "ReportLab PDF and audit records successfully generated"
                }).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": str(e)
                }).encode("utf-8"))
            return

        else:
            self.send_error(404, "Not Found")

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, MetrolabApiHandler)
    print(f"===========================================================")
    print(f"  Metrolab Web Application running at http://localhost:{PORT}")
    print(f"  Press Ctrl+C to terminate.")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server.")

if __name__ == "__main__":
    run_server()
