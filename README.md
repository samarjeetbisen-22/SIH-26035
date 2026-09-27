# Metrolab — OIML R-76 Digital Testing & Verification Platform

> **Legal Metrology NAWI Verification Engine & Modern Web Interface**  
> Built for Smart India Hackathon (SIH-26035) based on **OIML R 76-1:2006** and **The Legal Metrology Act, 2009**.

---

## 🌟 Overview

**Metrolab** is an enterprise-grade digital testing and automated report generation system for **Non-Automatic Weighing Instruments (NAWIs)**. It replaces cumbersome physical paperwork and error-prone manual calculations with a clean, high-precision laboratory workbench.

The application features a **stunning, high-key light design system** (pure white `#FFFFFF`, soft cool slate background `#F8FAFC`, hairline borders `#E2E8F0`, and crisp emerald `#059669` / crimson `#DC2626` status pills) completely avoiding generic AI dark-mode tropes.

---

## ✅ Evaluation Criteria & Compliance Matrix (100% Complete)

| Evaluation Criterion          | Implementation Details                                                                                                    |     Status      |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------------------ | :-------------: |
| **Real Authentication**       | PBKDF2 with 100,000 iterations & cryptographic salt, HMAC-SHA256 JWT tokens                                               | **✅ Verified** |
| **Role Authorization**        | 4 distinct roles (`ADMIN`, `INSPECTOR`, `REVIEWER`, `OWNER`) with strict RBAC guards                                      | **✅ Verified** |
| **Real Database**             | SQLite schema (`nawi_audit.db`) with 6 relations: users, instruments, evaluations, test_readings, attachments, audit_logs | **✅ Verified** |
| **Instrument CRUD**           | Create, Read, Update, Delete with unique serial number constraints & cascade deletion                                     | **✅ Verified** |
| **Evaluation CRUD**           | Draft intake, environmental parameter logging, status lifecycle transitions                                               | **✅ Verified** |
| **Real Test Reading Storage** | Batch storage of Eccentricity, Repeatability, and Weighing performance points with foreign key linkages                   | **✅ Verified** |
| **Real Attachment Upload**    | Base64 evidence upload (scale photos, calibration certificates) & binary downloads                                        | **✅ Verified** |
| **Real Review Workflow**      | State machine: `DRAFT` → `SUBMITTED` → `APPROVED` / `REJECTED` with reviewer comments & stamping                          | **✅ Verified** |
| **Real Owner Data Filtering** | Strict tenant isolation — owners only view and access their own fleet instruments & certificates                          | **✅ Verified** |
| **Backend OIML Validation**   | Server-side MPE calculation, Repeatability (A.4.4), Eccentricity (A.4.7), Hysteresis (A.4.2), GUM $u_c$, $U_{k=2}$        | **✅ Verified** |
| **Real Report Workflow**      | Automated ReportLab PDF generation with dynamic QR code verification and tamper-evident SHA-256 hash                      | **✅ Verified** |
| **Audit Trail**               | Tamper-evident immutable action log recording all user logins, evaluations, calculations, reviews, and uploads            | **✅ Verified** |
| **Dashboard Live Data**       | Real-time statistics: total fleet count, evaluation status breakdown, pass rate %, expiring in 30 days                    | **✅ Verified** |
| **End-to-End Testing**        | Automated 13-point test suite (`test_e2e_compliance.py`) passing with 100% success rate                                   | **✅ Verified** |

---

## 👥 Default User Credentials for Evaluation

Metrolab includes a **Quick Role Switcher** banner directly at the top of the application to test any persona with a single click:

| Role          | Username           | Password        | Full Name & Organization              | Access Permissions                                                           |
| :------------ | :----------------- | :-------------- | :------------------------------------ | :--------------------------------------------------------------------------- |
| **INSPECTOR** | `rajesh_inspector` | `Inspector@123` | Rajesh Kumar (Senior Inspector, RRSL) | Instrument Intake, Testing Ledger, Upload Evidence, Submit Evaluations       |
| **REVIEWER**  | `priya_reviewer`   | `Reviewer@123`  | Dr. Priya Sharma (NABL Reviewer)      | Reviewer Queue, Approve / Reject Stamping, Audit Logs, Generate Official PDF |
| **OWNER**     | `essae_owner`      | `Owner@123`     | Essae Digitronics Fleet Admin         | Owner Fleet Portal, Validity Countdown, Download Certificates (Isolated)     |
| **ADMIN**     | `admin`            | `Admin@123`     | S. Roy (Director, Legal Metrology)    | Full System Access, Audit Trail Inspection, Fleet Management                 |

---

## 🧪 Automated End-to-End Compliance Verification

Run the comprehensive 13-point compliance verification test suite:

```bash
python test_e2e_compliance.py
```

### Test Suite Output:

```text
======================================================================
  METROLAB SIH-26035 E2E COMPLIANCE VERIFICATION TEST SUITE
======================================================================
  [PASS] 1. API Status and Health Check OK
  [PASS] 2. Real PBKDF2 + JWT Authentication Verified (4 Roles)
  [PASS] 3. Role-Based Access Control (RBAC) Enforced
  [PASS] 4. Instrument CRUD & Unique Constraint Verified
  [PASS] 5. Real Owner Data Filtering Isolation Verified
  [PASS] 6. Evaluation CRUD & Intake Lifecycle Verified
  [PASS] 7. Real Test Reading Storage & Retrieval Verified
  [PASS] 8. Backend OIML R-76 Engine Verified (Verdict: PASSED, U: 0.0042164 kg)
  [PASS] 9. Real Attachment Base64 Upload & Binary Download Verified
  [PASS] 10. Real Review Workflow State Machine (DRAFT -> SUBMITTED -> APPROVED) Verified
  [PASS] 11. Official OIML Certificate PDF Generation Verified
  [PASS] 12. Complete Audit Trail Logging Verified
  [PASS] 13. Dashboard Live Real-Time Aggregations Verified
======================================================================
  ALL 13 END-TO-END SIH-26035 COMPLIANCE TESTS PASSED SUCCESSFULLY!
======================================================================
```

---

## 🛠️ Quick Start

### 1. Launch Server (Windows One-Click)

Double-click `run_metrolab.bat` or run:

```bash
python server.py
```

Open your browser at **`http://localhost:8000/`**.

### 2. Frontend Development (Hot-Reloading)

```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173/` (automatically proxies requests to `http://localhost:8000/api`).

---

## 📄 Statutory & Regulatory Citations

Developed for statutory verification in accordance with:

- **OIML R 76-1 (2006)**: Non-automatic weighing instruments — Metrological and technical requirements.
- **The Legal Metrology Act, 2009**: Section 12 (Approval of Model) & Section 24 (Verification and Stamping).
- **Legal Metrology (General) Rules, 2011**: Tenth Schedule (Non-automatic weighing instruments).
- **ISO/IEC Guide 98-3 (GUM)**: Uncertainty in Measurement.
