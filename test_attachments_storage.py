"""
Comprehensive Verification Test for Real Attachment Upload & Storage in Metrolab (SIH-26035)

Test Flow:
Upload -> Save -> Refresh -> Reopen evaluation -> View/download attachment -> Validation Checks -> Access Control
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import threading
import time
import json
import base64
import os
from pathlib import Path
import urllib.request
import urllib.error
from http.server import HTTPServer

import server
import db
import auth_security as auth

PORT = 8012

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

def get_raw(url, token=None):
    req = urllib.request.Request(url, method='GET')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)

def test_attachment_upload_and_storage():
    print("=" * 75)
    print("METROLAB ATTACHMENT UPLOAD & STORAGE TEST SUITE - SIH-26035")
    print("=" * 75)

    base = f"http://127.0.0.1:{PORT}"

    # Step 0: Authenticate Technician & Owner
    print("\n[AUTH] Authenticating Technician (rajesh_inspector) and Owner (essae_owner):")
    s, res = post_json(f"{base}/api/auth/login", {
        "username": "rajesh_inspector",
        "password": "Inspector@123"
    })
    assert s == 200 and res.get("token"), f"Tech login failed: {res}"
    tech_token = res["token"]
    print("  [PASS] Technician authenticated successfully.")

    s, res = post_json(f"{base}/api/auth/login", {
        "username": "essae_owner",
        "password": "Owner@123"
    })
    assert s == 200 and res.get("token"), f"Owner login failed: {res}"
    owner_token = res["token"]
    owner_id = res["user"]["id"]
    print(f"  [PASS] Owner authenticated successfully (User ID: {owner_id}).")

    # Step 1: Create Evaluation for existing instrument 'inst_essae_01'
    print("\n[STEP 1: CREATE EVALUATION] Creating new evaluation for 'inst_essae_01':")
    inst_id = "inst_essae_01"
    create_payload = {
        "instrument_id": inst_id,
        "test_date": "2026-09-29",
        "test_location": "National Metrology Verification Lab",
        "temperature_c": 23.0,
        "humidity_percent": 50.0,
        "status": "DRAFT"
    }
    s, res = post_json(f"{base}/api/evaluations", create_payload, token=tech_token)
    assert s == 201 and res.get("success")
    eval_id = res["evaluation_id"]
    print(f"  [PASS] Evaluation created with ID: {eval_id}")

    # Step 2: Test UPLOAD of valid supported files (PDF, PNG, CSV)
    print("\n[STEP 2: UPLOAD VALID ATTACHMENTS] Uploading PDF, PNG, and CSV evidence files:")
    
    # 2a: Valid PDF
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\nxref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n%%EOF"
    pdf_b64 = base64.b64encode(sample_pdf_bytes).decode('utf-8')
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", {
        "filename": "Class_F1_Calibration_Certificate.pdf",
        "file_data": pdf_b64,
        "description": "NPL-India Traceable Calibration Certificate for 15kg Weights",
        "mime_type": "application/pdf"
    }, token=tech_token)
    assert s == 201 and res.get("success"), f"PDF upload failed: {res}"
    pdf_att_id = res["attachment_id"]
    print(f"  [PASS] PDF uploaded successfully: {res['filename']} (ID: {pdf_att_id})")
    assert res.get("instrument_id") == inst_id, "Attachment must link to instrument_id"
    assert res.get("evaluation_id") == eval_id, "Attachment must link to evaluation_id"
    print(f"  [PASS] Linkage verified: evaluation_id={eval_id}, instrument_id={inst_id}")

    # 2b: Valid PNG Image
    sample_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    png_b64 = base64.b64encode(sample_png_bytes).decode('utf-8')
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", {
        "filename": "scale_nameplate_photo.png",
        "file_data": png_b64,
        "description": "Photograph of scale statutory nameplate & serial badge",
        "mime_type": "image/png"
    }, token=tech_token)
    assert s == 201 and res.get("success")
    png_att_id = res["attachment_id"]
    print(f"  [PASS] PNG image uploaded successfully: {res['filename']} (ID: {png_att_id})")

    # 2c: Valid CSV Ledger
    sample_csv_bytes = b"Step,Load_kg,Reading_kg,Error_kg\n1,0.0,0.0,0.0\n2,5.0,5.0002,0.0002\n3,10.0,10.0005,0.0005\n"
    csv_b64 = base64.b64encode(sample_csv_bytes).decode('utf-8')
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", {
        "filename": "raw_weights_measurements.csv",
        "file_data": csv_b64,
        "description": "Laboratory raw sensor measurement dump",
        "mime_type": "text/csv"
    }, token=tech_token)
    assert s == 201 and res.get("success")
    csv_att_id = res["attachment_id"]
    print(f"  [PASS] CSV evidence uploaded successfully: {res['filename']} (ID: {csv_att_id})")

    # Step 3: Verify Persistence in SQLite Database
    print("\n[STEP 3: DATABASE VERIFICATION] Inspecting attachments table in SQLite:")
    conn = db.get_db()
    att_rows = conn.execute("""
        SELECT id, evaluation_id, instrument_id, uploader_id, filename, original_name, file_size, mime_type, file_hash, description
        FROM attachments WHERE evaluation_id = ? ORDER BY uploaded_at ASC
    """, (eval_id,)).fetchall()
    conn.close()

    assert len(att_rows) == 3, f"Expected 3 attachments in DB, found {len(att_rows)}"
    for r in att_rows:
        assert r["evaluation_id"] == eval_id
        assert r["instrument_id"] == inst_id
        assert r["file_size"] > 0
        assert r["file_hash"] is not None
        assert r["original_name"] in ("Class_F1_Calibration_Certificate.pdf", "scale_nameplate_photo.png", "raw_weights_measurements.csv")
    print("  [PASS] All 3 attachment records verified in SQLite with full metadata & hashes.")

    # Step 4: REFRESH / REOPEN EVALUATION & RETRIEVE ATTACHMENTS
    print("\n[STEP 4: REFRESH & REOPEN] Simulating refresh and retrieving evaluation attachments:")
    s, res = get_json(f"{base}/api/evaluations/{eval_id}", token=tech_token)
    assert s == 200 and res.get("evaluation")
    loaded_atts = res.get("attachments", [])
    assert len(loaded_atts) == 3, f"Expected 3 attachments in evaluation details, got {len(loaded_atts)}"
    print(f"  [PASS] GET /api/evaluations/{eval_id} returned all {len(loaded_atts)} attachments.")

    s, res = get_json(f"{base}/api/evaluations/{eval_id}/attachments", token=tech_token)
    assert s == 200 and len(res.get("attachments", [])) == 3
    print(f"  [PASS] Dedicated GET /api/evaluations/{eval_id}/attachments verified.")

    # Step 5: VIEW / DOWNLOAD ATTACHMENT
    print("\n[STEP 5: VIEW / DOWNLOAD] Downloading uploaded attachments:")
    # 5a: With Authorization Header
    s, content, headers = get_raw(f"{base}/api/attachments/{pdf_att_id}/download", token=tech_token)
    assert s == 200 and content == sample_pdf_bytes, "Downloaded PDF bytes do not match uploaded bytes"
    print(f"  [PASS] PDF downloaded with Authorization header. Content verified bit-for-bit ({len(content)} bytes).")

    # 5b: With ?token= query parameter (simulating browser <a> tag download)
    s, content, headers = get_raw(f"{base}/api/attachments/{png_att_id}/download?token={tech_token}")
    assert s == 200 and content == sample_png_bytes, "Downloaded PNG bytes do not match uploaded bytes"
    print(f"  [PASS] PNG downloaded via browser-style ?token= link. Content verified bit-for-bit.")

    # Step 6: VALIDATION & SECURITY CHECKS
    print("\n[STEP 6: SECURITY & VALIDATION CHECKS] Testing negative scenarios:")

    # 6a: Reject Dangerous Executable/Script Files
    dangerous_payload = {
        "filename": "trojan_payload.exe",
        "file_data": base64.b64encode(b"MZ\x90\x00\x03\x00\x00\x00").decode('utf-8'),
        "mime_type": "application/x-msdownload"
    }
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", dangerous_payload, token=tech_token)
    assert s == 400 and ("forbidden" in res.get("error", "").lower() or "dangerous" in res.get("error", "").lower())
    print(f"  [PASS] Dangerous executable (.exe) rejected with HTTP 400: '{res.get('error')}'.")

    # 6b: Reject Script Files (.sh, .bat, .ps1, .js, .py)
    script_payload = {
        "filename": "hack.sh",
        "file_data": base64.b64encode(b"#!/bin/bash\nrm -rf /").decode('utf-8'),
        "mime_type": "text/x-shellscript"
    }
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", script_payload, token=tech_token)
    assert s == 400
    print(f"  [PASS] Script file (.sh) rejected with HTTP 400.")

    # 6c: Reject Empty Files
    empty_payload = {
        "filename": "empty_cert.pdf",
        "file_data": base64.b64encode(b"").decode('utf-8'),
        "mime_type": "application/pdf"
    }
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", empty_payload, token=tech_token)
    assert s == 400 and "empty" in res.get("error", "").lower()
    print(f"  [PASS] Empty file rejected with HTTP 400: '{res.get('error')}'.")

    # 6d: Reject File with Spoofed Extension (e.g. text/exe renamed as .pdf)
    spoofed_pdf = {
        "filename": "fake_document.pdf",
        "file_data": base64.b64encode(b"This is not a real PDF file!").decode('utf-8'),
        "mime_type": "application/pdf"
    }
    s, res = post_json(f"{base}/api/evaluations/{eval_id}/attachments", spoofed_pdf, token=tech_token)
    assert s == 400 and "not a valid pdf" in res.get("error", "").lower()
    print(f"  [PASS] Spoofed PDF rejected via magic bytes verification: '{res.get('error')}'.")

    # Step 7: ACCESS CONTROL & ISOLATION
    print("\n[STEP 7: ACCESS CONTROL & ISOLATION] Testing unauthorized & cross-tenant access:")

    # 7a: Unauthenticated download rejected
    s, content, _ = get_raw(f"{base}/api/attachments/{pdf_att_id}/download")
    assert s == 401
    print("  [PASS] Unauthenticated download blocked with HTTP 401.")

    # 7b: Owner can access their own instrument's evaluation attachment
    s, content, _ = get_raw(f"{base}/api/attachments/{pdf_att_id}/download", token=owner_token)
    assert s == 200, f"Owner should be able to access own attachment, got status {s}"
    print("  [PASS] Legitimate Instrument Owner successfully accessed their own evaluation attachment.")

    # 7c: Other Owner cannot access unrelated evaluation attachment
    # Create another owner user
    conn = db.get_db()
    other_owner_id = "usr_other_owner_test"
    conn.execute("""
        INSERT OR IGNORE INTO users (id, username, password_hash, role, full_name, email, organization, is_active, created_at)
        VALUES (?, 'unrelated_owner', 'dummy', 'OWNER', 'Unrelated Competitor Ltd', 'comp@test.com', 'Competitor Ltd', 1, '2026-09-29')
    """, (other_owner_id,))
    conn.commit()
    conn.close()

    other_owner_token = auth.create_jwt_token({
        "sub": other_owner_id, "username": "unrelated_owner", "role": "OWNER", "organization": "Competitor Ltd"
    })

    # Other owner tries to download Essae's attachment
    s, content, _ = get_raw(f"{base}/api/attachments/{pdf_att_id}/download", token=other_owner_token)
    assert s == 403, f"Expected HTTP 403 Forbidden for unrelated owner, got {s}"
    print("  [PASS] Unrelated Owner blocked from downloading competitor attachment -> HTTP 403 Forbidden.")

    # Other owner tries to query the evaluation
    s, res = get_json(f"{base}/api/evaluations/{eval_id}", token=other_owner_token)
    assert s == 403
    print("  [PASS] Unrelated Owner blocked from querying evaluation details -> HTTP 403 Forbidden.")

    # Clean up test user
    conn = db.get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (other_owner_id,))
    conn.commit()
    conn.close()

    print("\n" + "=" * 75)
    print("ALL ATTACHMENT UPLOAD & STORAGE TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("=" * 75)

if __name__ == "__main__":
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(0.6)

    try:
        test_attachment_upload_and_storage()
    except Exception as e:
        print(f"\n[FAILURE] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
