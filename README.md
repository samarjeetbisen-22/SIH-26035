# Metrolab — OIML R-76 Digital Testing & Verification Platform

> **Legal Metrology NAWI Verification Engine & Modern Web Interface**  
> Built for Smart India Hackathon (SIH-26035) based on **OIML R 76-1:2006** and **The Legal Metrology Act, 2009**.

---

## 🌟 Overview

**Metrolab** is an enterprise-grade digital testing and automated report generation system for **Non-Automatic Weighing Instruments (NAWIs)**. It replaces cumbersome physical paperwork and error-prone manual calculations with a clean, high-precision laboratory workbench.

The application features a **stunning, high-key light design system** (pure white `#FFFFFF`, soft cool slate background `#F8FAFC`, hairline borders `#E2E8F0`, and crisp emerald `#059669` / crimson `#DC2626` status pills) avoiding generic AI dark-mode tropes.

---

## 🚀 Key Features

### 1. Instrument Intake & Metrological Profiling
- Multi-section statutory intake form compliant with **Legal Metrology (Approval of Models) Rules, 2011**.
- Accuracy Class selection (**Class I Special, Class II High, Class III Medium, Class IIII Ordinary**).
- Real-time scale division validation ($n = \text{Max} / e$) checked against OIML Table 3 limits.
- Atmospheric and environmental baseline logging (Temperature, Humidity, Barometric Pressure, and Local Gravity $g$).

### 2. Testing & Metrological Data Ledger
- High-density data table with inline editing and real-time indication error ($E = I - L$) and ratio evaluation.
- **Eccentricity / Corner Load (OIML A.4.7):** Interactive 5-point platform diagram (Center, Front-Left, Front-Right, Back-Left, Back-Right) with automatic maximum deviation check.
- **Repeatability (OIML A.4.4):** Multi-run analysis calculating Mean ($\bar{x}$), Standard Deviation ($s$), and Range ($R = \max - \min$) vs MPE.
- **One-Click OIML Schedule Generation:** Pre-fills standard 10-point and 5-point ascending and descending verification sequences.

### 3. Computation & Official Certificate Generation
- **ISO/IEC Guide 98-3 (GUM) Uncertainty Budget:** Constituent components ($u_{\text{rep}}, u_{\text{lin}}, u_{\text{ecc}}, u_{\text{hyst}}$), Combined Standard Uncertainty ($u_c$), and Expanded Metrological Uncertainty ($U = 2 \cdot u_c$).
- **Interactive SVG Error Profile Chart:** Plots actual errors against official step-function $\pm\text{MPE}$ envelopes ($0.5e, 1.0e, 1.5e$).
- **Official Verification Certificate Preview:** Paper-like document with national emblem, statutory legal citations, security QR verification watermark, and inspector signature block.
- **Print & PDF Ready:** Optimized for direct A4 printing via browser `Ctrl+P`.
- **SQLite Audit Trail Integration:** Persists test reports to `nawi_audit.db` with tamper-evident hashing.
- **Python ReportLab PDF Generator:** Directly creates stamped PDF certificates with QR codes.

---

## 📦 Tech Stack

- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite
- **Backend Bridge:** Python 3 (Standard HTTP server, SQLite3, ReportLab, QRCode)
- **Standards:** OIML R 76-1:2006, The Legal Metrology Act 2009, ISO/IEC Guide 98-3 (GUM)

---

## 🛠️ Quick Start

### 1. One-Click Launch (Windows)
Double-click `run_metrolab.bat` in the root folder, or run:
```cmd
run_metrolab.bat
```
This automatically boots the server and opens your browser at **`http://localhost:8000/`**.

### 2. Manual Start

#### Backend API & Web Server:
```bash
python server.py
```
Access at `http://localhost:8000/`.

#### Frontend Dev Server (Optional for Hot-Reloading):
```bash
cd frontend
npm install
npm run dev
```
Access at `http://localhost:5173/`.

---

## 📄 License & Legal Framework
Developed for statutory compliance verification in accordance with:
- **OIML R 76-1 (2006)**: Non-automatic weighing instruments — Metrological and technical requirements.
- **The Legal Metrology Act, 2009**: Section 12 (Approval of Model) & Section 24 (Verification and Stamping).
- **Legal Metrology (Approval of Models) Rules, 2011**.
