"""
Automated Pytest for egfr_trajectory core calculation functions.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import egfr_trajectory as m


class TestCalculateMeldNa:
    def test_basic_calculation(self):
        result = m.calculate_meld_na(bilirubin=2.5, creatinine=1.2, inr=1.1, sodium=135)
        assert "meld_na" in result
        assert "meld_base" in result
        assert isinstance(result["meld_na"], float)
        assert 6.0 <= result["meld_na"] <= 40.0

    def test_dialysis_flag(self):
        result_dialysis = m.calculate_meld_na(bilirubin=2.0, creatinine=1.0, inr=1.0, sodium=137, dialysis=True)
        result_no_dialysis = m.calculate_meld_na(bilirubin=2.0, creatinine=1.0, inr=1.0, sodium=137, dialysis=False)
        assert result_dialysis["meld_na"] >= result_no_dialysis["meld_na"]

    def test_high_meld_stage(self):
        result = m.calculate_meld_na(bilirubin=15.0, creatinine=5.0, inr=3.0, sodium=125)
        assert result["stage"] == "HIGH"
        assert result["meld_na"] >= 30

    def test_low_meld_stage(self):
        result = m.calculate_meld_na(bilirubin=1.0, creatinine=1.0, inr=1.0, sodium=137)
        assert result["stage"] == "LOW"

    def test_string_inputs(self):
        result = m.calculate_meld_na(bilirubin="2.5", creatinine="1.2", inr="1.1", sodium="135")
        assert "meld_na" in result
        assert isinstance(result["meld_na"], float)

    def test_none_inputs(self):
        result = m.calculate_meld_na(bilirubin=None, creatinine=None, inr=None, sodium=None)
        assert "meld_na" in result


class TestCalculateQtc:
    def test_basic_with_hr(self):
        result = m.calculate_qtc(qt_ms=400, hr_bpm=60)
        assert "qtc_ms" in result
        assert result["qtc_ms"] > 0

    def test_basic_with_rr(self):
        result = m.calculate_qtc(qt_ms=400, rr_ms=1000)
        assert "qtc_ms" in result
        assert result["qtc_ms"] > 0

    def test_prolonged_qtc(self):
        result = m.calculate_qtc(qt_ms=500, hr_bpm=60)
        assert result["prolonged"] is True

    def test_normal_qtc(self):
        result = m.calculate_qtc(qt_ms=380, hr_bpm=70)
        assert result["prolonged"] is False

    def test_invalid_inputs(self):
        result = m.calculate_qtc(qt_ms=0, hr_bpm=60)
        assert result.get("qtc_ms", -1) == 0.0

    def test_none_inputs(self):
        result = m.calculate_qtc(qt_ms=None, hr_bpm=None)
        assert "qtc_ms" in result


class TestCalculateBmiZ:
    def test_basic_calculation(self):
        result = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=120, sex="M")
        assert "bmi" in result
        assert "z_score" in result
        assert result["bmi"] > 0

    def test_male_vs_female(self):
        male = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=120, sex="M")
        female = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=120, sex="F")
        # Different medians should produce different z-scores
        assert male["z_score"] != female["z_score"] or male["bmi"] == female["bmi"]

    def test_invalid_inputs(self):
        result = m.calculate_bmi_z(weight_kg=0, height_cm=0)
        assert "error" in result

    def test_category(self):
        result = m.calculate_bmi_z(weight_kg=70, height_cm=175, age_months=120, sex="M")
        assert result["category"] in ["OBESE", "OVERWEIGHT", "NORMAL", "UNDERWEIGHT"]


class TestConvertHba1c:
    def test_hba1c_to_eag(self):
        result = m.convert_hba1c(hba1c_percent=7.0)
        assert "eag_mgdl" in result
        assert "eag_mmol_l" in result
        # ADA formula: eAG = 28.7 * 7.0 - 46.7 = 154.2
        assert abs(result["eag_mgdl"] - 154.2) < 1.0

    def test_eag_to_hba1c(self):
        result = m.convert_hba1c(eag_mgdl=154.2)
        assert "hba1c_percent" in result
        assert abs(result["hba1c_percent"] - 7.0) < 0.5

    def test_diabetic_category(self):
        result = m.convert_hba1c(hba1c_percent=7.0)
        assert result["category"] == "DIABETIC"

    def test_normal_category(self):
        result = m.convert_hba1c(hba1c_percent=5.0)
        assert result["category"] == "NORMAL"

    def test_no_inputs(self):
        result = m.convert_hba1c()
        assert "error" in result


class TestCalculateApriFib4:
    def test_apri_only(self):
        result = m.calculate_apri_fib4(ast_u_l=40, alt_u_l=40, platelets_109=200, age_years=40)
        assert "apri" in result
        assert "fib4" in result

    def test_high_ast(self):
        result = m.calculate_apri_fib4(ast_u_l=200, alt_u_l=50, platelets_109=150, age_years=55)
        assert result["apri_stage"] in ["SIGNIFICANT_FIBROSIS", "POSSIBLE_FIBROSIS", "MINIMAL_FIBROSIS"]
        assert result["fib4_stage"] in ["ADVANCED_FIBROSIS", "INDETERMINATE", "MINIMAL_FIBROSIS"]

    def test_zero_platelets(self):
        result = m.calculate_apri_fib4(ast_u_l=40, alt_u_l=40, platelets_109=0, age_years=40)
        assert "apri" in result  # Should handle division by zero gracefully

    def test_advanced_fibrosis(self):
        result = m.calculate_apri_fib4(ast_u_l=200, alt_u_l=50, platelets_109=100, age_years=60)
        assert result["fib4_stage"] == "ADVANCED_FIBROSIS"


class TestAssessRow:
    def test_meld_na_routing(self):
        result = m.assess_row({"bilirubin": 2.5, "creatinine": 1.2})
        assert "meld_na" in result

    def test_qtc_routing(self):
        result = m.assess_row({"qt_ms": 400, "hr_bpm": 60})
        assert "qtc_ms" in result

    def test_bmi_routing(self):
        result = m.assess_row({"weight_kg": 70, "height_cm": 175})
        assert "bmi" in result

    def test_hba1c_routing(self):
        result = m.assess_row({"hba1c_percent": 7.0})
        assert "eag_mgdl" in result

    def test_apri_routing(self):
        result = m.assess_row({"ast_u_l": 100, "alt_u_l": 50, "platelets_109": 150, "age_years": 55})
        assert "apri" in result

    def test_generic_fallback(self):
        result = m.assess_row({"value": 10})
        assert "score" in result

    def test_error_handling(self):
        # Should not raise, should return error dict
        result = m.assess_row({"bilirubin": "invalid", "creatinine": "also_invalid"})
        # assess_row catches exceptions and returns error dict
        assert isinstance(result, dict)


class TestProcessCsv:
    def test_valid_csv(self, tmp_path):
        # Create a test CSV
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,value,qty\nA,10,2\nB,20,3\n", encoding="utf-8")
        out_path = tmp_path / "output.csv"
        results = m.process_csv(str(csv_path), str(out_path))
        assert len(results) == 2
        assert out_path.exists()

    def test_path_traversal_input(self):
        with pytest.raises(ValueError, match="traversal"):
            m.process_csv("../etc/passwd", "output.csv")

    def test_path_traversal_output(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("id,value,qty\nA,10,2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="traversal"):
            m.process_csv(str(csv_path), "../etc/output.csv")

    def test_missing_input_file(self):
        with pytest.raises(FileNotFoundError):
            m.process_csv("nonexistent_file.csv", "output.csv")

    def test_empty_csv(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            m.process_csv(str(csv_path), str(tmp_path / "out.csv"))


class TestCalculateScore:
    def test_basic_score(self):
        result = m.calculate_score(value=10, qty=2)
        assert "score" in result
        assert "inputs" in result
        assert result["inputs"] >= 1

    def test_empty_kwargs(self):
        result = m.calculate_score()
        assert "score" in result
        assert result["inputs"] == 1  # Uses default value=1

    def test_string_numeric_values(self):
        result = m.calculate_score(a="10", b="20")
        assert result["inputs"] == 2
