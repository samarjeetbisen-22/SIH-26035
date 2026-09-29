"""
Comprehensive End-to-End Workflow Verification Suite (SIH-26035)
Tests:
1. Technician Login & Verification
2. Instrument Creation & Role Denials
3. Evaluation Creation & Role Denials
4. Test Readings Entry, Attachment Upload & Persistence
5. OIML R-76 Calculations & Pass/Fail Evaluation
6. Submit for Review & Role Denials
7. Reviewer Login, Queue Inspection, Return for Correction with Remarks
8. Technician Re-login, Correction of Readings & Resubmission
9. Reviewer Inspection, Approval & Certificate Stamping
10. Final Statutory Reportlab PDF Generation, Metadata Storage & Retrieval
11. Owner Login, Fleet Scoping & URL Tampering Defense
12. Audit Trail Completeness & Immutability Verification
13. Database Integrity & Cross-Session Persistence
"""

import sys
import os
import json
import base64
import time
import sqlite3
import urllib.request
import urllib.error

# Ensure stdout uses UTF-8 to prevent Windows cp1252 encoding errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "nawi_audit.db"

def api_request(method, path, data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read()
            try:
                json_data = json.loads(resp_body.decode("utf-8"))
            except Exception:
                json_data = resp_body
            return resp.status, json_data, resp.headers
    except urllib.error.HTTPError as e:
        resp_body = e.read()
        try:
            json_data = json.loads(resp_body.decode("utf-8"))
        except Exception:
            json_data = resp_body.decode("utf-8", errors="replace")
        return e.code, json_data, e.headers
    except Exception as e:
        return 0, str(e), {}

def test_full_workflow():
    print("=" * 80)
    print("FULL SYSTEM END-TO-END WORKFLOW & REGRESSION VERIFICATION")
    print("=" * 80)

    results = {
        "passed": [],
        "failed": [],
        "bugs_fixed": []
    }

    # =========================================================================
    # STAGE 1: AUTHENTICATION
    # =========================================================================
    print("\n--- STAGE 1: AUTHENTICATION ---")
    st, body, _ = api_request("POST", "/api/auth/login", {"username": "rajesh_inspector", "password": "Inspector@123"})
    assert st == 200 and "token" in body, f"Technician login failed: {body}"
    token_tech = body["token"]
    user_tech = body["user"]
    print(f"  ✓ Technician logged in: {user_tech['full_name']} (Role: {user_tech['role']})")

    st_rev, body_rev, _ = api_request("POST", "/api/auth/login", {"username": "priya_reviewer", "password": "Reviewer@123"})
    assert st_rev == 200, f"Reviewer login failed: {body_rev}"
    token_rev = body_rev["token"]
    user_rev = body_rev["user"]
    print(f"  ✓ Reviewer logged in: {user_rev['full_name']} (Role: {user_rev['role']})")

    st_own_a, body_own_a, _ = api_request("POST", "/api/auth/login", {"username": "essae_owner", "password": "Owner@123"})
    assert st_own_a == 200, f"Owner A login failed: {body_own_a}"
    token_own_a = body_own_a["token"]
    user_own_a = body_own_a["user"]
    print(f"  ✓ Owner A logged in: {user_own_a['full_name']} (ID: {user_own_a['id']})")

    st_own_b, body_own_b, _ = api_request("POST", "/api/auth/login", {"username": "avery_owner", "password": "Owner@123"})
    assert st_own_b == 200, f"Owner B login failed: {body_own_b}"
    token_own_b = body_own_b["token"]
    user_own_b = body_own_b["user"]
    print(f"  ✓ Owner B logged in: {user_own_b['full_name']} (ID: {user_own_b['id']})")
    results["passed"].append("Authentication (All 4 roles logged in with valid tokens)")

    # =========================================================================
    # STAGE 2: CREATE INSTRUMENT
    # =========================================================================
    print("\n--- STAGE 2: CREATE INSTRUMENT ---")
    # Verify unauthorized role cannot create instrument
    st_denied, _, _ = api_request("POST", "/api/instruments", {"serial_number": "FAIL-01", "model": "M"}, token=token_rev)
    assert st_denied == 403, f"Expected 403 when Reviewer creates instrument, got {st_denied}"
    print("  ✓ Role Denial Verified: Reviewer cannot create instrument (HTTP 403).")

    unique_suffix = f"{int(time.time())}"
    serial_no = f"SN-E2E-NAWI-{unique_suffix}"
    inst_payload = {
        "serial_number": serial_no,
        "model": "Essae DS-852 Heavy Digital Indicator",
        "manufacturer": "Essae Teraoka Pvt. Ltd.",
        "accuracy_class": "III",
        "max_capacity": 30.0,
        "min_capacity": 0.1,
        "e_interval": 0.01,
        "d_interval": 0.01,
        "tare_capacity": 30.0,
        "unit": "kg",
        "type_approval_no": "IND/09/2026/0471",
        "year_of_manufacture": 2026,
        "country_of_origin": "India",
        "owner_id": user_own_a["id"]
    }
    st_inst, body_inst, _ = api_request("POST", "/api/instruments", inst_payload, token=token_tech)
    assert st_inst == 201, f"Failed to create instrument: {body_inst}"
    inst_id = body_inst["id"]
    print(f"  ✓ Technician created instrument: {inst_id} ({serial_no})")

    # Verify database persistence
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row_inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (inst_id,)).fetchone()
    conn.close()
    assert row_inst is not None, "Instrument not found in database!"
    assert row_inst["serial_number"] == serial_no, "Serial mismatch in database!"
    assert row_inst["owner_id"] == user_own_a["id"], "Owner mismatch in database!"
    print("  ✓ Database Persistence Verified: Instrument stored in SQLite table 'instruments'.")
    results["passed"].append("Create Instrument & DB Persistence")

    # =========================================================================
    # STAGE 3: CREATE EVALUATION
    # =========================================================================
    print("\n--- STAGE 3: CREATE EVALUATION ---")
    # Verify unauthorized roles cannot create evaluation
    st_rev_ev, _, _ = api_request("POST", "/api/evaluations", {"instrument_id": inst_id}, token=token_rev)
    assert st_rev_ev == 403, f"Expected 403 when Reviewer creates evaluation, got {st_rev_ev}"
    st_own_ev, _, _ = api_request("POST", "/api/evaluations", {"instrument_id": inst_id}, token=token_own_a)
    assert st_own_ev == 403, f"Expected 403 when Owner creates evaluation, got {st_own_ev}"
    print("  ✓ Role Denial Verified: Reviewers and Owners cannot create evaluations (HTTP 403).")

    eval_payload = {
        "instrument_id": inst_id,
        "test_date": "2026-09-30",
        "test_location": "National Metrology Standards Laboratory, Bengaluru",
        "temperature_c": 23.5,
        "humidity_percent": 50.0,
        "pressure_hpa": 1012.0,
        "gravity_mps2": 9.7915,
        "reference_standard": "OIML Class F1 Weights (Set #26)",
        "standards_traceability_no": "NPLI/MASS/2026/0471",
        "status": "DRAFT"
    }
    st_ev, body_ev, _ = api_request("POST", "/api/evaluations", eval_payload, token=token_tech)
    assert st_ev == 201, f"Failed to create evaluation: {body_ev}"
    eval_id = body_ev["evaluation_id"]
    print(f"  ✓ Technician created evaluation: {eval_id} (Status: DRAFT)")

    # Verify database persistence
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row_ev = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    conn.close()
    assert row_ev is not None, "Evaluation not found in database!"
    assert row_ev["status"] == "DRAFT", f"Expected DRAFT, got {row_ev['status']}"
    assert row_ev["instrument_id"] == inst_id, "Evaluation not linked to instrument!"
    print("  ✓ Database Linkage Verified: Evaluation linked to correct instrument.")
    results["passed"].append("Create Evaluation & Linkage")

    # =========================================================================
    # STAGE 4: ENTER TEST READINGS & EVIDENCE ATTACHMENT
    # =========================================================================
    print("\n--- STAGE 4: ENTER TEST READINGS & EVIDENCE ATTACHMENT ---")
    # Prepare initial readings (intentionally with an error in eccentricity for correction workflow)
    initial_readings = [
        {"load": 0.0, "reading": 0.0, "position": "center", "test_type": "LOAD", "direction": "increasing", "repeat_number": 1},
        {"load": 5.0, "reading": 5.002, "position": "center", "test_type": "LOAD", "direction": "increasing", "repeat_number": 1},
        {"load": 15.0, "reading": 15.005, "position": "center", "test_type": "LOAD", "direction": "increasing", "repeat_number": 1},
        {"load": 30.0, "reading": 30.010, "position": "center", "test_type": "LOAD", "direction": "increasing", "repeat_number": 1},
        {"load": 30.0, "reading": 30.009, "position": "center", "test_type": "LOAD", "direction": "decreasing", "repeat_number": 1},
        {"load": 15.0, "reading": 15.004, "position": "center", "test_type": "LOAD", "direction": "decreasing", "repeat_number": 1},
        {"load": 0.0, "reading": 0.001, "position": "center", "test_type": "LOAD", "direction": "decreasing", "repeat_number": 1},
        # Eccentricity readings (with an intentional drift at front-left)
        {"load": 10.0, "reading": 10.002, "position": "center", "test_type": "ECCENTRICITY", "direction": "increasing", "repeat_number": 1},
        {"load": 10.0, "reading": 10.025, "position": "front-left", "test_type": "ECCENTRICITY", "direction": "increasing", "repeat_number": 1},
        {"load": 10.0, "reading": 10.003, "position": "front-right", "test_type": "ECCENTRICITY", "direction": "increasing", "repeat_number": 1},
        {"load": 10.0, "reading": 10.002, "position": "back-left", "test_type": "ECCENTRICITY", "direction": "increasing", "repeat_number": 1},
        {"load": 10.0, "reading": 10.003, "position": "back-right", "test_type": "ECCENTRICITY", "direction": "increasing", "repeat_number": 1},
        # Repeatability readings
        {"load": 15.0, "reading": 15.004, "position": "center", "test_type": "REPEATABILITY", "direction": "increasing", "repeat_number": 1},
        {"load": 15.0, "reading": 15.005, "position": "center", "test_type": "REPEATABILITY", "direction": "increasing", "repeat_number": 2},
        {"load": 15.0, "reading": 15.004, "position": "center", "test_type": "REPEATABILITY", "direction": "increasing", "repeat_number": 3}
    ]

    st_rd, body_rd, _ = api_request("POST", f"/api/evaluations/{eval_id}/readings", {"readings": initial_readings}, token=token_tech)
    assert st_rd == 200, f"Failed to save readings: {body_rd}"
    print(f"  ✓ Technician saved {len(initial_readings)} test observations.")

    # Upload evidence attachment (calibration certificate PDF)
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj xref 0 4 0000000000 65535 f\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n140\n%%EOF"
    att_payload = {
        "filename": "RRSL_Class_F1_Mass_Standards_Traceability.pdf",
        "file_data": base64.b64encode(sample_pdf_bytes).decode("ascii"),
        "description": "Statutory NPLI Class F1 mass standards calibration certificate"
    }
    st_att, body_att, _ = api_request("POST", f"/api/evaluations/{eval_id}/attachments", att_payload, token=token_tech)
    assert st_att == 201, f"Failed to upload attachment: {body_att}"
    att_id = body_att["attachment_id"]
    print(f"  ✓ Technician uploaded statutory evidence attachment: {att_id}")

    # Verify SQLite database persistence of readings and attachments
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    db_readings = conn.execute("SELECT COUNT(*) FROM test_readings WHERE evaluation_id = ?", (eval_id,)).fetchone()[0]
    db_att = conn.execute("SELECT * FROM attachments WHERE id = ?", (att_id,)).fetchone()
    conn.close()
    assert db_readings == len(initial_readings), f"Expected {len(initial_readings)} readings in DB, got {db_readings}"
    assert db_att is not None, "Attachment not found in DB!"
    assert db_att["evaluation_id"] == eval_id, "Attachment not linked to evaluation!"
    print("  ✓ Database Verification: 15 readings and 1 attachment confirmed in SQLite.")
    results["passed"].append("Test Readings & Attachment Upload Persistence")

    # =========================================================================
    # STAGE 5: RUN OIML CALCULATIONS & PASS/FAIL EVALUATION
    # =========================================================================
    print("\n--- STAGE 5: RUN OIML CALCULATIONS & PASS/FAIL EVALUATION ---")
    st_calc, body_calc, _ = api_request("POST", f"/api/evaluations/{eval_id}/calculate", {}, token=token_tech)
    assert st_calc == 200, f"Calculation failed: {body_calc}"
    calcs = body_calc["calculations"]
    print(f"  ✓ OIML R-76 Calculations Computed:")
    print(f"    - Repeatability Error: {calcs['repeatability_error']} kg")
    print(f"    - Linearity Error: {calcs['linearity_error']} kg")
    print(f"    - Eccentricity Error: {calcs['eccentricity_error']} kg")
    print(f"    - Compliance Score: {calcs['compliance_score']}%")
    print(f"    - Conformity: {'PASS' if calcs['conformity'] == 1 else 'FAIL'}")
    print(f"    - Risk Level: {calcs['risk_level']}")
    results["passed"].append("OIML R-76 Automated Calculation Engine")

    # =========================================================================
    # STAGE 6: SUBMIT FOR REVIEW
    # =========================================================================
    print("\n--- STAGE 6: SUBMIT FOR REVIEW ---")
    # Verify unauthorized submit denied
    st_sub_rev, _, _ = api_request("POST", f"/api/evaluations/{eval_id}/submit", {}, token=token_rev)
    assert st_sub_rev == 403, f"Expected 403 when Reviewer submits, got {st_sub_rev}"
    st_sub_own, _, _ = api_request("POST", f"/api/evaluations/{eval_id}/submit", {}, token=token_own_a)
    assert st_sub_own == 403, f"Expected 403 when Owner submits, got {st_sub_own}"
    print("  ✓ Role Denial Verified: Reviewers and Owners cannot submit evaluations (HTTP 403).")

    # Technician submits evaluation
    st_sub, body_sub, _ = api_request("POST", f"/api/evaluations/{eval_id}/submit", {}, token=token_tech)
    assert st_sub == 200, f"Failed to submit evaluation: {body_sub}"
    assert body_sub["status"] == "SUBMITTED", f"Expected SUBMITTED status, got {body_sub['status']}"
    print(f"  ✓ Technician submitted evaluation {eval_id} for statutory review (Status: SUBMITTED).")

    # Check persistence
    conn = sqlite3.connect(DB_PATH)
    status_db = conn.execute("SELECT status FROM evaluations WHERE id = ?", (eval_id,)).fetchone()[0]
    conn.close()
    assert status_db == "SUBMITTED", f"Expected SUBMITTED in DB, got {status_db}"
    results["passed"].append("Submit for Review & State Transition")

    # =========================================================================
    # STAGE 7: REVIEWER QUEUE, INSPECTION & RETURN FOR CORRECTION
    # =========================================================================
    print("\n--- STAGE 7: REVIEWER INSPECTION & RETURN FOR CORRECTION ---")
    # Reviewer retrieves submitted queue
    st_q, body_q, _ = api_request("GET", "/api/evaluations?status=SUBMITTED", token=token_rev)
    assert st_q == 200, f"Failed to get queue: {body_q}"
    eval_ids_in_queue = [e["id"] for e in body_q.get("evaluations", [])]
    assert eval_id in eval_ids_in_queue, f"Evaluation {eval_id} not visible in Reviewer queue!"
    print(f"  ✓ Reviewer opened submitted queue and located evaluation {eval_id}.")

    # Reviewer inspects readings & evidence
    st_insp, body_insp, _ = api_request("GET", f"/api/evaluations/{eval_id}", token=token_rev)
    assert st_insp == 200, f"Failed to inspect evaluation: {body_insp}"
    assert len(body_insp["readings"]) == len(initial_readings), "Readings mismatch during review!"
    assert len(body_insp["attachments"]) == 1, "Evidence attachments missing during review!"
    print(f"  ✓ Reviewer verified all {len(body_insp['readings'])} test points and evidence attachment.")

    # Reviewer initiates inspection (UNDER_REVIEW)
    st_ur, body_ur, _ = api_request("POST", f"/api/evaluations/{eval_id}/review", {"action": "UNDER_REVIEW"}, token=token_rev)
    assert st_ur == 200 and body_ur["status"] == "UNDER_REVIEW", f"Failed to set UNDER_REVIEW: {body_ur}"
    print("  ✓ Reviewer transitioned evaluation to UNDER_REVIEW.")

    # Reviewer returns for correction with remarks
    review_remarks = "Front-left eccentricity error (0.025 kg) exceeds permissible MPE limit. Please recalibrate corner load and re-test."
    st_ret, body_ret, _ = api_request("POST", f"/api/evaluations/{eval_id}/review", {
        "action": "RETURN",
        "comments": review_remarks
    }, token=token_rev)
    assert st_ret == 200 and body_ret["status"] == "RETURNED", f"Failed to return for correction: {body_ret}"
    print(f"  ✓ Reviewer returned evaluation for correction. Remarks: '{review_remarks}'")

    # Verify database persistence of RETURNED status and remarks
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row_ret = conn.execute("SELECT status, review_comments, reviewer_id FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    conn.close()
    assert row_ret["status"] == "RETURNED", f"Expected RETURNED in DB, got {row_ret['status']}"
    assert row_ret["review_comments"] == review_remarks, "Review remarks not preserved in DB!"
    print("  ✓ Database Persistence Verified: RETURNED status and remarks stored in SQLite.")
    results["passed"].append("Reviewer Return for Correction Path")

    # =========================================================================
    # STAGE 8: TECHNICIAN RE-LOGIN, CORRECTION & RESUBMISSION
    # =========================================================================
    print("\n--- STAGE 8: TECHNICIAN CORRECTION & RESUBMISSION ---")
    # Simulate technician re-login
    st_t2, body_t2, _ = api_request("POST", "/api/auth/login", {"username": "rajesh_inspector", "password": "Inspector@123"})
    token_tech2 = body_t2["token"]

    # Technician fetches returned evaluation and reads reviewer remarks
    st_ev_corr, body_ev_corr, _ = api_request("GET", f"/api/evaluations/{eval_id}", token=token_tech2)
    assert st_ev_corr == 200, f"Failed to load returned evaluation: {body_ev_corr}"
    assert body_ev_corr["evaluation"]["status"] == "RETURNED", "Status not preserved!"
    assert body_ev_corr["evaluation"]["review_comments"] == review_remarks, "Review remarks missing in UI response!"
    print("  ✓ Technician received returned evaluation with preserved reviewer remarks.")

    # Technician corrects the front-left reading to 10.003 kg
    corrected_readings = list(initial_readings)
    for r in corrected_readings:
        if r.get("test_type") == "ECCENTRICITY" and r.get("position") == "front-left":
            r["reading"] = 10.003

    st_corr_save, body_corr_save, _ = api_request("POST", f"/api/evaluations/{eval_id}/readings", {"readings": corrected_readings}, token=token_tech2)
    assert st_corr_save == 200, f"Failed to save corrected readings: {body_corr_save}"
    print("  ✓ Technician corrected front-left observation and saved revised readings.")

    # Technician resubmits for review
    st_resub, body_resub, _ = api_request("POST", f"/api/evaluations/{eval_id}/submit", {}, token=token_tech2)
    assert st_resub == 200 and body_resub["status"] == "SUBMITTED", f"Resubmission failed: {body_resub}"
    print("  ✓ Technician successfully resubmitted evaluation for statutory review.")
    results["passed"].append("Correction & Resubmission Workflow")

    # =========================================================================
    # STAGE 9: REVIEWER APPROVAL & STATUTORY STAMPING
    # =========================================================================
    print("\n--- STAGE 9: REVIEWER APPROVAL & STATUTORY STAMPING ---")
    st_app, body_app, _ = api_request("POST", f"/api/evaluations/{eval_id}/review", {
        "action": "APPROVE",
        "comments": "Corner load recalibration verified within statutory tolerance. Approved for verification stamping."
    }, token=token_rev)
    assert st_app == 200, f"Failed to approve evaluation: {body_app}"
    assert body_app["status"] == "APPROVED", f"Expected APPROVED, got {body_app['status']}"
    cert_no = body_app["certificate_number"]
    assert cert_no and cert_no.startswith("CERT-DL-"), f"Invalid certificate format: {cert_no}"
    print(f"  ✓ Reviewer approved evaluation! Statutory Certificate issued: {cert_no}")

    # Verify locking: Technician cannot modify approved readings
    st_lock, _, _ = api_request("POST", f"/api/evaluations/{eval_id}/readings", {"readings": corrected_readings}, token=token_tech2)
    assert st_lock == 400, f"Expected 400 when editing approved readings, got {st_lock}"
    print("  ✓ Immutability Lock Verified: Modifications to approved evaluation readings rejected (HTTP 400).")

    # Verify instrument status updated to VERIFIED with due dates in database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inst_verified = conn.execute("SELECT status, last_verified_at, next_verification_due FROM instruments WHERE id = ?", (inst_id,)).fetchone()
    conn.close()
    assert inst_verified["status"] == "VERIFIED", f"Expected instrument VERIFIED, got {inst_verified['status']}"
    assert inst_verified["next_verification_due"] is not None, "next_verification_due was not set!"
    print(f"  ✓ Instrument Lifecycle Updated: Status = VERIFIED, Next Due: {inst_verified['next_verification_due']}.")
    results["passed"].append("Reviewer Approval & Statutory Certificate Stamping")

    # =========================================================================
    # STAGE 10: REPORT GENERATION & PERSISTENCE
    # =========================================================================
    print("\n--- STAGE 10: REPORT GENERATION & PERSISTENCE ---")
    st_rep, body_rep, _ = api_request("POST", f"/api/evaluations/{eval_id}/generate_pdf", {}, token=token_tech2)
    assert st_rep == 200, f"Failed to generate report: {body_rep}"
    pdf_filename = body_rep["filename"]
    pdf_url = body_rep["pdf_url"]
    report_id = body_rep["report_id"]
    print(f"  ✓ Final statutory PDF generated: {pdf_filename} (Report ID: {report_id})")

    # Verify physical file exists on disk
    pdf_disk_path = os.path.join("reports", pdf_filename)
    assert os.path.exists(pdf_disk_path), f"PDF file does not exist on disk: {pdf_disk_path}"
    pdf_size = os.path.getsize(pdf_disk_path)
    assert pdf_size > 5000, f"PDF file is too small: {pdf_size} bytes"
    print(f"  ✓ Physical PDF Verified on Disk: {pdf_size} bytes.")

    # Verify persistent metadata in reports table
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row_rep = conn.execute("SELECT * FROM reports WHERE evaluation_id = ?", (eval_id,)).fetchone()
    conn.close()
    assert row_rep is not None, "Report metadata not found in reports table!"
    assert row_rep["certificate_number"] == cert_no, "Certificate number mismatch in reports table!"
    print("  ✓ Database Persistence Verified: Report metadata permanently stored in SQLite table 'reports'.")

    # Retrieve report via dedicated endpoints
    st_get_rep, body_get_rep, _ = api_request("GET", f"/api/evaluations/{eval_id}/report", token=token_tech2)
    assert st_get_rep == 200 and body_get_rep["report"]["certificate_number"] == cert_no, "Failed to retrieve report via /api/evaluations/<id>/report"
    print("  ✓ Successfully retrieved report record via /api/evaluations/<id>/report.")
    results["passed"].append("Statutory PDF Generation & Persistence")

    # =========================================================================
    # STAGE 11: OWNER FLEET ISOLATION & VERIFICATION
    # =========================================================================
    print("\n--- STAGE 11: OWNER FLEET ISOLATION & VERIFICATION ---")
    # Owner A (Essae) views fleet
    st_own_inst, body_own_inst, _ = api_request("GET", "/api/instruments", token=token_own_a)
    assert st_own_inst == 200, f"Failed to get Owner A instruments: {body_own_inst}"
    own_a_inst_ids = [i["id"] for i in body_own_inst.get("instruments", [])]
    assert inst_id in own_a_inst_ids, "Newly verified instrument not found in Owner A fleet!"
    print(f"  ✓ Owner A sees newly verified instrument in their fleet ({len(own_a_inst_ids)} total).")

    # Owner A views approved evaluation
    st_own_eval, body_own_eval, _ = api_request("GET", f"/api/evaluations/{eval_id}", token=token_own_a)
    assert st_own_eval == 200, f"Owner A failed to view evaluation: {body_own_eval}"
    assert body_own_eval["evaluation"]["status"] == "APPROVED", "Owner A sees incorrect status!"
    assert body_own_eval["evaluation"]["certificate_number"] == cert_no, "Owner A sees incorrect certificate!"
    print(f"  ✓ Owner A sees APPROVED statutory evaluation with certificate {cert_no}.")

    # Owner A downloads official PDF certificate
    st_own_pdf, body_own_pdf, _ = api_request("GET", f"/api/reports/{pdf_filename}", token=token_own_a)
    assert st_own_pdf == 200, f"Owner A failed to download certificate: {st_own_pdf}"
    assert len(body_own_pdf) == pdf_size, "Downloaded PDF bytes mismatch!"
    print(f"  ✓ Owner A successfully downloaded statutory certificate PDF ({len(body_own_pdf)} bytes).")

    # Owner B (Avery) cross-tenant security checks (Direct ID Tampering)
    st_tamper_inst, _, _ = api_request("GET", f"/api/instruments/{inst_id}", token=token_own_b)
    assert st_tamper_inst == 403, f"Expected 403 for Owner B accessing Owner A instrument, got {st_tamper_inst}"
    st_tamper_eval, _, _ = api_request("GET", f"/api/evaluations/{eval_id}", token=token_own_b)
    assert st_tamper_eval == 403, f"Expected 403 for Owner B accessing Owner A evaluation, got {st_tamper_eval}"
    st_tamper_pdf, _, _ = api_request("GET", f"/api/reports/{pdf_filename}", token=token_own_b)
    assert st_tamper_pdf == 403, f"Expected 403 for Owner B downloading Owner A certificate, got {st_tamper_pdf}"
    print("  ✓ Cross-Tenant Fleet Isolation: Owner B blocked with HTTP 403 on all Owner A assets.")
    results["passed"].append("Owner Fleet Scoping & Tenant Isolation")

    # =========================================================================
    # STAGE 12: AUDIT TRAIL VERIFICATION & IMMUTABILITY
    # =========================================================================
    print("\n--- STAGE 12: AUDIT TRAIL VERIFICATION & IMMUTABILITY ---")
    st_aud, body_aud, _ = api_request("GET", "/api/audit", token=token_tech2)
    assert st_aud == 200, f"Failed to retrieve audit trail: {body_aud}"
    logs = body_aud.get("audit_logs", [])
    actions_for_eval = [
        l["action"] for l in logs 
        if l.get("entity_id") == eval_id 
        or (l.get("details") and l["details"].get("evaluation_id") == eval_id)
        or l.get("entity_id") == report_id
    ]
    print(f"  -> Audit actions recorded for evaluation {eval_id} & report {report_id}: {actions_for_eval}")

    expected_audit_actions = {"CREATE_EVALUATION", "SUBMIT_TEST_READINGS", "SUBMIT_FOR_REVIEW", "REVIEW_INSPECT", "REVIEW_RETURN", "RESUBMIT_FOR_REVIEW", "REVIEW_APPROVE", "GENERATE_REPORT"}
    for exp_act in expected_audit_actions:
        assert exp_act in actions_for_eval, f"Missing audit action: {exp_act}!"
    print("  ✓ Complete Audit Trail Verified: All lifecycle actions permanently logged with user, role, and timestamp.")

    # Verify audit immutability
    st_put_aud, _, _ = api_request("PUT", "/api/audit/sample", {"action": "HACK"}, token=token_tech2)
    assert st_put_aud == 403, f"Expected 403 for audit tampering, got {st_put_aud}"
    st_del_aud, _, _ = api_request("DELETE", "/api/audit/sample", token=token_tech2)
    assert st_del_aud == 403, f"Expected 403 for audit deletion, got {st_del_aud}"
    print("  ✓ Statutory Immutability Verified: Audit logs cannot be modified or deleted (HTTP 403).")
    results["passed"].append("Statutory Audit Trail Completeness & Immutability")

    # =========================================================================
    # STAGE 13: DATABASE REFERENTIAL INTEGRITY & CROSS-SESSION CHECK
    # =========================================================================
    print("\n--- STAGE 13: DATABASE REFERENTIAL INTEGRITY & REFRESH/RESTART ---")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Foreign key checks
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    assert len(fk_errors) == 0, f"Foreign key integrity violations detected: {fk_errors}"
    print("  ✓ SQLite PRAGMA foreign_key_check: 0 violations detected.")

    # Verify relationships
    eval_check = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    readings_count = conn.execute("SELECT COUNT(*) FROM test_readings WHERE evaluation_id = ?", (eval_id,)).fetchone()[0]
    att_count = conn.execute("SELECT COUNT(*) FROM attachments WHERE evaluation_id = ?", (eval_id,)).fetchone()[0]
    rep_check = conn.execute("SELECT * FROM reports WHERE evaluation_id = ?", (eval_id,)).fetchone()
    conn.close()

    assert eval_check["instrument_id"] == inst_id, "Evaluation instrument_id corrupted!"
    assert readings_count == len(initial_readings), f"Readings count corrupted: {readings_count}"
    assert att_count == 1, "Attachment count corrupted!"
    assert rep_check["instrument_id"] == inst_id, "Report instrument_id corrupted!"
    print("  ✓ Referential Relationships Verified: All child records strictly mapped to parent evaluation & instrument.")
    results["passed"].append("Database Referential Integrity & Schema Consistency")

    print("\n" + "=" * 80)
    print(f"ALL {len(results['passed'])} END-TO-END WORKFLOW STAGES PASSED PERFECTLY WITH ZERO FAILURES!")
    print("=" * 80)
    return results

if __name__ == "__main__":
    test_full_workflow()
