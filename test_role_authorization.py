import http.server
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error

import server
import db

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(resp.read().decode("utf-8"))
            else:
                return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}

def main():
    print("=" * 75)
    print("STARTING TEST SUITE: REAL SERVER-SIDE BACKEND ROLE AUTHORIZATION")
    print("=" * 75)

    # 0. Initialize & seed database
    db.init_db()
    db.seed_database()

    # Start test server
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    # Log in all roles
    print("\n[Step 0] Logging in all 4 roles to acquire tokens...")
    code, res_admin = make_req("/api/auth/login", "POST", {"username": "admin", "password": "Admin@123"})
    assert code == 200, f"Admin login failed: {res_admin}"
    admin_token = res_admin["token"]

    code, res_tech = make_req("/api/auth/login", "POST", {"username": "rajesh_inspector", "password": "Inspector@123"})
    assert code == 200, f"Technician login failed: {res_tech}"
    tech_token = res_tech["token"]

    code, res_rev = make_req("/api/auth/login", "POST", {"username": "priya_reviewer", "password": "Reviewer@123"})
    assert code == 200, f"Reviewer login failed: {res_rev}"
    rev_token = res_rev["token"]

    code, res_essae = make_req("/api/auth/login", "POST", {"username": "essae_owner", "password": "Owner@123"})
    assert code == 200, f"Essae Owner login failed: {res_essae}"
    essae_token = res_essae["token"]

    code, res_avery = make_req("/api/auth/login", "POST", {"username": "avery_owner", "password": "Owner@123"})
    assert code == 200, f"Avery Owner login failed: {res_avery}"
    avery_token = res_avery["token"]
    print("  ✓ Acquired authenticated JWT tokens for Admin, Technician, Reviewer, and 2 Owners")

    # -------------------------------------------------------------------------
    # SUITE 1: UNAUTHENTICATED REQUESTS
    # -------------------------------------------------------------------------
    print("\n[Suite 1] Testing Unauthenticated Requests (Every protected endpoint must return 401)...")
    unauth_endpoints = [
        ("GET", "/api/dashboard/stats"),
        ("GET", "/api/instruments"),
        ("GET", "/api/instruments/inst_non_existent"),
        ("GET", "/api/evaluations"),
        ("GET", "/api/evaluations/eval_non_existent"),
        ("GET", "/api/evaluations/eval_non_existent/report"),
        ("GET", "/api/evaluations/eval_non_existent/attachments"),
        ("GET", "/api/attachments/att_non_existent/download"),
        ("GET", "/api/reports"),
        ("GET", "/api/history"),
        ("GET", "/api/audit"),
        ("GET", "/api/reports/sample.pdf"),
        ("POST", "/api/instruments"),
        ("POST", "/api/evaluations"),
        ("POST", "/api/evaluations/eval_test/readings"),
        ("POST", "/api/evaluations/eval_test/calculate"),
        ("POST", "/api/evaluations/eval_test/submit"),
        ("POST", "/api/evaluations/eval_test/review"),
        ("POST", "/api/evaluations/eval_test/attachments"),
        ("POST", "/api/evaluations/eval_test/generate_pdf"),
        ("POST", "/api/save_audit"),
        ("PUT", "/api/instruments/inst_test"),
        ("PUT", "/api/evaluations/eval_test"),
        ("DELETE", "/api/instruments/inst_test"),
        ("DELETE", "/api/evaluations/eval_test"),
        ("DELETE", "/api/attachments/att_test"),
    ]

    for method, endpoint in unauth_endpoints:
        status, resp = make_req(endpoint, method=method, data={"test": True} if method in ("POST", "PUT") else None)
        assert status == 401, f"Expected 401 for unauthenticated {method} {endpoint}, got {status}: {resp}"
        print(f"  ✓ {method} {endpoint} -> HTTP 401 Unauthorized")

    # -------------------------------------------------------------------------
    # SUITE 2: TECHNICIAN ROLE AUTHORIZATION
    # -------------------------------------------------------------------------
    print("\n[Suite 2] Testing Technician Role Authorization...")
    # 2a. Technician Allowed: Create Instrument
    tech_inst_serial = f"TECH-INST-{int(time.time())}"
    status, res_tech_inst = make_req("/api/instruments", "POST", {
        "serial_number": tech_inst_serial,
        "model": "Benchtop Scale 3000",
        "manufacturer": "Essae Teraoka",
        "accuracy_class": "III",
        "max_capacity": 30.0,
        "min_capacity": 0.1,
        "e_interval": 0.01,
        "d_interval": 0.01,
        "unit": "kg"
    }, token=tech_token)
    assert status == 201, f"Technician could not create instrument: {status} {res_tech_inst}"
    tech_inst_id = res_tech_inst["instrument_id"]
    print(f"  ✓ Technician allowed: Created instrument {tech_inst_id}")

    # 2b. Technician Allowed: Update Instrument
    status, res_tech_inst_up = make_req(f"/api/instruments/{tech_inst_id}", "PUT", {
        "model": "Benchtop Scale 3000 Pro"
    }, token=tech_token)
    assert status == 200, f"Technician could not update instrument: {status} {res_tech_inst_up}"
    print("  ✓ Technician allowed: Updated instrument details")

    # 2c. Technician Allowed: Create Evaluation
    status, res_tech_eval = make_req("/api/evaluations", "POST", {
        "instrument_id": tech_inst_id,
        "test_location": "Delhi Metrology Laboratory",
        "temperature_c": 22.0,
        "humidity_percent": 50.0,
        "pressure_hpa": 1012.0
    }, token=tech_token)
    assert status == 201, f"Technician could not create evaluation: {status} {res_tech_eval}"
    tech_eval_id = res_tech_eval["evaluation_id"]
    print(f"  ✓ Technician allowed: Created evaluation {tech_eval_id}")

    # 2d. Technician Allowed: Log readings
    status, res_tech_rd = make_req(f"/api/evaluations/{tech_eval_id}/readings", "POST", {
        "readings": [
            {"load": 0.0, "reading": 0.0, "position": "center", "direction": "increasing", "repeat_number": 1},
            {"load": 10.0, "reading": 10.002, "position": "center", "direction": "increasing", "repeat_number": 1},
            {"load": 30.0, "reading": 30.005, "position": "center", "direction": "increasing", "repeat_number": 1}
        ]
    }, token=tech_token)
    assert status == 200, f"Technician could not log readings: {status} {res_tech_rd}"
    print("  ✓ Technician allowed: Submitted test observations/readings")

    # 2e. Technician Allowed: Submit for Review
    status, res_tech_sub = make_req(f"/api/evaluations/{tech_eval_id}/submit", "POST", token=tech_token)
    assert status == 200, f"Technician could not submit evaluation: {status} {res_tech_sub}"
    print("  ✓ Technician allowed: Submitted evaluation for review")

    # 2f. Technician FORBIDDEN: Cannot call Review/Approval endpoint
    status, res_tech_rev = make_req(f"/api/evaluations/{tech_eval_id}/review", "POST", {
        "verdict": "APPROVE",
        "comments": "Attempted self-approval by technician"
    }, token=tech_token)
    assert status == 403, f"Technician was not blocked from review endpoint! Expected 403, got {status}: {res_tech_rev}"
    print(f"  ✓ Technician forbidden: Calling Review/Approve blocked -> HTTP 403 ({res_tech_rev.get('error')})")

    # 2g. Technician FORBIDDEN: Cannot access Admin-only user directory
    status, res_tech_users = make_req("/api/auth/users", "GET", token=tech_token)
    assert status == 401, f"Technician was not blocked from user directory! Expected 401, got {status}: {res_tech_users}"
    print(f"  ✓ Technician forbidden: Calling Admin User Directory blocked -> HTTP 401")

    # -------------------------------------------------------------------------
    # SUITE 3: REVIEWER ROLE AUTHORIZATION
    # -------------------------------------------------------------------------
    print("\n[Suite 3] Testing Reviewer Role Authorization...")
    # 3a. Reviewer Allowed: Inspect evaluation and readings
    status, res_rev_eval = make_req(f"/api/evaluations/{tech_eval_id}", "GET", token=rev_token)
    assert status == 200 and len(res_rev_eval.get("readings", [])) >= 3
    print("  ✓ Reviewer allowed: Inspected evaluation details and readings")

    # 3b. Reviewer Allowed: Run server-side recalculation
    status, res_rev_calc = make_req(f"/api/evaluations/{tech_eval_id}/calculate", "POST", token=rev_token)
    assert status == 200
    print("  ✓ Reviewer allowed: Verified calculations on evaluation")

    # 3c. Reviewer Allowed: Return for correction
    status, res_rev_ret = make_req(f"/api/evaluations/{tech_eval_id}/review", "POST", {
        "verdict": "RETURN",
        "comments": "Please add zero-load return observation."
    }, token=rev_token)
    assert status == 200 and res_rev_ret.get("status") == "RETURNED"
    print("  ✓ Reviewer allowed: Returned evaluation for correction")

    # Resubmit as technician so reviewer can approve
    status, _ = make_req(f"/api/evaluations/{tech_eval_id}/submit", "POST", token=tech_token)
    assert status == 200

    # 3d. Reviewer Allowed: Approve evaluation
    status, res_rev_app = make_req(f"/api/evaluations/{tech_eval_id}/review", "POST", {
        "verdict": "APPROVE",
        "comments": "All statutory requirements verified and approved."
    }, token=rev_token)
    assert status == 200 and res_rev_app.get("status") == "APPROVED"
    print(f"  ✓ Reviewer allowed: Approved evaluation, Certificate: {res_rev_app.get('certificate_number')}")

    # 3e. Reviewer FORBIDDEN: Cannot create instruments
    status, res_rev_no_inst = make_req("/api/instruments", "POST", {
        "serial_number": "REV-ILLEGAL-01",
        "model": "Scale",
        "max_capacity": 10.0,
        "e_interval": 0.01
    }, token=rev_token)
    assert status == 403, f"Reviewer was not blocked from creating instruments! Expected 403, got {status}: {res_rev_no_inst}"
    print(f"  ✓ Reviewer forbidden: Create Instrument blocked -> HTTP 403 ({res_rev_no_inst.get('error')})")

    # 3f. Reviewer FORBIDDEN: Cannot modify instruments
    status, res_rev_no_up = make_req(f"/api/instruments/{tech_inst_id}", "PUT", {
        "model": "Tampered Model"
    }, token=rev_token)
    assert status == 403, f"Reviewer was not blocked from updating instruments! Expected 403, got {status}: {res_rev_no_up}"
    print(f"  ✓ Reviewer forbidden: Update Instrument blocked -> HTTP 403")

    # 3g. Reviewer FORBIDDEN: Cannot delete instruments
    status, res_rev_no_del = make_req(f"/api/instruments/{tech_inst_id}", "DELETE", token=rev_token)
    assert status == 403, f"Reviewer was not blocked from deleting instruments! Expected 403, got {status}: {res_rev_no_del}"
    print(f"  ✓ Reviewer forbidden: Delete Instrument blocked -> HTTP 403")

    # 3h. Reviewer FORBIDDEN: Cannot create evaluations
    status, res_rev_no_eval = make_req("/api/evaluations", "POST", {
        "instrument_id": tech_inst_id
    }, token=rev_token)
    assert status == 403, f"Reviewer was not blocked from creating evaluations! Expected 403, got {status}: {res_rev_no_eval}"
    print(f"  ✓ Reviewer forbidden: Create Evaluation blocked -> HTTP 403 ({res_rev_no_eval.get('error')})")

    # 3i. Reviewer FORBIDDEN: Cannot submit test observations
    status, res_rev_no_rd = make_req(f"/api/evaluations/{tech_eval_id}/readings", "POST", {
        "readings": [{"load": 5.0, "reading": 5.0}]
    }, token=rev_token)
    assert status == 403, f"Reviewer was not blocked from submitting readings! Expected 403, got {status}: {res_rev_no_rd}"
    print(f"  ✓ Reviewer forbidden: Submit Test Readings blocked -> HTTP 403")

    # 3j. Reviewer FORBIDDEN: Cannot submit evaluation for review
    status, res_rev_no_sub = make_req(f"/api/evaluations/{tech_eval_id}/submit", "POST", token=rev_token)
    assert status == 403, f"Reviewer was not blocked from submit endpoint! Expected 403, got {status}: {res_rev_no_sub}"
    print(f"  ✓ Reviewer forbidden: Submit for Review blocked -> HTTP 403")

    # 3k. Reviewer FORBIDDEN: Cannot access Admin-only user directory
    status, res_rev_users = make_req("/api/auth/users", "GET", token=rev_token)
    assert status == 401, f"Reviewer was not blocked from user directory! Expected 401, got {status}: {res_rev_users}"
    print(f"  ✓ Reviewer forbidden: Calling Admin User Directory blocked -> HTTP 401")

    # -------------------------------------------------------------------------
    # SUITE 4: INSTRUMENT OWNER ROLE & CROSS-TENANT FLEET ISOLATION
    # -------------------------------------------------------------------------
    print("\n[Suite 4] Testing Instrument Owner Role & Cross-Tenant Fleet Isolation...")
    # Seed an instrument and evaluation explicitly owned by Avery (Owner 2)
    conn = db.get_db()
    avery_inst_id = f"inst_avery_{int(time.time())}"
    now_str = time.strftime('%Y-%m-%dT%H:%M:%S')
    conn.execute("""
    INSERT INTO instruments (id, serial_number, model, manufacturer, accuracy_class, max_capacity, min_capacity, e_interval, d_interval, unit, tare_capacity, owner_id, status, created_at, updated_at)
    VALUES (?, ?, 'Avery Scale', 'Avery Weigh-Tronix', 'III', 50.0, 0.2, 0.02, 0.02, 'kg', 50.0, 'usr_owner_02', 'REGISTERED', ?, ?)
    """, (avery_inst_id, f"AVERY-SN-{int(time.time())}", now_str, now_str))

    avery_eval_id = f"eval_avery_{int(time.time())}"
    conn.execute("""
    INSERT INTO evaluations (id, instrument_id, inspector_id, status, test_date, test_location, temperature_c, humidity_percent, pressure_hpa, gravity_mps2, created_at, updated_at)
    VALUES (?, ?, 'usr_inspector_01', 'SUBMITTED', '2026-09-29', 'Avery Plant', 25.0, 55.0, 1013.0, 9.7915, ?, ?)
    """, (avery_eval_id, avery_inst_id, now_str, now_str))

    conn.commit()
    conn.close()

    # 4a. Essae Owner lists instruments -> Must NOT see Avery's instrument
    status, res_essae_insts = make_req("/api/instruments", "GET", token=essae_token)
    assert status == 200
    inst_ids = [i["id"] for i in res_essae_insts.get("instruments", [])]
    assert avery_inst_id not in inst_ids, f"Data Leak: Essae owner saw Avery instrument in list! {inst_ids}"
    print("  ✓ Owner Fleet Isolation: GET /api/instruments strictly excludes other owners' instruments")

    # 4b. Essae Owner attempts to get Avery's instrument directly -> 403 Forbidden
    status, res_essae_get_avery = make_req(f"/api/instruments/{avery_inst_id}", "GET", token=essae_token)
    assert status == 403, f"Owner was not blocked from viewing another owner's instrument! Expected 403, got {status}: {res_essae_get_avery}"
    print(f"  ✓ Cross-Tenant Isolation: Essae cannot view Avery instrument -> HTTP 403 ({res_essae_get_avery.get('error')})")

    # 4c. Essae Owner attempts to update Avery's instrument -> 403 Forbidden
    status, res_essae_put_avery = make_req(f"/api/instruments/{avery_inst_id}", "PUT", {"model": "Hacked"}, token=essae_token)
    assert status == 403, f"Owner was not blocked from updating another owner's instrument! Expected 403, got {status}: {res_essae_put_avery}"
    print(f"  ✓ Cross-Tenant Isolation: Essae cannot modify Avery instrument -> HTTP 403")

    # 4d. Essae Owner attempts to delete Avery's instrument -> 403 Forbidden
    status, res_essae_del_avery = make_req(f"/api/instruments/{avery_inst_id}", "DELETE", token=essae_token)
    assert status == 403, f"Owner was not blocked from deleting another owner's instrument! Expected 403, got {status}: {res_essae_del_avery}"
    print(f"  ✓ Cross-Tenant Isolation: Essae cannot delete Avery instrument -> HTTP 403")

    # 4e. Essae Owner lists evaluations -> Must NOT see Avery's evaluation
    status, res_essae_evals = make_req("/api/evaluations", "GET", token=essae_token)
    assert status == 200
    eval_ids = [e["id"] for e in res_essae_evals.get("evaluations", [])]
    assert avery_eval_id not in eval_ids, f"Data Leak: Essae owner saw Avery evaluation in list! {eval_ids}"
    print("  ✓ Owner Fleet Isolation: GET /api/evaluations strictly excludes other owners' evaluations")

    # 4f. Essae Owner attempts to get Avery's evaluation directly -> 403 Forbidden
    status, res_essae_get_avery_eval = make_req(f"/api/evaluations/{avery_eval_id}", "GET", token=essae_token)
    assert status == 403, f"Owner was not blocked from viewing another owner's evaluation! Expected 403, got {status}: {res_essae_get_avery_eval}"
    print(f"  ✓ Cross-Tenant Isolation: Essae cannot view Avery evaluation -> HTTP 403")

    # 4g. Owner FORBIDDEN: Cannot create evaluations
    status, res_owner_no_eval = make_req("/api/evaluations", "POST", {"instrument_id": avery_inst_id}, token=essae_token)
    assert status == 403, f"Owner was not blocked from creating evaluations! Expected 403, got {status}: {res_owner_no_eval}"
    print(f"  ✓ Owner forbidden: Create Evaluation blocked -> HTTP 403 ({res_owner_no_eval.get('error')})")

    # 4h. Owner FORBIDDEN: Cannot enter test observations
    status, res_owner_no_rd = make_req(f"/api/evaluations/{tech_eval_id}/readings", "POST", {"readings": [{"load": 1.0, "reading": 1.0}]}, token=essae_token)
    assert status == 403, f"Owner was not blocked from entering readings! Expected 403, got {status}: {res_owner_no_rd}"
    print(f"  ✓ Owner forbidden: Submit Test Readings blocked -> HTTP 403")

    # 4i. Owner FORBIDDEN: Cannot submit evaluations for review
    status, res_owner_no_sub = make_req(f"/api/evaluations/{tech_eval_id}/submit", "POST", token=essae_token)
    assert status == 403, f"Owner was not blocked from submit endpoint! Expected 403, got {status}: {res_owner_no_sub}"
    print(f"  ✓ Owner forbidden: Submit for Review blocked -> HTTP 403")

    # 4j. Owner FORBIDDEN: Cannot review or approve evaluations
    status, res_owner_no_rev = make_req(f"/api/evaluations/{tech_eval_id}/review", "POST", {"verdict": "APPROVE"}, token=essae_token)
    assert status == 403, f"Owner was not blocked from review endpoint! Expected 403, got {status}: {res_owner_no_rev}"
    print(f"  ✓ Owner forbidden: Review/Approve Evaluation blocked -> HTTP 403")

    # 4k. Owner FORBIDDEN: Cannot access Admin-only user directory
    status, res_owner_users = make_req("/api/auth/users", "GET", token=essae_token)
    assert status == 401, f"Owner was not blocked from user directory! Expected 401, got {status}: {res_owner_users}"
    print(f"  ✓ Owner forbidden: Calling Admin User Directory blocked -> HTTP 401")

    # -------------------------------------------------------------------------
    # SUITE 5: ADMIN ROLE UNIVERSAL AUTHORIZATION
    # -------------------------------------------------------------------------
    print("\n[Suite 5] Testing Admin Role Universal Authorization...")
    # 5a. Admin can access user directory
    status, res_admin_users = make_req("/api/auth/users", "GET", token=admin_token)
    assert status == 200 and len(res_admin_users.get("users", [])) >= 4
    print(f"  ✓ Admin allowed: Accessed User Management Directory ({len(res_admin_users['users'])} users)")

    # 5b. Admin can inspect Avery's instrument
    status, res_admin_inst = make_req(f"/api/instruments/{avery_inst_id}", "GET", token=admin_token)
    assert status == 200
    print("  ✓ Admin allowed: Universal access to all instruments")

    # 5c. Admin can inspect Avery's evaluation
    status, res_admin_eval = make_req(f"/api/evaluations/{avery_eval_id}", "GET", token=admin_token)
    assert status == 200
    print("  ✓ Admin allowed: Universal access to all evaluations")

    # 5d. Admin can review / approve evaluations
    status, res_admin_rev = make_req(f"/api/evaluations/{avery_eval_id}/review", "POST", {
        "verdict": "UNDER_REVIEW",
        "comments": "Admin inspection underway."
    }, token=admin_token)
    assert status == 200 and res_admin_rev.get("status") == "UNDER_REVIEW"
    print("  ✓ Admin allowed: Administrative oversight and review authority")

    print("\n" + "=" * 75)
    print("ALL 5 ROLE AUTHORIZATION SUITES PASSED PERFECTLY!")
    print("=" * 75)

if __name__ == "__main__":
    main()
