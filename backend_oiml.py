"""
Backend OIML R-76 Validation and Metrology Engine for Metrolab (SIH-26035)
Implements statutory compliance calculations, MPE limits, uncertainty analysis,
and verification hashing according to OIML R 76-1:2006.
"""

import math
import hashlib
from collections import defaultdict
import prototype_sih26035 as proto

def calculate_mpe(load_e: float, accuracy_class: str) -> float:
    """Calculates Maximum Permissible Error (MPE) in e units according to OIML R 76-1 Table 6."""
    c = str(accuracy_class).upper().strip()
    if c == 'I':
        if load_e <= 50000:
            return 0.5
        elif load_e <= 200000:
            return 1.0
        else:
            return 1.5
    elif c == 'II':
        if load_e <= 5000:
            return 0.5
        elif load_e <= 20000:
            return 1.0
        else:
            return 1.5
    elif c == 'III':
        if load_e <= 500:
            return 0.5
        elif load_e <= 2000:
            return 1.0
        else:
            return 1.5
    elif c in ('IIII', '4', 'IV'):
        if load_e <= 50:
            return 0.5
        elif load_e <= 200:
            return 1.0
        else:
            return 1.5
    return 1.0

def validate_oiml_compliance(instrument: dict, readings: list) -> dict:
    """
    Computes metrological errors, uncertainties, compliance score, and pass/fail conformity
    for an instrument and its test readings.
    """
    capacity = float(instrument.get('max_capacity') or instrument.get('maxCapacity') or 15.0)
    e = float(instrument.get('e_interval') or instrument.get('verificationScaleIntervalE') or 0.005)
    if e <= 0:
        e = 0.001
    acc_class = str(instrument.get('accuracy_class') or instrument.get('accuracyClass') or 'III')
    serial = str(instrument.get('serial_number') or instrument.get('serialNumber') or 'UNKNOWN')

    point_results = []
    overall_pass = True

    grouped_by_load = defaultdict(list)

    for idx, r in enumerate(readings):
        load_val = float(r.get('load') if 'load' in r else r.get('load_val', 0.0))
        reading_val = float(r.get('reading', load_val))
        direction = str(r.get('direction', 'increasing')).lower()
        position = str(r.get('position', 'center'))
        if position not in ('center', 'front-left', 'front-right', 'back-left', 'back-right'):
            position = 'center'
        repeat_no = int(r.get('repeat_number') or r.get('repeatNumber') or 1)
        raw_tt = r.get('test_type') or r.get('testType')
        if raw_tt and str(raw_tt).upper() in ('LOAD', 'ECCENTRICITY', 'REPEATABILITY'):
            test_type = str(raw_tt).upper()
        else:
            if position != 'center':
                test_type = 'ECCENTRICITY'
            elif repeat_no > 1:
                test_type = 'REPEATABILITY'
            else:
                test_type = 'LOAD'

        load_e = load_val / e
        mpe_e = calculate_mpe(load_e, acc_class)
        mpe_val = mpe_e * e
        error_val = reading_val - load_val
        passed = abs(error_val) <= (mpe_val + 1e-9)

        if not passed:
            overall_pass = False

        ratio = abs(error_val) / mpe_val if mpe_val > 0 else 0.0

        item = {
            'id': r.get('id'),
            'load': load_val,
            'reading': reading_val,
            'error': error_val,
            'mpe': mpe_val,
            'ratio': ratio,
            'passed': passed,
            'direction': direction,
            'position': position,
            'repeat_number': repeat_no,
            'test_type': test_type,
        }
        point_results.append(item)
        grouped_by_load[load_val].append(item)

    # 1. Repeatability error
    repeatability = 0.0
    for load, r_list in grouped_by_load.items():
        readings_sub = [pt['reading'] for pt in r_list if pt['direction'] == 'increasing']
        if len(readings_sub) > 1:
            mean = sum(readings_sub) / len(readings_sub)
            variance = sum((x - mean) ** 2 for x in readings_sub) / (len(readings_sub) - 1)
            stdev = math.sqrt(variance)
            err = stdev / capacity if capacity > 0 else stdev
            if err > repeatability:
                repeatability = err

    # 2. Linearity error
    linearity = 0.0
    for pt in point_results:
        dev = abs(pt['error']) / capacity if capacity > 0 else abs(pt['error'])
        if dev > linearity:
            linearity = dev

    # 3. Hysteresis error
    hysteresis = 0.0
    for load, r_list in grouped_by_load.items():
        inc = [pt['reading'] for pt in r_list if pt['direction'] == 'increasing']
        dec = [pt['reading'] for pt in r_list if pt['direction'] == 'decreasing']
        if inc and dec:
            diff = abs((sum(inc) / len(inc)) - (sum(dec) / len(dec))) / capacity if capacity > 0 else 0.0
            if diff > hysteresis:
                hysteresis = diff

    # 4. Eccentricity error
    eccentricity = 0.0
    for load, r_list in grouped_by_load.items():
        positions = defaultdict(list)
        for pt in r_list:
            positions[pt['position']].append(pt['reading'])
        if len(positions) > 1:
            means = {p: sum(v) / len(v) for p, v in positions.items()}
            diff = (max(means.values()) - min(means.values())) / capacity if capacity > 0 else 0.0
            if diff > eccentricity:
                eccentricity = diff

    # 5. Combined & Expanded Uncertainty
    combined_unc = math.sqrt(repeatability**2 + linearity**2 + eccentricity**2 + hysteresis**2)
    if combined_unc == 0.0:
        combined_unc = 0.0001
    expanded_unc = combined_unc * 2.0  # k=2, 95% coverage

    # 6. Compliance score
    if point_results:
        ratios = [pt['ratio'] for pt in point_results]
        avg_ratio = sum(ratios) / len(ratios)
        worst_ratio = max(ratios)
        blended = 0.7 * avg_ratio + 0.3 * worst_ratio
        score = max(0.0, min(100.0, 100.0 * (1.0 - blended)))
    else:
        score = 100.0

    score = round(score, 2)

    if score >= 90 and overall_pass:
        risk_level = "LOW"
    elif score >= 70:
        risk_level = "MEDIUM"
    elif score >= 50:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    if not overall_pass and risk_level == "LOW":
        risk_level = "MEDIUM"

    hash_source = f"{serial}|{capacity}|{e}|{acc_class}|{score}|{overall_pass}|{len(point_results)}"
    verification_hash = f"OIML-R76-SHA256-{hashlib.sha256(hash_source.encode('utf-8')).hexdigest()[:16].upper()}"

    return {
        "repeatability_error": round(repeatability, 6),
        "linearity_error": round(linearity, 6),
        "hysteresis_error": round(hysteresis, 6),
        "eccentricity_error": round(eccentricity, 6),
        "combined_uncertainty": round(combined_unc, 6),
        "expanded_uncertainty": round(expanded_unc, 6),
        "compliance_score": score,
        "risk_level": risk_level,
        "conformity": 1 if overall_pass else 0,
        "verification_hash": verification_hash,
        "point_results": point_results,
    }
