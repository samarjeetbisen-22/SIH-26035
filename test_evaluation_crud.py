"""
Comprehensive Verification Test for Evaluation CRUD in Metrolab (SIH-26035)
Test Scenario:
Create -> Save -> Refresh -> Reopen -> Edit -> Save -> Reopen -> Status Workflow -> Relationship Preservation
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import threading
import time
import json
import urllib.request
import urllib.error
from http.server import HTTPServer

import server
import db
import auth_security as auth

PORT = 8009

def run_test_server():
    httpd = HTTPServer(('127.0.0.1', PORT), server.MetrolabServerHandler)
    httpd.serve_forever()

def post_json(url, data, token=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def put_json(url, data, token=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='PUT')
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def get_json(url, token=None):
    req = urllib.request.Request(url, method='GET')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def run_crud_tests():
    print("=" * 70)
    print("METROLAB EVALUATION CRUD TEST SUITE - SIH-26035")
    print("=" * 70)

    base = f"http://127.0.0.1:{PORT}"

    # Step 0: Authenticate Technician & Reviewer
    print("\n[AUTH] Authenticating Technician and Reviewer:")
    s, res = post_json(f"{base}/api/auth/login", {
        "username": "rajesh_inspector",
        "password": "Inspector@123"
    })
    assert s == 200 and res.get("token"), f"Tech login failed: {res}"
    tech_token = res["token"]
    print("  [PASS] Technician authenticated successfully.")

    s, res = post_json(f"{base}/api/auth/login", {
        "username": "priya_reviewer",
        "password": "Reviewer@123"
    })
    assert s == 200 and res.get("token"), f"Reviewer login failed: {res}"
    rev_token = res["token"]
    print("  [PASS] Reviewer authenticated successfully.")

    # Step 1: CREATE Evaluation for Existing Instrument
    print("\n[STEP 1: CREATE] Creating new evaluation for existing instrument:")
    inst_id = "inst_essae_01"  # Existing instrument in nawi_audit.db
    eval_payload = {
        "instrument_id": inst_id,
        "test_date": "2026-09-28",
        "test_location": "Regional Reference Standards Laboratory, Bengaluru",
        "temperature_c": 24.5,
        "humidity_percent": 52.0,
        "pressure_hpa": 1012.0,
        "gravity_mps2": 9.7915,
        "reference_standard": "OIML Class F1 Mass Standards",
        "standards_traceability_no": "NPLI/MASS/2026/0471",
        "status": "DRAFT",
        "readings": [
            {"load": 0.0, "reading": 0.0, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 5.0, "reading": 5.001, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 10.0, "reading": 10.002, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 15.0, "reading": 15.003, "direction": "increasing", "position": "center", "repeat_number": 1},
        ]
    }

    s, res = post_json(f"{base}/api/evaluations", eval_payload, tech_token)
    assert s == 201, f"Create failed with status {s}: {res}"
    assert res.get("success") is True, f"Create error: {res}"
    created_eval_id = res.get("evaluation_id")
    assert created_eval_id, "Missing evaluation_id in response"
    print(f"  [PASS] Created evaluation ID: {created_eval_id}")

    # Step 2: SAVE Verification in Database
    print("\n[STEP 2: SAVE] Verifying permanent database persistence in nawi_audit.db:")
    conn = db.get_db()
    row = conn.execute("SELECT * FROM evaluations WHERE id = ?", (created_eval_id,)).fetchone()
    assert row is not None, "Evaluation not found in database!"
    assert row["instrument_id"] == inst_id, f"Instrument mismatch: {row['instrument_id']}"
    assert row["status"] == "DRAFT", f"Status mismatch: {row['status']}"
    assert row["temperature_c"] == 24.5, f"Temperature mismatch: {row['temperature_c']}"
    assert row["test_location"] == "Regional Reference Standards Laboratory, Bengaluru"
    
    # Check readings in test_readings table
    rd_count = conn.execute("SELECT COUNT(*) FROM test_readings WHERE evaluation_id = ?", (created_eval_id,)).fetchone()[0]
    conn.close()
    assert rd_count == 4, f"Expected 4 readings in database, found {rd_count}"
    print(f"  [PASS] Evaluation permanently saved in SQLite (ID: {created_eval_id}, readings: {rd_count}).")

    # Step 3: REFRESH / READ (Simulating page refresh or re-login)
    print("\n[STEP 3: REFRESH / READ] Loading evaluation after refresh / re-login:")
    s, res = get_json(f"{base}/api/evaluations/{created_eval_id}", tech_token)
    assert s == 200, f"Refresh failed with status {s}: {res}"
    loaded_ev = res.get("evaluation")
    assert loaded_ev is not None, "Evaluation object missing"
    assert loaded_ev["id"] == created_eval_id, "Evaluation ID mismatch on reload"
    assert loaded_ev["instrument_id"] == inst_id, "Instrument relationship changed on reload"
    assert loaded_ev["temperature_c"] == 24.5
    assert loaded_ev["humidity_percent"] == 52.0
    assert len(res.get("readings", [])) == 4
    print(f"  [PASS] Loaded evaluation restored: {loaded_ev['model']} ({loaded_ev['serial_number']})")
    print(f"  [PASS] Conditions restored: Temp={loaded_ev['temperature_c']}C, Humidity={loaded_ev['humidity_percent']}%, Location={loaded_ev['test_location']}")

    # Step 4: REOPEN from Evaluations List
    print("\n[STEP 4: REOPEN] Reopening evaluation from list query:")
    s, list_res = get_json(f"{base}/api/evaluations?instrument_id={inst_id}", tech_token)
    assert s == 200, f"List failed: {list_res}"
    found = any(e["id"] == created_eval_id for e in list_res.get("evaluations", []))
    assert found, f"Created evaluation {created_eval_id} not found in evaluations list"
    print(f"  [PASS] Evaluation successfully located and reopened from evaluations list.")

    # Step 5: EDIT (Modifying test conditions & readings)
    print("\n[STEP 5: EDIT] Editing evaluation conditions and adding test readings:")
    edit_payload = {
        "test_date": "2026-09-29",
        "test_location": "NPL India Metrology Calibration Centre, New Delhi",
        "temperature_c": 28.5,
        "humidity_percent": 62.0,
        "pressure_hpa": 1010.5,
        "gravity_mps2": 9.7912,
        "reference_standard": "OIML Class E2 Precision Standards",
        "standards_traceability_no": "NPLI/MASS/2026/0999",
        "status": "DRAFT",
        "readings": [
            {"load": 0.0, "reading": 0.0, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 3.0, "reading": 3.001, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 6.0, "reading": 6.002, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 9.0, "reading": 9.002, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 12.0, "reading": 12.003, "direction": "increasing", "position": "center", "repeat_number": 1},
            {"load": 15.0, "reading": 15.004, "direction": "increasing", "position": "center", "repeat_number": 1},
        ]
    }

    # Step 6: SAVE Changes permanently (PUT /api/evaluations/<id>)
    print("\n[STEP 6: SAVE (UPDATE)] Saving edits permanently to database via PUT:")
    s, put_res = put_json(f"{base}/api/evaluations/{created_eval_id}", edit_payload, tech_token)
    assert s == 200, f"PUT failed with status {s}: {put_res}"
    assert put_res.get("success") is True, f"PUT error: {put_res}"
    print(f"  [PASS] Update accepted: {put_res.get('message')}")

    # Verify relationship preservation: Attempt to disconnect or assign non-existent instrument
    s_bad, bad_res = put_json(f"{base}/api/evaluations/{created_eval_id}", {
        "instrument_id": "non_existent_instrument_9999"
    }, tech_token)
    assert s_bad == 400, f"Expected 400 for invalid instrument relationship, got {s_bad}"
    print(f"  [PASS] Relationship protected: Invalid instrument disconnected attempt blocked -> HTTP {s_bad}")

    # Step 7: REOPEN and verify all edits were permanently saved
    print("\n[STEP 7: REOPEN] Reopening evaluation to verify edited values:")
    s, reload_res = get_json(f"{base}/api/evaluations/{created_eval_id}", tech_token)
    assert s == 200
    reloaded_ev = reload_res["evaluation"]
    assert reloaded_ev["temperature_c"] == 28.5, f"Expected 28.5, got {reloaded_ev['temperature_c']}"
    assert reloaded_ev["humidity_percent"] == 62.0, f"Expected 62.0, got {reloaded_ev['humidity_percent']}"
    assert reloaded_ev["test_location"] == "NPL India Metrology Calibration Centre, New Delhi"
    assert reloaded_ev["reference_standard"] == "OIML Class E2 Precision Standards"
    assert len(reload_res.get("readings", [])) == 6, f"Expected 6 readings, found {len(reload_res.get('readings', []))}"
    print(f"  [PASS] Edits verified: Temp={reloaded_ev['temperature_c']}C, Humidity={reloaded_ev['humidity_percent']}%, Location='{reloaded_ev['test_location']}'")
    print(f"  [PASS] Readings updated: {len(reload_res['readings'])} test points verified.")

    # Step 8: STATUS WORKFLOW Persistence
    print("\n[STEP 8: STATUS WORKFLOW] Verifying status progression and persistence:")
    # 8a: Submit for Review
    s_sub, sub_res = post_json(f"{base}/api/evaluations/{created_eval_id}/submit", {}, tech_token)
    assert s_sub == 200, f"Submit failed: {sub_res}"
    
    conn = db.get_db()
    status_db = conn.execute("SELECT status FROM evaluations WHERE id = ?", (created_eval_id,)).fetchone()[0]
    conn.close()
    assert status_db == "SUBMITTED", f"Expected SUBMITTED, got {status_db}"
    print(f"  [PASS] Evaluation submitted: status = '{status_db}' persisted in database.")

    # 8b: Reviewer Approves
    s_rev, rev_res = post_json(f"{base}/api/evaluations/{created_eval_id}/review", {
        "verdict": "APPROVE",
        "comments": "Statutory OIML R-76 MPE verification approved under Legal Metrology Act, 2009."
    }, rev_token)
    assert s_rev == 200, f"Review failed: {rev_res}"

    conn = db.get_db()
    approved_row = conn.execute("SELECT status, review_comments, certificate_number FROM evaluations WHERE id = ?", (created_eval_id,)).fetchone()
    conn.close()
    assert approved_row["status"] == "APPROVED", f"Expected APPROVED, got {approved_row['status']}"
    assert "OIML R-76" in approved_row["review_comments"]
    assert approved_row["certificate_number"] is not None
    print(f"  [PASS] Reviewer approved: status = '{approved_row['status']}', Certificate = '{approved_row['certificate_number']}' persisted in database.")

    print("\n" + "=" * 70)
    print("ALL EVALUATION CRUD TEST CASES PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == '__main__':
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(1.0)
    run_crud_tests()
    sys.exit(0)
