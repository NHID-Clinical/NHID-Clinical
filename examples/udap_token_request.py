"""
NHID-Clinical — putting a delegation into a UDAP B2B token request

Run this directly:
    python examples/udap_token_request.py

What it demonstrates:
    1. A provider issues a scoped, NPI-bound, call-bound delegation
    2. The `hl7-b2b` object UDAP requires — and the hole in it
    3. The `nhid-agent` sibling object that fills the hole
    4. The receiving side verifying it: passport first, then every field
    5. A tampered field, with the passport signature still perfectly valid
    6. A purpose of use the provider never delegated authority for

Every identifier here is synthetic. `1234567890` is the NPI from UDAP's own
worked format example and `CA-SYNTHETIC-*` are not real call identifiers.
The engine format-validates an NPI and nothing more, so no example needs a
registered one — and none should have one.

What this is NOT: a conformance demonstration. `nhid-agent` is a proposal
against the extension point UDAP's own text leaves open; it carries no HL7,
UDAP.org or trust-community standing, and no payer has evaluated it. See
docs/claim-boundaries.md.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.agent_identity import AgentIdentityManager
from src.udap_agent_extension import (
    build_extension,
    check_purpose_of_use,
    purpose_of_use_to_uri,
    purposes_for_scope,
    verify_extension,
)

PROVIDER_NPI = "1234567890"
CALL_SID = "CA-SYNTHETIC-0001"


def section(title):
    print(f"\n{'─' * 68}")
    print(f"  {title}")
    print(f"{'─' * 68}")


def show(label, obj):
    print(f"{label}:\n{json.dumps(obj, indent=2)}")


def main():
    manager = AgentIdentityManager()

    # ── 1. The provider delegates ────────────────────────────────────────────
    section("1. The provider issues a delegation")
    prov_priv, prov_pub = manager.generate_agent_keys()
    agent_priv, agent_pub = manager.generate_agent_keys()

    delegation = manager.create_delegation(
        prov_priv, "agent-frontdesk-01", agent_pub,
        scope=["eligibility", "claim_status"],
        call_sid=CALL_SID,
        provider_npi=PROVIDER_NPI,
    )
    passport = manager.create_agent_passport(
        delegation, manager.sign_delegation(prov_priv, delegation), agent_priv
    )
    print(f"  provider NPI : {delegation.provider_npi}")
    print(f"  agent        : {delegation.agent_id}")
    print(f"  scope        : {delegation.scope}")
    print(f"  bound to call: {delegation.call_sid}")

    # ── 2. What UDAP can say about this agent today ──────────────────────────
    section("2. The `hl7-b2b` object — and what it cannot say")
    hl7_b2b = {
        "version": "1",
        "subject_name": delegation.agent_id,
        "organization_id": "https://clinic.example.org",
        "purpose_of_use": purposes_for_scope(delegation.scope),
    }
    show("  hl7-b2b", hl7_b2b)
    print("\n  Note what is absent and why:")
    print("    subject_id   — UDAP: \"Omit for non-human requestors\"")
    print("    subject_role — UDAP: required only \"for human requestors\"")
    print("  So the agent is a name string. Nothing here says which provider")
    print("  authorized it, for what, until when, or on which call.")

    # ── 3. The sibling object ────────────────────────────────────────────────
    section("3. The `nhid-agent` sibling object")
    extension = build_extension(passport)
    show("  nhid-agent", extension)
    print("\n  Every field is read off the signed delegation. There are no")
    print("  caller-supplied fields, which is what makes step 4 total.")

    section("4. What actually goes in the authentication JWT")
    show("  extensions", {"hl7-b2b": hl7_b2b, "nhid-agent": extension})

    # ── 5. The receiving side checks it ──────────────────────────────────────
    section("5. The receiving side verifies — passport first")
    result = verify_extension(extension, passport, prov_pub,
                              manager=manager, call_sid=CALL_SID)
    print(f"  valid        : {result.valid}")
    print(f"  reason       : {result.reason}")
    print(f"  provider NPI : {result.provider_npi}   (from the signature,")
    print( "                 not from the object that claimed it)")

    purpose = check_purpose_of_use(hl7_b2b, result.scope)
    print(f"\n  purpose check: {purpose.valid} — {purpose.reason}")

    # ── 6. A tampered field, over a valid signature ──────────────────────────
    section("6. A tampered field — the signature is still valid")
    tampered = dict(extension,
                    provider_npi="urn:oid:2.16.840.1.113883.4.6#9999999999")
    bad = verify_extension(tampered, passport, prov_pub,
                           manager=manager, call_sid=CALL_SID)
    print("  The passport is untouched and verifies. Only the object lies.")
    print(f"  valid        : {bad.valid}")
    print(f"  reason       : {bad.reason}")
    print("\n  This is the whole point. An object that could disagree with")
    print("  its passport and still pass would launder an unsigned claim")
    print("  through something that looks cryptographic.")

    # ── 7. A purpose the provider never delegated ────────────────────────────
    section("7. A purpose of use outside the delegation")
    overreaching = dict(hl7_b2b,
                        purpose_of_use=[purpose_of_use_to_uri("COVAUTH")])
    print("  The token request asserts COVAUTH — prior authorization.")
    print(f"  The delegation covers {delegation.scope}.")
    over = check_purpose_of_use(overreaching, result.scope)
    print(f"\n  valid        : {over.valid}")
    print(f"  reason       : {over.reason}")
    print("\n  Nothing in UDAP can detect this today, because today there is")
    print("  no delegation in the token request to compare the purpose to.")

    section("Done")
    print("  Nothing above contacted a network or a payer. Verification is")
    print("  offline against a provider public key the verifier already has.")
    print("  See docs/nhid-auth-pki-and-oauth2-integration.md §3.1–3.3.")


if __name__ == "__main__":
    main()
