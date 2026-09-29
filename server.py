"""
Metrolab Enterprise Server (SIH-26035)
Full REST API with Real Authentication, RBAC, Database CRUD, OIML R-76 Validation,
Review Workflow, Owner Filtering, Attachments, Audit Trail, and ReportLab PDF Generation.
"""

import os
import sys
import json
import sqlite3
import datetime
import mimetypes
import secrets
import hashlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

import db
import auth_security as auth
import backend_oiml
import prototype_sih26035 as proto

PORT = 8000
BASE_DIR = Path(__file__).parent.resolve()
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
REPORTS_DIR = BASE_DIR / "reports"
UPLOADS_DIR = BASE_DIR / "uploads"

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Ensure DB is initialized and seeded
db.init_db()
db.seed_database()

class MetrolabServerHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def get_auth_user(self):
        """Extracts and verifies JWT token from Authorization header or ?token= query parameter."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        else:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            token = q.get("token", [""])[0].strip()

        if not token:
            return None
        payload = auth.verify_jwt_token(token)
        if not payload:
            return None
        return payload

    def parse_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def send_json(self, data, status=200):
        self._set_cors_headers(status=status)
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def send_error_json(self, message, status=400):
        self._set_cors_headers(status=status)
        self.wfile.write(json.dumps({"error": message, "success": False}).encode("utf-8"))

    # =========================================================================
    # HTTP GET HANDLER
    # =========================================================================
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Health & Status
        if path == "/api/status":
            conn = db.get_db()
            total_inst = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
            total_eval = conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
            conn.close()
            self.send_json({
                "status": "online",
                "engine": "OIML R-76 SIH-26035 Metrolab Backend",
                "instruments_count": total_inst,
                "evaluations_count": total_eval,
                "server_time": datetime.datetime.now().isoformat()
            })
            return

        # 2. Authentication: Get Current Profile (/api/auth/me)
        elif path == "/api/auth/me":
            user = self.get_auth_user()
            if not user:
                self.send_error_json("Unauthorized", 401)
                return
            conn = db.get_db()
            row = conn.execute("SELECT id, username, email, full_name, role, organization, badge_id FROM users WHERE id = ?", (user["sub"],)).fetchone()
            conn.close()
            if not row:
                self.send_error_json("User not found", 404)
                return
            self.send_json({"user": dict(row)})
            return

        # 3. Authentication: Users List (/api/auth/users) - Admin Only
        elif path == "/api/auth/users":
            user = self.get_auth_user()
            if not user or user.get("role") != "ADMIN":
                self.send_error_json("Unauthorized: Admin required", 401)
                return
            conn = db.get_db()
            rows = conn.execute("SELECT id, username, email, full_name, role, organization, badge_id, is_active, created_at FROM users ORDER BY role, full_name").fetchall()
            conn.close()
            self.send_json({"users": [dict(r) for r in rows]})
            return

        # 4. Live Dashboard Stats (/api/dashboard/stats)
        elif path == "/api/dashboard/stats":
            user = self.get_auth_user()
            conn = db.get_db()
            owner_filter = " WHERE owner_id = ?" if user and user["role"] == "OWNER" else ""
            params = (user["sub"],) if user and user["role"] == "OWNER" else ()

            total_instruments = conn.execute(f"SELECT COUNT(*) FROM instruments{owner_filter}", params).fetchone()[0]
            classes_breakdown = dict(conn.execute(f"SELECT accuracy_class, COUNT(*) FROM instruments{owner_filter} GROUP BY accuracy_class", params).fetchall())
            inst_status_breakdown = dict(conn.execute(f"SELECT status, COUNT(*) FROM instruments{owner_filter} GROUP BY status", params).fetchall())

            eval_query = """
            SELECT e.status, e.conformity, e.compliance_score, e.risk_level
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            """
            eval_params = ()
            if user and user["role"] == "OWNER":
                eval_query += " WHERE i.owner_id = ?"
                eval_params = (user["sub"],)

            eval_rows = conn.execute(eval_query, eval_params).fetchall()
            total_evals = len(eval_rows)
            passed_evals = sum(1 for r in eval_rows if r["conformity"] == 1)
            pass_rate = round((passed_evals / total_evals * 100), 1) if total_evals > 0 else 0.0
            avg_score = round(sum(r["compliance_score"] for r in eval_rows) / total_evals, 1) if total_evals > 0 else 0.0

            eval_status_breakdown = {}
            for r in eval_rows:
                s = r["status"]
                eval_status_breakdown[s] = eval_status_breakdown.get(s, 0) + 1

            risk_breakdown = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            for r in eval_rows:
                rk = r["risk_level"] or "LOW"
                risk_breakdown[rk] = risk_breakdown.get(rk, 0) + 1

            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            in_30_days = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            expiring_soon_query = f"""
            SELECT COUNT(*) FROM instruments 
            WHERE next_verification_due <= ? AND next_verification_due >= ?
            """
            exp_params = [in_30_days, today_str]
            if user and user["role"] == "OWNER":
                expiring_soon_query += " AND owner_id = ?"
                exp_params.append(user["sub"])
            expiring_count = conn.execute(expiring_soon_query, tuple(exp_params)).fetchone()[0]

            recent_logs = conn.execute("""
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.timestamp, u.full_name as user_name, u.role as user_role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC LIMIT 10
            """).fetchall()

            conn.close()

            stats_dict = {
                "total_instruments": total_instruments,
                "total_evaluations": total_evals,
                "approved_evaluations": eval_status_breakdown.get("APPROVED", 0),
                "pass_rate": pass_rate,
                "avg_compliance_score": avg_score,
                "expiring_soon_count": expiring_count,
                "classes_breakdown": classes_breakdown,
                "instruments_status": inst_status_breakdown,
                "evaluations_status": eval_status_breakdown,
                "risk_distribution": risk_breakdown
            }

            self.send_json({
                **stats_dict,
                "stats": stats_dict,
                "recent_activity": [dict(r) for r in recent_logs]
            })
            return

        # 5. Instruments CRUD: List (/api/instruments) - With Real Owner Scoping!
        elif path == "/api/instruments":
            user = self.get_auth_user()
            conn = db.get_db()

            query_sql = """
            SELECT i.*, u.full_name as owner_name, u.organization as owner_organization
            FROM instruments i
            LEFT JOIN users u ON i.owner_id = u.id
            WHERE 1=1
            """
            params = []

            if user and user["role"] == "OWNER":
                query_sql += " AND i.owner_id = ?"
                params.append(user["sub"])

            q = query.get("q", [""])[0].strip()
            if q:
                query_sql += " AND (i.serial_number LIKE ? OR i.model LIKE ? OR i.manufacturer LIKE ?)"
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

            cls = query.get("class", [""])[0].strip()
            if cls:
                query_sql += " AND i.accuracy_class = ?"
                params.append(cls)

            status_f = query.get("status", [""])[0].strip()
            if status_f:
                query_sql += " AND i.status = ?"
                params.append(status_f)

            query_sql += " ORDER BY i.updated_at DESC"
            rows = conn.execute(query_sql, tuple(params)).fetchall()
            conn.close()

            self.send_json({"instruments": [dict(r) for r in rows]})
            return

        # 6. Instrument Details: Get One (/api/instruments/<id>)
        elif path.startswith("/api/instruments/"):
            inst_id = path.split("/")[3]
            user = self.get_auth_user()
            conn = db.get_db()

            inst = conn.execute("""
            SELECT i.*, u.full_name as owner_name, u.organization as owner_organization
            FROM instruments i
            LEFT JOIN users u ON i.owner_id = u.id
            WHERE i.id = ?
            """, (inst_id,)).fetchone()

            if not inst:
                conn.close()
                self.send_error_json("Instrument not found", 404)
                return

            if user and user["role"] == "OWNER" and inst["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access denied: Not your instrument", 403)
                return

            evals = conn.execute("""
            SELECT e.*, u.full_name as inspector_name
            FROM evaluations e
            LEFT JOIN users u ON e.inspector_id = u.id
            WHERE e.instrument_id = ?
            ORDER BY e.created_at DESC
            """, (inst_id,)).fetchall()

            conn.close()
            self.send_json({
                "instrument": dict(inst),
                "evaluations": [dict(e) for e in evals]
            })
            return

        # 7. Evaluations CRUD: List (/api/evaluations) - With Role Filtering
        elif path == "/api/evaluations":
            user = self.get_auth_user()
            conn = db.get_db()

            query_sql = """
            SELECT e.*, i.serial_number, i.model, i.manufacturer, i.accuracy_class, i.max_capacity, i.unit,
                   u_ins.full_name as inspector_name, u_rev.full_name as reviewer_name,
                   u_own.full_name as owner_name
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            LEFT JOIN users u_ins ON e.inspector_id = u_ins.id
            LEFT JOIN users u_rev ON e.reviewer_id = u_rev.id
            LEFT JOIN users u_own ON i.owner_id = u_own.id
            WHERE 1=1
            """
            params = []

            if user and user["role"] == "OWNER":
                query_sql += " AND i.owner_id = ?"
                params.append(user["sub"])

            status_f = query.get("status", [""])[0].strip()
            if status_f:
                query_sql += " AND e.status = ?"
                params.append(status_f)

            inst_f = query.get("instrument_id", [""])[0].strip()
            if inst_f:
                query_sql += " AND e.instrument_id = ?"
                params.append(inst_f)

            query_sql += " ORDER BY e.created_at DESC"
            rows = conn.execute(query_sql, tuple(params)).fetchall()
            conn.close()

            self.send_json({"evaluations": [dict(r) for r in rows]})
            return

        # 7b. Evaluations History Compatible View (/api/history)
        elif path == "/api/history":
            conn = db.get_db()
            serial = query.get("serial", [""])[0].strip()
            sql = """
            SELECT e.id as report_id, e.id as evaluation_id, e.status, e.certificate_number, e.test_date, e.created_at,
                   e.compliance_score, e.risk_level, e.conformity,
                   i.id as instrument_id, i.model as instrument_model, i.serial_number as instrument_serial, i.accuracy_class as class,
                   u.full_name as inspector_name,
                   rep.pdf_filename, rep.pdf_url, rep.report_id as official_report_id
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            LEFT JOIN users u ON e.inspector_id = u.id
            LEFT JOIN reports rep ON rep.evaluation_id = e.id
            """
            params = []
            if serial:
                sql += " WHERE i.serial_number = ?"
                params.append(serial)
            sql += " ORDER BY e.created_at DESC"
            rows = conn.execute(sql, tuple(params)).fetchall()
            conn.close()
            self.send_json({"history": [dict(r) for r in rows]})
            return

        # 7c. Real Reports List & Retrieval (/api/reports)
        elif path == "/api/reports":
            conn = db.get_db()
            eval_id = query.get("evaluation_id", [""])[0].strip()
            inst_id = query.get("instrument_id", [""])[0].strip()
            serial = query.get("serial", [""])[0].strip()
            user = self.get_auth_user()

            sql = """
            SELECT r.*, e.status as evaluation_status, e.test_date, e.conformity as eval_conformity
            FROM reports r
            LEFT JOIN evaluations e ON r.evaluation_id = e.id
            LEFT JOIN instruments i ON r.instrument_id = i.id
            WHERE 1=1
            """
            params = []
            if eval_id:
                sql += " AND r.evaluation_id = ?"
                params.append(eval_id)
            if inst_id:
                sql += " AND r.instrument_id = ?"
                params.append(inst_id)
            if serial:
                sql += " AND r.instrument_serial = ?"
                params.append(serial)
            if user and user["role"] == "OWNER":
                sql += " AND i.owner_id = ?"
                params.append(user["sub"])

            sql += " ORDER BY r.created_at DESC"
            rows = conn.execute(sql, tuple(params)).fetchall()
            conn.close()
            self.send_json({"success": True, "reports": [dict(r) for r in rows]})
            return

        # 7d. Evaluation Report Retrieval (/api/evaluations/<id>/report, /api/evaluations/<id>/reports)
        elif path.startswith("/api/evaluations/") and (path.endswith("/report") or path.endswith("/reports")):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            conn = db.get_db()

            ev = conn.execute("""
            SELECT e.id, e.instrument_id, i.owner_id
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            WHERE e.id = ?
            """, (eval_id,)).fetchone()

            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if user and user["role"] == "OWNER" and ev["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access forbidden: You do not own this instrument", 403)
                return

            report = conn.execute("""
            SELECT * FROM reports WHERE evaluation_id = ? ORDER BY created_at DESC LIMIT 1
            """, (eval_id,)).fetchone()
            conn.close()

            if report:
                self.send_json({"success": True, "report": dict(report)})
            else:
                self.send_error_json("No report generated for this evaluation yet", 404)
            return

        # 8a. Evaluation Attachments List (/api/evaluations/<id>/attachments)
        elif path.startswith("/api/evaluations/") and path.endswith("/attachments"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user:
                self.send_error_json("Unauthorized", 401)
                return

            conn = db.get_db()
            ev = conn.execute("""
            SELECT e.id, e.instrument_id, i.owner_id 
            FROM evaluations e 
            JOIN instruments i ON e.instrument_id = i.id 
            WHERE e.id = ?
            """, (eval_id,)).fetchone()
            
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if user["role"] == "OWNER" and ev["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access denied: Not your instrument evaluation", 403)
                return

            attachments = conn.execute("""
            SELECT id, evaluation_id, instrument_id, filename, original_name, file_size, mime_type, file_hash, description, uploaded_at, uploader_id
            FROM attachments
            WHERE evaluation_id = ?
            ORDER BY uploaded_at DESC
            """, (eval_id,)).fetchall()
            conn.close()

            self.send_json({
                "attachments": [dict(a) for a in attachments],
                "count": len(attachments)
            })
            return

        # 8b. Evaluation Details: Get One (/api/evaluations/<id>)
        elif path.startswith("/api/evaluations/"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            conn = db.get_db()

            ev = conn.execute("""
            SELECT e.*, i.serial_number, i.model, i.manufacturer, i.accuracy_class, 
                   i.max_capacity, i.min_capacity, i.e_interval, i.d_interval, i.unit,
                   i.tare_capacity, i.type_approval_no, i.owner_id,
                   u_ins.full_name as inspector_name, u_ins.badge_id as inspector_badge,
                   u_rev.full_name as reviewer_name, u_rev.badge_id as reviewer_badge,
                   u_own.full_name as owner_name, u_own.organization as owner_organization
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            LEFT JOIN users u_ins ON e.inspector_id = u_ins.id
            LEFT JOIN users u_rev ON e.reviewer_id = u_rev.id
            LEFT JOIN users u_own ON i.owner_id = u_own.id
            WHERE e.id = ?
            """, (eval_id,)).fetchone()

            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if user and user["role"] == "OWNER" and ev["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access denied: Not your instrument evaluation", 403)
                return

            readings = conn.execute("""
            SELECT id, test_type, load_val, reading, error, mpe, ratio, passed, direction, position, repeat_number
            FROM test_readings
            WHERE evaluation_id = ?
            ORDER BY rowid ASC
            """, (eval_id,)).fetchall()

            attachments = conn.execute("""
            SELECT id, evaluation_id, instrument_id, filename, original_name, file_size, mime_type, file_hash, description, uploaded_at, uploader_id
            FROM attachments
            WHERE evaluation_id = ?
            ORDER BY uploaded_at DESC
            """, (eval_id,)).fetchall()

            report = conn.execute("""
            SELECT report_id, evaluation_id, instrument_id, instrument_serial, instrument_model,
                   capacity, class, combined_error, mpe, conformity, compliance_score, risk_level,
                   created_at, inspector_name, inspector_id, pdf_filename, pdf_url, certificate_number
            FROM reports
            WHERE evaluation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """, (eval_id,)).fetchone()

            conn.close()

            self.send_json({
                "evaluation": dict(ev),
                "readings": [dict(r) for r in readings],
                "attachments": [dict(a) for a in attachments],
                "report": dict(report) if report else None
            })
            return

        # 9. Attachments: Download File (/api/attachments/<id>/download)
        elif path.startswith("/api/attachments/") and path.endswith("/download"):
            att_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user:
                self.send_error_json("Unauthorized: Authentication required to download attachments", 401)
                return

            conn = db.get_db()
            att = conn.execute("""
            SELECT a.*, e.instrument_id as eval_inst_id, i.owner_id 
            FROM attachments a
            LEFT JOIN evaluations e ON a.evaluation_id = e.id
            LEFT JOIN instruments i ON COALESCE(a.instrument_id, e.instrument_id) = i.id
            WHERE a.id = ?
            """, (att_id,)).fetchone()
            conn.close()

            if not att:
                self.send_error_json("Attachment not found", 404)
                return

            # Access control: Owner can only access attachments belonging to their instruments
            if user["role"] == "OWNER" and att["owner_id"] and att["owner_id"] != user["sub"]:
                self.send_error_json("Access forbidden: You cannot access unrelated evaluation attachments", 403)
                return

            # Resolve disk path with fallback to ensure persistence across restarts or directory moves
            disk_path = Path(att["file_path"])
            if not disk_path.exists():
                disk_path = UPLOADS_DIR / att["filename"]

            if not disk_path.exists():
                self.send_error_json("Attachment file not found on disk", 404)
                return

            mime = att["mime_type"] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="{att["original_name"]}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
            with open(disk_path, "rb") as f:
                self.wfile.write(f.read())
            return

        # 10. Audit Logs List (/api/audit_logs, /api/audit) - Admin & Reviewer Only
        elif path in ("/api/audit_logs", "/api/audit"):
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "REVIEWER"):
                self.send_error_json("Access forbidden: Requires Admin or Reviewer role", 403)
                return

            conn = db.get_db()
            logs = conn.execute("""
            SELECT a.*, u.username, u.full_name, u.role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT 100
            """).fetchall()
            conn.close()

            logs_list = [dict(l) for l in logs]
            self.send_json({"audit_logs": logs_list, "logs": logs_list})
            return

        # 11. Reports Serving (/api/reports/<filename>)
        elif path.startswith("/api/reports/"):
            filename = os.path.basename(path)
            file_path = REPORTS_DIR / filename
            if file_path.exists():
                mime = "application/pdf" if filename.endswith(".pdf") else "text/html"
                self._set_cors_headers(content_type=mime)
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Report file not found")
            return

        # 12. Static Frontend Single Page Application
        else:
            rel_path = path.lstrip("/")
            target_file = FRONTEND_DIST / rel_path

            if not rel_path or not target_file.exists() or target_file.is_dir():
                target_file = FRONTEND_DIST / "index.html"

            if target_file.exists():
                content_type, _ = mimetypes.guess_type(str(target_file))
                if content_type is None:
                    if str(target_file).endswith(".js"):
                        content_type = "application/javascript"
                    elif str(target_file).endswith(".css"):
                        content_type = "text/css"
                    elif str(target_file).endswith(".svg"):
                        content_type = "image/svg+xml"
                    else:
                        content_type = "text/html"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                with open(target_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Frontend build not found.")

    # =========================================================================
    # HTTP POST HANDLER
    # =========================================================================
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        # 1. Authentication: Login (/api/auth/login)
        if path == "/api/auth/login":
            username = body.get("username", "").strip()
            password = body.get("password", "")

            if not username or not password:
                self.send_error_json("Username and password are required", 400)
                return

            conn = db.get_db()
            user = conn.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)).fetchone()
            conn.close()

            if not user or not db.verify_password(password, user["salt"], user["password_hash"]):
                self.send_error_json("Invalid credentials", 401)
                return

            token = auth.create_jwt_token({
                "sub": user["id"],
                "username": user["username"],
                "role": user["role"],
                "full_name": user["full_name"],
                "org": user["organization"]
            })

            db.log_audit(user["id"], "LOGIN", "USER", user["id"], {"role": user["role"]}, self.client_address[0])

            self.send_json({
                "success": True,
                "token": token,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                    "organization": user["organization"],
                    "badge_id": user["badge_id"]
                }
            })
            return

        # 2. Authentication: Logout (/api/auth/logout)
        elif path == "/api/auth/logout":
            user = self.get_auth_user()
            if user:
                db.log_audit(user["sub"], "LOGOUT", "USER", user["sub"], {}, self.client_address[0])
            self.send_json({"success": True, "message": "Logged out successfully"})
            return

        # 3. Instruments CRUD: Create (/api/instruments)
        elif path == "/api/instruments":
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR", "OWNER"):
                self.send_error_json("Unauthorized to create instruments", 403)
                return

            serial = body.get("serial_number", "").strip()
            model = body.get("model", "").strip()
            manufacturer = body.get("manufacturer", "").strip()
            accuracy_class = body.get("accuracy_class", "III").strip()
            max_cap = float(body.get("max_capacity", 0))
            min_cap = float(body.get("min_capacity", 0))
            e_val = float(body.get("e_interval", 0.001))
            d_val = float(body.get("d_interval", e_val))
            tare = float(body.get("tare_capacity", max_cap))
            unit = body.get("unit", "kg")
            type_app = body.get("type_approval_no", "")
            year = int(body.get("year_of_manufacture", datetime.datetime.now().year))
            country = body.get("country_of_origin", "India")
            owner_id = user["sub"] if user["role"] == "OWNER" else body.get("owner_id", user["sub"])

            if not serial or not model or max_cap <= 0 or e_val <= 0:
                self.send_error_json("Invalid instrument parameters: serial, model, capacity and e required", 400)
                return

            conn = db.get_db()
            existing = conn.execute("SELECT id FROM instruments WHERE serial_number = ?", (serial,)).fetchone()
            if existing:
                conn.close()
                self.send_error_json(f"Instrument with serial '{serial}' already exists", 409)
                return

            inst_id = f"inst_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
            now = datetime.datetime.now().isoformat()

            conn.execute("""
            INSERT INTO instruments (
                id, serial_number, model, manufacturer, accuracy_class, max_capacity, min_capacity,
                e_interval, d_interval, unit, tare_capacity, type_approval_no, year_of_manufacture,
                country_of_origin, owner_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'REGISTERED', ?, ?)
            """, (
                inst_id, serial, model, manufacturer, accuracy_class, max_cap, min_cap,
                e_val, d_val, unit, tare, type_app, year, country, owner_id, now, now
            ))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "CREATE", "INSTRUMENT", inst_id, {"serial": serial, "model": model}, self.client_address[0])
            self.send_json({"success": True, "instrument_id": inst_id, "message": "Instrument registered successfully"}, 201)
            return

        # 4. Evaluations CRUD: Create Evaluation (/api/evaluations)
        elif path == "/api/evaluations":
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Only Inspectors and Admins can conduct metrological evaluations", 403)
                return

            conn = db.get_db()
            instrument_id = body.get("instrument_id")

            # Look up or auto-link instrument
            if not instrument_id and body.get("serial_number"):
                row = conn.execute("SELECT id FROM instruments WHERE serial_number = ?", (body.get("serial_number"),)).fetchone()
                if row:
                    instrument_id = row["id"]

            if not instrument_id and body.get("instrument"):
                inst_info = body.get("instrument")
                sn = inst_info.get("serialNumber") or inst_info.get("serial_number")
                if sn:
                    row = conn.execute("SELECT id FROM instruments WHERE serial_number = ?", (sn,)).fetchone()
                    if row:
                        instrument_id = row["id"]
                    else:
                        instrument_id = f"inst_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
                        now_inst = datetime.datetime.now().isoformat()
                        # Auto-associate instrument with manufacturer owner if available
                        owner_id = inst_info.get("owner_id") or body.get("owner_id")
                        if not owner_id:
                            mfr = inst_info.get("manufacturer", "")
                            mfr_first = mfr.split()[0] if mfr else ""
                            owner_row = conn.execute("SELECT id FROM users WHERE role = 'OWNER' AND (organization LIKE ? OR full_name LIKE ?)", (f"%{mfr_first}%", f"%{mfr_first}%")).fetchone()
                            owner_id = owner_row["id"] if owner_row else user["sub"]

                        conn.execute("""
                        INSERT INTO instruments (
                            id, serial_number, model, manufacturer, accuracy_class, max_capacity,
                            min_capacity, e_interval, d_interval, unit, tare_capacity, type_approval_no,
                            owner_id, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_VERIFICATION', ?, ?)
                        """, (
                            instrument_id, sn,
                            inst_info.get("model", "NAWI Device"),
                            inst_info.get("manufacturer", "Manufacturer"),
                            inst_info.get("accuracyClass", "III"),
                            float(inst_info.get("maxCapacity", 15.0)),
                            float(inst_info.get("minCapacity", 0.04)),
                            float(inst_info.get("verificationScaleIntervalE", 0.005)),
                            float(inst_info.get("actualScaleIntervalD", 0.005)),
                            inst_info.get("unit", "kg"),
                            float(inst_info.get("tareCapacity", 15.0)),
                            inst_info.get("typeApprovalNumber", ""),
                            owner_id, now_inst, now_inst
                        ))

            if not instrument_id:
                conn.close()
                self.send_error_json("Instrument ID or Serial Number required", 400)
                return

            inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
            if not inst:
                conn.close()
                self.send_error_json("Instrument not found", 404)
                return

            eval_id = body.get("id") or body.get("evaluation_id") or f"eval_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
            now = datetime.datetime.now().isoformat()

            test_date = body.get("test_date", now[:10])
            test_location = body.get("test_location", "Regional Reference Standards Laboratory")
            temp_c = float(body.get("temperature_c", 25.0))
            humidity = float(body.get("humidity_percent", 55.0))
            pressure = float(body.get("pressure_hpa", 1013.25))
            gravity = float(body.get("gravity_mps2", 9.7915))
            ref_std = body.get("reference_standard", "OIML Class F1 Weights")
            trace_no = body.get("standards_traceability_no", "NPLI/LM/MASS/2026/01")
            status = body.get("status", "DRAFT")

            conn.execute("""
            INSERT INTO evaluations (
                id, instrument_id, inspector_id, status, test_date, test_location,
                temperature_c, humidity_percent, pressure_hpa, gravity_mps2,
                reference_standard, standards_traceability_no, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eval_id, instrument_id, user["sub"], status, test_date, test_location,
                temp_c, humidity, pressure, gravity, ref_std, trace_no, now, now
            ))

            # Store readings if provided
            readings_list = body.get("readings", [])
            if readings_list and isinstance(readings_list, list):
                inst_dict = {
                    "max_capacity": inst["max_capacity"],
                    "e_interval": inst["e_interval"],
                    "accuracy_class": inst["accuracy_class"],
                    "serial_number": inst["serial_number"],
                    "model": inst["model"]
                }
                results = backend_oiml.validate_oiml_compliance(inst_dict, readings_list)
                for pt in results["point_results"]:
                    rd_id = f"tr_{secrets.token_hex(6)}"
                    test_type = pt.get("test_type", "LOAD")
                    if test_type not in ("LOAD", "ECCENTRICITY", "REPEATABILITY"):
                        test_type = "LOAD"
                    pos = pt.get("position", "center")
                    if pos not in ('center', 'front-left', 'front-right', 'back-left', 'back-right'):
                        pos = 'center'
                    conn.execute("""
                    INSERT INTO test_readings (
                        id, evaluation_id, test_type, load_val, reading, error, mpe, ratio, passed,
                        direction, position, repeat_number, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rd_id, eval_id, test_type, pt["load"], pt["reading"], pt["error"],
                        pt["mpe"], pt["ratio"], 1 if pt["passed"] else 0,
                        pt["direction"], pos, pt["repeat_number"], now
                    ))
                conn.execute("""
                UPDATE evaluations SET
                    repeatability_error = ?, linearity_error = ?, hysteresis_error = ?,
                    eccentricity_error = ?, combined_uncertainty = ?, expanded_uncertainty = ?,
                    compliance_score = ?, risk_level = ?, conformity = ?, verification_hash = ?
                WHERE id = ?
                """, (
                    results["repeatability_error"], results["linearity_error"], results["hysteresis_error"],
                    results["eccentricity_error"], results["combined_uncertainty"], results["expanded_uncertainty"],
                    results["compliance_score"], results["risk_level"], results["conformity"], results["verification_hash"],
                    eval_id
                ))

            conn.execute("UPDATE instruments SET status = 'PENDING_VERIFICATION', updated_at = ? WHERE id = ?", (now, instrument_id))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "CREATE", "EVALUATION", eval_id, {"instrument": inst["serial_number"], "status": status}, self.client_address[0])
            self.send_json({"success": True, "evaluation_id": eval_id, "message": "Evaluation created successfully", "status": status}, 201)
            return

        # 5. Real Test Readings Storage & Server-side Recalculation
        elif path.startswith("/api/evaluations/") and path.endswith("/readings"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Only Inspectors and Admins can log readings", 403)
                return

            conn = db.get_db()
            ev = conn.execute("SELECT e.*, i.* FROM evaluations e JOIN instruments i ON e.instrument_id = i.id WHERE e.id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if ev["status"] == "APPROVED":
                conn.close()
                self.send_error_json("Cannot modify readings on an approved evaluation", 400)
                return

            readings_list = body.get("readings", [])
            if not readings_list:
                conn.close()
                self.send_error_json("No readings provided", 400)
                return

            inst_dict = {
                "max_capacity": ev["max_capacity"],
                "e_interval": ev["e_interval"],
                "accuracy_class": ev["accuracy_class"],
                "serial_number": ev["serial_number"],
                "model": ev["model"]
            }
            results = backend_oiml.validate_oiml_compliance(inst_dict, readings_list)

            conn.execute("DELETE FROM test_readings WHERE evaluation_id = ?", (eval_id,))
            now = datetime.datetime.now().isoformat()

            for pt in results["point_results"]:
                rd_id = f"tr_{secrets.token_hex(6)}"
                test_type = pt.get("test_type", "LOAD")
                if test_type not in ("LOAD", "ECCENTRICITY", "REPEATABILITY"):
                    test_type = "LOAD"
                pos = pt.get("position", "center")
                if pos not in ('center', 'front-left', 'front-right', 'back-left', 'back-right'):
                    pos = 'center'
                conn.execute("""
                INSERT INTO test_readings (
                    id, evaluation_id, test_type, load_val, reading, error, mpe, ratio, passed,
                    direction, position, repeat_number, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rd_id, eval_id, test_type, pt["load"], pt["reading"], pt["error"],
                    pt["mpe"], pt["ratio"], 1 if pt["passed"] else 0,
                    pt["direction"], pos, pt["repeat_number"], now
                ))

            conn.execute("""
            UPDATE evaluations SET
                repeatability_error = ?,
                linearity_error = ?,
                hysteresis_error = ?,
                eccentricity_error = ?,
                combined_uncertainty = ?,
                expanded_uncertainty = ?,
                compliance_score = ?,
                risk_level = ?,
                conformity = ?,
                verification_hash = ?,
                updated_at = ?
            WHERE id = ?
            """, (
                results["repeatability_error"],
                results["linearity_error"],
                results["hysteresis_error"],
                results["eccentricity_error"],
                results["combined_uncertainty"],
                results["expanded_uncertainty"],
                results["compliance_score"],
                results["risk_level"],
                results["conformity"],
                results["verification_hash"],
                now, eval_id
            ))

            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "BATCH_INSERT", "EVALUATION", eval_id, {
                "points_count": len(results["point_results"]),
                "compliance_score": results["compliance_score"],
                "conformity": results["conformity"]
            }, self.client_address[0])

            self.send_json({
                "success": True,
                "inserted_count": len(results["point_results"]),
                "readings_count": len(results["point_results"]),
                "compliance_score": results["compliance_score"],
                "conformity": results["conformity"],
                "message": f"Successfully stored {len(results['point_results'])} readings and verified OIML compliance",
                "calculations": results
            })
            return

        # Real Backend OIML Validation Recalculate (/api/evaluations/<id>/calculate)
        elif path.startswith("/api/evaluations/") and path.endswith("/calculate"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR", "REVIEWER"):
                self.send_error_json("Unauthorized to run OIML calculations", 403)
                return

            conn = db.get_db()
            ev = conn.execute("SELECT e.*, i.serial_number, i.model, i.max_capacity, i.e_interval, i.accuracy_class FROM evaluations e JOIN instruments i ON e.instrument_id = i.id WHERE e.id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            inst_dict = {
                "max_capacity": ev["max_capacity"],
                "e_interval": ev["e_interval"],
                "accuracy_class": ev["accuracy_class"],
                "serial_number": ev["serial_number"],
                "model": ev["model"]
            }

            body_readings = body.get("readings") if isinstance(body, dict) else None
            if not body_readings:
                stored = conn.execute("SELECT * FROM test_readings WHERE evaluation_id = ?", (eval_id,)).fetchall()
                body_readings = [dict(r) for r in stored]

            if not body_readings:
                conn.close()
                self.send_error_json("No readings found for evaluation", 400)
                return

            results = backend_oiml.validate_oiml_compliance(inst_dict, body_readings)
            now = datetime.datetime.now().isoformat()

            conn.execute("""
            UPDATE evaluations SET
                repeatability_error = ?,
                linearity_error = ?,
                hysteresis_error = ?,
                eccentricity_error = ?,
                combined_uncertainty = ?,
                expanded_uncertainty = ?,
                compliance_score = ?,
                risk_level = ?,
                conformity = ?,
                verification_hash = ?,
                updated_at = ?
            WHERE id = ?
            """, (
                results["repeatability_error"],
                results["linearity_error"],
                results["hysteresis_error"],
                results["eccentricity_error"],
                results["combined_uncertainty"],
                results["expanded_uncertainty"],
                results["compliance_score"],
                results["risk_level"],
                results["conformity"],
                results["verification_hash"],
                now, eval_id
            ))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "CALCULATE", "EVALUATION", eval_id, {
                "compliance_score": results["compliance_score"],
                "conformity": results["conformity"]
            }, self.client_address[0])

            self.send_json({
                "success": True,
                "calculations": results
            })
            return

        # 6. Real Review Workflow: Submit for Review (/api/evaluations/<id>/submit)
        elif path.startswith("/api/evaluations/") and path.endswith("/submit"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Only Inspectors and Admins can submit evaluations for review", 403)
                return

            conn = db.get_db()
            ev = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if ev["status"] == "APPROVED":
                conn.close()
                self.send_error_json("Cannot submit an already approved evaluation", 400)
                return

            readings_count = conn.execute("SELECT COUNT(*) FROM test_readings WHERE evaluation_id = ?", (eval_id,)).fetchone()[0]
            if readings_count == 0:
                conn.close()
                self.send_error_json("Cannot submit evaluation with zero test readings", 400)
                return

            now = datetime.datetime.now().isoformat()
            conn.execute("""
            UPDATE evaluations SET status = 'SUBMITTED', submitted_at = ?, updated_at = ? WHERE id = ?
            """, (now, now, eval_id))
            conn.commit()
            conn.close()

            action_name = "RESUBMIT_FOR_REVIEW" if ev["status"] in ("REJECTED", "RETURNED") else "SUBMIT_FOR_REVIEW"
            db.log_audit(user["sub"], action_name, "EVALUATION", eval_id, {"previous_status": ev["status"]}, self.client_address[0])
            self.send_json({"success": True, "status": "SUBMITTED", "message": "Evaluation submitted to Reviewer queue"})
            return

        # 7. Real Review Workflow: Approve / Reject / Return / Under Review (/api/evaluations/<id>/review)
        elif path.startswith("/api/evaluations/") and path.endswith("/review"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "REVIEWER"):
                self.send_error_json("Access forbidden: Only Reviewers and Admins can approve/reject evaluations", 403)
                return

            action_raw = (body.get("verdict") or body.get("action") or "").upper().strip()
            comments = body.get("comments", "").strip()

            conn = db.get_db()
            ev = conn.execute("SELECT e.*, i.serial_number, i.accuracy_class FROM evaluations e JOIN instruments i ON e.instrument_id = i.id WHERE e.id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            now = datetime.datetime.now().isoformat()

            if action_raw in ("UNDER_REVIEW", "INSPECT"):
                conn.execute("""
                UPDATE evaluations SET status = 'UNDER_REVIEW', reviewer_id = ?, updated_at = ? WHERE id = ?
                """, (user["sub"], now, eval_id))
                conn.commit()
                conn.close()
                db.log_audit(user["sub"], "REVIEW_INSPECT", "EVALUATION", eval_id, {"status": "UNDER_REVIEW"}, self.client_address[0])
                self.send_json({"success": True, "status": "UNDER_REVIEW", "message": "Evaluation marked as under review"})
                return

            elif action_raw in ("APPROVE", "APPROVED"):
                new_status = "APPROVED"
                cert_no = f"CERT-DL-2026-{ev['serial_number'].replace('/', '').replace('-', '')[-6:]}"
                today_str = now[:10]
                next_year_str = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')

                conn.execute("""
                UPDATE evaluations SET 
                    status = 'APPROVED', reviewer_id = ?, review_comments = ?, certificate_number = ?,
                    reviewed_at = ?, updated_at = ?
                WHERE id = ?
                """, (user["sub"], comments or "OIML R-76 statutory requirements verified. Approved.", cert_no, now, now, eval_id))

                conn.execute("""
                UPDATE instruments SET 
                    status = 'VERIFIED', last_verified_at = ?, next_verification_due = ?, updated_at = ?
                WHERE id = ?
                """, (today_str, next_year_str, now, ev["instrument_id"]))

                conn.commit()
                conn.close()

                db.log_audit(user["sub"], "REVIEW_APPROVE", "EVALUATION", eval_id, {"certificate_number": cert_no, "comments": comments}, self.client_address[0])
                self.send_json({"success": True, "verdict": "APPROVED", "status": "APPROVED", "certificate_number": cert_no, "message": "Evaluation approved successfully"})
                return

            elif action_raw in ("REJECT", "REJECTED", "RETURN", "RETURNED", "RETURN_FOR_CORRECTION"):
                if not comments:
                    conn.close()
                    self.send_error_json("Review remarks explaining the return/rejection reason are required", 400)
                    return

                new_status = "RETURNED" if "RETURN" in action_raw else "REJECTED"
                conn.execute("""
                UPDATE evaluations SET 
                    status = ?, reviewer_id = ?, review_comments = ?, reviewed_at = ?, updated_at = ?
                WHERE id = ?
                """, (new_status, user["sub"], comments, now, now, eval_id))

                conn.execute("""
                UPDATE instruments SET status = 'PENDING_VERIFICATION', updated_at = ? WHERE id = ?
                """, (now, ev["instrument_id"]))

                conn.commit()
                conn.close()

                audit_act = "REVIEW_RETURN" if new_status == "RETURNED" else "REVIEW_REJECT"
                db.log_audit(user["sub"], audit_act, "EVALUATION", eval_id, {"status": new_status, "comments": comments}, self.client_address[0])
                self.send_json({"success": True, "verdict": new_status, "status": new_status, "message": f"Evaluation returned for correction ({new_status})"})
                return

            else:
                conn.close()
                self.send_error_json("Invalid review action. Must be 'APPROVE', 'REJECT', 'RETURN', or 'UNDER_REVIEW'", 400)
                return

        # 8. Real Attachment Upload: POST /api/evaluations/<id>/attachments
        elif path.startswith("/api/evaluations/") and path.endswith("/attachments"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user:
                self.send_error_json("Unauthorized: Authentication required", 401)
                return

            conn = db.get_db()
            # Link attachment to evaluation & its instrument
            ev = conn.execute("""
            SELECT e.id, e.instrument_id, i.owner_id 
            FROM evaluations e 
            JOIN instruments i ON e.instrument_id = i.id 
            WHERE e.id = ?
            """, (eval_id,)).fetchone()

            instrument_id = None
            if ev:
                instrument_id = ev["instrument_id"]
                if user["role"] == "OWNER" and ev["owner_id"] != user["sub"]:
                    conn.close()
                    self.send_error_json("Access denied: You do not own the instrument for this evaluation", 403)
                    return
            else:
                # Check if eval_id was an instrument ID directly
                inst = conn.execute("SELECT id, owner_id FROM instruments WHERE id = ?", (eval_id,)).fetchone()
                if inst:
                    instrument_id = inst["id"]
                    if user["role"] == "OWNER" and inst["owner_id"] != user["sub"]:
                        conn.close()
                        self.send_error_json("Access denied: Not your instrument", 403)
                        return
                else:
                    conn.close()
                    self.send_error_json("Evaluation not found", 404)
                    return

            original_name = (body.get("filename") or body.get("file_name") or "").strip()
            file_data_base64 = body.get("file_data")
            description = (body.get("description") or "").strip()
            mime_type = body.get("mime_type") or "application/octet-stream"

            if not original_name:
                conn.close()
                self.send_error_json("Filename is required", 400)
                return

            if not file_data_base64:
                conn.close()
                self.send_error_json("Empty file data: File content is required", 400)
                return

            # Basic File Validation: Extension checks
            safe_ext = os.path.splitext(original_name)[1].lower()
            if not safe_ext:
                conn.close()
                self.send_error_json("File must have a valid extension", 400)
                return

            DANGEROUS_EXTENSIONS = {
                ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".py", ".php",
                ".pl", ".dll", ".scr", ".msi", ".jar", ".com", ".hta", ".bin", ".iso",
                ".wsf", ".reg", ".elf", ".pif", ".c", ".cpp", ".pyw"
            }
            if safe_ext in DANGEROUS_EXTENSIONS:
                conn.close()
                self.send_error_json(f"Dangerous file type '{safe_ext}' is forbidden for security", 400)
                return

            ALLOWED_EXTENSIONS = {
                ".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx", ".xls", ".txt", ".docx", ".doc"
            }
            if safe_ext not in ALLOWED_EXTENSIONS:
                conn.close()
                self.send_error_json(f"Unsupported file type '{safe_ext}'. Allowed formats: PDF, PNG, JPG/JPEG, CSV, XLSX, TXT, DOCX", 400)
                return

            # Decode base64 payload
            try:
                import base64
                file_bytes = base64.b64decode(file_data_base64)
            except Exception:
                conn.close()
                self.send_error_json("Invalid base64 payload", 400)
                return

            # Size limits: 1 byte to 10 MB
            if len(file_bytes) == 0:
                conn.close()
                self.send_error_json("Empty file cannot be uploaded", 400)
                return

            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
            if len(file_bytes) > MAX_FILE_SIZE:
                conn.close()
                self.send_error_json("File size exceeds maximum allowed limit of 10 MB", 400)
                return

            # Content signature / magic bytes validation
            if safe_ext == ".pdf" and not file_bytes.startswith(b"%PDF-"):
                conn.close()
                self.send_error_json("Invalid file content: Not a valid PDF document", 400)
                return
            elif safe_ext == ".png" and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                conn.close()
                self.send_error_json("Invalid file content: Not a valid PNG image", 400)
                return
            elif safe_ext in (".jpg", ".jpeg") and not file_bytes.startswith(b"\xff\xd8\xff"):
                conn.close()
                self.send_error_json("Invalid file content: Not a valid JPEG image", 400)
                return
            elif safe_ext in (".txt", ".csv") and b"\x00" in file_bytes[:1024]:
                conn.close()
                self.send_error_json("Invalid file content: Binary data detected in text file", 400)
                return

            att_id = f"att_{secrets.token_hex(6)}"
            saved_filename = f"{att_id}{safe_ext}"
            file_path = UPLOADS_DIR / saved_filename

            with open(file_path, "wb") as f:
                f.write(file_bytes)

            file_hash = hashlib.sha256(file_bytes).hexdigest()
            now = datetime.datetime.now().isoformat()

            conn.execute("""
            INSERT INTO attachments (
                id, evaluation_id, instrument_id, uploader_id, filename, original_name, file_path,
                file_size, mime_type, file_hash, description, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                att_id, ev["id"] if ev else None, instrument_id, user["sub"], saved_filename, original_name,
                str(file_path), len(file_bytes), mime_type, file_hash, description or "Metrological test attachment", now
            ))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "UPLOAD_ATTACHMENT", "ATTACHMENT", att_id, {
                "filename": original_name,
                "file_size": len(file_bytes),
                "eval_id": eval_id,
                "instrument_id": instrument_id
            }, self.client_address[0])

            self.send_json({
                "success": True,
                "attachment_id": att_id,
                "filename": original_name,
                "file_size": len(file_bytes),
                "file_hash": file_hash,
                "evaluation_id": ev["id"] if ev else None,
                "instrument_id": instrument_id,
                "message": f"Attachment '{original_name}' uploaded successfully"
            }, 201)
            return

        # 9. Real Report Workflow: Generate Official Statutory PDF Report & Store Metadata
        elif (path.startswith("/api/evaluations/") and path.endswith("/generate_pdf")) or path == "/api/generate_pdf":
            user = self.get_auth_user()
            if not user:
                self.send_error_json("Unauthorized: Authentication required", 401)
                return

            if path == "/api/generate_pdf":
                eval_id = (body.get("evaluation_id") or body.get("report_id") or body.get("id") or "").strip()
                if not eval_id:
                    self.send_error_json("Evaluation ID is required to generate official statutory report. Statutory review and approval is required.", 400)
                    return
            else:
                eval_id = path.split("/")[3]

            conn = db.get_db()
            ev = conn.execute("""
            SELECT e.*, i.*,
                   u_ins.full_name as inspector_name, u_ins.badge_id as inspector_badge,
                   u_rev.full_name as reviewer_name, u_rev.badge_id as reviewer_badge
            FROM evaluations e
            JOIN instruments i ON e.instrument_id = i.id
            LEFT JOIN users u_ins ON e.inspector_id = u_ins.id
            LEFT JOIN users u_rev ON e.reviewer_id = u_rev.id
            WHERE e.id = ?
            """, (eval_id,)).fetchone()

            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if user["role"] == "OWNER" and ev["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access forbidden: You do not own this instrument", 403)
                return

            # Required Approval Status Constraint: Only APPROVED evaluations can be issued final statutory reports
            if ev["status"] != "APPROVED":
                conn.close()
                self.send_error_json(f"Cannot generate final statutory report: Evaluation status is '{ev['status']}'. Only APPROVED evaluations can receive final statutory reports.", 400)
                return

            readings = conn.execute("SELECT * FROM test_readings WHERE evaluation_id = ? ORDER BY rowid ASC", (eval_id,)).fetchall()
            if not readings or len(readings) == 0:
                conn.close()
                self.send_error_json("Cannot generate final report: Zero test readings recorded for this evaluation.", 400)
                return

            serial_clean = ev["serial_number"].replace("/", "_").replace("-", "_").replace(" ", "_")
            pdf_filename = f"report_{serial_clean}_{eval_id}.pdf"
            pdf_path = REPORTS_DIR / pdf_filename

            report_id = (ev["certificate_number"] or f"REP-{serial_clean}-{eval_id[-6:]}").replace("/", "_").replace(":", "_").replace(" ", "_")
            cert_no = ev["certificate_number"] or report_id

            report_data = {
                "report_id": report_id,
                "certificate_number": cert_no,
                "instrument": {
                    "manufacturer": ev["manufacturer"],
                    "model": ev["model"],
                    "serial_number": ev["serial_number"],
                    "accuracy_class": ev["accuracy_class"],
                    "max_capacity": float(ev["max_capacity"]),
                    "min_capacity": float(ev["min_capacity"]),
                    "verification_scale_interval_e": float(ev["e_interval"]),
                    "actual_scale_interval_d": float(ev["d_interval"] or ev["e_interval"]),
                    "unit": ev["unit"] or "kg"
                },
                "test_conditions": {
                    "inspector_name": ev["inspector_name"] or "Authorized Officer",
                    "inspector_id": ev["inspector_badge"] or ev["inspector_id"] or "INS-001",
                    "reviewer_name": ev["reviewer_name"] or "Central Legal Metrology Board",
                    "location": ev["test_location"],
                    "temperature": float(ev["temperature_c"]),
                    "humidity": float(ev["humidity_percent"]),
                    "pressure": float(ev["pressure_hpa"]),
                    "gravity": float(ev["gravity_mps2"]),
                    "test_date": ev["test_date"]
                },
                "generated_at": ev["created_at"],
                "conformity": ev["conformity"] == 1,
                "hash": ev["verification_hash"] or "OIML-R76-VERIFIED",
                "calculations": {
                    "compliance_score": float(ev["compliance_score"] or 100.0),
                    "risk_level": ev["risk_level"] or "LOW",
                    "repeatability": float(ev["repeatability_error"] or 0.0),
                    "linearity": float(ev["linearity_error"] or 0.0),
                    "hysteresis": float(ev["hysteresis_error"] or 0.0),
                    "eccentricity": float(ev["eccentricity_error"] or 0.0),
                    "combined_uncertainty": float(ev["combined_uncertainty"] or 0.0),
                    "expanded_uncertainty": float(ev["expanded_uncertainty"] or 0.0),
                    "point_results": [
                        {
                            "load_kg": float(r["load_val"]),
                            "reading": float(r["reading"]),
                            "direction": r["direction"],
                            "position": r["position"],
                            "repeat_number": r["repeat_number"],
                            "test_type": r["test_type"],
                            "error_kg": float(r["error"]),
                            "mpe_kg": float(r["mpe"]),
                            "passed": r["passed"] == 1
                        }
                        for r in readings
                    ]
                }
            }

            try:
                # Ensure QR code image is generated first
                qr_path = REPORTS_DIR / f"qr_{eval_id}.png"
                proto.generate_qr(report_data, str(qr_path))
                proto.generate_pdf_report(report_data, str(pdf_path))

                pdf_url = f"/api/reports/{pdf_filename}"
                now = datetime.datetime.now().isoformat()

                # Store report metadata persistently in reports table
                conn.execute("""
                INSERT OR REPLACE INTO reports (
                    report_id, evaluation_id, instrument_id, instrument_serial, instrument_model,
                    capacity, class, combined_error, mpe, conformity, compliance_score, risk_level,
                    created_at, inspector_name, inspector_id, pdf_filename, pdf_url, certificate_number, json_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id, eval_id, ev["instrument_id"], ev["serial_number"], ev["model"],
                    float(ev["max_capacity"]), ev["accuracy_class"], float(ev["combined_uncertainty"] or 0.0),
                    float(readings[0]["mpe"]) if readings else 0.0, 1 if ev["conformity"] == 1 else 0,
                    float(ev["compliance_score"] or 100.0), ev["risk_level"] or "LOW",
                    now, ev["inspector_name"] or "Authorized Officer", ev["inspector_id"],
                    pdf_filename, pdf_url, cert_no, json.dumps(report_data).encode("utf-8")
                ))
                conn.commit()
                conn.close()

                db.log_audit(user["sub"], "GENERATE_REPORT", "REPORT", report_id, {
                    "evaluation_id": eval_id,
                    "instrument_id": ev["instrument_id"],
                    "serial_number": ev["serial_number"],
                    "certificate_number": cert_no,
                    "pdf": pdf_filename
                }, self.client_address[0])

                self.send_json({
                    "success": True,
                    "report_id": report_id,
                    "evaluation_id": eval_id,
                    "instrument_id": ev["instrument_id"],
                    "certificate_number": cert_no,
                    "pdf_url": pdf_url,
                    "report_url": pdf_url,
                    "filename": pdf_filename,
                    "created_at": now,
                    "message": "Final statutory report generated and stored permanently in database"
                })
            except Exception as e:
                conn.close()
                self.send_error_json(f"PDF Generation failed: {str(e)}", 500)
            return

        # 10. Direct Save to DB Bridge (/api/save_audit)
        elif path == "/api/save_audit":
            user = self.get_auth_user()
            inspector_id = user["sub"] if user else "usr_inspector_01"
            report_id = body.get("report_id") or f"eval_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
            inst_data = body.get("instrument", {})
            cond_data = body.get("test_conditions", {})
            calcs = body.get("calculations", {})

            conn = db.get_db()
            serial = inst_data.get("serialNumber") or inst_data.get("serial_number")
            inst_row = None
            if serial:
                inst_row = conn.execute("SELECT id FROM instruments WHERE serial_number = ?", (serial,)).fetchone()
            
            if inst_row:
                inst_id = inst_row["id"]
            else:
                inst_id = f"inst_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
                now_str = datetime.datetime.now().isoformat()
                conn.execute("""
                INSERT INTO instruments (
                    id, serial_number, model, manufacturer, accuracy_class, max_capacity,
                    min_capacity, e_interval, d_interval, unit, tare_capacity, type_approval_no,
                    owner_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_VERIFICATION', ?, ?)
                """, (
                    inst_id, serial or f"SN-{secrets.token_hex(4)}",
                    inst_data.get("model", "Bench Scale"),
                    inst_data.get("manufacturer", "Manufacturer"),
                    inst_data.get("accuracyClass", "III"),
                    float(inst_data.get("maxCapacity", 15.0)),
                    float(inst_data.get("minCapacity", 0.04)),
                    float(inst_data.get("verificationScaleIntervalE", 0.005)),
                    float(inst_data.get("actualScaleIntervalD", 0.005)),
                    inst_data.get("unit", "kg"),
                    float(inst_data.get("tareCapacity", 15.0)),
                    inst_data.get("typeApprovalNumber", ""),
                    inspector_id, now_str, now_str
                ))

            now = datetime.datetime.now().isoformat()
            existing_ev = conn.execute("SELECT id FROM evaluations WHERE id = ?", (report_id,)).fetchone()
            if existing_ev:
                conn.execute("""
                UPDATE evaluations SET
                    instrument_id = ?, test_location = ?, temperature_c = ?, humidity_percent = ?,
                    pressure_hpa = ?, gravity_mps2 = ?, combined_uncertainty = ?, compliance_score = ?,
                    risk_level = ?, conformity = ?, verification_hash = ?, updated_at = ?
                WHERE id = ?
                """, (
                    inst_id, cond_data.get("location", "Regional Reference Standards Laboratory"),
                    float(cond_data.get("temperature", 25.0)), float(cond_data.get("humidity", 55.0)),
                    float(cond_data.get("pressure", 1013.25)), float(cond_data.get("gravity", 9.7915)),
                    float(calcs.get("combined_uncertainty", 0.0)), float(calcs.get("compliance_score", 100.0)),
                    calcs.get("risk_level", "LOW"), 1 if body.get("conformity") else 0,
                    calcs.get("verification_hash", ""), now, report_id
                ))
            else:
                conn.execute("""
                INSERT INTO evaluations (
                    id, instrument_id, inspector_id, status, test_date, test_location,
                    temperature_c, humidity_percent, pressure_hpa, gravity_mps2,
                    combined_uncertainty, compliance_score, risk_level, conformity,
                    verification_hash, created_at, updated_at
                ) VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id, inst_id, inspector_id, now[:10],
                    cond_data.get("location", "Regional Reference Standards Laboratory"),
                    float(cond_data.get("temperature", 25.0)), float(cond_data.get("humidity", 55.0)),
                    float(cond_data.get("pressure", 1013.25)), float(cond_data.get("gravity", 9.7915)),
                    float(calcs.get("combined_uncertainty", 0.0)), float(calcs.get("compliance_score", 100.0)),
                    calcs.get("risk_level", "LOW"), 1 if body.get("conformity") else 0,
                    calcs.get("verification_hash", ""), now, now
                ))

            conn.commit()
            conn.close()
            db.log_audit(inspector_id, "SAVE_AUDIT", "EVALUATION", report_id, {}, self.client_address[0])
            self.send_json({"success": True, "evaluation_id": report_id, "message": "Saved evaluation permanently to database"})
            return

        else:
            self.send_error(404, "Not Found")

    # =========================================================================
    # HTTP PUT HANDLER
    # =========================================================================
    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        if path.startswith("/api/instruments/"):
            inst_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR", "OWNER"):
                self.send_error_json("Unauthorized", 403)
                return

            conn = db.get_db()
            inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (inst_id,)).fetchone()
            if not inst:
                conn.close()
                self.send_error_json("Instrument not found", 404)
                return

            if user["role"] == "OWNER" and inst["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access denied: Not your instrument", 403)
                return

            now = datetime.datetime.now().isoformat()
            model = body.get("model", inst["model"])
            manufacturer = body.get("manufacturer", inst["manufacturer"])
            type_approval = body.get("type_approval_no", inst["type_approval_no"])
            max_capacity = float(body.get("max_capacity", inst["max_capacity"]))
            min_capacity = float(body.get("min_capacity", inst["min_capacity"]))
            e_interval = float(body.get("e_interval", inst["e_interval"]))
            accuracy_class = body.get("accuracy_class", inst["accuracy_class"])

            conn.execute("""
            UPDATE instruments SET
                model = ?, manufacturer = ?, type_approval_no = ?, max_capacity = ?,
                min_capacity = ?, e_interval = ?, accuracy_class = ?, updated_at = ?
            WHERE id = ?
            """, (model, manufacturer, type_approval, max_capacity, min_capacity, e_interval, accuracy_class, now, inst_id))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "UPDATE", "INSTRUMENT", inst_id, {"model": model}, self.client_address[0])
            self.send_json({"success": True, "message": "Instrument updated successfully"})
            return

        elif path.startswith("/api/evaluations/"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Unauthorized", 403)
                return

            conn = db.get_db()
            ev = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if ev["status"] == "APPROVED":
                conn.close()
                self.send_error_json("Cannot modify finalized approved evaluation", 400)
                return

            now = datetime.datetime.now().isoformat()
            
            # Check instrument relationship - cannot disconnect or set invalid instrument
            target_inst_id = body.get("instrument_id")
            if target_inst_id and target_inst_id != ev["instrument_id"]:
                inst_check = conn.execute("SELECT id FROM instruments WHERE id = ?", (target_inst_id,)).fetchone()
                if not inst_check:
                    conn.close()
                    self.send_error_json("Target instrument does not exist. Evaluation cannot be disconnected from a valid instrument.", 400)
                    return
                instrument_id = target_inst_id
            else:
                instrument_id = ev["instrument_id"]

            test_date = body.get("test_date", ev["test_date"])
            test_location = body.get("test_location", ev["test_location"])
            temp_c = float(body.get("temperature_c", ev["temperature_c"]))
            humidity = float(body.get("humidity_percent", ev["humidity_percent"]))
            pressure = float(body.get("pressure_hpa", ev["pressure_hpa"]))
            gravity = float(body.get("gravity_mps2", ev["gravity_mps2"]))
            ref_std = body.get("reference_standard", ev["reference_standard"])
            trace_no = body.get("standards_traceability_no", ev["standards_traceability_no"])
            status = body.get("status", ev["status"])

            conn.execute("""
            UPDATE evaluations SET
                instrument_id = ?, test_date = ?, test_location = ?, temperature_c = ?,
                humidity_percent = ?, pressure_hpa = ?, gravity_mps2 = ?,
                reference_standard = ?, standards_traceability_no = ?, status = ?,
                updated_at = ?
            WHERE id = ?
            """, (instrument_id, test_date, test_location, temp_c, humidity, pressure, gravity, ref_std, trace_no, status, now, eval_id))

            # Store updated readings if provided
            readings_list = body.get("readings")
            if readings_list is not None and isinstance(readings_list, list):
                inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
                inst_dict = {
                    "max_capacity": inst["max_capacity"],
                    "e_interval": inst["e_interval"],
                    "accuracy_class": inst["accuracy_class"],
                    "serial_number": inst["serial_number"],
                    "model": inst["model"]
                }
                results = backend_oiml.validate_oiml_compliance(inst_dict, readings_list)
                conn.execute("DELETE FROM test_readings WHERE evaluation_id = ?", (eval_id,))
                for pt in results["point_results"]:
                    rd_id = f"tr_{secrets.token_hex(6)}"
                    test_type = pt.get("test_type", "LOAD")
                    if test_type not in ("LOAD", "ECCENTRICITY", "REPEATABILITY"):
                        test_type = "LOAD"
                    pos = pt.get("position", "center")
                    if pos not in ('center', 'front-left', 'front-right', 'back-left', 'back-right'):
                        pos = 'center'
                    conn.execute("""
                    INSERT INTO test_readings (
                        id, evaluation_id, test_type, load_val, reading, error, mpe, ratio, passed,
                        direction, position, repeat_number, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rd_id, eval_id, test_type, pt["load"], pt["reading"], pt["error"],
                        pt["mpe"], pt["ratio"], 1 if pt["passed"] else 0,
                        pt["direction"], pos, pt["repeat_number"], now
                    ))
                conn.execute("""
                UPDATE evaluations SET
                    repeatability_error = ?, linearity_error = ?, hysteresis_error = ?,
                    eccentricity_error = ?, combined_uncertainty = ?, expanded_uncertainty = ?,
                    compliance_score = ?, risk_level = ?, conformity = ?, verification_hash = ?
                WHERE id = ?
                """, (
                    results["repeatability_error"], results["linearity_error"], results["hysteresis_error"],
                    results["eccentricity_error"], results["combined_uncertainty"], results["expanded_uncertainty"],
                    results["compliance_score"], results["risk_level"], results["conformity"], results["verification_hash"],
                    eval_id
                ))

            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "UPDATE", "EVALUATION", eval_id, {"status": status}, self.client_address[0])
            self.send_json({"success": True, "message": "Evaluation updated permanently", "evaluation_id": eval_id, "status": status})
            return

        else:
            self.send_error(404, "Not Found")

    # =========================================================================
    # HTTP DELETE HANDLER
    # =========================================================================
    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/instruments/"):
            inst_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "OWNER"):
                self.send_error_json("Unauthorized: Requires Admin or Owner role", 403)
                return

            conn = db.get_db()
            inst = conn.execute("SELECT * FROM instruments WHERE id = ?", (inst_id,)).fetchone()
            if not inst:
                conn.close()
                self.send_error_json("Instrument not found", 404)
                return

            if user["role"] == "OWNER" and inst["owner_id"] != user["sub"]:
                conn.close()
                self.send_error_json("Access denied: Not your instrument", 403)
                return

            evals = conn.execute("SELECT id FROM evaluations WHERE instrument_id = ?", (inst_id,)).fetchall()
            for ev_row in evals:
                conn.execute("DELETE FROM test_readings WHERE evaluation_id = ?", (ev_row["id"],))
                conn.execute("DELETE FROM attachments WHERE evaluation_id = ?", (ev_row["id"],))
            conn.execute("DELETE FROM evaluations WHERE instrument_id = ?", (inst_id,))
            conn.execute("DELETE FROM instruments WHERE id = ?", (inst_id,))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "DELETE", "INSTRUMENT", inst_id, {"serial": inst["serial_number"]}, self.client_address[0])
            self.send_json({"success": True, "message": "Instrument deleted"})
            return

        elif path.startswith("/api/evaluations/"):
            eval_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Unauthorized", 403)
                return

            conn = db.get_db()
            ev = conn.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,)).fetchone()
            if not ev:
                conn.close()
                self.send_error_json("Evaluation not found", 404)
                return

            if ev["status"] == "APPROVED":
                conn.close()
                self.send_error_json("Cannot delete approved evaluation record", 400)
                return

            conn.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "DELETE", "EVALUATION", eval_id, {}, self.client_address[0])
            self.send_json({"success": True, "message": "Evaluation deleted"})
            return

        elif path.startswith("/api/attachments/"):
            att_id = path.split("/")[3]
            user = self.get_auth_user()
            if not user or user["role"] not in ("ADMIN", "INSPECTOR"):
                self.send_error_json("Unauthorized", 403)
                return

            conn = db.get_db()
            att = conn.execute("SELECT * FROM attachments WHERE id = ?", (att_id,)).fetchone()
            if not att:
                conn.close()
                self.send_error_json("Attachment not found", 404)
                return

            disk_path = Path(att["file_path"])
            if not disk_path.exists():
                disk_path = UPLOADS_DIR / att["filename"]
            if disk_path.exists():
                try:
                    os.remove(disk_path)
                except Exception:
                    pass

            conn.execute("DELETE FROM attachments WHERE id = ?", (att_id,))
            conn.commit()
            conn.close()

            db.log_audit(user["sub"], "DELETE", "ATTACHMENT", att_id, {"filename": att["original_name"]}, self.client_address[0])
            self.send_json({"success": True, "message": "Attachment deleted successfully"})
            return

        else:
            self.send_error(404, "Not Found")

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, MetrolabServerHandler)
    print(f"===========================================================")
    print(f"  Metrolab Enterprise Server (SIH-26035) running on port {PORT}")
    print(f"  API: http://localhost:{PORT}/api/status")
    print(f"  Web: http://localhost:{PORT}/")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server.")

if __name__ == "__main__":
    run_server()
