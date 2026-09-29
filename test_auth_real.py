"""
Comprehensive Verification Test for Real Authentication in Metrolab (SIH-26035)
Tests:
1. Technician login (rajesh_inspector / Inspector@123 and technician / Technician@123)
2. Reviewer login (priya_reviewer / Reviewer@123)
3. Admin login (admin / Admin@123)
4. Owner login (essae_owner / Owner@123)
5. Incorrect password (admin / WrongPassword) -> 401 Invalid credentials
6. Logout (/api/auth/logout) -> token cleared & audit logged
7. Direct access to protected pages/APIs without login -> 401/403
"""

import threading
import time
import json
import urllib.request
import urllib.error
from http.server import HTTPServer
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import server
import db
import auth_security as auth

PORT = 8008

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

def run_all_tests():
    print("=" * 70)
    print("METROLAB AUTHENTICATION TEST SUITE - SIH-26035")
    print("=" * 70)

    base = f"http://127.0.0.1:{PORT}"

    # 1. Test Technician Login
    print("\n[TEST 1] Technician Login:")
    status, res = post_json(f"{base}/api/auth/login", {
        "username": "rajesh_inspector",
        "password": "Inspector@123"
    })
    assert status == 200, f"Expected 200, got {status}: {res}"
    assert res.get("success") is True, f"Failed: {res}"
    assert res.get("user", {}).get("role") == "INSPECTOR", f"Wrong role: {res}"
    tech_token = res["token"]
    print(f"  [PASS] rajesh_inspector logged in successfully. Role: {res['user']['role']}, Name: {res['user']['full_name']}")

    # Verify /api/auth/me with Technician token
    me_status, me_res = get_json(f"{base}/api/auth/me", tech_token)
    assert me_status == 200 and me_res["user"]["username"] == "rajesh_inspector", f"Me failed: {me_res}"
    print("  [PASS] /api/auth/me successfully verified token identity.")

    # Also test technician alias
    alias_status, alias_res = post_json(f"{base}/api/auth/login", {
        "username": "technician",
        "password": "Technician@123"
    })
    assert alias_status == 200 and alias_res["user"]["role"] == "INSPECTOR"
    print(f"  [PASS] technician alias logged in successfully. Role: {alias_res['user']['role']}")

    # 2. Test Reviewer Login
    print("\n[TEST 2] Reviewer Login:")
    status, res = post_json(f"{base}/api/auth/login", {
        "username": "priya_reviewer",
        "password": "Reviewer@123"
    })
    assert status == 200, f"Expected 200, got {status}: {res}"
    assert res["user"]["role"] == "REVIEWER", f"Wrong role: {res}"
    reviewer_token = res["token"]
    print(f"  [PASS] priya_reviewer logged in successfully. Role: {res['user']['role']}, Name: {res['user']['full_name']}")

    # Reviewer access to Reviewer Queue / Evaluations
    eval_status, eval_res = get_json(f"{base}/api/evaluations", reviewer_token)
    assert eval_status == 200, f"Reviewer failed to get evaluations: {eval_res}"
    print(f"  [PASS] Reviewer authorized for evaluations queue ({len(eval_res.get('evaluations', []))} records).")

    # 3. Test Admin Login
    print("\n[TEST 3] Admin Login:")
    status, res = post_json(f"{base}/api/auth/login", {
        "username": "admin",
        "password": "Admin@123"
    })
    assert status == 200, f"Expected 200, got {status}: {res}"
    assert res["user"]["role"] == "ADMIN", f"Wrong role: {res}"
    admin_token = res["token"]
    print(f"  [PASS] admin logged in successfully. Role: {res['user']['role']}, Name: {res['user']['full_name']}")

    # Admin access to User Management
    users_status, users_res = get_json(f"{base}/api/auth/users", admin_token)
    assert users_status == 200, f"Admin failed to access users: {users_res}"
    print(f"  [PASS] Admin authorized for user directory ({len(users_res.get('users', []))} total accounts).")

    # 4. Test Owner Login
    print("\n[TEST 4] Instrument Owner Login:")
    status, res = post_json(f"{base}/api/auth/login", {
        "username": "essae_owner",
        "password": "Owner@123"
    })
    assert status == 200, f"Expected 200, got {status}: {res}"
    assert res["user"]["role"] == "OWNER", f"Wrong role: {res}"
    owner_token = res["token"]
    print(f"  [PASS] essae_owner logged in successfully. Role: {res['user']['role']}, Name: {res['user']['full_name']}")

    # Owner access to scoped fleet
    inst_status, inst_res = get_json(f"{base}/api/instruments", owner_token)
    assert inst_status == 200, f"Owner failed to access instruments: {inst_res}"
    print(f"  [PASS] Owner authorized for scoped fleet instruments ({len(inst_res.get('instruments', []))} owned instruments).")

    # 5. Test Incorrect Password
    print("\n[TEST 5] Incorrect Password Handling:")
    status, res = post_json(f"{base}/api/auth/login", {
        "username": "admin",
        "password": "WrongPassword@999"
    })
    assert status == 401, f"Expected 401 Unauthorized, got {status}"
    assert "Invalid credentials" in res.get("error", ""), f"Unexpected error message: {res}"
    print(f"  [PASS] Correctly rejected with HTTP 401: '{res.get('error')}'")

    # Also test nonexistent user
    status_non, res_non = post_json(f"{base}/api/auth/login", {
        "username": "unknown_intruder",
        "password": "Password@123"
    })
    assert status_non == 401
    print(f"  [PASS] Non-existent user correctly rejected with HTTP 401: '{res_non.get('error')}'")

    # 6. Test Logout
    print("\n[TEST 6] Logout Handling:")
    status, res = post_json(f"{base}/api/auth/logout", {}, admin_token)
    assert status == 200, f"Expected 200, got {status}"
    assert res.get("success") is True, f"Logout failed: {res}"
    print(f"  [PASS] Logout endpoint executed successfully: {res.get('message')}")

    # Verify audit log entry for LOGOUT
    conn = db.get_db()
    logout_log = conn.execute("SELECT action, entity_type FROM audit_logs WHERE action = 'LOGOUT' ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()
    assert logout_log is not None and logout_log["action"] == "LOGOUT", "Audit trail missing logout event"
    print("  [PASS] Audit trail verified: LOGOUT event recorded in SQLite database.")

    # 7. Test Direct Access to Protected Pages/APIs Without Login
    print("\n[TEST 7] Direct Access Prevention (Without Login):")
    # A. Unauthenticated /api/auth/me
    s1, r1 = get_json(f"{base}/api/auth/me")
    assert s1 == 401, f"Expected 401 for /api/auth/me without token, got {s1}"
    print(f"  [PASS] Protected /api/auth/me blocked without token -> HTTP {s1} ({r1.get('error')})")

    # B. Unauthenticated /api/auth/users
    s2, r2 = get_json(f"{base}/api/auth/users")
    assert s2 == 401, f"Expected 401 for /api/auth/users without token, got {s2}"
    print(f"  [PASS] Protected /api/auth/users blocked without token -> HTTP {s2} ({r2.get('error')})")

    # C. Unauthenticated /api/audit
    s3, r3 = get_json(f"{base}/api/audit")
    assert s3 in (401, 403), f"Expected 401 or 403 for /api/audit without token, got {s3}"
    print(f"  [PASS] Protected /api/audit blocked without token -> HTTP {s3} ({r3.get('error')})")

    # D. Technician attempting to access Admin-only /api/auth/users
    s4, r4 = get_json(f"{base}/api/auth/users", tech_token)
    assert s4 == 401, f"Technician should not access /api/auth/users, got {s4}"
    print(f"  [PASS] Privilege escalation blocked: Technician denied Admin directory -> HTTP {s4}")

    # E. Malformed or Expired token
    bad_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsig"
    s5, r5 = get_json(f"{base}/api/auth/me", bad_token)
    assert s5 == 401
    print(f"  [PASS] Invalid/tampered JWT token blocked -> HTTP {s5}")

    print("\n" + "=" * 70)
    print("ALL 7 AUTHENTICATION TEST SUITES PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == '__main__':
    # Start test server in background thread
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(1.0)
    run_all_tests()
    sys.exit(0)
