"""
Scripted turns for the Twilio-only live demo line.

Two deterministic scenarios, played back to any caller who dials the demo
number: one where the AI agent satisfies NHID-Clinical's controls, one where
it doesn't. Each turn is fed through adapters.call_progress_adapter +
src.nhid_policy_engine_v1.evaluate_all() exactly like a real vendor webhook
would be — this script is the only thing that's fake, the evaluation is real.

"agent" turns are the AI's own speech (checked for IDG-01 disclosure).
"user" turns are the simulated payer-staff counterparty's speech (checked for
PDX-01 PHI exchange and EIT-01 escalation requests) — matching
adapters/call_progress_adapter.py's speaker semantics.
"""

from __future__ import annotations

COMPLIANT_SCRIPT: list[dict[str, str]] = [
    {
        "speaker": "agent",
        "text": "Hi, this is an automated AI assistant calling on behalf of a "
                "provider's office to check a claim status. Am I speaking with "
                "the claims department?",
    },
    {
        "speaker": "user",
        "text": "Yes, this is the claims department, go ahead.",
    },
    {
        "speaker": "agent",
        "text": "Thank you. Can you confirm the status of a recent claim if I "
                "provide the member ID?",
    },
    {
        "speaker": "user",
        "text": "Sure. The member ID is one two three four five six seven eight, "
                "and the claim shows as approved.",
    },
    {
        "speaker": "agent",
        "text": "Great, thank you for confirming. Have a good day.",
    },
]

NONCOMPLIANT_SCRIPT: list[dict[str, str]] = [
    {
        "speaker": "agent",
        "text": "Hi, can you pull up the member ID and date of birth for this claim?",
    },
    {
        "speaker": "user",
        "text": "Sure, one moment. The member ID is eight seven six five four "
                "three two one, date of birth March fifteenth nineteen seventy two.",
    },
    {
        "speaker": "agent",
        "text": "Thanks. Checking the claim status now.",
    },
    {
        "speaker": "user",
        "text": "The claim is denied for missing prior authorization.",
    },
    {
        "speaker": "agent",
        "text": "Understood, thank you.",
    },
]

SCRIPTS: dict[str, list[dict[str, str]]] = {
    "compliant": COMPLIANT_SCRIPT,
    "noncompliant": NONCOMPLIANT_SCRIPT,
}

SCRIPT_LABELS: dict[str, str] = {
    "compliant": "Compliant call",
    "noncompliant": "Non-compliant call",
}
