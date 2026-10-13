"""Regression coverage for tamper detection and renal API validation."""
import pytest
from fastapi import HTTPException
from agents.base import AuditTrail
from agents.api import api_trajectory


def test_audit_hmac_detects_metadata_and_signature_tampering():
    trail = AuditTrail(secret_key="local-test-key-" * 4)
    trail.log("tester", "qa", "CHECK", {"value": 1})
    trail.log("tester", "qa", "CHECK", {"value": 2})
    assert trail.verify_integrity()
    snapshot = trail.get_trail()
    snapshot[0]["actor"] = "modified"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "modified"
    assert not trail.verify_integrity()


def test_audit_hmac_detects_last_signature_corruption():
    trail = AuditTrail(secret_key="local-test-key-" * 4)
    trail.log("tester", "qa", "CHECK", {"value": 1})
    trail.logs[-1]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_renal_api_and_invalid_input():
    payload = {"observations": [
        {"timestamp": "2026-01-01", "creatinine_mg_dl": 1},
        {"timestamp": "2026-01-03", "creatinine_mg_dl": 1.3}
    ]}
    assert api_trajectory(payload)["aki_stage"] == 1
    with pytest.raises(HTTPException) as error:
        api_trajectory({"observations": [{"timestamp": "bogus", "creatinine_mg_dl": 1}]})
    assert error.value.status_code == 422
