import hashlib
import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse

from llm import call_llm
from nhid_event_store import (
    append_events_batch,
    get_events,
    get_events_for_request,
    get_response_for_request,
    get_session_trace,
    is_duplicate_request,
    reconstruct_session,
    reconstruct_session_from_events,
)
from nhid_policy import NHIDPolicyEngine, PolicyAction
from twilio_helper import twiml

app = FastAPI()
policy = NHIDPolicyEngine()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nhid-proxy")


@app.post("/voice/incoming")
async def incoming(request: Request):
    """INGRESS LAYER: Accept incoming call.

    Minimal I/O boundary. Routes to orchestrator.
    """
    session_id = "unknown"

    try:
        form = await request.form()
        session_id = (form.get("CallSid") or "unknown").strip()

        tw_response = twiml(
            "This is an automated healthcare intake system. Please describe your concern."
        )

        append_events_batch(
            session_id,
            [
                {
                    "event_type": "CALL_STARTED",
                    "state_before": "INIT",
                    "state_after": "DISCLOSURE",
                    "input_text": None,
                    "policy_action": "CALL_STARTED",
                    "reason_code": "CALL_STARTED",
                    "response_text": None,
                    "policy_version": policy.POLICY_VERSION,
                },
                {
                    "event_type": "RESPONSE",
                    "state_before": "DISCLOSURE",
                    "state_after": "DISCLOSURE",
                    "input_text": None,
                    "policy_action": "CALL_STARTED",
                    "reason_code": "CALL_STARTED",
                    "response_text": tw_response,
                    "policy_version": policy.POLICY_VERSION,
                },
            ],
            "incoming",
            mark_processed=True,
        )

        logger.info(
            "incoming call",
            extra={
                "call_sid": session_id,
                "state_before": "INIT",
                "state_after": "DISCLOSURE",
                "policy_action": "CALL_STARTED",
                "reason_code": "CALL_STARTED",
                "request_id": "incoming",
            },
        )

        return Response(content=tw_response, media_type="application/xml")
    except Exception:
        logger.exception("incoming failure", extra={"call_sid": session_id})
        raise HTTPException(status_code=500, detail="incoming failure")


def _generate_request_id(session_id: str, user_text: str, message_sid: str = None) -> str:
    # Deterministic idempotency key.
    # Prefer explicit MessageSid when provided by Twilio.
    if message_sid:
        return f"{session_id}:{message_sid}"

    # If MessageSid is not provided, derive a stable hash from the session_id
    # and user_text (no time component) to ensure deterministic keys across retries.
    digest = hashlib.sha256(f"{session_id}:{user_text}".encode("utf-8")).hexdigest()
    return f"{session_id}:{digest}"


async def process_pipeline(request: Request) -> str:
    session_id = "unknown"
    request_id = None

    try:
        form = await request.form()
        session_id = (form.get("CallSid") or "unknown").strip()
        message_sid = (form.get("MessageSid") or "").strip()
        raw_text = form.get("SpeechResult")
        user_text = " ".join((raw_text or "").split())

        request_id = _generate_request_id(session_id, user_text, message_sid)
        if is_duplicate_request(request_id):
            cached_response = get_response_for_request(request_id)
            if cached_response is not None:
                return cached_response

            # Recovery path for an inconsistent processed request: reconstruct session and regenerate response deterministically
            from nhid_event_store import get_events_for_request

            request_events = get_events_for_request(request_id)
            if not request_events:
                raise HTTPException(
                    status_code=500,
                    detail=f"duplicate request {request_id} has no recorded events",
                )

            session_id_for_request = request_events[0].get("session_id") or session_id
            all_events = reconstruct_session(session_id_for_request)
            event_chain = [e for e in get_events(session_id_for_request) if e.get("id") < request_events[0].get("id")]
            from nhid_event_store import reconstruct_session_from_events
            prior_session = reconstruct_session_from_events(event_chain)

            user_input_event = next((e for e in request_events if e.get("event_type") == "USER_INPUT"), None)
            if not user_input_event:
                raise HTTPException(
                    status_code=500,
                    detail=f"duplicate request {request_id} missing USER_INPUT for recovery",
                )
            recovered_user_text = user_input_event.get("input_text") or ""

            try:
                decision = policy.evaluate(prior_session, recovered_user_text)
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail=f"duplicate request {request_id} recovery failed during policy re-evaluation",
                )

            if decision.action == PolicyAction.ROUTE_LLM:
                decision_event = next((e for e in request_events if e.get("event_type") == "POLICY_DECISION"), None)
                llm_output_value = decision_event.get("llm_output") if decision_event else None
                if llm_output_value is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"duplicate request {request_id} missing cached LLM output for recovery",
                    )
                response_payload = llm_output_value
            else:
                if decision.message is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"duplicate request {request_id} recovery could not derive message",
                    )
                response_payload = decision.message

            return twiml(response_payload, gather=decision.gather)

        session = reconstruct_session(session_id)
        session["turn_count"] += 1
        session["last_user_text"] = user_text

        try:
            decision = policy.evaluate(session, user_text)
        except Exception:
            logger.exception("policy failure", extra={"call_sid": session_id, "request_id": request_id})
            raise HTTPException(status_code=500, detail="policy evaluation failed")

        if decision.action == PolicyAction.ROUTE_LLM:
            llm_output = await call_llm(user_text)
            response_payload = llm_output
            llm_input = user_text
            llm_output_value = llm_output
        else:
            if decision.message is None:
                logger.error(
                    "policy decision produced no message",
                    extra={"call_sid": session_id, "request_id": request_id, "action": decision.action},
                )
                raise HTTPException(status_code=500, detail="policy decision returned no message")
            response_payload = decision.message
            llm_input = None
            llm_output_value = None

        tw_response = twiml(response_payload, gather=decision.gather)

        append_events_batch(
            session_id,
            [
                {
                    "event_type": "USER_INPUT",
                    "state_before": session.get("state"),
                    "state_after": session.get("state"),
                    "input_text": user_text,
                    "policy_action": None,
                    "reason_code": None,
                    "response_text": None,
                    "policy_version": session.get("policy_version"),
                },
                {
                    "event_type": "POLICY_DECISION",
                    "state_before": session.get("state"),
                    "state_after": decision.next_state,
                    "input_text": user_text,
                    "policy_action": decision.action.value,
                    "reason_code": decision.reason_code,
                    "response_text": None,
                    "llm_input": llm_input,
                    "llm_output": llm_output_value,
                    "policy_version": decision.policy_version,
                },
                {
                    "event_type": "STATE_TRANSITION",
                    "state_before": session.get("state"),
                    "state_after": decision.next_state,
                    "input_text": user_text,
                    "policy_action": decision.action.value,
                    "reason_code": decision.reason_code,
                    "response_text": None,
                    "policy_version": decision.policy_version,
                },
                {
                    "event_type": "RESPONSE",
                    "state_before": decision.next_state,
                    "state_after": decision.next_state,
                    "input_text": user_text,
                    "policy_action": decision.action.value,
                    "reason_code": decision.reason_code,
                    "response_text": tw_response,
                    "llm_input": llm_input,
                    "llm_output": llm_output_value,
                    "policy_version": decision.policy_version,
                },
            ],
            request_id,
            mark_processed=True,
        )
        return tw_response
    except HTTPException:
        raise
    except Exception:
        logger.exception("pipeline failure", extra={"call_sid": session_id, "request_id": request_id})
        raise HTTPException(status_code=500, detail="pipeline failure")


@app.post("/voice/process")
async def process(request: Request):
    return Response(
        content=await process_pipeline(request),
        media_type="application/xml",
    )


@app.get("/debug/replay/{session_id}")
async def debug_replay(session_id: str):
    """DEBUG ENDPOINT: Full forensic trace.

    Returns complete call replay for audit + debugging.
    """
    try:
        trace = get_session_trace(session_id)
        return JSONResponse(trace)
    except Exception:
        return JSONResponse(
            {
                "call_sid": session_id,
                "error": "could not reconstruct session",
            },
            status_code=500,
        )

