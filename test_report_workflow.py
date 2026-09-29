"""
End-to-End Test Suite for Real Report Workflow
Lifecycle: Evaluation -> Testing -> Review -> Approval -> Generate Report -> Refresh -> Reopen -> Retrieve Report
"""

import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
import os
import urllib.request
import urllib.error
import threading
import http.server

import server
import db

PORT = 8112
BASE_URL = f"http://127.0.0.1:{PORT}"

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, server.MetrolabServerHandler)
    httpd.serve_forever()

def make_req(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}

def main():
    print("=" * 70)
    print("STARTING TEST SUITE: REAL REPORT WORKFLOW")
    print("=" * 70)

    # 0. Initialize & seed database
    db.init_db()
    db.seed_database()

    # Start test server
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    # 1. Authenticate roles
    print("\n[Step 1] Authenticating all roles...")
    code, res_tech = make_req("/api/auth/login", "POST", {"username": "rajesh_inspector", "password": "Inspector@123"})
    assert code == 200 and res_tech.get("token"), f"Technician login failed: {res_tech}"
    tech_token = res_tech["token"]

    code, res_rev = make_req("/api/auth/login", "POST", {"username": "priya_reviewer", "password": "Reviewer@123"})
    assert code == 200 and res_rev.get("token"), f"Reviewer login failed: {res_rev}"
    rev_token = res_rev["token"]

    code, res_admin = make_req("/api/auth/login", "POST", {"username": "admin", "password": "Admin@123"})
    assert code == 200 and res_admin.get("token"), f"Admin login failed: {res_admin}"
    admin_token = res_admin["token"]

    code, res_essae = make_req("/api/auth/login", "POST", {"username": "essae_owner", "password": "Owner@123"})
    assert code == 200 and res_essae.get("token"), f"Essae Owner login failed: {res_essae}"
    essae_token = res_essae["token"]

    code, res_avery = make_req("/api/auth/login", "POST", {"username": "avery_owner", "password": "Owner@123"})
    assert code == 200 and res_avery.get("token"), f"Avery Owner login failed: {res_avery}"
    avery_token = res_avery["token"]
    print("  [OK] Authenticated Technician, Reviewer, Admin, Essae Owner, and Avery Owner.")

    # 2. Technician creates evaluation with test readings
    print("\n[Step 2] Technician creates evaluation with test readings...")
    unique_serial = f"WB-E2E-{int(time.time())}"
    inst_payload = {
        "manufacturer": "Essae Teraoka",
        "model": "DS-215 Benchmark Scale",
        "serialNumber": unique_serial,
        "typeApprovalNo": "IND/09/2024/777",
        "accuracyClass": "III",
        "maxCapacity": 150.0,
        "minCapacity": 1.0,
        "verificationScaleIntervalE": 0.05,
        "actualScaleIntervalD": 0.05,
        "unit": "kg",
        "tareCapacity": 50.0,
        "yearOfManufacture": 2024,
        "countryOfOrigin": "India"
    }

    test_readings = [
        {"id": "rd_1", "load": 1.0, "reading": 1.000, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"id": "rd_2", "load": 50.0, "reading": 50.002, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"id": "rd_3", "load": 100.0, "reading": 100.005, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"id": "rd_4", "load": 150.0, "reading": 150.008, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"}
    ]

    code, res_create = make_req("/api/evaluations", "POST", {
        "instrument": inst_payload,
        "serial_number": unique_serial,
        "test_date": "2026-09-29",
        "test_location": "National Metrology Testing Bay 3",
        "temperature_c": 20.8,
        "humidity_percent": 53.0,
        "pressure_hpa": 1012.4,
        "gravity_mps2": 9.792,
        "reference_standard": "Class F1 Standard Weights",
        "standards_traceability_no": "RRSL/DEL/2026/089",
        "status": "DRAFT",
        "readings": test_readings
    }, token=tech_token)
    assert code == 201 and res_create.get("evaluation_id"), f"Creation failed: {res_create}"
    eval_id = res_create["evaluation_id"]
    print(f"  [OK] Created evaluation: {eval_id} (Status: DRAFT)")

    # 3. Attempt to generate final report while DRAFT -> MUST BE PREVENTED (400)
    print("\n[Step 3] Attempting final report generation while in DRAFT status...")
    code, res_draft_gen = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", token=tech_token)
    assert code == 400, f"Expected 400 when generating report on DRAFT, got {code}: {res_draft_gen}"
    print(f"  [OK] Correctly prevented report generation on DRAFT evaluation: {res_draft_gen.get('error')}")

    # 4. Technician submits evaluation -> SUBMITTED
    print("\n[Step 4] Submitting evaluation for statutory review...")
    code, res_sub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", token=tech_token)
    assert code == 200 and res_sub.get("status") == "SUBMITTED", f"Submit failed: {res_sub}"
    print(f"  [OK] Evaluation submitted (Status: SUBMITTED)")

    # 5. Attempt to generate final report while SUBMITTED -> MUST BE PREVENTED (400)
    print("\n[Step 5] Attempting final report generation while in SUBMITTED status...")
    code, res_sub_gen = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", token=tech_token)
    assert code == 400, f"Expected 400 on SUBMITTED, got {code}: {res_sub_gen}"
    print(f"  [OK] Correctly prevented report generation on SUBMITTED evaluation: {res_sub_gen.get('error')}")

    # 6. Reviewer marks UNDER_REVIEW -> attempt to generate -> MUST BE PREVENTED (400)
    print("\n[Step 6] Reviewer marks UNDER_REVIEW and attempts report generation...")
    code, res_under = make_req(f"/api/evaluations/{eval_id}/review", "POST", {
        "verdict": "UNDER_REVIEW",
        "comments": "Commencing statutory checks and tolerance verification."
    }, token=rev_token)
    assert code == 200 and res_under.get("status") == "UNDER_REVIEW"
    
    code, res_under_gen = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", token=tech_token)
    assert code == 400, f"Expected 400 on UNDER_REVIEW, got {code}"
    print(f"  [OK] Correctly prevented report generation on UNDER_REVIEW evaluation")

    # 7. Reviewer APPROVES evaluation
    print("\n[Step 7] Reviewer approves evaluation...")
    code, res_app = make_req(f"/api/evaluations/{eval_id}/review", "POST", {
        "verdict": "APPROVE",
        "comments": "Statutory verification complete. Conforms to OIML R 76-1 accuracy specifications."
    }, token=rev_token)
    assert code == 200 and res_app.get("status") == "APPROVED", f"Approval failed: {res_app}"
    cert_num = res_app.get("certificate_number")
    assert cert_num, "Certificate number was not generated upon approval"
    print(f"  [OK] Evaluation approved! Generated Certificate: {cert_num}")

    # 8. Generate Final Statutory Report
    print("\n[Step 8] Generating final statutory ReportLab PDF report...")
    code, res_gen = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", token=tech_token)
    assert code == 200 and res_gen.get("success") is True, f"Report generation failed: {res_gen}"
    assert res_gen.get("evaluation_id") == eval_id
    assert res_gen.get("certificate_number") == cert_num
    assert res_gen.get("pdf_url")
    assert res_gen.get("filename")
    pdf_filename = res_gen["filename"]
    pdf_url = res_gen["pdf_url"]
    report_id = res_gen["report_id"]
    print(f"  [OK] Report generated successfully: {report_id}")
    print(f"    - Filename: {pdf_filename}")
    print(f"    - URL: {pdf_url}")
    print(f"    - Certificate No: {cert_num}")

    # Verify physical file existence and non-zero size
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    file_path = os.path.join(reports_dir, pdf_filename)
    assert os.path.exists(file_path), f"Generated PDF not found on disk at {file_path}"
    file_size = os.path.getsize(file_path)
    assert file_size > 1000, f"Generated PDF file size unexpectedly small: {file_size} bytes"
    print(f"  [OK] Verified PDF file on disk ({file_size:,} bytes)")

    # 9. Verify Persistent Storage & Retrieval (Refresh / Re-login Simulation)
    print("\n[Step 9] Simulating refresh / re-login to verify report retrieval...")

    # 9a. GET /api/evaluations/<eval_id> includes report metadata
    code, res_get_eval = make_req(f"/api/evaluations/{eval_id}", "GET", token=tech_token)
    assert code == 200
    eval_resp = res_get_eval.get("evaluation")
    report_resp = res_get_eval.get("report")
    assert eval_resp["status"] == "APPROVED"
    assert report_resp is not None, "Report object missing in GET /api/evaluations/<id>"
    assert report_resp["pdf_filename"] == pdf_filename
    assert report_resp["pdf_url"] == pdf_url
    assert report_resp["certificate_number"] == cert_num
    print("  [OK] GET /api/evaluations/<id> correctly restored report record and PDF URL")

    # 9b. GET /api/evaluations/<eval_id>/report
    code, res_direct_rep = make_req(f"/api/evaluations/{eval_id}/report", "GET", token=tech_token)
    assert code == 200 and res_direct_rep.get("success") is True
    assert res_direct_rep["report"]["pdf_filename"] == pdf_filename
    print("  [OK] GET /api/evaluations/<id>/report directly returned report metadata")

    # 9c. GET /api/reports?evaluation_id=<eval_id>
    code, res_filter_rep = make_req(f"/api/reports?evaluation_id={eval_id}", "GET", token=tech_token)
    assert code == 200
    rep_list = res_filter_rep.get("reports", [])
    assert len(rep_list) >= 1
    assert any(r["evaluation_id"] == eval_id and r["pdf_filename"] == pdf_filename for r in rep_list)
    print("  [OK] GET /api/reports query filter returned matching report")

    # 9d. GET /api/history includes pdf_url and certificate_number
    code, res_hist = make_req(f"/api/history?serial={unique_serial}", "GET", token=tech_token)
    assert code == 200
    hist = res_hist.get("history", [])
    assert len(hist) >= 1
    matching_hist = next(h for h in hist if h["report_id"] == eval_id)
    assert matching_hist.get("pdf_url") == pdf_url
    assert matching_hist.get("certificate_number") == cert_num
    print("  [OK] GET /api/history returns joined PDF link and statutory certificate number")

    # 10. Role & Fleet Security / Owner Isolation
    print("\n[Step 10] Testing Role & Fleet Access Controls...")
    # 10a. Reviewer can access report
    code, res_rev_rep = make_req(f"/api/evaluations/{eval_id}/report", "GET", token=rev_token)
    assert code == 200, f"Reviewer was denied access: {code}"

    # 10b. Admin can access report
    code, res_admin_rep = make_req(f"/api/evaluations/{eval_id}/report", "GET", token=admin_token)
    assert code == 200, f"Admin was denied access: {code}"

    # 10c. Associated Instrument Owner (Essae Teraoka) can access report
    code, res_essae_rep = make_req(f"/api/evaluations/{eval_id}/report", "GET", token=essae_token)
    assert code == 200, f"Associated owner was denied access: {code}"
    print("  [OK] Reviewer, Admin, and Associated Owner have legitimate access to report")

    # 10d. Unrelated Owner (Avery Weigh-Tronix) gets 403 Forbidden
    code, res_avery_rep = make_req(f"/api/evaluations/{eval_id}/report", "GET", token=avery_token)
    assert code == 403, f"Expected 403 for unrelated owner, got {code}: {res_avery_rep}"

    # 10e. Unrelated Owner attempting to generate PDF gets 403 Forbidden
    code, res_avery_gen = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", token=avery_token)
    assert code == 403, f"Expected 403 for unrelated owner generate, got {code}: {res_avery_gen}"
    print("  [OK] Unrelated owner properly blocked with 403 Forbidden (fleet isolation enforced)")

    # 11. Audit Trail Verification
    print("\n[Step 11] Verifying immutable Audit Log entries...")
    code, res_audit = make_req("/api/audit", "GET", token=admin_token)
    assert code == 200
    logs = res_audit.get("audit_logs", [])
    gen_logs = [l for l in logs if l.get("action") == "GENERATE_REPORT" and eval_id in str(l.get("details_json", ""))]
    assert len(gen_logs) >= 1, "GENERATE_REPORT audit log entry was not found!"
    print(f"  [OK] Verified GENERATE_REPORT audit log entry: {gen_logs[0]['id']}")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED: REAL REPORT WORKFLOW IS COMPLETE AND VERIFIED!")
    print("=" * 70)

if __name__ == "__main__":
    main()
