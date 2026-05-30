import os
from typing import List
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from src.voice_policy import run_voice_policy

router = APIRouter()

_STATE_REQUIREMENTS = {
    "WA_SB5395": {"required_rules": ["IDG-01","DBC-01","EIT-01"], "effective_date": "2025-07-27", "reporting": False, "description": "Requires AI to disclose non-human nature at start of interactions."},
    "IN_HB1271": {"required_rules": ["IDG-01"], "effective_date": "2025-07-01", "reporting": False, "description": "Requires automated systems to identify themselves before substantive conversation."},
    "MD_HB1563": {"required_rules": ["IDG-01","ATR-01"], "effective_date": "2026-10-01", "reporting": True, "description": "Requires disclosure and audit logging for AI voice systems in healthcare."},
    "UT_SB319": {"required_rules": ["IDG-01","DBC-01"], "effective_date": "2025-05-07", "reporting": False, "description": "Prohibits AI from impersonating humans in commercial communications."},
    "AL_SB63": {"required_rules": ["IDG-01"], "effective_date": "2026-01-01", "reporting": False, "description": "Requires AI voice agents to disclose automated nature in first exchange."},
    "GA_SB544": {"required_rules": ["IDG-01","EIT-01"], "effective_date": "2025-07-01", "reporting": False, "description": "Requires disclosure and honors human escalation requests in healthcare."},
}

@router.get("/v1/compliance/states")
def get_state_requirements():
    return _STATE_REQUIREMENTS

class PolicyEvaluateRequest(BaseModel):
    session_id: str
    agent_id: str
    transcript_text: str
    disclosure_confirmed: bool

@router.post("/v1/policy/evaluate")
def evaluate_policy(body: PolicyEvaluateRequest):
    result = run_voice_policy(
        transcript_text=body.transcript_text,
        session_state={"disclosure_confirmed": body.disclosure_confirmed},
    )
    return {
        "session_id": body.session_id,
        "action": result["action"],
        "reason_code": result["reason_code"],
        "policy_version": result["policy_version"],
    }