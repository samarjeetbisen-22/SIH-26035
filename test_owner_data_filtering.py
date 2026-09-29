"""
Test Suite: Secure Server-Side Owner-Specific Data Filtering (SIH-26035)
Tests isolation between Owner A (Essae) and Owner B (Avery), URL/ID tampering defense,
and database-level query scoping across Instruments, Evaluations, Reports, and Downloads.
"""

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

PORT = 8115
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
    print("TEST SUITE: SECURE SERVER-SIDE OWNER-SPECIFIC DATA FILTERING")
    print("=" * 75)

    # 0. Initialize & seed database
    db.init_db()
    db.seed_database()

    # Start test server
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    # Step 1: Login Owner A (Essae) and Owner B (Avery)
    print("\n[Step 1] Authenticating Owner A (Essae) and Owner B (Avery)...")
    status_a, res_a = make_req("/api/auth/login", "POST", {"username": "essae_owner", "password": "Owner@123"})
    assert status_a == 200, f"Owner A login failed: {res_a}"
    token_a = res_a["token"]
    user_a = res_a["user"]
    assert user_a["id"] == "usr_owner_01" and user_a["role"] == "OWNER"
    print(f"  ✓ Owner A authenticated: {user_a['full_name']} (ID: {user_a['id']})")

    status_b, res_b = make_req("/api/auth/login", "POST", {"username": "avery_owner", "password": "Owner@123"})
    assert status_b == 200, f"Owner B login failed: {res_b}"
    token_b = res_b["token"]
    user_b = res_b["user"]
    assert user_b["id"] == "usr_owner_02" and user_b["role"] == "OWNER"
    print(f"  ✓ Owner B authenticated: {user_b['full_name']} (ID: {user_b['id']})")

    # Step 2: Owner A Data Retrieval (Must see ONLY Owner A's records)
    print("\n[Step 2] Testing Owner A data scoping (GET /api/instruments, /api/evaluations, /api/reports)...")
    # 2a. Instruments list
    s, insts_a = make_req("/api/instruments", "GET", token=token_a)
    assert s == 200
    a_inst_list = insts_a.get("instruments", [])
    a_inst_ids = [i["id"] for i in a_inst_list]
    print(f"  -> Owner A retrieved {len(a_inst_list)} instruments: {a_inst_ids}")
    assert "inst_essae_01" in a_inst_ids, "Owner A missing inst_essae_01"
    assert "inst_avery_01" not in a_inst_ids, "CRITICAL: Owner B's instrument leaked to Owner A in list!"
    assert all(i.get("owner_id") == "usr_owner_01" for i in a_inst_list), "Owner A list contains foreign owner_id!"
    print("  ✓ Owner A instruments list strictly limited to usr_owner_01")

    # 2b. Evaluations list
    s, evals_a = make_req("/api/evaluations", "GET", token=token_a)
    assert s == 200
    a_eval_list = evals_a.get("evaluations", [])
    a_eval_ids = [e["id"] for e in a_eval_list]
    print(f"  -> Owner A retrieved {len(a_eval_list)} evaluations: {a_eval_ids}")
    assert "eval_demo_01" in a_eval_ids, "Owner A missing eval_demo_01"
    assert "eval_avery_demo_01" not in a_eval_ids, "CRITICAL: Owner B's evaluation leaked to Owner A in list!"
    # Verify testing/review/approval status is preserved
    eval_demo_obj = next(e for e in a_eval_list if e["id"] == "eval_demo_01")
    assert eval_demo_obj["status"] == "APPROVED", f"Expected APPROVED, got {eval_demo_obj['status']}"
    assert eval_demo_obj["certificate_number"] == "CERT-DL-2026-0471"
    eval_sub_obj = next(e for e in a_eval_list if e["id"] == "eval_submitted_02")
    assert eval_sub_obj["status"] == "SUBMITTED", f"Expected SUBMITTED, got {eval_sub_obj['status']}"
    print(f"  ✓ Owner A sees accurate statutory statuses: eval_demo_01 ({eval_demo_obj['status']}), eval_submitted_02 ({eval_sub_obj['status']})")

    # 2c. Reports list
    s, reps_a = make_req("/api/reports", "GET", token=token_a)
    assert s == 200
    a_rep_list = reps_a.get("reports", [])
    a_rep_ids = [r["report_id"] for r in a_rep_list]
    print(f"  -> Owner A retrieved {len(a_rep_list)} reports: {a_rep_ids}")
    assert "REP_ESSAE_01" in a_rep_ids
    assert "REP_AVERY_01" not in a_rep_ids, "CRITICAL: Owner B's report leaked to Owner A in reports list!"
    print("  ✓ Owner A reports list strictly limited to usr_owner_01")

    # 2d. Dashboard stats scoped to Owner A
    s, stats_a = make_req("/api/dashboard/stats", "GET", token=token_a)
    assert s == 200
    stats_data_a = stats_a.get("stats", {})
    assert stats_data_a.get("total_instruments") == len(a_inst_list)
    assert stats_data_a.get("total_evaluations") == len(a_eval_list)
    print(f"  ✓ Owner A dashboard stats scoped to fleet (Instruments: {stats_data_a.get('total_instruments')}, Evaluations: {stats_data_a.get('total_evaluations')})")

    # Step 3: Owner B Data Retrieval (Must see ONLY Owner B's records)
    print("\n[Step 3] Testing Owner B data scoping (GET /api/instruments, /api/evaluations, /api/reports)...")
    # 3a. Instruments list
    s, insts_b = make_req("/api/instruments", "GET", token=token_b)
    assert s == 200
    b_inst_list = insts_b.get("instruments", [])
    b_inst_ids = [i["id"] for i in b_inst_list]
    print(f"  -> Owner B retrieved {len(b_inst_list)} instruments: {b_inst_ids}")
    assert "inst_avery_01" in b_inst_ids
    assert "inst_essae_01" not in b_inst_ids, "CRITICAL: Owner A's instrument leaked to Owner B in list!"
    assert all(i.get("owner_id") == "usr_owner_02" for i in b_inst_list), "Owner B list contains foreign owner_id!"
    print("  ✓ Owner B instruments list strictly limited to usr_owner_02")

    # 3b. Evaluations list
    s, evals_b = make_req("/api/evaluations", "GET", token=token_b)
    assert s == 200
    b_eval_list = evals_b.get("evaluations", [])
    b_eval_ids = [e["id"] for e in b_eval_list]
    print(f"  -> Owner B retrieved {len(b_eval_list)} evaluations: {b_eval_ids}")
    assert "eval_avery_demo_01" in b_eval_ids
    assert "eval_demo_01" not in b_eval_ids, "CRITICAL: Owner A's evaluation leaked to Owner B in list!"
    avery_eval_obj = next(e for e in b_eval_list if e["id"] == "eval_avery_demo_01")
    assert avery_eval_obj["status"] == "APPROVED"
    assert avery_eval_obj["certificate_number"] == "CERT-DL-2026-AWT0881"
    print(f"  ✓ Owner B sees accurate statutory statuses: eval_avery_demo_01 ({avery_eval_obj['status']}, {avery_eval_obj['certificate_number']})")

    # 3c. Reports list
    s, reps_b = make_req("/api/reports", "GET", token=token_b)
    assert s == 200
    b_rep_list = reps_b.get("reports", [])
    b_rep_ids = [r["report_id"] for r in b_rep_list]
    print(f"  -> Owner B retrieved {len(b_rep_list)} reports: {b_rep_ids}")
    assert "REP_AVERY_01" in b_rep_ids
    assert "REP_ESSAE_01" not in b_rep_ids, "CRITICAL: Owner A's report leaked to Owner B in reports list!"
    print("  ✓ Owner B reports list strictly limited to usr_owner_02")

    # 3d. Dashboard stats scoped to Owner B
    s, stats_b = make_req("/api/dashboard/stats", "GET", token=token_b)
    assert s == 200
    stats_data_b = stats_b.get("stats", {})
    assert stats_data_b.get("total_instruments") == len(b_inst_list)
    assert stats_data_b.get("total_evaluations") == len(b_eval_list)
    print(f"  ✓ Owner B dashboard stats scoped to fleet (Instruments: {stats_data_b.get('total_instruments')}, Evaluations: {stats_data_b.get('total_evaluations')})")

    # Step 4: Defense Against Direct URL / ID Parameter Tampering (Owner A attacking Owner B)
    print("\n[Step 4] Testing Direct ID Tampering in URL/API: Owner A attempting to access Owner B's records...")
    
    # 4a. GET /api/instruments/<b_id>
    s, r = make_req("/api/instruments/inst_avery_01", "GET", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner A GET /api/instruments/inst_avery_01 -> DENIED HTTP 403 ({r.get('error')})")

    # 4b. PUT /api/instruments/<b_id>
    s, r = make_req("/api/instruments/inst_avery_01", "PUT", {"model": "Tampered"}, token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner A PUT /api/instruments/inst_avery_01 -> DENIED HTTP 403")

    # 4c. DELETE /api/instruments/<b_id>
    s, r = make_req("/api/instruments/inst_avery_01", "DELETE", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner A DELETE /api/instruments/inst_avery_01 -> DENIED HTTP 403")

    # 4d. GET /api/evaluations/<b_eval_id>
    s, r = make_req("/api/evaluations/eval_avery_demo_01", "GET", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner A GET /api/evaluations/eval_avery_demo_01 -> DENIED HTTP 403 ({r.get('error')})")

    # 4e. GET /api/evaluations/<b_eval_id>/report
    s, r = make_req("/api/evaluations/eval_avery_demo_01/report", "GET", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner A GET /api/evaluations/eval_avery_demo_01/report -> DENIED HTTP 403 ({r.get('error')})")

    # 4f. GET /api/evaluations/<b_eval_id>/attachments
    s, r = make_req("/api/evaluations/eval_avery_demo_01/attachments", "GET", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner A GET /api/evaluations/eval_avery_demo_01/attachments -> DENIED HTTP 403")

    # 4g. POST /api/evaluations/<b_eval_id>/generate_pdf
    s, r = make_req("/api/evaluations/eval_avery_demo_01/generate_pdf", "POST", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner A POST /api/evaluations/eval_avery_demo_01/generate_pdf -> DENIED HTTP 403")

    # 4h. GET /api/reports/<b_pdf_filename>
    s, r = make_req("/api/reports/report_AWT_WB_50T_2026_88_eval_avery_demo_01.pdf", "GET", token=token_a)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner A GET /api/reports/report_AWT_...pdf -> DENIED HTTP 403")

    # Step 5: Defense Against Direct URL / ID Parameter Tampering (Owner B attacking Owner A)
    print("\n[Step 5] Testing Direct ID Tampering in URL/API: Owner B attempting to access Owner A's records...")
    
    # 5a. GET /api/instruments/<a_id>
    s, r = make_req("/api/instruments/inst_essae_01", "GET", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner B GET /api/instruments/inst_essae_01 -> DENIED HTTP 403 ({r.get('error')})")

    # 5b. PUT /api/instruments/<a_id>
    s, r = make_req("/api/instruments/inst_essae_01", "PUT", {"model": "Tampered"}, token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner B PUT /api/instruments/inst_essae_01 -> DENIED HTTP 403")

    # 5c. DELETE /api/instruments/<a_id>
    s, r = make_req("/api/instruments/inst_essae_01", "DELETE", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner B DELETE /api/instruments/inst_essae_01 -> DENIED HTTP 403")

    # 5d. GET /api/evaluations/<a_eval_id>
    s, r = make_req("/api/evaluations/eval_demo_01", "GET", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner B GET /api/evaluations/eval_demo_01 -> DENIED HTTP 403 ({r.get('error')})")

    # 5e. GET /api/evaluations/<a_eval_id>/report
    s, r = make_req("/api/evaluations/eval_demo_01/report", "GET", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print(f"  ✓ Owner B GET /api/evaluations/eval_demo_01/report -> DENIED HTTP 403 ({r.get('error')})")

    # 5f. GET /api/evaluations/<a_eval_id>/attachments
    s, r = make_req("/api/evaluations/eval_demo_01/attachments", "GET", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner B GET /api/evaluations/eval_demo_01/attachments -> DENIED HTTP 403")

    # 5g. POST /api/evaluations/<a_eval_id>/generate_pdf
    s, r = make_req("/api/evaluations/eval_demo_01/generate_pdf", "POST", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner B POST /api/evaluations/eval_demo_01/generate_pdf -> DENIED HTTP 403")

    # 5h. GET /api/reports/<a_pdf_filename>
    s, r = make_req("/api/reports/report_ET_DS852_2026_0471_eval_demo_01.pdf", "GET", token=token_b)
    assert s == 403, f"Expected 403, got {s}: {r}"
    print("  ✓ Owner B GET /api/reports/report_ET_...pdf -> DENIED HTTP 403")

    # Step 6: Legitimate Direct Access by Authorized Owners
    print("\n[Step 6] Testing Legitimate Access: Owners accessing their OWN records...")
    # 6a. Owner A accessing own instrument
    s, r = make_req("/api/instruments/inst_essae_01", "GET", token=token_a)
    assert s == 200 and r["instrument"]["serial_number"] == "ET-DS852-2026-0471"
    print("  ✓ Owner A successfully accessed own instrument inst_essae_01")

    # 6b. Owner A accessing own evaluation
    s, r = make_req("/api/evaluations/eval_demo_01", "GET", token=token_a)
    assert s == 200 and r["evaluation"]["certificate_number"] == "CERT-DL-2026-0471"
    print("  ✓ Owner A successfully accessed own evaluation eval_demo_01")

    # 6c. Owner A accessing own report
    s, r = make_req("/api/evaluations/eval_demo_01/report", "GET", token=token_a)
    assert s == 200 and r["report"]["report_id"] == "REP_ESSAE_01"
    print("  ✓ Owner A successfully accessed own report metadata")

    # 6d. Owner A downloading own PDF
    s, r = make_req("/api/reports/report_ET_DS852_2026_0471_eval_demo_01.pdf", "GET", token=token_a)
    assert s == 200 and len(r) > 10
    print(f"  ✓ Owner A successfully downloaded own statutory report PDF ({len(r)} bytes)")

    # 6e. Owner B accessing own instrument
    s, r = make_req("/api/instruments/inst_avery_01", "GET", token=token_b)
    assert s == 200 and r["instrument"]["serial_number"] == "AWT-WB-50T-2026-88"
    print("  ✓ Owner B successfully accessed own instrument inst_avery_01")

    # 6f. Owner B accessing own evaluation
    s, r = make_req("/api/evaluations/eval_avery_demo_01", "GET", token=token_b)
    assert s == 200 and r["evaluation"]["certificate_number"] == "CERT-DL-2026-AWT0881"
    print("  ✓ Owner B successfully accessed own evaluation eval_avery_demo_01")

    # 6g. Owner B accessing own report
    s, r = make_req("/api/evaluations/eval_avery_demo_01/report", "GET", token=token_b)
    assert s == 200 and r["report"]["report_id"] == "REP_AVERY_01"
    print("  ✓ Owner B successfully accessed own report metadata")

    # 6h. Owner B downloading own PDF
    s, r = make_req("/api/reports/report_AWT_WB_50T_2026_88_eval_avery_demo_01.pdf", "GET", token=token_b)
    assert s == 200 and len(r) > 10
    print(f"  ✓ Owner B successfully downloaded own statutory report PDF ({len(r)} bytes)")

    print("\n" + "=" * 75)
    print("ALL OWNER-SPECIFIC DATA FILTERING TESTS PASSED PERFECTLY!")
    print("=" * 75)

if __name__ == "__main__":
    main()
