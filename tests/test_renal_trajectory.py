"""Clinically focused boundary and input validation tests for renal trajectory screening."""
import pytest
from renal_trajectory import assess_trajectory


def obs(day, scr=None, egfr=None):
    row = {"timestamp": f"2026-01-{day:02d}T00:00:00Z"}
    if scr is not None:
        row["creatinine_mg_dl"] = scr
    if egfr is not None:
        row["egfr_ml_min_1_73m2"] = egfr
    return row


def test_48_hour_cutoff_and_stage1():
    assert assess_trajectory([obs(1, 1), obs(3, 1.3)])["aki_stage"] == 1
    assert assess_trajectory([obs(1, 1), obs(4, 1.3)])["aki_stage"] == 0


def test_ratio_stages_and_seven_day_window():
    for ratio, stage in [(1.5, 1), (2, 2), (3, 3)]:
        assert assess_trajectory([obs(1, 1), obs(8, ratio)])["aki_stage"] == stage
    assert assess_trajectory([obs(1, 1), obs(9, 3)])["aki_stage"] is None


def test_absolute_creatinine_four_requires_documented_acute_rise():
    assert assess_trajectory([obs(1, 3.6), obs(2, 4.0)])["aki_stage"] == 3
    assert assess_trajectory([obs(1, 4.2), obs(2, 4.2)])["aki_stage"] == 0


def test_urine_output_staging_and_rrt():
    x = [obs(1, egfr=60)]
    assert assess_trajectory(x, urine_output_ml_kg_h=0.4, urine_duration_hours=5)["aki_stage"] == 0
    assert assess_trajectory(x, urine_output_ml_kg_h=0.4, urine_duration_hours=6)["aki_stage"] == 1
    assert assess_trajectory(x, urine_output_ml_kg_h=0.4, urine_duration_hours=12)["aki_stage"] == 2
    assert assess_trajectory(x, urine_output_ml_kg_h=0.2, urine_duration_hours=24)["aki_stage"] == 3
    assert assess_trajectory(x, urine_output_ml_kg_h=0, urine_duration_hours=12)["aki_stage"] == 3
    assert assess_trajectory(x, renal_replacement_therapy=True)["aki_stage"] == 3


def test_inadequate_data_and_no_false_rapid_decline():
    x = assess_trajectory([obs(1, egfr=95), obs(3, egfr=70)])
    assert x["aki_stage"] is None
    assert x["egfr_slope_ml_min_1_73m2_per_year"] < 0
    assert x["rapid_egfr_decline_flag"] is None


def test_longitudinal_rapid_decline():
    result = assess_trajectory([
        {"timestamp": "2024-01-01", "egfr_ml_min_1_73m2": 65},
        {"timestamp": "2025-01-01", "egfr_ml_min_1_73m2": 57},
        {"timestamp": "2026-01-01", "egfr_ml_min_1_73m2": 48},
    ])
    assert result["rapid_egfr_decline_flag"] is True
    assert -10 < result["egfr_slope_ml_min_1_73m2_per_year"] < -7


@pytest.mark.parametrize("bad", [[obs(1, -1)], [obs(1, float("nan"))],
                                  [obs(1, 1), obs(1, 2)], ["bad"], []])
def test_bad_observations_rejected(bad):
    with pytest.raises(ValueError):
        assess_trajectory(bad)


def test_out_of_order_sorting():
    assert assess_trajectory([obs(2, 1.5), obs(1, 1)])["aki_stage"] == 1


def test_missing_urine_parameter():
    with pytest.raises(ValueError):
        assess_trajectory([obs(1, 1)], urine_duration_hours=6)
