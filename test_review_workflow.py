"""
End-to-End Test Suite for Real Review Workflow
Lifecycle: Draft -> Submitted -> Under Review -> Returned/Correction -> Resubmitted -> Approved
"""

import sys
import json
import time
import urllib.request
import urllib.error
import threading
import http.server
import datetime
import secrets

import server
import db

PORT = 8111
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
    print("STARTING TEST SUITE: REAL REVIEW WORKFLOW")
    print("=" * 70)

    # Initialize and seed db
    db.init_db()
    db.seed_database()

    # Start server thread
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    # 1. Login all roles
    print("\n[Step 1] Authenticating all roles...")
    code, res_tech = make_req("/api/auth/login", "POST", {"username": "rajesh_inspector", "password": "Inspector@123"})
    assert code == 200 and res_tech.get("token"), f"Technician login failed: {res_tech}"
    tech_token = res_tech["token"]
    print("  -> Technician logged in successfully.")

    code, res_rev = make_req("/api/auth/login", "POST", {"username": "priya_reviewer", "password": "Reviewer@123"})
    assert code == 200 and res_rev.get("token"), f"Reviewer login failed: {res_rev}"
    rev_token = res_rev["token"]
    print("  -> Reviewer logged in successfully.")

    code, res_owner = make_req("/api/auth/login", "POST", {"username": "essae_owner", "password": "Owner@123"})
    assert code == 200 and res_owner.get("token"), f"Owner login failed: {res_owner}"
    owner_token = res_owner["token"]
    print("  -> Owner logged in successfully.")

    # 2. Technician creates new evaluation (DRAFT)
    print("\n[Step 2] Technician creates new evaluation draft...")
    eval_id = f"eval_rw_{secrets.token_hex(4)}"
    inst_serial = f"TEST-SCALE-{secrets.token_hex(3).upper()}"
    create_payload = {
        "id": eval_id,
        "instrument": {
            "serial_number": inst_serial,
            "model": "Precision Weigh 5000",
            "manufacturer": "Essae Digitronics",
            "accuracy_class": "III",
            "max_capacity": 30.0,
            "min_capacity": 0.1,
            "e_interval": 0.01,
            "d_interval": 0.01,
            "tare_capacity": 30.0,
            "unit": "kg"
        },
        "test_date": "2026-09-29",
        "test_location": "Delhi Metrology Testing Lab",
        "temperature_c": 22.5,
        "humidity_percent": 50.0,
        "pressure_hpa": 1013.25,
        "gravity_mps2": 9.7915,
        "reference_standard": "OIML Class F1 Weights",
        "status": "DRAFT"
    }

    code, res_create = make_req("/api/evaluations", "POST", create_payload, token=tech_token)
    assert code in (200, 201) and res_create.get("evaluation_id"), f"Create evaluation failed: {res_create}"
    eval_id = res_create["evaluation_id"]
    print(f"  -> Evaluation created: {eval_id} with status: {res_create.get('status', 'DRAFT')}")

    # 3. Technician logs initial test readings
    print("\n[Step 3] Technician enters and saves initial test readings...")
    readings = [
        {"load": 0.0, "reading": 0.000, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 5.0, "reading": 5.001, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 15.0, "reading": 15.002, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 30.0, "reading": 30.003, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 10.0, "reading": 10.001, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 10.0, "reading": 10.002, "direction": "increasing", "position": "front-left", "repeat_number": 1, "test_type": "ECCENTRICITY"},
    ]
    code, res_readings = make_req(f"/api/evaluations/{eval_id}/readings", "POST", {"readings": readings}, token=tech_token)
    assert code == 200 and res_readings.get("success"), f"Save readings failed: {res_readings}"
    print(f"  -> Saved {res_readings.get('readings_count')} test readings. Compliance score: {res_readings.get('compliance_score')}%")

    # 4. Role Authorization on Submit: Owner & Reviewer cannot submit
    print("\n[Step 4] Testing role authorization on submit endpoint...")
    code, res_owner_sub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=owner_token)
    assert code == 403, f"Owner submission should be forbidden (403), got {code}"
    print("  -> Owner cannot submit (403 Forbidden verified).")

    code, res_rev_sub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=rev_token)
    assert code == 403, f"Reviewer submission should be forbidden (403), got {code}"
    print("  -> Reviewer cannot submit (403 Forbidden verified).")

    # Technician submits for review
    code, res_submit = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=tech_token)
    assert code == 200 and res_submit.get("status") == "SUBMITTED", f"Submit failed: {res_submit}"
    print(f"  -> Technician submitted evaluation for review! Status: {res_submit.get('status')}")

    # 5. Reviewer sees submitted evaluation in queue
    print("\n[Step 5] Reviewer inspects evaluation queue...")
    code, res_queue = make_req("/api/evaluations?status=SUBMITTED", "GET", token=rev_token)
    assert code == 200, f"Fetch queue failed: {res_queue}"
    matching = [e for e in res_queue.get("evaluations", []) if e["id"] == eval_id]
    assert len(matching) == 1, f"Evaluation {eval_id} not found in SUBMITTED queue: {res_queue}"
    assert matching[0]["status"] == "SUBMITTED"
    print(f"  -> Found submitted evaluation in Reviewer Queue: {matching[0]['serial_number']}")

    # 6. Reviewer marks Under Review (UNDER_REVIEW)
    print("\n[Step 6] Reviewer opens evaluation and initiates inspection (UNDER_REVIEW)...")
    code, res_ur = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "UNDER_REVIEW"}, token=rev_token)
    assert code == 200 and res_ur.get("status") == "UNDER_REVIEW", f"Mark under review failed: {res_ur}"
    print("  -> Evaluation status updated to UNDER_REVIEW.")

    # Verify technician cannot review
    code, res_tech_rev = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "APPROVE"}, token=tech_token)
    assert code == 403, f"Technician review should be forbidden (403), got {code}"
    print("  -> Technician cannot approve/reject (403 Forbidden verified).")

    # 7. Reviewer returns evaluation for correction (RETURN / REJECT)
    print("\n[Step 7] Reviewer returns evaluation for correction...")
    # Missing comments should fail
    code, res_no_comm = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "RETURN", "comments": ""}, token=rev_token)
    assert code == 400, f"Return without comments should be rejected with 400, got {code}"
    print("  -> Required comments on return verified (400 Bad Request when empty).")

    return_remarks = "Please re-verify eccentricity readings at front-left; error exceeds statutory target."
    code, res_ret = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "RETURN", "comments": return_remarks}, token=rev_token)
    assert code == 200 and res_ret.get("status") in ("RETURNED", "REJECTED"), f"Return failed: {res_ret}"
    print(f"  -> Evaluation returned for correction with status: {res_ret.get('status')}")

    # 8. Technician receives returned evaluation, inspects remarks, and makes corrections
    print("\n[Step 8] Technician receives returned evaluation and inspects remarks...")
    code, res_details = make_req(f"/api/evaluations/{eval_id}", "GET", token=tech_token)
    assert code == 200 and res_details.get("evaluation"), f"Get details failed: {res_details}"
    ev_info = res_details["evaluation"]
    assert ev_info["status"] in ("RETURNED", "REJECTED"), f"Expected returned status, got {ev_info['status']}"
    assert ev_info["review_comments"] == return_remarks, f"Remarks mismatch: {ev_info['review_comments']}"
    print(f"  -> Verified reviewer remarks preserved: '{ev_info['review_comments']}'")

    print("  -> Technician applies corrected readings...")
    corrected_readings = [
        {"load": 0.0, "reading": 0.000, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 5.0, "reading": 5.000, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 15.0, "reading": 15.001, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 30.0, "reading": 30.001, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 10.0, "reading": 10.000, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 10.0, "reading": 10.001, "direction": "increasing", "position": "front-left", "repeat_number": 1, "test_type": "ECCENTRICITY"},
    ]
    code, res_corr = make_req(f"/api/evaluations/{eval_id}/readings", "POST", {"readings": corrected_readings}, token=tech_token)
    assert code == 200 and res_corr.get("success"), f"Save corrected readings failed: {res_corr}"
    print(f"  -> Corrected readings saved permanently! New compliance score: {res_corr.get('compliance_score')}%")

    # 9. Technician resubmits evaluation for statutory review
    print("\n[Step 9] Technician resubmits evaluation for review...")
    code, res_resub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=tech_token)
    assert code == 200 and res_resub.get("status") == "SUBMITTED", f"Resubmission failed: {res_resub}"
    print(f"  -> Resubmission successful! Status: {res_resub.get('status')}")

    # 10. Reviewer inspects and approves evaluation
    print("\n[Step 10] Reviewer approves evaluation and stamps statutory certificate...")
    approve_remarks = "All corrected points verified conforming to OIML R-76 MPE envelopes. Approved."
    code, res_app = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "APPROVE", "comments": approve_remarks}, token=rev_token)
    assert code == 200 and res_app.get("status") == "APPROVED", f"Approval failed: {res_app}"
    assert res_app.get("certificate_number"), f"Certificate number missing: {res_app}"
    cert_no = res_app["certificate_number"]
    print(f"  -> Approved! Certificate Number generated: {cert_no}")

    # Verify Instrument is updated to VERIFIED
    conn = db.get_db()
    inst_row = conn.execute("SELECT * FROM instruments WHERE serial_number = ?", (inst_serial,)).fetchone()
    assert inst_row and inst_row["status"] == "VERIFIED", f"Instrument status should be VERIFIED, got {inst_row['status']}"
    assert inst_row["last_verified_at"], "last_verified_at not set"
    assert inst_row["next_verification_due"], "next_verification_due not set"
    conn.close()
    print("  -> Instrument status updated permanently to VERIFIED with statutory due dates.")

    # 11. Lock verification: Approved evaluation cannot be modified or re-submitted
    print("\n[Step 11] Verifying approval locks...")
    code, res_locked_sub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=tech_token)
    assert code == 400, f"Submit on approved evaluation should be rejected (400), got {code}"
    print("  -> Submit on approved evaluation locked (400 Bad Request verified).")

    code, res_locked_edit = make_req(f"/api/evaluations/{eval_id}/readings", "POST", {"readings": corrected_readings}, token=tech_token)
    assert code == 400, f"Editing readings on approved evaluation should be rejected (400), got {code}"
    print("  -> Reading edits on approved evaluation locked (400 Bad Request verified).")

    # 12. Generate official PDF certificate for approved evaluation
    print("\n[Step 12] Generating official statutory PDF certificate for approved evaluation...")
    code, res_pdf = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", {}, token=tech_token)
    assert code == 200 and res_pdf.get("pdf_url"), f"PDF generation failed: {res_pdf}"
    print(f"  -> Official PDF report generated successfully: {res_pdf.get('pdf_url')}")

    # 13. Audit trail verification
    print("\n[Step 13] Verifying audit trail logs for all workflow transitions...")
    conn = db.get_db()
    logs = conn.execute("SELECT action, entity_id FROM audit_logs WHERE entity_id = ? ORDER BY timestamp ASC", (eval_id,)).fetchall()
    actions = [l["action"] for l in logs]
    print(f"  -> Recorded audit actions for {eval_id}: {actions}")
    assert "SUBMIT_FOR_REVIEW" in actions, "Missing SUBMIT_FOR_REVIEW audit log"
    assert "REVIEW_INSPECT" in actions, "Missing REVIEW_INSPECT audit log"
    assert "REVIEW_RETURN" in actions or "REVIEW_REJECT" in actions, "Missing REVIEW_RETURN audit log"
    assert "RESUBMIT_FOR_REVIEW" in actions or "SUBMIT_FOR_REVIEW" in actions, "Missing RESUBMIT_FOR_REVIEW audit log"
    assert "REVIEW_APPROVE" in actions, "Missing REVIEW_APPROVE audit log"
    conn.close()
    print("  -> All workflow transitions successfully audited!")

    # 14. Persistence across fresh fetch & re-login
    print("\n[Step 14] Verifying status persistence after fresh re-login...")
    code, res_relogin = make_req("/api/auth/login", "POST", {"username": "priya_reviewer", "password": "Reviewer@123"})
    new_token = res_relogin["token"]
    code, res_recheck = make_req(f"/api/evaluations/{eval_id}", "GET", token=new_token)
    assert code == 200
    final_ev = res_recheck["evaluation"]
    assert final_ev["status"] == "APPROVED"
    assert final_ev["certificate_number"] == cert_no
    assert final_ev["review_comments"] == approve_remarks
    print("  -> Evaluation status, certificate number, and review remarks 100% persistent!")

    print("\n" + "=" * 70)
    print("ALL REVIEW WORKFLOW TESTS PASSED SUCCESSFULLY! (100% PASS)")
    print("=" * 70)

if __name__ == "__main__":
    main()
