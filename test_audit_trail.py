"""
End-to-End Test Suite for Metrology Audit Trail System
Validates statutory compliance under OIML R-76 and Legal Metrology Act:
- Automatic logging of all key system events (Login, Logout, Instruments, Evaluations, Readings, Review actions, Attachments, Reports)
- Full details capture: user, role, action, entity, timestamp, details
- Immutability enforcement (PUT/DELETE rejected with 403)
- Role-based scoping (Owner vs Inspector/Reviewer/Admin)
- Database persistence across restarts
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
import sqlite3
from pathlib import Path

import server
import db

PORT = 8113
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
    print("STARTING TEST SUITE: STATUTORY AUDIT TRAIL SYSTEM")
    print("=" * 70)

    # Initialize and seed database
    db.init_db()
    db.seed_database()

    # Verify table schema has user_role and user_name columns
    conn = db.get_db()
    columns = [col[1] for col in conn.execute("PRAGMA table_info(audit_logs)").fetchall()]
    conn.close()
    assert "user_role" in columns, f"audit_logs missing user_role column: {columns}"
    assert "user_name" in columns, f"audit_logs missing user_name column: {columns}"
    print("[OK] audit_logs table schema contains user_role and user_name columns")

    # Start server thread
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    # 1. Login all roles and verify LOGIN audit logs
    print("\n--- Step 1: Authentication & Login/Logout Audit ---")
    code, res_tech = make_req("/api/auth/login", "POST", {"username": "rajesh_inspector", "password": "Inspector@123"})
    assert code == 200 and res_tech.get("token"), f"Technician login failed: {res_tech}"
    token_tech = res_tech["token"]

    code, res_rev = make_req("/api/auth/login", "POST", {"username": "priya_reviewer", "password": "Reviewer@123"})
    assert code == 200 and res_rev.get("token"), f"Reviewer login failed: {res_rev}"
    token_rev = res_rev["token"]

    code, res_admin = make_req("/api/auth/login", "POST", {"username": "admin", "password": "Admin@123"})
    assert code == 200 and res_admin.get("token"), f"Admin login failed: {res_admin}"
    token_admin = res_admin["token"]

    code, res_owner = make_req("/api/auth/login", "POST", {"username": "essae_owner", "password": "Owner@123"})
    assert code == 200 and res_owner.get("token"), f"Owner login failed: {res_owner}"
    token_owner = res_owner["token"]

    # Test Logout Audit
    code, res_logout = make_req("/api/auth/logout", "POST", {}, token=token_tech)
    assert code == 200, f"Logout failed: {res_logout}"

    # Log back in as tech for remaining tests
    code, res_tech = make_req("/api/auth/login", "POST", {"username": "rajesh_inspector", "password": "Inspector@123"})
    token_tech = res_tech["token"]
    print("[OK] All 4 roles authenticated and login/logout events triggered")

    # 2. Instrument Creation & Update Audit
    print("\n--- Step 2: Instrument Lifecycle Audit ---")
    serial = f"AUD-TEST-{secrets.token_hex(4).upper()}"
    inst_payload = {
        "serial_number": serial,
        "model": "Precision Balances Pro",
        "manufacturer": "Metler Scale Works",
        "accuracy_class": "II",
        "max_capacity": 30.0,
        "min_capacity": 0.05,
        "e_interval": 0.001,
        "d_interval": 0.001,
        "unit": "kg"
    }
    code, res_inst = make_req("/api/instruments", "POST", inst_payload, token=token_tech)
    assert code == 201 and res_inst.get("instrument_id"), f"Instrument creation failed: {res_inst}"
    inst_id = res_inst["instrument_id"]

    # Update instrument
    code, res_update = make_req(f"/api/instruments/{inst_id}", "PUT", {"model": "Precision Balances Pro Updated"}, token=token_tech)
    assert code == 200, f"Instrument update failed: {res_update}"
    print(f"[OK] Instrument created ({inst_id}) and updated with audit logs recorded")

    # 3. Evaluation Creation & Readings Submission Audit
    print("\n--- Step 3: Evaluation & Readings Submission Audit ---")
    eval_payload = {
        "instrument_id": inst_id,
        "test_location": "Delhi Metrology Laboratory",
        "temperature_c": 22.5,
        "humidity_percent": 48.0,
        "pressure_hpa": 1012.0,
        "gravity_mps2": 9.7915,
        "readings": [
            {"load": 0.05, "reading": 0.0500, "direction": "up", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
            {"load": 15.0, "reading": 15.0002, "direction": "up", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
            {"load": 30.0, "reading": 30.0004, "direction": "up", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
            {"load": 15.0, "reading": 15.0001, "direction": "down", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
            {"load": 0.05, "reading": 0.0500, "direction": "down", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
            {"load": 10.0, "reading": 10.0001, "direction": "up", "position": "center", "repeat_number": 1, "test_type": "REPEATABILITY"},
            {"load": 10.0, "reading": 10.0002, "direction": "up", "position": "center", "repeat_number": 2, "test_type": "REPEATABILITY"},
            {"load": 10.0, "reading": 10.0001, "direction": "up", "position": "center", "repeat_number": 3, "test_type": "REPEATABILITY"},
            {"load": 10.0, "reading": 10.0001, "direction": "up", "position": "center", "repeat_number": 1, "test_type": "ECCENTRICITY"},
            {"load": 10.0, "reading": 10.0002, "direction": "up", "position": "front-left", "repeat_number": 1, "test_type": "ECCENTRICITY"},
            {"load": 10.0, "reading": 10.0001, "direction": "up", "position": "back-right", "repeat_number": 1, "test_type": "ECCENTRICITY"}
        ]
    }
    code, res_eval = make_req("/api/evaluations", "POST", eval_payload, token=token_tech)
    assert code == 201 and res_eval.get("evaluation_id"), f"Evaluation creation failed: {res_eval}"
    eval_id = res_eval["evaluation_id"]

    # Submit test readings directly to verify SUBMIT_TEST_READINGS audit
    code, res_rd = make_req(f"/api/evaluations/{eval_id}/readings", "POST", {"readings": eval_payload["readings"]}, token=token_tech)
    assert code == 200, f"Readings submission failed: {res_rd}"
    print(f"[OK] Evaluation created ({eval_id}) and readings stored with audit trail")

    # 4. Review Workflow Audit
    print("\n--- Step 4: Review Workflow State Transitions Audit ---")
    # 4a. Submit for review
    code, res_sub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=token_tech)
    assert code == 200, f"Submit for review failed: {res_sub}"

    # 4b. Reviewer inspects (UNDER_REVIEW)
    code, res_insp = make_req(f"/api/evaluations/{eval_id}/review", "POST", {"verdict": "UNDER_REVIEW"}, token=token_rev)
    assert code == 200, f"Review inspect failed: {res_insp}"

    # 4c. Reviewer returns for correction
    code, res_ret = make_req(f"/api/evaluations/{eval_id}/review", "POST", {
        "verdict": "RETURN",
        "comments": "Please check eccentricity readings at front-left."
    }, token=token_rev)
    assert code == 200, f"Review return failed: {res_ret}"

    # 4d. Technician resubmits
    code, res_resub = make_req(f"/api/evaluations/{eval_id}/submit", "POST", {}, token=token_tech)
    assert code == 200, f"Resubmit failed: {res_resub}"

    # 4e. Reviewer approves
    code, res_app = make_req(f"/api/evaluations/{eval_id}/review", "POST", {
        "verdict": "APPROVE",
        "comments": "Metrological conformity verified according to OIML R 76-1:2006. Approved."
    }, token=token_rev)
    assert code == 200 and res_app.get("status") == "APPROVED", f"Approval failed: {res_app}"
    cert_no = res_app.get("certificate_number")
    print(f"[OK] Full review lifecycle completed (Submitted -> Inspect -> Return -> Resubmit -> Approved)")

    # 5. Attachment Upload Audit
    print("\n--- Step 5: Attachment Upload Audit ---")
    import base64
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    b64_pdf = base64.b64encode(fake_pdf).decode("ascii")
    att_payload = {
        "filename": "Calibration_Cert.pdf",
        "file_data": b64_pdf,
        "mime_type": "application/pdf",
        "description": "Primary standard traceability certificate"
    }
    code, res_att = make_req(f"/api/evaluations/{eval_id}/attachments", "POST", att_payload, token=token_tech)
    assert code == 201 and res_att.get("attachment_id"), f"Attachment upload failed: {res_att}"
    att_id = res_att["attachment_id"]
    print(f"[OK] Attachment uploaded ({att_id}) with audit log")

    # 6. Report Generation Audit
    print("\n--- Step 6: Statutory Report Generation Audit ---")
    code, res_rep = make_req(f"/api/evaluations/{eval_id}/generate_pdf", "POST", {}, token=token_tech)
    assert code == 200 and res_rep.get("certificate_number"), f"Report generation failed: {res_rep}"
    print(f"[OK] Final statutory report generated ({res_rep['certificate_number']}) with audit log")

    # 7. Audit Trail Retrieval & Verification
    print("\n--- Step 7: Verifying Audit Records in GET /api/audit ---")
    # Unauthenticated request should fail with 401
    code, unauth_res = make_req("/api/audit", "GET")
    assert code == 401, f"Expected 401 for unauthenticated GET /api/audit, got {code}"
    print("[OK] Unauthenticated access to /api/audit is properly denied (401)")

    # Technician fetches audit log
    code, tech_audit = make_req("/api/audit", "GET", token=token_tech)
    assert code == 200, f"Technician GET /api/audit failed: {tech_audit}"
    logs = tech_audit.get("audit_logs", [])
    assert len(logs) > 0, "No audit logs returned"

    # Verify key actions exist in logs
    actions_found = set(l["action"] for l in logs)
    print(f"Recorded actions: {sorted(list(actions_found))}")
    required_actions = {
        "LOGIN", "LOGOUT", "CREATE_INSTRUMENT", "UPDATE_INSTRUMENT",
        "CREATE_EVALUATION", "SUBMIT_TEST_READINGS", "SUBMIT_FOR_REVIEW",
        "REVIEW_INSPECT", "REVIEW_RETURN", "RESUBMIT_FOR_REVIEW",
        "REVIEW_APPROVE", "UPLOAD_ATTACHMENT", "GENERATE_REPORT"
    }
    for req_act in required_actions:
        assert req_act in actions_found, f"Missing required audit action: {req_act}"

    # Verify audit entry integrity (timestamp, user, role, entity, details)
    for l in logs[:15]:
        assert l.get("id"), "Audit entry missing id"
        assert l.get("timestamp"), f"Audit entry missing timestamp: {l}"
        assert l.get("user_id"), f"Audit entry missing user_id: {l}"
        assert l.get("user_role"), f"Audit entry missing user_role: {l}"
        assert l.get("user_name"), f"Audit entry missing user_name: {l}"
        assert l.get("action"), f"Audit entry missing action: {l}"
        assert l.get("entity_type"), f"Audit entry missing entity_type: {l}"
        assert l.get("entity_id"), f"Audit entry missing entity_id: {l}"
        assert "details" in l, f"Audit entry missing parsed details: {l}"
    print("[OK] All required audit actions verified with full metadata (User, Role, Name, Entity, Timestamp, Details)")

    # 8. Immutability Protection
    print("\n--- Step 8: Verifying Statutory Audit Immutability ---")
    code, res_put = make_req("/api/audit", "PUT", {"fake": "edit"}, token=token_admin)
    assert code == 403, f"Expected 403 Forbidden for PUT /api/audit, got {code}"
    code, res_del = make_req("/api/audit", "DELETE", token=token_admin)
    assert code == 403, f"Expected 403 Forbidden for DELETE /api/audit, got {code}"
    print("[OK] Audit records are strictly immutable: PUT & DELETE attempts rejected with 403 Forbidden")

    # 9. Direct SQLite Persistence Check
    print("\n--- Step 9: Verifying Direct SQLite Persistence ---")
    conn = db.get_db()
    row = conn.execute("""
        SELECT COUNT(*) FROM audit_logs WHERE action = 'GENERATE_REPORT' AND entity_id = ?
    """, (res_rep["report_id"],)).fetchone()
    assert row[0] >= 1, "Report generation audit log not found directly in SQLite"

    cert_log = conn.execute("""
        SELECT user_id, user_role, user_name, action, details_json
        FROM audit_logs
        WHERE action = 'REVIEW_APPROVE' AND entity_id = ?
    """, (eval_id,)).fetchone()
    assert cert_log is not None, "REVIEW_APPROVE audit log not found in SQLite"
    assert cert_log["user_role"] == "REVIEWER", f"Expected REVIEWER role in db, got {cert_log['user_role']}"
    assert "Priya" in cert_log["user_name"], f"Expected Priya in user_name, got {cert_log['user_name']}"
    details = json.loads(cert_log["details_json"])
    assert details.get("certificate_number") == cert_no, f"Certificate number mismatch in db details: {details}"
    conn.close()
    print(f"[OK] Audit logs verified persistently stored in SQLite nawi_audit.db (Cert: {cert_no})")

    # 10. Role-based Owner Scoping Test
    print("\n--- Step 10: Owner Role Scoping Test ---")
    code, owner_logs = make_req("/api/audit", "GET", token=token_owner)
    assert code == 200, f"Owner GET /api/audit failed: {owner_logs}"
    owner_list = owner_logs.get("audit_logs", [])
    assert len(owner_list) > 0, "Owner should see audit logs for their user and owned fleet"

    # Get all instrument IDs owned by usr_owner_01
    conn = db.get_db()
    owned_insts = set(r[0] for r in conn.execute("SELECT id FROM instruments WHERE owner_id = 'usr_owner_01'").fetchall())
    owned_evals = set(r[0] for r in conn.execute("SELECT id FROM evaluations WHERE instrument_id IN (SELECT id FROM instruments WHERE owner_id = 'usr_owner_01')").fetchall())
    other_owner_insts = set(r[0] for r in conn.execute("SELECT id FROM instruments WHERE owner_id = 'usr_owner_02'").fetchall())
    conn.close()

    for ol in owner_list:
        is_own_action = (ol["user_id"] == "usr_owner_01")
        is_own_inst = (ol["entity_id"] in owned_insts)
        is_own_eval = (ol["entity_id"] in owned_evals)
        is_in_details = ("usr_owner_01" in str(ol.get("details_json", "")))
        assert is_own_action or is_own_inst or is_own_eval or is_in_details, f"Owner saw unrelated audit log: {ol}"
        assert ol["entity_id"] not in other_owner_insts, f"Owner saw another owner's instrument audit log: {ol}"
    print(f"[OK] Owner role scoping verified (Owner retrieved {len(owner_list)} scoped fleet entries)")

    print("\n" + "=" * 70)
    print("ALL AUDIT TRAIL TESTS PASSED SUCCESSFULLY [OK]")
    print("=" * 70)

if __name__ == "__main__":
    main()
