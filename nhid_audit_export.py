import csv
import io
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# In-memory audit log for demo purposes
# In production this connects to your hash-chained audit DB
_audit_log = []

class AuditEvent(BaseModel):
    session_id: str
    agent_id: str
    event_type: str
    transcript_text: Optional[str] = None
    action: Optional[str] = None
    timestamp: Optional[str] = None

@router.post("/v1/audit/log")
def log_audit_event(event: AuditEvent):
    entry = event.model_dump()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    _audit_log.append(entry)
    return {"logged": True, "timestamp": entry["timestamp"]}

@router.get("/v1/audit/export/{session_id}")
def export_audit_fhir(session_id: str, format: str = "fhir"):
    events = [e for e in _audit_log if e["session_id"] == session_id]
    if not events:
        raise HTTPException(status_code=404, detail="No audit events found for session")

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_{session_id}.csv"}
        )

    # FHIR AuditEvent bundle
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "AuditEvent",
                    "id": f"nhid-{e['session_id']}-{i}",
                    "action": "E",
                    "recorded": e["timestamp"],
                    "agent": [{"who": {"display": e["agent_id"]}, "requestor": True}],
                    "entity": [{"detail": [
                        {"type": k, "valueString": str(v)}
                        for k, v in e.items()
                    ]}]
                }
            }
            for i, e in enumerate(events)
        ]
    }
    return JSONResponse(content=fhir_bundle)