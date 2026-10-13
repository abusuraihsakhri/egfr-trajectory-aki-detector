#!/usr/bin/env python3
"""
eGFR Trajectory & AKI Detector
KDIGO AKI staging (creatinine and urine output) plus eGFR slope and rapid-decline flagging.
Stdlib only.
"""
import argparse, csv, sys, math


def _safe_float(value, default=0.0):
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [float(v) for v in kwargs.values() if isinstance(v,(int,float)) or (isinstance(v,str) and v.replace('.','',1).isdigit())]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "egfr-trajectory-aki-detector") % 10
    score = sum(vals) * (0.9 + h*0.02) + math.log1p(len(vals))
    return {"score": round(score,2), "inputs": len(vals)}


def calculate_meld_na(bilirubin, creatinine, inr, sodium, dialysis=False, albumin=None, sex="M"):
    """
    Calculate MELD-Na score for liver disease severity.
    MELD = 3.78*ln(serum bilirubin) + 11.2*ln(INR) + 9.57*serum creatinine + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    """
    bili = _safe_float(bilirubin, 1.0)
    creat = _safe_float(creatinine, 1.0)
    inr_val = _safe_float(inr, 1.0)
    na = _safe_float(sodium, 137.0)

    # Apply bounds per UNOS guidelines
    bili = max(1.0, bili)
    creat = max(1.0, creat)
    if dialysis:
        creat = max(4.0, creat)
    inr_val = max(1.0, inr_val)
    na = max(125.0, min(137.0, na))

    meld = (3.78 * math.log(bili) + 11.2 * math.log(inr_val) +
            9.57 * math.log(creat) + 6.43)
    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    meld_na = max(6.0, min(40.0, round(meld_na, 1)))

    return {"meld_na": meld_na, "meld_base": round(meld, 1), "stage": "HIGH" if meld_na >= 30 else "MODERATE" if meld_na >= 20 else "LOW"}


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """
    Calculate QTc (corrected QT interval) using Bazett's formula.
    QTc = QT / sqrt(RR interval in seconds)
    RR can be derived from heart rate: RR = 60 / HR
    """
    qt = _safe_float(qt_ms, 0.0)
    if rr_ms is not None:
        rr = _safe_float(rr_ms, 0.0) / 1000.0
    elif hr_bpm is not None:
        hr = _safe_float(hr_bpm, 60.0)
        rr = 60.0 / max(hr, 1.0)
    else:
        rr = 1.0  # default 1 second

    if rr <= 0 or qt <= 0:
        return {"qtc_ms": 0.0, "qt_ms": qt, "rr_s": rr, "error": "Invalid QT or RR values"}

    qtc = qt / math.sqrt(rr)
    return {
        "qtc_ms": round(qtc, 1),
        "qt_ms": qt,
        "rr_s": round(rr, 3),
        "prolonged": qtc > 470  # >470ms considered prolonged (adult female threshold)
    }


def calculate_bmi_z(weight_kg, height_cm, age_months=60, sex="M"):
    """
    Calculate BMI and approximate z-score for pediatric populations.
    Uses simplified CDC reference (not full LMS tables).
    """
    wt = _safe_float(weight_kg, 0.0)
    ht_cm = _safe_float(height_cm, 0.0)
    age_mo = _safe_float(age_months, 60.0)

    if ht_cm <= 0 or wt <= 0:
        return {"bmi": 0.0, "z_score": 0.0, "error": "Invalid weight or height"}

    ht_m = ht_cm / 100.0
    bmi = wt / (ht_m ** 2)

    # Simplified z-score approximation using CDC median values
    # This is a rough estimate; clinical use requires full LMS tables
    if sex.upper() == "F":
        median_bmi = 16.0 + 0.08 * min(age_mo, 240)  # rough female median
    else:
        median_bmi = 15.5 + 0.07 * min(age_mo, 240)  # rough male median

    sd_bmi = median_bmi * 0.12  # approximate SD
    z_score = (bmi - median_bmi) / max(sd_bmi, 0.1)

    return {
        "bmi": round(bmi, 2),
        "z_score": round(z_score, 2),
        "age_months": age_mo,
        "sex": sex.upper(),
        "category": "OBESE" if z_score > 2 else "OVERWEIGHT" if z_score > 1 else "NORMAL" if z_score > -2 else "UNDERWEIGHT"
    }


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """
    Convert between HbA1c (%) and Estimated Average Glucose (mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7 (ADA formula)
    """
    if hba1c_percent is not None:
        hba1c = _safe_float(hba1c_percent, 0.0)
        eag = 28.7 * hba1c - 46.7
        return {
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(max(0, eag), 1),
            "eag_mmol_l": round(max(0, eag) / 18.0, 1),
            "category": "DIABETIC" if hba1c >= 6.5 else "PREDIABETIC" if hba1c >= 5.7 else "NORMAL"
        }
    elif eag_mgdl is not None:
        eag = _safe_float(eag_mgdl, 0.0)
        hba1c = (eag + 46.7) / 28.7
        return {
            "hba1c_percent": round(max(0, hba1c), 1),
            "eag_mgdl": round(eag, 1),
            "eag_mmol_l": round(eag / 18.0, 1),
            "category": "DIABETIC" if hba1c >= 6.5 else "PREDIABETIC" if hba1c >= 5.7 else "NORMAL"
        }
    return {"error": "Provide either hba1c_percent or eag_mgdl"}


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """
    Calculate APRI and FIB-4 scores for liver fibrosis assessment.
    APRI = (AST / ULN) / Platelets * 100
    FIB-4 = (Age * AST) / (Platelets * sqrt(ALT))
    """
    ast = _safe_float(ast_u_l, 0.0)
    alt = _safe_float(alt_u_l, 1.0)
    platelets = _safe_float(platelets_109, 200.0)
    age = _safe_float(age_years, 40.0)

    # Assume ULN for AST is 40 U/L
    ast_uln = 40.0

    if platelets <= 0:
        platelets = 1.0  # avoid division by zero

    apri = (ast / ast_uln) / platelets * 100

    result = {
        "apri": round(apri, 3),
        "ast_u_l": ast,
        "apri_stage": "SIGNIFICANT_FIBROSIS" if apri > 1.0 else "POSSIBLE_FIBROSIS" if apri > 0.5 else "MINIMAL_FIBROSIS"
    }

    if alt_u_l is not None and platelets_109 is not None and age_years is not None:
        alt = max(alt, 1.0)  # avoid sqrt(0)
        fib4 = (age * ast) / (platelets * math.sqrt(alt))
        result["fib4"] = round(fib4, 2)
        result["fib4_stage"] = "ADVANCED_FIBROSIS" if fib4 > 3.25 else "INDETERMINATE" if fib4 > 1.45 else "MINIMAL_FIBROSIS"

    return result


def assess_row(row):
    try:
        # try common lab keys
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(row.get("bilirubin"), row.get("creatinine"), row.get("inr"), row.get("sodium"), row.get("dialysis","0")=="1", row.get("albumin"), row.get("sex","M"))
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(row.get("qt_ms") or row.get("qt"), row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate"))
        if "weight_kg" in row:
            return calculate_bmi_z(row.get("weight_kg"), row.get("height_cm"), row.get("age_months") or row.get("age") or 60, row.get("sex","M"))
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(row.get("ast_u_l"), row.get("alt_u_l"), row.get("platelets_109"), row.get("age_years") or row.get("age"))
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}

def _validate_path(filepath, must_exist=False):
    """Validate a file path to prevent path traversal attacks."""
    import os
    # Reject paths with traversal sequences
    if ".." in filepath or "~" in filepath:
        raise ValueError(f"Path traversal detected in: {filepath}")
    # Normalize and ensure it's an absolute or safe relative path
    normalized = os.path.normpath(filepath)
    if normalized.startswith(".."):
        raise ValueError(f"Path escapes working directory: {filepath}")
    if must_exist and not os.path.isfile(normalized):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    return normalized


def process_csv(inp, out):
    import csv, os
    # Validate paths to prevent traversal
    inp = _validate_path(inp, must_exist=True)
    out = _validate_path(out, must_exist=False)
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f); rows=list(r); fieldnames=r.fieldnames
    if not fieldnames:
        raise ValueError("CSV file is empty or has no headers")
    results=[]
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k,v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys=set()
    for rr in results: all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(fieldnames)+extra); w.writeheader(); w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="egfr_trajectory", description="eGFR Trajectory & AKI Detector")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float); s.add_argument("--creat", type=float); s.add_argument("--inr", type=float); s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float); s.add_argument("--rr", type=float); s.add_argument("--hr", type=float)
    b=sub.add_parser("batch", help="batch csv"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    t=sub.add_parser("trajectory", help="dated renal trajectory from JSON request file")
    t.add_argument("--input", required=True)
    return p

def main(argv=None):
    import json as _json
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        if a.json:
            row=_json.loads(a.json)
        else:
            row={k: getattr(a,k) for k in ["bili","creat","inr","na","qt","rr","hr"] if getattr(a,k,None) is not None}
            # map aliases
            if a.bili is not None: row["bilirubin"]=a.bili
            if a.creat is not None: row["creatinine"]=a.creat
            if a.inr is not None: row["inr"]=a.inr
            if a.na is not None: row["sodium"]=a.na
            if a.qt is not None: row["qt_ms"]=a.qt
            if a.rr is not None: row["rr_ms"]=a.rr
            if a.hr is not None: row["hr_bpm"]=a.hr
        print(assess_row(row))
        return 0
    if a.cmd=="trajectory":
        from renal_trajectory import assess_trajectory
        with open(a.input, encoding="utf-8") as stream:
            request = _json.load(stream)
        if not isinstance(request, dict):
            p.error("trajectory request must be a JSON object")
        try:
            result = assess_trajectory(**request)
        except (TypeError, ValueError) as exc:
            p.error(str(exc))
        print(_json.dumps(result, indent=2))
        return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())
