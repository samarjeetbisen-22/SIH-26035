"""
End-to-End Test Suite for Complete Instrument CRUD System
Validates statutory requirements under OIML R-76 and Legal Metrology Act:
1. CREATE:
   - Create instrument via POST /api/instruments (supports camelCase and snake_case)
   - Save permanently in SQLite instruments table
   - Verify CREATE_INSTRUMENT audit record is created
2. READ:
   - Load instruments from /api/instruments
   - Retrieve single instrument details via /api/instruments/<id>
   - Scoping by owner (Owner sees own instruments, Inspector/Admin sees all)
3. UPDATE:
   - Modify instrument details via PUT /api/instruments/<id>
   - Save changes permanently in SQLite
   - Verify UPDATE_INSTRUMENT audit record is created
4. DELETE & SAFE ARCHIVE:
   - Referential integrity: when an instrument has linked evaluations/reports, safe archive to 'ARCHIVED'
   - Verify evaluations and test readings remain completely intact
   - When an unlinked instrument is deleted, perform clean delete
   - Verify ARCHIVE_INSTRUMENT and DELETE_INSTRUMENT audit records
5. PERSISTENCE:
   - Direct verification against SQLite nawi_audit.db
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

PORT = 8114
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
    print("STARTING TEST SUITE: COMPLETE INSTRUMENT CRUD & SAFE ARCHIVE")
    print("=" * 70)

    # Initialize and seed database
    db.init_db()
    db.seed_database()

    # Launch server in background thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.2)

    # 1. AUTHENTICATE USERS
    print("\n--- 1. Authenticating Roles ---")
    status, res = make_req("/api/auth/login", method="POST", data={"username": "rajesh_inspector", "password": "Inspector@123"})
    assert status == 200, f"Inspector login failed: {res}"
    inspector_token = res["token"]
    print("[OK] Inspector authenticated successfully")

    status, res = make_req("/api/auth/login", method="POST", data={"username": "essae_owner", "password": "Owner@123"})
    assert status == 200, f"Owner login failed: {res}"
    owner_token = res["token"]
    owner_id = res["user"]["id"]
    print(f"[OK] Owner authenticated successfully (owner_id: {owner_id})")

    # 2. CREATE INSTRUMENT (via Inspector)
    print("\n--- 2. CREATE Instrument via API ---")
    rand_suffix = secrets.token_hex(3).upper()
    test_serial = f"TEST-SCALE-{rand_suffix}"
    inst_payload = {
        "serialNumber": test_serial,
        "model": "Precision Alpha 3000",
        "manufacturer": "Bharat Metrology Labs Pvt Ltd",
        "accuracyClass": "II",
        "maxCapacity": 30.0,
        "minCapacity": 0.1,
        "verificationScaleIntervalE": 0.001,
        "actualScaleIntervalD": 0.001,
        "unit": "kg",
        "tareCapacity": 30.0,
        "typeApprovalNo": "IND/09/2026/999",
        "yearOfManufacture": 2026,
        "countryOfOrigin": "India",
        "owner_id": owner_id
    }
    status, res = make_req("/api/instruments", method="POST", data=inst_payload, token=inspector_token)
    assert status == 201, f"Failed to create instrument: {res}"
    created_inst_id = res.get("instrument_id") or res.get("id")
    assert created_inst_id, "Instrument ID missing in response"
    print(f"[OK] Instrument created successfully with ID: {created_inst_id}")

    # Verify in SQLite database
    conn = db.get_db()
    db_row = conn.execute("SELECT * FROM instruments WHERE id = ?", (created_inst_id,)).fetchone()
    assert db_row, "Instrument not found in SQLite database"
    assert db_row["serial_number"] == test_serial
    assert db_row["model"] == "Precision Alpha 3000"
    assert db_row["accuracy_class"] == "II"
    assert float(db_row["max_capacity"]) == 30.0
    assert db_row["status"] == "REGISTERED"
    print("[OK] Verified instrument fields stored permanently in SQLite")

    # Verify Audit Trail for CREATE_INSTRUMENT
    audit_row = conn.execute("SELECT * FROM audit_logs WHERE action = 'CREATE_INSTRUMENT' AND entity_id = ?", (created_inst_id,)).fetchone()
    assert audit_row, "CREATE_INSTRUMENT audit trail record missing"
    print(f"[OK] Verified audit trail logged for CREATE_INSTRUMENT (audit ID: {audit_row['id']})")
    conn.close()

    # 3. READ INSTRUMENTS (List and Detail)
    print("\n--- 3. READ Instrument via API ---")
    # Read single instrument
    status, res = make_req(f"/api/instruments/{created_inst_id}", method="GET", token=inspector_token)
    assert status == 200, f"Failed to retrieve instrument details: {res}"
    inst_detail = res["instrument"]
    assert inst_detail["serial_number"] == test_serial
    assert inst_detail["model"] == "Precision Alpha 3000"
    print(f"[OK] GET /api/instruments/{created_inst_id} returned accurate instrument details")

    # Read list as Inspector
    status, res = make_req("/api/instruments", method="GET", token=inspector_token)
    assert status == 200
    all_insts = res.get("instruments", [])
    assert any(i["id"] == created_inst_id for i in all_insts), "Created instrument not in all instruments list"
    print(f"[OK] GET /api/instruments returned list containing created scale ({len(all_insts)} total)")

    # Read list as Owner (verifying owner filtering)
    status, res = make_req("/api/instruments", method="GET", token=owner_token)
    assert status == 200
    owner_insts = res.get("instruments", [])
    assert any(i["id"] == created_inst_id for i in owner_insts), "Created instrument assigned to owner was not returned"
    assert all(i["owner_id"] == owner_id for i in owner_insts), "Owner received instruments belonging to other users"
    print(f"[OK] Owner scoping verified: Owner received {len(owner_insts)} instruments strictly belonging to them")

    # 4. UPDATE INSTRUMENT
    print("\n--- 4. UPDATE Instrument via API ---")
    update_payload = {
        "model": "Precision Alpha 3000 Ultra Pro",
        "maxCapacity": 35.0,
        "tareCapacity": 35.0,
        "typeApprovalNo": "IND/09/2026/999-REV1"
    }
    status, res = make_req(f"/api/instruments/{created_inst_id}", method="PUT", data=update_payload, token=inspector_token)
    assert status == 200, f"Failed to update instrument: {res}"
    assert res["instrument"]["model"] == "Precision Alpha 3000 Ultra Pro"
    assert float(res["instrument"]["max_capacity"]) == 35.0
    print("[OK] Instrument updated via API")

    # Verify persistence in SQLite
    conn = db.get_db()
    updated_row = conn.execute("SELECT * FROM instruments WHERE id = ?", (created_inst_id,)).fetchone()
    assert updated_row["model"] == "Precision Alpha 3000 Ultra Pro"
    assert float(updated_row["max_capacity"]) == 35.0
    assert updated_row["type_approval_no"] == "IND/09/2026/999-REV1"
    print("[OK] Verified updated values persisted in SQLite instruments table")

    # Verify Audit Trail for UPDATE_INSTRUMENT
    audit_update = conn.execute("SELECT * FROM audit_logs WHERE action = 'UPDATE_INSTRUMENT' AND entity_id = ?", (created_inst_id,)).fetchone()
    assert audit_update, "UPDATE_INSTRUMENT audit record missing"
    print(f"[OK] Verified audit trail logged for UPDATE_INSTRUMENT (audit ID: {audit_update['id']})")
    conn.close()

    # 5. REFERENTIAL INTEGRITY & SAFE ARCHIVE
    print("\n--- 5. Referential Integrity & Safe Archive Test ---")
    # Attach an evaluation to this instrument
    eval_payload = {
        "instrument_id": created_inst_id,
        "serial_number": test_serial,
        "test_date": "2026-09-29",
        "test_location": "Metrology Verification Laboratory 1",
        "temperature_c": 21.5,
        "humidity_percent": 50.0,
        "pressure_hpa": 1013.25,
        "gravity_mps2": 9.792,
        "reference_standard": "OIML Class F1 Brass Weights",
        "standards_traceability_no": "NPL-IND-2026-881",
        "status": "DRAFT",
        "readings": [
            {"load": 0.0, "reading": 0.0, "direction": "increasing", "position": "center", "repeatNumber": 1},
            {"load": 10.0, "reading": 10.0002, "direction": "increasing", "position": "center", "repeatNumber": 1},
            {"load": 20.0, "reading": 19.9998, "direction": "increasing", "position": "center", "repeatNumber": 1}
        ]
    }
    status, res = make_req("/api/evaluations", method="POST", data=eval_payload, token=inspector_token)
    assert status == 201, f"Failed to create evaluation for instrument: {res}"
    eval_id = res["evaluation_id"]
    print(f"[OK] Created evaluation {eval_id} linked to instrument {created_inst_id}")

    # Now attempt to DELETE the instrument
    print("Attempting to delete instrument with active evaluation...")
    status, res = make_req(f"/api/instruments/{created_inst_id}", method="DELETE", token=inspector_token)
    assert status == 200, f"Delete request failed: {res}"
    assert res.get("archived") is True, f"Expected safe archive, got: {res}"
    print(f"[OK] Backend performed Safe Archive: {res['message']}")

    # Verify instrument status is ARCHIVED and evaluation remains intact!
    conn = db.get_db()
    archived_inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (created_inst_id,)).fetchone()
    assert archived_inst is not None, "Instrument was deleted instead of archived!"
    assert archived_inst["status"] == "ARCHIVED", f"Status should be ARCHIVED, got {archived_inst['status']}"

    preserved_eval = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
    assert preserved_eval is not None, "Evaluation was deleted! Referential integrity violated!"
    assert preserved_eval["instrument_id"] == created_inst_id, "Evaluation instrument relationship was broken!"

    preserved_readings = conn.execute("SELECT COUNT(*) FROM test_readings WHERE evaluation_id = ?", (eval_id,)).fetchone()[0]
    assert preserved_readings == 3, f"Readings were deleted! Expected 3, got {preserved_readings}"

    # Verify ARCHIVE_INSTRUMENT audit record
    audit_archive = conn.execute("SELECT * FROM audit_logs WHERE action = 'ARCHIVE_INSTRUMENT' AND entity_id = ?", (created_inst_id,)).fetchone()
    assert audit_archive is not None, "ARCHIVE_INSTRUMENT audit record missing"
    print(f"[OK] Verified statutory referential integrity: Evaluation {eval_id} and {preserved_readings} test readings remain 100% intact")
    print(f"[OK] Verified audit trail logged for ARCHIVE_INSTRUMENT")
    conn.close()

    # 6. CLEAN DELETE (UNLINKED INSTRUMENT)
    print("\n--- 6. Clean Deletion of Unlinked Instrument ---")
    clean_serial = f"CLEAN-SCALE-{secrets.token_hex(3).upper()}"
    status, res = make_req("/api/instruments", method="POST", data={
        "serialNumber": clean_serial,
        "model": "Disposable Test Scale",
        "manufacturer": "Test Mfr",
        "accuracyClass": "III",
        "maxCapacity": 15.0,
        "verificationScaleIntervalE": 0.005,
        "actualScaleIntervalD": 0.005
    }, token=inspector_token)
    assert status == 201
    clean_inst_id = res["instrument_id"]
    print(f"[OK] Created unlinked scale {clean_inst_id} ({clean_serial})")

    # Call DELETE on unlinked scale
    status, res = make_req(f"/api/instruments/{clean_inst_id}", method="DELETE", token=inspector_token)
    assert status == 200
    assert res.get("archived") is False, "Unlinked scale should have been cleanly deleted, not archived"
    print(f"[OK] Unlinked scale cleanly deleted: {res['message']}")

    # Verify gone from SQLite
    conn = db.get_db()
    deleted_row = conn.execute("SELECT * FROM instruments WHERE id = ?", (clean_inst_id,)).fetchone()
    assert deleted_row is None, "Instrument still exists in SQLite after clean deletion"

    # Verify DELETE_INSTRUMENT audit record
    audit_del = conn.execute("SELECT * FROM audit_logs WHERE action = 'DELETE_INSTRUMENT' AND entity_id = ?", (clean_inst_id,)).fetchone()
    assert audit_del is not None, "DELETE_INSTRUMENT audit record missing"
    print("[OK] Verified instrument was removed from SQLite and DELETE_INSTRUMENT logged to audit trail")
    conn.close()

    print("\n" + "=" * 70)
    print("ALL INSTRUMENT CRUD AND REFERENTIAL INTEGRITY TESTS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    main()
