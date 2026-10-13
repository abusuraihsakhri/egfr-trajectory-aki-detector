"""Conservative timed KDIGO 2012 AKI screening and descriptive eGFR trends.

Not a diagnosis. Creatinine in mg/dL, eGFR in mL/min/1.73m².
Only documented observations are considered; no baseline is imputed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math


def _number(value, name, *, allow_zero=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number) or (number < 0 if allow_zero else number <= 0):
        raise ValueError(f"{name} must be {'nonnegative' if allow_zero else 'positive'} and finite")
    return number


def _date(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO 8601 string") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def assess_trajectory(observations, *, urine_output_ml_kg_h=None,
                      urine_duration_hours=None, renal_replacement_therapy=False):
    """Screen latest observation against documented prior creatinine values.

    Creatinine stage 1: >=0.3 mg/dL rise within 48 h, or >=1.5x within 7 d.
    Stage 2: >=2x within 7 d. Stage 3: >=3x within 7 d or an acute
    increase to >=4 mg/dL. Urine output is a sustained rate/duration pair.
    Inadequate observations cannot be used to exclude AKI.
    """
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a nonempty list")
    if len(observations) > 10000:
        raise ValueError("maximum 10000 observations")
    if not isinstance(renal_replacement_therapy, bool):
        raise ValueError("renal_replacement_therapy must be boolean")
    items = []
    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            raise ValueError(f"observation {index + 1} must be an object")
        when = _date(row.get("timestamp"))
        creat = row.get("creatinine_mg_dl")
        egfr = row.get("egfr_ml_min_1_73m2")
        if creat in (None, "") and egfr in (None, ""):
            raise ValueError(f"observation {index + 1} needs creatinine or eGFR")
        items.append((when,
                      _number(creat, "creatinine_mg_dl") if creat not in (None, "") else None,
                      _number(egfr, "egfr_ml_min_1_73m2") if egfr not in (None, "") else None))
    items.sort(key=lambda x: x[0])
    if len({r[0] for r in items}) != len(items):
        raise ValueError("duplicate timestamps are ambiguous")
    if (urine_output_ml_kg_h is None) != (urine_duration_hours is None):
        raise ValueError("urine output rate and duration must be provided together")
    urine_stage = None
    if urine_output_ml_kg_h is not None:
        rate = _number(urine_output_ml_kg_h, "urine_output_ml_kg_h", allow_zero=True)
        hours = _number(urine_duration_hours, "urine_duration_hours")
        urine_stage = (3 if (rate == 0 and hours >= 12) or (rate < 0.3 and hours >= 24)
                       else 2 if rate < 0.5 and hours >= 12
                       else 1 if rate < 0.5 and hours >= 6 else 0)
    latest = items[-1]
    latest_creat = latest[1]
    prior_48 = [r[1] for r in items[:-1] if r[1] is not None
                and 0 < (latest[0] - r[0]).total_seconds() <= 48 * 3600]
    prior_7d = [r[1] for r in items[:-1] if r[1] is not None
                and 0 < (latest[0] - r[0]).total_seconds() <= 7 * 24 * 3600]
    rise = latest_creat - min(prior_48) if latest_creat is not None and prior_48 else None
    baseline = min(prior_7d) if latest_creat is not None and prior_7d else None
    ratio = latest_creat / baseline if baseline is not None else None
    creat_stage = None
    if rise is not None or ratio is not None:
        creat_stage = 0
        rise_criterion = rise is not None and rise >= 0.3 - 1e-9
        ratio_criterion = ratio is not None and ratio >= 1.5 - 1e-9
        if rise_criterion or ratio_criterion:
            creat_stage = 1
        if ratio is not None and ratio >= 2.0 - 1e-9:
            creat_stage = 2
        if (ratio is not None and ratio >= 3.0 - 1e-9) or (
            latest_creat >= 4.0 and (rise_criterion or ratio_criterion)
        ):
            creat_stage = 3
    available = [s for s in (creat_stage, urine_stage) if s is not None]
    stage = max(available + ([3] if renal_replacement_therapy else [])) if (available or renal_replacement_therapy) else None
    egfr_points = [(r[0], r[2]) for r in items if r[2] is not None]
    slope = None
    rapid_decline = None
    span = None
    if len(egfr_points) >= 2:
        start = egfr_points[0][0]
        xs = [(r[0] - start).total_seconds() / (365.25 * 24 * 3600) for r in egfr_points]
        ys = [r[1] for r in egfr_points]
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        denom = sum((x - x_mean) ** 2 for x in xs)
        slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom
        span = (egfr_points[-1][0] - start).total_seconds() / (24 * 3600)
        if span >= 365:
            rapid_decline = slope < -5.0
    warnings = []
    if creat_stage is None and urine_stage is None and not renal_replacement_therapy:
        warnings.append("AKI stage not assessable: no eligible creatinine comparison or urine-output interval")
    if urine_stage is None:
        warnings.append("Urine-output staging unavailable; AKI may be missed")
    if len(egfr_points) < 2:
        warnings.append("At least two dated eGFR values are needed for slope")
    elif span < 365:
        warnings.append("eGFR follow-up under 365 days: long-term rapid-decline flag withheld")
    if latest_creat is None:
        warnings.append("Latest observation has no creatinine; serum-creatinine staging unavailable")
    warnings.append("Screening only: clinical context, baseline uncertainty, and non-steady-state eGFR require review")
    return {
        "latest_timestamp": latest[0].isoformat().replace("+00:00", "Z"),
        "observation_count": len(items),
        "aki_stage": stage,
        "creatinine_stage": creat_stage,
        "urine_output_stage": urine_stage,
        "baseline_creatinine_7d_mg_dl": round(baseline, 4) if baseline is not None else None,
        "creatinine_rise_48h_mg_dl": round(rise, 4) if rise is not None else None,
        "creatinine_ratio_7d": round(ratio, 4) if ratio is not None else None,
        "egfr_slope_ml_min_1_73m2_per_year": round(slope, 3) if slope is not None else None,
        "egfr_span_days": round(span, 2) if span is not None else None,
        "rapid_egfr_decline_flag": rapid_decline,
        "warnings": warnings,
    }
