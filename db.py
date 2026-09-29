"""
Metrolab Database Module
Manages SQLite database schema, connections, and seeding for SIH-26035 Legal Metrology.
"""

import os
import sqlite3
import hashlib
import hmac
import secrets
import json
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = str(BASE_DIR / "nawi_audit.db")
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return pwd_hash, salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    pwd_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(pwd_hash, expected_hash)

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('ADMIN', 'INSPECTOR', 'REVIEWER', 'OWNER')),
        organization TEXT,
        badge_id TEXT,
        created_at TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS instruments (
        id TEXT PRIMARY KEY,
        serial_number TEXT UNIQUE NOT NULL,
        model TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        accuracy_class TEXT NOT NULL CHECK(accuracy_class IN ('I', 'II', 'III', 'IIII')),
        max_capacity REAL NOT NULL,
        min_capacity REAL NOT NULL,
        e_interval REAL NOT NULL,
        d_interval REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'kg',
        tare_capacity REAL NOT NULL,
        type_approval_no TEXT,
        year_of_manufacture INTEGER,
        country_of_origin TEXT,
        owner_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'REGISTERED' CHECK(status IN ('REGISTERED', 'PENDING_VERIFICATION', 'VERIFIED', 'REJECTED', 'EXPIRED')),
        last_verified_at TEXT,
        next_verification_due TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (owner_id) REFERENCES users(id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        id TEXT PRIMARY KEY,
        instrument_id TEXT NOT NULL,
        inspector_id TEXT NOT NULL,
        reviewer_id TEXT,
        status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'RETURNED')),
        test_date TEXT NOT NULL,
        test_location TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        humidity_percent REAL NOT NULL,
        pressure_hpa REAL NOT NULL,
        gravity_mps2 REAL NOT NULL DEFAULT 9.7915,
        reference_standard TEXT,
        standards_traceability_no TEXT,
        
        repeatability_error REAL DEFAULT 0.0,
        linearity_error REAL DEFAULT 0.0,
        hysteresis_error REAL DEFAULT 0.0,
        eccentricity_error REAL DEFAULT 0.0,
        combined_uncertainty REAL DEFAULT 0.0,
        expanded_uncertainty REAL DEFAULT 0.0,
        compliance_score REAL DEFAULT 0.0,
        risk_level TEXT DEFAULT 'LOW',
        conformity INTEGER DEFAULT 0,
        verification_hash TEXT,
        certificate_number TEXT,
        
        review_comments TEXT,
        reviewed_at TEXT,
        submitted_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id),
        FOREIGN KEY (inspector_id) REFERENCES users(id),
        FOREIGN KEY (reviewer_id) REFERENCES users(id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS test_readings (
        id TEXT PRIMARY KEY,
        evaluation_id TEXT NOT NULL,
        test_type TEXT NOT NULL CHECK(test_type IN ('LOAD', 'ECCENTRICITY', 'REPEATABILITY')),
        load_val REAL NOT NULL,
        reading REAL NOT NULL,
        error REAL NOT NULL,
        mpe REAL NOT NULL,
        ratio REAL NOT NULL,
        passed INTEGER NOT NULL,
        direction TEXT NOT NULL CHECK(direction IN ('increasing', 'decreasing')),
        position TEXT NOT NULL DEFAULT 'center' CHECK(position IN ('center', 'front-left', 'front-right', 'back-left', 'back-right')),
        repeat_number INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS attachments (
        id TEXT PRIMARY KEY,
        evaluation_id TEXT,
        instrument_id TEXT,
        uploader_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        description TEXT,
        uploaded_at TEXT NOT NULL,
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id) ON DELETE CASCADE,
        FOREIGN KEY (uploader_id) REFERENCES users(id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        details_json TEXT,
        ip_address TEXT,
        timestamp TEXT NOT NULL,
        user_role TEXT,
        user_name TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        report_id TEXT PRIMARY KEY,
        evaluation_id TEXT,
        instrument_id TEXT,
        instrument_serial TEXT,
        instrument_model TEXT,
        capacity REAL,
        class TEXT,
        combined_error REAL,
        mpe REAL,
        conformity INTEGER,
        compliance_score REAL,
        risk_level TEXT,
        created_at TEXT,
        inspector_name TEXT,
        inspector_id TEXT,
        pdf_filename TEXT,
        pdf_url TEXT,
        certificate_number TEXT,
        json_data BLOB,
        FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
        FOREIGN KEY (instrument_id) REFERENCES instruments(id) ON DELETE CASCADE
    )
    ''')

    # Add missing columns to reports table if they do not exist
    c.execute("PRAGMA table_info(reports)")
    existing_rep_cols = {col[1] for col in c.fetchall()}
    for col_name, col_type in [
        ("evaluation_id", "TEXT"),
        ("instrument_id", "TEXT"),
        ("pdf_filename", "TEXT"),
        ("pdf_url", "TEXT"),
        ("certificate_number", "TEXT"),
    ]:
        if col_name not in existing_rep_cols:
            c.execute(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type}")

    # Add missing columns to audit_logs table if they do not exist
    c.execute("PRAGMA table_info(audit_logs)")
    existing_aud_cols = {col[1] for col in c.fetchall()}
    for col_name, col_type in [
        ("user_role", "TEXT"),
        ("user_name", "TEXT"),
    ]:
        if col_name not in existing_aud_cols:
            c.execute(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_type}")

    conn.commit()

    # Migrate evaluations table if 'RETURNED' is missing from status check constraint
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='evaluations'")
    ev_schema_row = c.fetchone()
    if ev_schema_row and "RETURNED" not in ev_schema_row[0]:
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute('''
        CREATE TABLE evaluations_temp (
            id TEXT PRIMARY KEY,
            instrument_id TEXT NOT NULL,
            inspector_id TEXT NOT NULL,
            reviewer_id TEXT,
            status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'RETURNED')),
            test_date TEXT NOT NULL,
            test_location TEXT NOT NULL,
            temperature_c REAL NOT NULL,
            humidity_percent REAL NOT NULL,
            pressure_hpa REAL NOT NULL,
            gravity_mps2 REAL NOT NULL DEFAULT 9.7915,
            reference_standard TEXT,
            standards_traceability_no TEXT,
            repeatability_error REAL DEFAULT 0.0,
            linearity_error REAL DEFAULT 0.0,
            hysteresis_error REAL DEFAULT 0.0,
            eccentricity_error REAL DEFAULT 0.0,
            combined_uncertainty REAL DEFAULT 0.0,
            expanded_uncertainty REAL DEFAULT 0.0,
            compliance_score REAL DEFAULT 0.0,
            risk_level TEXT DEFAULT 'LOW',
            conformity INTEGER DEFAULT 0,
            verification_hash TEXT,
            certificate_number TEXT,
            review_comments TEXT,
            reviewed_at TEXT,
            submitted_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (instrument_id) REFERENCES instruments(id),
            FOREIGN KEY (inspector_id) REFERENCES users(id),
            FOREIGN KEY (reviewer_id) REFERENCES users(id)
        )
        ''')
        c.execute("INSERT INTO evaluations_temp SELECT * FROM evaluations")
        c.execute("DROP TABLE evaluations")
        c.execute("ALTER TABLE evaluations_temp RENAME TO evaluations")
        c.execute("PRAGMA foreign_keys = ON")
        conn.commit()

    conn.close()

def log_audit(user_id: str, action: str, entity_type: str, entity_id: str = None, details: dict = None, ip_address: str = "127.0.0.1", user_role: str = None, user_name: str = None):
    try:
        conn = get_db()
        log_id = f"aud_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"

        # Automatically resolve user_role and user_name if missing
        if user_id and (not user_role or not user_name):
            try:
                urow = conn.execute("SELECT full_name, username, role FROM users WHERE id = ?", (user_id,)).fetchone()
                if urow:
                    user_role = user_role or urow["role"]
                    user_name = user_name or urow["full_name"] or urow["username"]
            except Exception:
                pass

        user_role = user_role or "SYSTEM"
        user_name = user_name or "System Administrator"

        conn.execute('''
        INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, details_json, ip_address, timestamp, user_role, user_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_id,
            user_id,
            action,
            entity_type,
            entity_id,
            json.dumps(details or {}, default=str),
            ip_address,
            datetime.datetime.now().isoformat(),
            user_role,
            user_name
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging audit: {e}")

def seed_database():
    conn = get_db()
    c = conn.cursor()

    now = datetime.datetime.now().isoformat()
    now_dt = datetime.datetime.now()
    next_year = (now_dt + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    expiry_soon = (now_dt + datetime.timedelta(days=18)).strftime('%Y-%m-%d')

    users_to_seed = [
        {
            "id": "usr_admin_01",
            "username": "admin",
            "email": "admin@metrolab.gov.in",
            "password": "Admin@123",
            "full_name": "Dr. V. K. Ramanathan",
            "role": "ADMIN",
            "organization": "Directorate of Legal Metrology HQ",
            "badge_id": "ADM-GOI-001"
        },
        {
            "id": "usr_inspector_01",
            "username": "rajesh_inspector",
            "email": "rajesh.sharma@metrolab.gov.in",
            "password": "Inspector@123",
            "full_name": "Rajesh Kumar Sharma",
            "role": "INSPECTOR",
            "organization": "Regional Reference Standards Laboratory (RRSL), New Delhi",
            "badge_id": "INS-DL-2024-0087"
        },
        {
            "id": "usr_reviewer_01",
            "username": "priya_reviewer",
            "email": "dr.priya.verma@metrolab.gov.in",
            "password": "Reviewer@123",
            "full_name": "Dr. Priya Verma",
            "role": "REVIEWER",
            "organization": "Central Verification & Review Board, New Delhi",
            "badge_id": "REV-DL-2021-0023"
        },
        {
            "id": "usr_owner_01",
            "username": "essae_owner",
            "email": "compliance@essae.com",
            "password": "Owner@123",
            "full_name": "Essae Teraoka Pvt. Ltd. (Metrology Rep)",
            "role": "OWNER",
            "organization": "Essae Teraoka Pvt. Ltd.",
            "badge_id": "MFR-IND-0471"
        },
        {
            "id": "usr_owner_02",
            "username": "avery_owner",
            "email": "regulatory@averyweigh-tronix.in",
            "password": "Owner@123",
            "full_name": "Avery Weigh-Tronix India Ltd.",
            "role": "OWNER",
            "organization": "Avery Weigh-Tronix India Ltd.",
            "badge_id": "MFR-IND-0881"
        },
        {
            "id": "usr_technician_alias",
            "username": "technician",
            "email": "technician@metrolab.gov.in",
            "password": "Technician@123",
            "full_name": "Rajesh Kumar (Technician)",
            "role": "INSPECTOR",
            "organization": "Regional Reference Standards Laboratory (RRSL)",
            "badge_id": "TECH-DL-2024-0087"
        },
        {
            "id": "usr_reviewer_alias",
            "username": "reviewer",
            "email": "reviewer@metrolab.gov.in",
            "password": "Reviewer@123",
            "full_name": "Dr. Priya Verma (Reviewer)",
            "role": "REVIEWER",
            "organization": "Central Verification & Review Board",
            "badge_id": "REV-DL-2021-0023"
        },
        {
            "id": "usr_owner_alias",
            "username": "owner",
            "email": "owner@metrolab.gov.in",
            "password": "Owner@123",
            "full_name": "Essae Digitronics (Instrument Owner)",
            "role": "OWNER",
            "organization": "Essae Teraoka Pvt. Ltd.",
            "badge_id": "MFR-IND-0471"
        }
    ]

    for u in users_to_seed:
        c.execute("SELECT id FROM users WHERE username = ?", (u["username"],))
        if not c.fetchone():
            p_hash, salt = hash_password(u["password"])
            c.execute('''
            INSERT INTO users (id, username, email, password_hash, salt, full_name, role, organization, badge_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (u["id"], u["username"], u["email"], p_hash, salt, u["full_name"], u["role"], u["organization"], u["badge_id"], now))

    instruments_to_seed = [
        {
            "id": "inst_essae_01",
            "serial_number": "ET-DS852-2026-0471",
            "model": "DS-852 Heavy-Duty Digital Scale",
            "manufacturer": "Essae Teraoka Pvt. Ltd.",
            "accuracy_class": "III",
            "max_capacity": 15.0,
            "min_capacity": 0.04,
            "e_interval": 0.005,
            "d_interval": 0.005,
            "unit": "kg",
            "tare_capacity": 15.0,
            "type_approval_no": "IND/LM/09/2026/0471",
            "year_of_manufacture": 2026,
            "country_of_origin": "India",
            "owner_id": "usr_owner_01",
            "status": "VERIFIED",
            "last_verified_at": now[:10],
            "next_verification_due": next_year
        },
        {
            "id": "inst_essae_02",
            "serial_number": "ET-DS415-2026-0912",
            "model": "DS-415 Bench Counting Scale",
            "manufacturer": "Essae Teraoka Pvt. Ltd.",
            "accuracy_class": "III",
            "max_capacity": 30.0,
            "min_capacity": 0.1,
            "e_interval": 0.01,
            "d_interval": 0.01,
            "unit": "kg",
            "tare_capacity": 30.0,
            "type_approval_no": "IND/LM/09/2026/0912",
            "year_of_manufacture": 2025,
            "country_of_origin": "India",
            "owner_id": "usr_owner_01",
            "status": "PENDING_VERIFICATION",
            "last_verified_at": "2025-10-15",
            "next_verification_due": expiry_soon
        },
        {
            "id": "inst_sartorius_01",
            "serial_number": "SAR-2026-99042",
            "model": "Cubis II Ultra-Microbalance MCA2.7S",
            "manufacturer": "Sartorius Lab Instruments GmbH",
            "accuracy_class": "I",
            "max_capacity": 0.0021,
            "min_capacity": 0.00001,
            "e_interval": 0.000001,
            "d_interval": 0.0000001,
            "unit": "kg",
            "tare_capacity": 0.0021,
            "type_approval_no": "PTB-1.12-4091",
            "year_of_manufacture": 2025,
            "country_of_origin": "Germany",
            "owner_id": "usr_owner_01",
            "status": "VERIFIED",
            "last_verified_at": now[:10],
            "next_verification_due": next_year
        },
        {
            "id": "inst_avery_01",
            "serial_number": "AWT-WB-50T-2026-88",
            "model": "BMS-T Pitless Heavy Weighbridge",
            "manufacturer": "Avery Weigh-Tronix India Ltd.",
            "accuracy_class": "IIII",
            "max_capacity": 50000.0,
            "min_capacity": 400.0,
            "e_interval": 20.0,
            "d_interval": 20.0,
            "unit": "kg",
            "tare_capacity": 50000.0,
            "type_approval_no": "IND/LM/WB/2026/0881",
            "year_of_manufacture": 2026,
            "country_of_origin": "India",
            "owner_id": "usr_owner_02",
            "status": "VERIFIED",
            "last_verified_at": now[:10],
            "next_verification_due": next_year
        }
    ]

    for inst in instruments_to_seed:
        c.execute("SELECT id FROM instruments WHERE serial_number = ?", (inst["serial_number"],))
        if not c.fetchone():
            c.execute('''
            INSERT INTO instruments (
                id, serial_number, model, manufacturer, accuracy_class, max_capacity, min_capacity,
                e_interval, d_interval, unit, tare_capacity, type_approval_no, year_of_manufacture,
                country_of_origin, owner_id, status, last_verified_at, next_verification_due, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inst["id"], inst["serial_number"], inst["model"], inst["manufacturer"], inst["accuracy_class"],
                inst["max_capacity"], inst["min_capacity"], inst["e_interval"], inst["d_interval"], inst["unit"],
                inst["tare_capacity"], inst["type_approval_no"], inst["year_of_manufacture"], inst["country_of_origin"],
                inst["owner_id"], inst["status"], inst["last_verified_at"], inst["next_verification_due"], now, now
            ))

    c.execute("SELECT id FROM evaluations WHERE id = 'eval_demo_01'")
    if not c.fetchone():
        c.execute('''
        INSERT INTO evaluations (
            id, instrument_id, inspector_id, reviewer_id, status, test_date, test_location,
            temperature_c, humidity_percent, pressure_hpa, gravity_mps2, reference_standard,
            standards_traceability_no, repeatability_error, linearity_error, hysteresis_error,
            eccentricity_error, combined_uncertainty, expanded_uncertainty, compliance_score,
            risk_level, conformity, verification_hash, certificate_number, review_comments,
            reviewed_at, submitted_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "eval_demo_01", "inst_essae_01", "usr_inspector_01", "usr_reviewer_01", "APPROVED",
            now[:10], "Regional Reference Standards Laboratory, New Delhi",
            25.2, 58.0, 1012.5, 9.7915, "OIML Class F1 Cast Iron & Stainless Steel Weights",
            "NPLI/LM/MASS/2026/0942", 0.000090, 0.000467, 0.000076, 0.000267,
            0.000550, 0.001100, 94.64, "LOW", 1, "OIML-R76-2026-E471-DS852",
            "CERT-DL-2026-0471", "Instrument satisfies all OIML R-76 statutory limits. Approved for 1-year verification stamp.",
            now, now, now, now
        ))

        readings_sample = [
            ("eval_demo_01", "LOAD", 0.0, 0.0, 0.0, 0.0025, 0.0, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 1.0, 1.002, 0.002, 0.0025, 0.8, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 3.0, 3.003, 0.003, 0.0050, 0.6, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 5.0, 5.004, 0.004, 0.0050, 0.8, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 7.5, 7.503, 0.003, 0.0050, 0.6, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 10.0, 10.004, 0.004, 0.0050, 0.8, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 12.0, 12.004, 0.004, 0.0075, 0.53, 1, "increasing", "center", 1),
            ("eval_demo_01", "LOAD", 15.0, 15.006, 0.006, 0.0075, 0.8, 1, "increasing", "center", 1),
            ("eval_demo_01", "REPEATABILITY", 5.0, 5.003, 0.003, 0.0050, 0.6, 1, "increasing", "center", 2),
            ("eval_demo_01", "REPEATABILITY", 5.0, 5.005, 0.005, 0.0050, 1.0, 1, "increasing", "center", 3),
            ("eval_demo_01", "ECCENTRICITY", 5.0, 5.004, 0.004, 0.0050, 0.8, 1, "increasing", "front-left", 1),
            ("eval_demo_01", "ECCENTRICITY", 5.0, 5.003, 0.003, 0.0050, 0.6, 1, "increasing", "front-right", 1),
            ("eval_demo_01", "ECCENTRICITY", 5.0, 5.005, 0.005, 0.0050, 1.0, 1, "increasing", "back-left", 1),
            ("eval_demo_01", "ECCENTRICITY", 5.0, 5.002, 0.002, 0.0050, 0.4, 1, "increasing", "back-right", 1),
        ]

        for idx, r in enumerate(readings_sample):
            c.execute('''
            INSERT INTO test_readings (
                id, evaluation_id, test_type, load_val, reading, error, mpe, ratio, passed, direction, position, repeat_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f"tr_demo_{idx+1}", *r, now))

    c.execute("SELECT id FROM evaluations WHERE id = 'eval_submitted_02'")
    if not c.fetchone():
        c.execute('''
        INSERT INTO evaluations (
            id, instrument_id, inspector_id, status, test_date, test_location,
            temperature_c, humidity_percent, pressure_hpa, gravity_mps2, reference_standard,
            standards_traceability_no, repeatability_error, linearity_error, hysteresis_error,
            eccentricity_error, combined_uncertainty, expanded_uncertainty, compliance_score,
            risk_level, conformity, verification_hash, submitted_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "eval_submitted_02", "inst_essae_02", "usr_inspector_01", "SUBMITTED",
            now[:10], "Regional Reference Standards Laboratory, New Delhi",
            24.8, 55.0, 1014.0, 9.7915, "OIML Class F1 Precision Weights",
            "NPLI/LM/MASS/2026/1044", 0.00012, 0.00035, 0.00008, 0.00021,
            0.00042, 0.00084, 91.2, "LOW", 1, "OIML-R76-2026-SUBMITTED-DS415",
            now, now, now
        ))

    conn.commit()
    conn.close()

    log_audit("usr_admin_01", "SYSTEM_INIT", "DATABASE", "nawi_audit.db", {"status": "Database initialized and seeded with 4 roles"})

if __name__ == "__main__":
    init_db()
    seed_database()
    print("Database initialized and seeded successfully.")
