import asyncio
from pathlib import Path
from pprint import pprint

from app import _generate_request_id
from nhid_event_store import (
    append_events_batch,
    append_event,
    mark_request_processed,
    is_duplicate_request,
    get_response_for_request,
    reconstruct_session,
    get_session_trace,
    get_events,
)
from nhid_policy import NHIDPolicyEngine, PolicyAction
from nhid_engine import apply_state
from llm import call_llm
from twilio_helper import twiml

policy = NHIDPolicyEngine()


async def run_full_pipeline(session_id: str, message_sid: str, user_text: str, request_id: str = None):
    request_id = request_id or _generate_request_id(session_id, user_text, message_sid)

    # 1 & 2: idempotency check
    if is_duplicate_request(request_id):
        return get_response_for_request(request_id)

    # reconstruct
    session = reconstruct_session(session_id)

    # 3. append USER_INPUT
    user_event = {
        "event_type": "USER_INPUT",
        "state_before": session.get("state"),
        "state_after": session.get("state"),
        "input_text": user_text,
        "policy_action": None,
        "reason_code": None,
        "response_text": None,
    }
    append_events_batch(session_id, [user_event], request_id)

    # 4. policy
    decision = policy.evaluate(session, user_text)

    # 5. append POLICY_DECISION
    pd = {
        "event_type": "POLICY_DECISION",
        "state_before": session.get("state"),
        "state_after": decision.next_state,
        "input_text": user_text,
        "policy_action": decision.action.value,
        "reason_code": decision.reason_code,
        "response_text": None,
        "policy_version": decision.policy_version,
    }
    append_events_batch(session_id, [pd], request_id)

    # 6. apply state transition
    current_state = session.get("state")
    next_state = apply_state(current_state, decision.next_state)

    # 7. append STATE_TRANSITION
    st = {
        "event_type": "STATE_TRANSITION",
        "state_before": current_state,
        "state_after": next_state,
        "input_text": user_text,
        "policy_action": decision.action.value,
        "reason_code": decision.reason_code,
        "response_text": None,
        "policy_version": decision.policy_version,
    }
    append_events_batch(session_id, [st], request_id)

    # 8. execute action
    if decision.action == PolicyAction.ROUTE_LLM:
        response_text = await call_llm(user_text)
        gather = True
    elif decision.action == PolicyAction.ESCALATE:
        response_text = decision.message
        gather = False
    elif decision.action == PolicyAction.BLOCK:
        response_text = decision.message
        gather = False
    elif decision.action == PolicyAction.DISCLOSE:
        response_text = decision.message
        gather = True
    else:
        response_text = "system error"
        gather = False

    # 9. append RESPONSE (store TwiML so duplicates return identical payload)
    tw_response = twiml(response_text, gather=gather)
    resp = {
        "event_type": "RESPONSE",
        "state_before": next_state,
        "state_after": next_state,
        "input_text": user_text,
        "policy_action": decision.action.value,
        "reason_code": decision.reason_code,
        "response_text": tw_response,
        "policy_version": decision.policy_version,
    }
    append_events_batch(session_id, [resp], request_id)

    # mark processed
    mark_request_processed(request_id, session_id)

    # 10 return TwiML content
    return tw_response


async def test_duplicate_webhook():
    session = "dup-test-session"
    message_sid = "msg-1"
    user_text = "hello world"

    # ensure clean DB
    Path('nhid_events.db').unlink(missing_ok=True)

    # first run
    first = await run_full_pipeline(session, message_sid, user_text)

    # repeated runs
    responses = [await run_full_pipeline(session, message_sid, user_text) for _ in range(9)]

    all_same = all(r == first for r in responses)

    events = [e for e in get_events(session) if e.get('request_id')]
    # filter only this request_id
    # count distinct event_types
    request_id = _generate_request_id(session, user_text, message_sid)
    events_for_req = [e for e in events if e.get('request_id') == request_id]
    types = [e['event_type'] for e in events_for_req]

    return {
        'first_response': first,
        'all_duplicates_same': all_same,
        'request_id': request_id,
        'event_types': types,
        'events_count': len(events_for_req),
    }


async def test_crash_recovery():
    session = "crash-session"
    message_sid = "msg-crash"
    user_text = "please create"

    Path('nhid_events.db').unlink(missing_ok=True)

    request_id = _generate_request_id(session, user_text, message_sid)

    # 1: append USER_INPUT and POLICY_DECISION only (simulate crash before state/response)
    sess = reconstruct_session(session)
    user_event = {
        "event_type": "USER_INPUT",
        "state_before": sess.get('state'),
        "state_after": sess.get('state'),
        "input_text": user_text,
        "policy_action": None,
        "reason_code": None,
        "response_text": None,
    }
    append_events_batch(session, [user_event], request_id)

    decision = policy.evaluate(sess, user_text)
    pd = {
        "event_type": "POLICY_DECISION",
        "state_before": sess.get('state'),
        "state_after": decision.next_state,
        "input_text": user_text,
        "policy_action": decision.action.value,
        "reason_code": decision.reason_code,
        "response_text": None,
        "policy_version": decision.policy_version,
    }
    append_events_batch(session, [pd], request_id)

    # simulate crash (no state transition or response persisted)

    # restart and run full pipeline again (should complete and not duplicate events)
    final = await run_full_pipeline(session, message_sid, user_text, request_id=request_id)

    events_for_req = [e for e in get_events(session) if e.get('request_id') == request_id]
    types = [e['event_type'] for e in events_for_req]

    reconstructed = reconstruct_session(session)

    return {
        'final_response': final,
        'event_types': types,
        'events_count': len(events_for_req),
        'reconstructed_state': reconstructed,
    }


async def test_memory_wipe():
    session = 'mem-wipe'
    message_sid = 'm1'
    user_text = 'status'

    Path('nhid_events.db').unlink(missing_ok=True)

    # run pipeline
    resp = await run_full_pipeline(session, message_sid, user_text)

    # ensure no runtime memory relied on: call reconstruct_session anew
    reconstructed = reconstruct_session(session)

    return {'response': resp, 'reconstructed': reconstructed}


async def test_concurrency():
    session = 'concur'
    Path('nhid_events.db').unlink(missing_ok=True)

    tasks = []
    for i in range(5):
        ms = f'msg-{i}'
        tasks.append(run_full_pipeline(session, ms, f'hello {i}'))

    results = await asyncio.gather(*tasks)

    # verify processed_requests count and events
    evs = get_events(session)
    request_ids = set(e['request_id'] for e in evs if e.get('request_id'))
    return {'responses': results, 'unique_request_ids': len(request_ids), 'events_total': len(evs)}


async def test_parallel_duplicate_requests():
    session = 'parallel-dup'
    message_sid = 'dup-1'
    user_text = 'parallel test'
    Path('nhid_events.db').unlink(missing_ok=True)

    # Launch multiple identical requests concurrently
    tasks = [run_full_pipeline(session, message_sid, user_text) for _ in range(8)]
    results = await asyncio.gather(*tasks)

    request_id = _generate_request_id(session, user_text, message_sid)
    evs = [e for e in get_events(session) if e.get('request_id') == request_id]

    return {
        'responses': results,
        'events_count': len(evs),
        'event_types': [e['event_type'] for e in evs],
    }


async def main():
    print('Running Test A: duplicate webhook')
    a = await test_duplicate_webhook()
    pprint(a)

    print('\nRunning Test B: crash recovery')
    b = await test_crash_recovery()
    pprint(b)

    print('\nRunning Test C: memory wipe')
    c = await test_memory_wipe()
    pprint(c)

    print('\nRunning Test D: concurrency')
    d = await test_concurrency()
    pprint(d)


if __name__ == '__main__':
    asyncio.run(main())
