"""
Test Suite for Persistent Test Reading Storage in Metrolab (SIH-26035)
Test Scenario:
Create evaluation -> enter readings -> save -> refresh -> reopen -> verify all readings -> edit reading -> save -> reopen -> verify persistence
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

PORT = 8011

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

def test_persistent_reading_storage():
    print("=" * 70)
    print("METROLAB PERSISTENT TEST READING STORAGE TEST SUITE - SIH-26035")
    print("=" * 70)

    base = f"http://127.0.0.1:{PORT}"

    # Step 0: Authenticate Technician
    print("\n[AUTH] Authenticating Technician (rajesh_inspector):")
    s, res = post_json(f"{base}/api/auth/login", {
        "username": "rajesh_inspector",
        "password": "Inspector@123"
    })
    assert s == 200 and res.get("token"), f"Tech login failed: {res}"
    tech_token = res["token"]
    print("  [PASS] Technician authenticated successfully. Token received.")

    # Step 1: Create Evaluation
    print("\n[STEP 1: CREATE] Creating an evaluation for instrument 'inst_essae_01':")
    inst_id = "inst_essae_01"
    create_payload = {
        "instrument_id": inst_id,
        "test_date": "2026-09-29",
        "test_location": "NABL Calibration Hall B",
        "temperature_c": 22.5,
        "humidity_percent": 52.0,
        "pressure_hpa": 1012.8,
        "gravity_mps2": 9.7915,
        "reference_standard": "OIML Class F1 Stainless Steel Mass Set",
        "standards_traceability_no": "NPLI/LM/MASS/2026/044",
        "status": "DRAFT"
    }
    s, res = post_json(f"{base}/api/evaluations", create_payload, token=tech_token)
    assert s == 201 and res.get("success"), f"Evaluation creation failed: {res}"
    eval_id = res["evaluation_id"]
    print(f"  [PASS] Evaluation created with ID: {eval_id}")

    # Step 2: Enter Readings (Load, Eccentricity, Repeatability)
    print("\n[STEP 2: ENTER READINGS] Preparing OIML R-76 test reading ledger:")
    sample_readings = [
        # Increasing run (LOAD)
        {"load": 0.0, "reading": 0.0, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 1.5, "reading": 1.5002, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 5.0, "reading": 5.0005, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 10.0, "reading": 10.0010, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 15.0, "reading": 15.0015, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},

        # Decreasing run (LOAD)
        {"load": 15.0, "reading": 15.0012, "direction": "decreasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 10.0, "reading": 10.0008, "direction": "decreasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 5.0, "reading": 5.0004, "direction": "decreasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},
        {"load": 1.5, "reading": 1.5001, "direction": "decreasing", "position": "center", "repeat_number": 1, "test_type": "LOAD"},

        # Repeatability runs (REPEATABILITY)
        {"load": 7.5, "reading": 7.5004, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "REPEATABILITY"},
        {"load": 7.5, "reading": 7.5006, "direction": "increasing", "position": "center", "repeat_number": 2, "test_type": "REPEATABILITY"},
        {"load": 7.5, "reading": 7.5005, "direction": "increasing", "position": "center", "repeat_number": 3, "test_type": "REPEATABILITY"},

        # Eccentricity Corner Load runs (ECCENTRICITY)
        {"load": 5.0, "reading": 5.0002, "direction": "increasing", "position": "center", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 5.0, "reading": 5.0007, "direction": "increasing", "position": "front-left", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 5.0, "reading": 5.0005, "direction": "increasing", "position": "front-right", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 5.0, "reading": 5.0003, "direction": "increasing", "position": "back-left", "repeat_number": 1, "test_type": "ECCENTRICITY"},
        {"load": 5.0, "reading": 5.0006, "direction": "increasing", "position": "back-right", "repeat_number": 1, "test_type": "ECCENTRICITY"}
    ]
    print(f"  [INFO] Total test readings prepared: {len(sample_readings)}")

    # Step 3: SAVE Readings through Backend
    print("\n[STEP 3: SAVE] Saving readings to database via POST /api/evaluations/<id>/readings:")
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/readings", {"readings": sample_readings}, token=tech_token)
    assert s == 200 and res.get("success"), f"Save readings failed: {res}"
    print(f"  [PASS] Stored {res.get('readings_count')} readings successfully.")
    print(f"  [PASS] Compliance Score: {res.get('compliance_score')}%, Conformity: {res.get('conformity')}")

    # Step 4: Direct DB verification
    print("\n[STEP 4: DIRECT DB CHECK] Querying SQLite table test_readings directly:")
    conn = db.get_db()
    rows = conn.execute("""
        SELECT test_type, load_val, reading, error, mpe, ratio, passed, direction, position, repeat_number
        FROM test_readings WHERE evaluation_id = ? ORDER BY rowid ASC
    """, (eval_id,)).fetchall()
    conn.close()
    assert len(rows) == len(sample_readings), f"Expected {len(sample_readings)} rows in DB, found {len(rows)}"
    print(f"  [PASS] Exactly {len(rows)} reading records confirmed in SQLite test_readings.")

    # Check test types
    types = [r["test_type"] for r in rows]
    assert "LOAD" in types and "ECCENTRICITY" in types and "REPEATABILITY" in types
    print("  [PASS] All test types preserved: LOAD, ECCENTRICITY, REPEATABILITY.")

    # Step 5: REFRESH / REOPEN Evaluation
    print("\n[STEP 5: REFRESH / REOPEN] Simulating page refresh & reloading evaluation via GET /api/evaluations/<id>:")
    s, res = get_json(f"{base}/api/evaluations/{eval_id}", token=tech_token)
    assert s == 200 and res.get("evaluation"), f"Get evaluation failed: {res}"
    reloaded_readings = res.get("readings", [])
    assert len(reloaded_readings) == len(sample_readings), f"Expected {len(sample_readings)} readings, got {len(reloaded_readings)}"
    print(f"  [PASS] Reopened evaluation loaded all {len(reloaded_readings)} readings accurately.")

    # Verify first and corner eccentricity readings
    first_rd = reloaded_readings[0]
    assert first_rd["load_val"] == 0.0 and first_rd["reading"] == 0.0 and first_rd["test_type"] == "LOAD"
    
    corner_rds = [r for r in reloaded_readings if r["test_type"] == "ECCENTRICITY"]
    assert len(corner_rds) == 5, f"Expected 5 corner readings, got {len(corner_rds)}"
    print(f"  [PASS] First load reading and all 5 eccentricity readings verified.")

    # Step 6: EDIT READING
    print("\n[STEP 6: EDIT READING] Modifying a reading (adjusting load point 15.0 from 15.0015 to 15.0020):")
    edited_readings = list(sample_readings)
    # Modify the 15kg load reading
    edited_readings[4]["reading"] = 15.0020
    # Add an additional repeatability reading
    edited_readings.append({
        "load": 7.5, "reading": 7.5004, "direction": "increasing", "position": "center", "repeat_number": 4, "test_type": "REPEATABILITY"
    })
    print(f"  [INFO] New readings count after edit: {len(edited_readings)}")

    # Step 7: SAVE Updated Readings
    print("\n[STEP 7: SAVE UPDATED] Saving updated readings to backend:")
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/readings", {"readings": edited_readings}, token=tech_token)
    assert s == 200 and res.get("success"), f"Save updated readings failed: {res}"
    assert res.get("readings_count") == len(edited_readings)
    print(f"  [PASS] Updated readings saved successfully. Total: {res.get('readings_count')}")

    # Step 8: REOPEN AFTER EDIT & VERIFY
    print("\n[STEP 8: REOPEN AFTER EDIT] Reopening evaluation to verify updated values and persistence:")
    s, res = get_json(f"{base}/api/evaluations/{eval_id}", token=tech_token)
    assert s == 200
    rds_after_edit = res.get("readings", [])
    assert len(rds_after_edit) == len(edited_readings)
    
    # Verify the edited load reading
    edited_item = [r for r in rds_after_edit if r["load_val"] == 15.0 and r["direction"] == "increasing"][0]
    assert abs(edited_item["reading"] - 15.0020) < 1e-5, f"Expected reading 15.0020, got {edited_item['reading']}"
    print(f"  [PASS] Verified edited reading value: {edited_item['reading']} kg with updated error {edited_item['error']:.4f} kg.")

    # Verify the 4th repeatability reading exists
    rep4 = [r for r in rds_after_edit if r["test_type"] == "REPEATABILITY" and r["repeat_number"] == 4]
    assert len(rep4) == 1, "4th repeatability reading not found"
    print(f"  [PASS] Verified newly added 4th repeatability reading is stored permanently.")

    # Step 9: RE-LOGIN TEST
    print("\n[STEP 9: RE-LOGIN] Simulating user logout and fresh re-login:")
    post_json(f"{base}/api/auth/logout", {}, token=tech_token)
    
    # Re-login with fresh credentials
    s, res = post_json(f"{base}/api/auth/login", {
        "username": "rajesh_inspector",
        "password": "Inspector@123"
    })
    assert s == 200 and res.get("token")
    new_token = res["token"]
    print("  [PASS] Fresh session established after re-login.")

    # Re-fetch evaluation with new token
    s, res = get_json(f"{base}/api/evaluations/{eval_id}", token=new_token)
    assert s == 200
    rds_after_relogin = res.get("readings", [])
    assert len(rds_after_relogin) == len(edited_readings)
    print(f"  [PASS] Re-login verified: all {len(rds_after_relogin)} readings retained without data loss.")

    print("\n" + "=" * 70)
    print("ALL PERSISTENT TEST READING STORAGE TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("=" * 70)

if __name__ == "__main__":
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(0.6)

    try:
        test_persistent_reading_storage()
    except Exception as e:
        print(f"\n[FAILURE] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
