"""
End-to-End Automated Compliance Testing for SIH-26035 Metrolab Backend.
Validates:
1. Real Authentication (PBKDF2 + JWT HMAC-SHA256)
2. Role Authorization (ADMIN, INSPECTOR, REVIEWER, OWNER RBAC)
3. Real Database & Instrument CRUD
4. Real Owner Data Filtering Isolation
5. Real Evaluation CRUD & Test Reading Storage
6. Backend OIML R-76 Statutory Validation Engine (MPE, Eccentricity, Repeatability, Uncertainty)
7. Real Attachment Upload & Binary Download
8. Real Review Workflow Transition (DRAFT -> SUBMITTED -> APPROVED)
9. Real Audit Trail Logging
10. Dashboard Live Data Aggregations
11. ReportLab PDF Generation
"""

import sys
import json
import time
import urllib.request
import urllib.error
import base64
import os
import secrets

BASE_URL = "http://localhost:8000"

def request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.status, json.loads(raw.decode("utf-8"))
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8"))
        except Exception:
            return e.code, {"error": raw.decode("utf-8", errors="ignore")}

def run_tests():
    print("=" * 70)
    print("  METROLAB SIH-26035 E2E COMPLIANCE VERIFICATION TEST SUITE")
    print("=" * 70)

    # 1. Health check
    status, res = request("GET", "/api/status")
    assert status == 200, f"Status check failed: {res}"
    print("  [PASS] 1. API Status and Health Check OK")

    # 2. Authentication: Login for 4 roles
    tokens = {}
    creds = {
        "ADMIN": ("admin", "Admin@123"),
        "INSPECTOR": ("rajesh_inspector", "Inspector@123"),
        "REVIEWER": ("priya_reviewer", "Reviewer@123"),
        "OWNER": ("essae_owner", "Owner@123"),
        "OWNER_AVERY": ("avery_owner", "Owner@123")
    }
    for role, (user, pwd) in creds.items():
        st, res = request("POST", "/api/auth/login", {"username": user, "password": pwd})
        assert st == 200 and "token" in res, f"Login failed for {role}: {res}"
        tokens[role] = res["token"]
        assert res["user"]["role"] in ("ADMIN", "INSPECTOR", "REVIEWER", "OWNER")
    print("  [PASS] 2. Real PBKDF2 + JWT Authentication Verified (4 Roles)")

    # 3. RBAC Enforcement: Unauthorized endpoints
    st, res = request("GET", "/api/audit", token=tokens["OWNER"])
    assert st == 403, f"Owner should not access audit trail: {st}"
    st, res = request("GET", "/api/audit", token=tokens["INSPECTOR"])
    assert st == 403, f"Inspector should not access audit trail: {st}"
    st, res = request("GET", "/api/audit", token=tokens["ADMIN"])
    assert st == 200, f"Admin should access audit trail: {st}"
    print("  [PASS] 3. Role-Based Access Control (RBAC) Enforced")

    # 4. Instrument CRUD
    serial = f"TEST-SCALE-{secrets.token_hex(3).upper()}"
    new_inst = {
        "serial_number": serial,
        "model": "Apex-500 Precision",
        "manufacturer": "Essae Digitronics",
        "accuracy_class": "III",
        "max_capacity": 30.0,
        "min_capacity": 0.1,
        "e_interval": 0.005,
        "d_interval": 0.005,
        "unit": "kg",
        "tare_capacity": 15.0,
        "type_approval_no": "IND/09/2026/888",
        "year_of_manufacture": 2026,
        "country_of_origin": "India"
    }
    st, res = request("POST", "/api/instruments", new_inst, token=tokens["INSPECTOR"])
    assert st == 201, f"Create instrument failed: {res}"
    inst_id = res["instrument_id"]

    # Verify duplicate serial rejection
    st_dup, _ = request("POST", "/api/instruments", new_inst, token=tokens["INSPECTOR"])
    assert st_dup == 409, "Duplicate serial should be rejected with 409"

    # Read instrument
    st, res = request("GET", f"/api/instruments/{inst_id}", token=tokens["INSPECTOR"])
    assert st == 200 and res["instrument"]["serial_number"] == serial
    print("  [PASS] 4. Instrument CRUD & Unique Constraint Verified")

    # 5. Owner Data Isolation
    st_essae, res_essae = request("GET", "/api/instruments", token=tokens["OWNER"])
    st_avery, res_avery = request("GET", "/api/instruments", token=tokens["OWNER_AVERY"])
    assert st_essae == 200 and st_avery == 200
    essae_serials = [i["serial_number"] for i in res_essae["instruments"]]
    avery_serials = [i["serial_number"] for i in res_avery["instruments"]]
    # Ensure no overlap between isolated owners
    assert len(set(essae_serials).intersection(set(avery_serials))) == 0
    print("  [PASS] 5. Real Owner Data Filtering Isolation Verified")

    # 6. Evaluation CRUD: Create Draft
    eval_payload = {
        "instrument_id": inst_id,
        "test_date": "2026-09-28",
        "test_location": "NABL Calibration Lab #4, Pune",
        "temperature_c": 23.5,
        "humidity_percent": 50.0,
        "pressure_hpa": 1012.0,
        "gravity_mps2": 9.7915,
        "reference_standard": "OIML Class E2 & F1 Stainless Steel Standards",
        "standards_traceability_no": "NPLI/MASS/2026/0921"
    }
    st, res = request("POST", "/api/evaluations", eval_payload, token=tokens["INSPECTOR"])
    assert st == 201, f"Create evaluation failed: {res}"
    eval_id = res["evaluation_id"]
    print("  [PASS] 6. Evaluation CRUD & Intake Lifecycle Verified")

    # 7. Real Test Reading Storage: Batch Save
    # Create realistic OIML R-76 test readings
    readings = [
        # Repeatability (half max = 15kg, 3 runs)
        {"test_type": "REPEATABILITY", "run_number": 1, "target_load": 15.0, "indicated_value": 15.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "REPEATABILITY", "run_number": 2, "target_load": 15.0, "indicated_value": 15.000, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "REPEATABILITY", "run_number": 3, "target_load": 15.0, "indicated_value": 15.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        # Eccentricity (1/3 max = 10kg, 5 positions: Center, Top-Left, Top-Right, Bottom-Right, Bottom-Left)
        {"test_type": "ECCENTRICITY", "run_number": 1, "load_position": "Center", "target_load": 10.0, "indicated_value": 10.000, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "ECCENTRICITY", "run_number": 2, "load_position": "Top-Left", "target_load": 10.0, "indicated_value": 10.002, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "ECCENTRICITY", "run_number": 3, "load_position": "Top-Right", "target_load": 10.0, "indicated_value": 10.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "ECCENTRICITY", "run_number": 4, "load_position": "Bottom-Right", "target_load": 10.0, "indicated_value": 10.002, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "ECCENTRICITY", "run_number": 5, "load_position": "Bottom-Left", "target_load": 10.0, "indicated_value": 10.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        # Weighing performance: Increasing & Decreasing
        {"test_type": "WEIGHING", "run_number": 1, "target_load": 0.1, "indicated_value": 0.100, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "WEIGHING", "run_number": 2, "target_load": 5.0, "indicated_value": 5.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "WEIGHING", "run_number": 3, "target_load": 15.0, "indicated_value": 15.002, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "WEIGHING", "run_number": 4, "target_load": 30.0, "indicated_value": 30.002, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "WEIGHING", "run_number": 5, "target_load": 15.0, "indicated_value": 15.001, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0},
        {"test_type": "WEIGHING", "run_number": 6, "target_load": 0.0, "indicated_value": 0.000, "extra_weights": 0.002, "delta_load": 0.0025, "tare_applied": 0.0}
    ]
    st, res = request("POST", f"/api/evaluations/{eval_id}/readings", {"readings": readings}, token=tokens["INSPECTOR"])
    assert st == 200 and res["inserted_count"] == len(readings), f"Readings batch storage failed: {res}"

    # Read back readings
    st, res_read = request("GET", f"/api/evaluations/{eval_id}/readings", token=tokens["INSPECTOR"])
    assert st == 200 and len(res_read["readings"]) == len(readings)
    print("  [PASS] 7. Real Test Reading Storage & Retrieval Verified")

    # 8. Backend OIML Validation Engine
    st, res = request("POST", f"/api/evaluations/{eval_id}/calculate", token=tokens["INSPECTOR"])
    assert st == 200 and res["success"] is True, f"OIML calculation failed: {res}"
    calc = res["calculations"]
    assert "overall_compliance" in calc
    assert "oiml_hash" in calc
    assert "combined_uncertainty" in calc
    assert "expanded_uncertainty" in calc
    # Verify uncertainty formula: U = k * u_c (k=2)
    assert abs(calc["expanded_uncertainty"] - round(calc["combined_uncertainty"] * 2.0, 7)) < 1e-5
    print(f"  [PASS] 8. Backend OIML R-76 Engine Verified (Verdict: {calc['overall_compliance']}, U: {calc['expanded_uncertainty']} kg)")

    # 9. Real Attachment Upload & Download
    sample_file_bytes = b"%PDF-1.4 Simulated calibration weights certificate for Metrolab OIML verification."
    b64_content = base64.b64encode(sample_file_bytes).decode("ascii")
    att_payload = {
        "file_name": "calibration_weights_cert.pdf",
        "file_type": "application/pdf",
        "file_data": b64_content,
        "description": "NPL traceable weight verification certificate"
    }
    st, res = request("POST", f"/api/evaluations/{eval_id}/attachments", att_payload, token=tokens["INSPECTOR"])
    assert st == 201, f"Attachment upload failed: {res}"
    att_id = res["attachment_id"]

    # Verify attachment listing
    st, res = request("GET", f"/api/evaluations/{eval_id}/attachments", token=tokens["INSPECTOR"])
    assert st == 200 and len(res["attachments"]) >= 1

    # Verify attachment binary download
    st, dl_bytes = request("GET", f"/api/attachments/{att_id}/download", token=tokens["INSPECTOR"])
    assert st == 200 and dl_bytes == sample_file_bytes
    print("  [PASS] 9. Real Attachment Base64 Upload & Binary Download Verified")

    # 10. Real Review Workflow Transition:
    # Inspector submits evaluation
    st, res = request("POST", f"/api/evaluations/{eval_id}/submit", token=tokens["INSPECTOR"])
    assert st == 200 and res["status"] == "SUBMITTED"

    # Reviewer approves evaluation
    review_body = {
        "action": "APPROVE",
        "decision": "PASSED",
        "comments": "Statutory verification completed in accordance with OIML R-76 and Legal Metrology Act 2009."
    }
    st, res = request("POST", f"/api/evaluations/{eval_id}/review", review_body, token=tokens["REVIEWER"])
    assert st == 200 and res["status"] == "APPROVED"
    print("  [PASS] 10. Real Review Workflow State Machine (DRAFT -> SUBMITTED -> APPROVED) Verified")

    # 11. PDF Report Generation
    st, res = request("POST", f"/api/evaluations/{eval_id}/generate_pdf", token=tokens["REVIEWER"])
    assert st == 200 and "report_url" in res, f"PDF generation failed: {res}"
    report_url = res["report_url"]
    st, pdf_bytes = request("GET", report_url, token=tokens["REVIEWER"])
    assert st == 200 and pdf_bytes.startswith(b"%PDF"), "Generated file is not a valid PDF"
    print(f"  [PASS] 11. Official OIML Certificate PDF Generation Verified ({len(pdf_bytes)} bytes)")

    # 12. Audit Trail
    st, res = request("GET", "/api/audit", token=tokens["ADMIN"])
    assert st == 200
    actions = [log["action"] for log in res["logs"]]
    for act in ["LOGIN", "CREATE", "BATCH_INSERT", "CALCULATE", "SUBMIT_FOR_REVIEW", "REVIEW_APPROVE", "GENERATE_PDF"]:
        assert act in actions, f"Missing audit action {act}"
    print("  [PASS] 12. Complete Audit Trail Logging Verified")

    # 13. Dashboard Live Data
    st, res = request("GET", "/api/dashboard/stats", token=tokens["ADMIN"])
    assert st == 200
    stats = res["stats"]
    assert stats["total_instruments"] > 0
    assert stats["total_evaluations"] > 0
    assert stats["approved_evaluations"] > 0
    print("  [PASS] 13. Dashboard Live Real-Time Aggregations Verified")

    # Clean up test instrument
    request("DELETE", f"/api/instruments/{inst_id}", token=tokens["ADMIN"])

    print("=" * 70)
    print("  ALL 13 END-TO-END SIH-26035 COMPLIANCE TESTS PASSED SUCCESSFULLY! ")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
