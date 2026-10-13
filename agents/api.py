"""
FastAPI REST API Server for Egfr Trajectory Aki Detector.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from renal_trajectory import assess_trajectory

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Egfr Trajectory Aki Detector API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "egfr-trajectory-aki-detector", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail="Identifier rejected by input filter") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail="Input rejected by identifier filter") from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


@app.post("/api/trajectory")
def api_trajectory(payload: Dict[str, Any]):
    """KDIGO creatinine/urine-output screening and descriptive eGFR slope."""
    try:
        return assess_trajectory(
            payload.get("observations"),
            urine_output_ml_kg_h=payload.get("urine_output_ml_kg_h"),
            urine_duration_hours=payload.get("urine_duration_hours"),
            renal_replacement_therapy=payload.get("renal_replacement_therapy", False),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
