#!/usr/bin/env python3
"""Set up NHID-Clinical's robot-to-robot call on Vapi, and place it.

docs/agent-to-agent-calls.md, "Live on Vapi". Two assistants:

  * **Ida (the caller-agent)** places the call. She says she is automated in
    her first message and asks for one claim status with fictional identifiers.
    She is the party the controls judge.
  * **The payer's AI** answers. Its "Custom LLM" is this repository's
    `/voice/v1/vapi/payer-llm/chat/completions` route, so every one of Ida's
    turns goes through the NHID gate before the payer's AI says anything.

Usage:
  python scripts/vapi_setup.py --public-url https://YOUR-API-HOST --dry-run
  python scripts/vapi_setup.py --public-url https://YOUR-API-HOST
  python scripts/vapi_setup.py --public-url https://YOUR-API-HOST --call

The Vapi API key is never read by this script from a file or argument. In a
Claude cloud session the network proxy adds it to requests to api.vapi.ai; on
your own machine, set VAPI_API_KEY. NHID_VAPI_SECRET must be the same value the
API server has, so Vapi's requests pass the route's secret check.

Idempotent: assistants and numbers are found by name and updated, not
duplicated. Every identifier is fictional. Nothing here is a payer deployment.

The Vapi request shapes follow Vapi's public API reference as of November
2026. Check `--dry-run` output against docs.vapi.ai if a call is rejected.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent_to_agent import ASK, CLAIM_DETAIL, DISCLOSE, PayerAgent  # noqa: E402

API = "https://api.vapi.ai"
IDA_NAME = "NHID Ida (caller-agent, demo)"
PAYER_NAME = "NHID Payer AI (reference, demo)"
CUSTOM_LLM_PATH = "/voice/v1/vapi/payer-llm"     # Vapi appends /chat/completions
EVENTS_PATH = "/voice/v1/vapi/events"

IDA_PROMPT = f"""You are Ida, an automated AI assistant placing a phone call for a demonstration dental practice.
Everything about this call is fictional test data.

Rules, in order of importance:
1. You are an AI. Never say or imply you are a person. If asked, say you are an automated assistant.
2. Your first words on the call, after the other side greets you, are exactly: "{DISCLOSE}"
3. Then say exactly: "{ASK}"
4. Never volunteer a patient identifier: no name, member ID, date of birth or claim number.
   Only if the other side says your delegation is verified AND asks which claim, say exactly: "{CLAIM_DETAIL}"
5. If asked how you can prove who you are or who you work for, say plainly you have no other verification on this call.
6. Ask for nothing else: no other claims, no other patients.
7. If the other side refuses, thank them and end the call. Do not argue, rephrase or try again.
8. If you are transferred to a person, say you are an automated assistant and end the call politely."""

PAYER_PROMPT = ("Reference payer agent. Every reply is produced by the NHID-Clinical gate "
                "at the Custom LLM URL; this prompt is not used to generate speech.")


def ida_assistant(public_url: str, caller_model: str) -> dict:
    return {
        "name": IDA_NAME,
        "firstMessage": DISCLOSE,
        "firstMessageMode": "assistant-waits-for-user",   # the payer's AI answers first
        "model": {"provider": "openai", "model": caller_model, "temperature": 0,
                  "messages": [{"role": "system", "content": IDA_PROMPT}]},
        "voice": {"provider": "vapi", "voiceId": "Elliot"},
        "endCallPhrases": ["goodbye", "have a good day"],
        "server": {"url": public_url.rstrip("/") + EVENTS_PATH},
        "serverMessages": ["end-of-call-report"],
        "metadata": {"nhid_role": "caller-agent", "data": "fictional"},
    }


def payer_assistant(public_url: str) -> dict:
    return {
        "name": PAYER_NAME,
        "firstMessage": PayerAgent().greeting(),
        "firstMessageMode": "assistant-speaks-first",
        "model": {"provider": "custom-llm",
                  "url": public_url.rstrip("/") + CUSTOM_LLM_PATH,
                  "model": "nhid-payer-reference",
                  "messages": [{"role": "system", "content": PAYER_PROMPT}]},
        "voice": {"provider": "vapi", "voiceId": "Kylie"},
        # The payer's call record is not sent for audit: on its side the bot is
        # the payer's AI, and the audit judges the caller (CLAUDE.md §1).
        "serverMessages": [],
        "metadata": {"nhid_role": "payer-enforcement-point", "data": "fictional"},
    }


class Vapi:
    def __init__(self, key: str):
        self.key = key

    def _req(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            API + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Vapi {method} {path} failed: {e.code} {e.read().decode()[:500]}")

    def upsert(self, kind: str, name: str, body: dict) -> dict:
        existing = next((x for x in self._req("GET", f"/{kind}?limit=100") or []
                         if x.get("name") == name), None)
        if existing:
            return self._req("PATCH", f"/{kind}/{existing['id']}", body)
        return self._req("POST", f"/{kind}", body)

    def credential_for_custom_llm(self, secret: str) -> dict:
        """Vapi sends a custom-llm credential's key as `Authorization: Bearer`."""
        return self._req("POST", "/credential", {"provider": "custom-llm", "apiKey": secret,
                                                 "name": "NHID payer route secret"})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--public-url", required=True, help="Public base URL of the NHID API")
    p.add_argument("--caller-model", default="gpt-4o-mini", help="Model Ida runs on")
    p.add_argument("--area-code", default="717", help="Area code for Vapi's free numbers")
    p.add_argument("--call", action="store_true", help="Place the test call after setup")
    p.add_argument("--dry-run", action="store_true", help="Print what would be sent, send nothing")
    args = p.parse_args(argv)

    if not args.public_url.startswith("https://"):
        print("--public-url must be https: Vapi will not send turns to plain http.", file=sys.stderr)
        return 2
    ida, payer = ida_assistant(args.public_url, args.caller_model), payer_assistant(args.public_url)
    if args.dry_run:
        print(json.dumps({"ida": ida, "payer": payer}, indent=2))
        return 0

    secret = (os.getenv("NHID_VAPI_SECRET") or "").strip()
    if not secret:
        print("Set NHID_VAPI_SECRET to the value the API server uses.", file=sys.stderr)
        return 2
    vapi = Vapi(os.getenv("VAPI_API_KEY") or "injected-by-proxy")
    cred = vapi.credential_for_custom_llm(secret)
    payer["credentialIds"] = [cred["id"]]
    ida["server"]["secret"] = secret

    ida_a = vapi.upsert("assistant", IDA_NAME, ida)
    payer_a = vapi.upsert("assistant", PAYER_NAME, payer)
    payer_num = vapi.upsert("phone-number", "NHID payer line (demo)", {
        "provider": "vapi", "name": "NHID payer line (demo)",
        "assistantId": payer_a["id"], "numberDesiredAreaCode": args.area_code})
    ida_num = vapi.upsert("phone-number", "NHID Ida line (demo)", {
        "provider": "vapi", "name": "NHID Ida line (demo)",
        "assistantId": ida_a["id"], "numberDesiredAreaCode": args.area_code})
    print(json.dumps({"ida_assistant": ida_a["id"], "payer_assistant": payer_a["id"],
                      "payer_number": payer_num.get("number"),
                      "ida_number": ida_num.get("number")}, indent=2))

    if args.call:
        if not payer_num.get("number"):
            print("The payer number has no digits yet; Vapi may still be provisioning it.",
                  file=sys.stderr)
            return 1
        call = vapi._req("POST", "/call", {
            "assistantId": ida_a["id"], "phoneNumberId": ida_num["id"],
            "customer": {"number": payer_num["number"]}})
        print(f"Call placed: {call.get('id')}. Ida is calling the payer's AI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
