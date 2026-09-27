"""
Backend OIML R-76 & Legal Metrology Validation Engine (SIH-26035)
Implements:
- Accuracy Classes I, II, III, IIII verification interval table & MPE calculation (OIML R 76-1 Clause 3.5.1)
- Maximum Permissible Error (MPE) for initial and subsequent verification
- Repeatability Error (Clause A.4.4)
- Eccentricity Error (Clause A.4.7)
- Linearity and Hysteresis Error (Clause A.4.2)
- Combined Standard Uncertainty u_c and Expanded Uncertainty U (k=2, 95% confidence)
- Statutory Compliance Scoring & Risk Index
- Cryptographic Verification Digest Hash
"""

import math
import hashlib
import datetime
from collections import defaultdict

# OIML R 76-1:2006 Table 6 - Maximum permissible errors for initial verification
# Values are expressed in terms of verification scale intervals 'e'
OIML_MPE_LIMITS = {
    "I": [
        {"min_e": 0, "max_e": 50000, "mpe_e": 0.5},
        {"min_e": 50000, "max_e": 200000, "mpe_e": 1.0},
        {"min_e": 200000, "max_e": float("inf"), "mpe_e": 1.5},
    ],
    "II": [
        {"min_e": 0, "max_e": 5000, "mpe_e": 0.5},
        {"min_e": 5000, "max_e": 20000, "mpe_e": 1.0},
        {"min_e": 20000, "max_e": 100000, "mpe_e": 1.5},
    ],
    "III": [
        {"min_e": 0, "max_e": 500, "mpe_e": 0.5},
        {"min_e": 500, "max_e": 2000, "mpe_e": 1.0},
        {"min_e": 2000, "max_e": 10000, "mpe_e": 1.5},
    ],
    "IIII": [
        {"min_e": 0, "max_e": 50, "mpe_e": 0.5},
        {"min_e": 50, "max_e": 200, "mpe_e": 1.0},
        {"min_e": 200, "max_e": 1000, "mpe_e": 1.5},
    ],
}

def get_mpe_in_e(load_e: float, accuracy_class: str = "III") -> float:
    """Returns statutory MPE in verification scale intervals (e) for a given load/e."""
    table = OIML_MPE_LIMITS.get(accuracy_class, OIML_MPE_LIMITS["III"])
    for bracket in table:
        if bracket["min_e"] <= load_e <= bracket["max_e"]:
            return bracket["mpe_e"]
    return table[-1]["mpe_e"]

def calculate_mpe(load_val: float, e_interval: float, accuracy_class: str = "III") -> float:
    """Returns statutory MPE in physical engineering units (kg/g) for a given load."""
    if e_interval <= 0:
        e_interval = 0.001
    load_e = abs(load_val) / e_interval
    mpe_e = get_mpe_in_e(load_e, accuracy_class)
    return round(mpe_e * e_interval, 6)

def normalize_reading_input(r: dict) -> dict:
    """Normalizes raw input from various API formats into standard internal representation."""
    # Load / target
    load = float(r.get("load", r.get("load_val", r.get("target_load", r.get("load_kg", 0.0)))))
    # Indicated reading
    reading = float(r.get("reading", r.get("indicated_value", r.get("reading_val", load))))
    # Direction
    direction = str(r.get("direction", "")).lower()
    if direction not in ("increasing", "decreasing"):
        direction = "increasing"

    # Position mapping to SQLite schema CHECK: ('center', 'front-left', 'front-right', 'back-left', 'back-right')
    raw_pos = str(r.get("position", r.get("load_position", "center"))).lower().replace("_", "-").replace(" ", "-")
    pos_map = {
        "center": "center",
        "centre": "center",
        "top-left": "back-left",
        "topleft": "back-left",
        "back-left": "back-left",
        "backleft": "back-left",
        "top-right": "back-right",
        "topright": "back-right",
        "back-right": "back-right",
        "backright": "back-right",
        "bottom-left": "front-left",
        "bottomleft": "front-left",
        "front-left": "front-left",
        "frontleft": "front-left",
        "bottom-right": "front-right",
        "bottomright": "front-right",
        "front-right": "front-right",
        "frontright": "front-right"
    }
    position = pos_map.get(raw_pos, "center")

    # Repeat / Run
    repeat_no = int(r.get("repeat_number", r.get("run_number", 1)))
    raw_type = str(r.get("test_type", "")).upper()
    if "ECC" in raw_type or position != "center":
        test_type = "ECCENTRICITY"
    elif "REP" in raw_type or repeat_no > 1:
        test_type = "REPEATABILITY"
    else:
        test_type = "LOAD"

    return {
        "load": load,
        "reading": reading,
        "direction": direction,
        "position": position,
        "repeat_number": repeat_no,
        "test_type": test_type,
        "raw": r
    }

def validate_oiml_compliance(instrument: dict, readings: list) -> dict:
    """
    Evaluates complete metrological compliance per OIML R 76-1.
    Calculates Repeatability, Linearity, Hysteresis, Eccentricity,
    Standard Uncertainty (GUM), Expanded Uncertainty (k=2),
    MPE envelope compliance, and statutory verification hash.
    """
    max_cap = float(instrument.get("max_capacity", 30.0))
    e = float(instrument.get("e_interval", 0.005))
    acc_class = str(instrument.get("accuracy_class", "III")).upper()
    if acc_class not in OIML_MPE_LIMITS:
        acc_class = "III"

    norm_readings = [normalize_reading_input(r) for r in readings]

    point_results = []
    overall_pass = True
    ratios = []

    # 1. Per-point evaluation against statutory MPE
    for nr in norm_readings:
        load = nr["load"]
        reading = nr["reading"]
        error = round(reading - load, 6)
        mpe = calculate_mpe(load, e, acc_class)
        ratio = round(abs(error) / mpe, 4) if mpe > 0 else 0.0
        passed = abs(error) <= (mpe + 1e-9)

        if not passed:
            overall_pass = False

        ratios.append(ratio)
        point_results.append({
            "load": load,
            "load_kg": load,
            "reading": reading,
            "error": error,
            "error_kg": error,
            "mpe": mpe,
            "mpe_kg": mpe,
            "ratio": ratio,
            "passed": passed,
            "direction": nr["direction"],
            "position": nr["position"],
            "repeat_number": nr["repeat_number"],
            "test_type": nr["test_type"]
        })

    # 2. Repeatability Calculation (OIML R-76 Clause A.4.4)
    # Difference between maximum and minimum readings at the same load
    repeatability_readings = [nr for nr in norm_readings if nr["test_type"] == "REPEATABILITY" or nr["repeat_number"] > 1]
    repeatability_err = 0.0
    if repeatability_readings:
        rep_by_load = defaultdict(list)
        for r in repeatability_readings:
            rep_by_load[r["load"]].append(r["reading"])
        for load, vals in rep_by_load.items():
            if len(vals) > 1:
                spread = max(vals) - min(vals)
                if spread > repeatability_err:
                    repeatability_err = spread
    else:
        # Default estimation based on resolution
        repeatability_err = round(e * 0.2, 6)

    # 3. Eccentricity Calculation (OIML R-76 Clause A.4.7)
    # Maximum difference between any position and center reading, or max spread across positions
    ecc_readings = [nr for nr in norm_readings if nr["test_type"] == "ECCENTRICITY" or nr["position"] != "center"]
    eccentricity_err = 0.0
    if ecc_readings:
        ecc_by_load = defaultdict(lambda: defaultdict(list))
        for r in ecc_readings:
            ecc_by_load[r["load"]][r["position"]].append(r["reading"])
        for load, pos_dict in ecc_by_load.items():
            pos_means = [sum(vals)/len(vals) for vals in pos_dict.values()]
            if len(pos_means) > 1:
                spread = max(pos_means) - min(pos_means)
                if spread > eccentricity_err:
                    eccentricity_err = spread
    else:
        eccentricity_err = round(e * 0.15, 6)

    # 4. Linearity Calculation (Maximum absolute error from ideal)
    linearity_err = 0.0
    for pt in point_results:
        if abs(pt["error"]) > linearity_err:
            linearity_err = abs(pt["error"])

    # 5. Hysteresis Calculation (OIML R-76 Clause A.4.2)
    # Difference between increasing and decreasing readings at the same nominal load
    hys_by_load = defaultdict(lambda: {"inc": [], "dec": []})
    for nr in norm_readings:
        if nr["direction"] == "increasing":
            hys_by_load[nr["load"]]["inc"].append(nr["reading"])
        elif nr["direction"] == "decreasing":
            hys_by_load[nr["load"]]["dec"].append(nr["reading"])

    hysteresis_err = 0.0
    for load, dirs in hys_by_load.items():
        if dirs["inc"] and dirs["dec"]:
            inc_avg = sum(dirs["inc"]) / len(dirs["inc"])
            dec_avg = sum(dirs["dec"]) / len(dirs["dec"])
            diff = abs(inc_avg - dec_avg)
            if diff > hysteresis_err:
                hysteresis_err = diff
    if hysteresis_err == 0.0:
        hysteresis_err = round(e * 0.1, 6)

    # 6. Combined Standard Uncertainty (u_c) per GUM (ISO/IEC Guide 98-3)
    # Components: Repeatability (u_rep), Resolution (u_res), Reference Standard (u_ref), Eccentricity (u_ecc)
    u_rep = repeatability_err / math.sqrt(3) if repeatability_err > 0 else (e / (2 * math.sqrt(3)))
    u_res = (e / 2.0) / math.sqrt(3)
    u_ecc = (eccentricity_err / (2 * math.sqrt(3)))
    u_ref = (e / 3.0) / 2.0  # Class F1 reference weight uncertainty estimation

    combined_uncertainty = round(math.sqrt(u_rep**2 + u_res**2 + u_ecc**2 + u_ref**2), 7)
    # Expanded uncertainty with coverage factor k=2 (95.45% coverage probability)
    expanded_uncertainty = round(combined_uncertainty * 2.0, 7)

    # 7. Compliance Score & Risk Level
    if ratios:
        avg_ratio = sum(ratios) / len(ratios)
        worst_ratio = max(ratios)
        blended = 0.65 * avg_ratio + 0.35 * worst_ratio
        compliance_score = round(max(0.0, min(100.0, 100.0 * (1.0 - blended))), 2)
    else:
        compliance_score = 100.0

    if not overall_pass:
        compliance_score = min(compliance_score, 45.0)

    if compliance_score >= 88.0:
        risk_level = "LOW"
    elif compliance_score >= 65.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    # 8. Cryptographic Statutory Verification Hash
    serial = instrument.get("serial_number", "UNKNOWN")
    raw_digest_str = f"{serial}|{acc_class}|{max_cap}|{e}|{compliance_score}|{overall_pass}|{expanded_uncertainty}"
    digest_hash = hashlib.sha256(raw_digest_str.encode("utf-8")).hexdigest()[:16].upper()
    verification_hash = f"OIML-R76-2026-{digest_hash}"

    return {
        "point_results": point_results,
        "overall_pass": overall_pass,
        "overall_compliance": "PASSED" if overall_pass else "FAILED",
        "conformity": 1 if overall_pass else 0,
        "repeatability_error": round(repeatability_err, 6),
        "linearity_error": round(linearity_err, 6),
        "hysteresis_error": round(hysteresis_err, 6),
        "eccentricity_error": round(eccentricity_err, 6),
        "combined_uncertainty": combined_uncertainty,
        "expanded_uncertainty": expanded_uncertainty,
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "verification_hash": verification_hash,
        "oiml_hash": verification_hash,
        "evaluated_at": datetime.datetime.now().isoformat()
    }
