#!/usr/bin/env python3
"""Mint demonstration credentials for Ida, the reference caller-agent.

Prints the environment values a demo deployment needs, as KEY=value lines:

  IDA_AGENT_KEY_B64     Ida's own Ed25519 key (agent side; a secret)
  IDA_PRACTICE_KEY_B64  the fictional practice's root key (issuer side; a secret)
  IDA_PRACTICE_NPI      the practice's fictional NPI
  IDA_PRACTICE_KID      which practice key signed
  NHID_TRUST_ANCHORS    the practice's public key, as the payer gate trusts it

Put the two keys in the deployment's secret store (NoEcho parameters), never in
the repository. These are demonstration keys for a fictional practice; nothing
here is a production credential, and no one should trust them for anything else.

    python scripts/ida_demo_credentials.py            # print values
    python scripts/ida_demo_credentials.py --selftest # run one gated turn in-process
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from src.reference_agent import (  # noqa: E402
    DEMO_PRACTICE_NPI, PracticeIssuer, private_key_to_b64,
)


def mint() -> dict:
    practice = PracticeIssuer(key=Ed25519PrivateKey.generate(), npi=DEMO_PRACTICE_NPI, kid="demo-1")
    return {
        "IDA_AGENT_KEY_B64": private_key_to_b64(Ed25519PrivateKey.generate()),
        "IDA_PRACTICE_KEY_B64": private_key_to_b64(practice.key),
        "IDA_PRACTICE_NPI": practice.npi,
        "IDA_PRACTICE_KID": practice.kid,
        "NHID_TRUST_ANCHORS": practice.trust_anchor_entry(),
    }


def selftest(values: dict) -> int:
    os.environ.update(values)
    from functions import handler
    handler._IDA_SIGNER = None
    status, body = handler.ida_gate({
        "session_id": "CA-selftest-0001",
        "turn": "The member ID is RVD-204-7731 and the claim number is 9921-0417. What's the status?",
        "disclosed": "true",
        "turn_index": "2",
        "heard": "Go ahead.",
    })
    print(f"status {status}: action={body.get('action')} reason={body.get('reason_code')} "
          f"allowed={body.get('allowed')} delegation_checked={body.get('delegation_checked')}")
    return 0 if status == 200 and body.get("allowed") and body.get("delegation_checked") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run one gated turn in-process")
    args = ap.parse_args()
    values = mint()
    if args.selftest:
        return selftest(values)
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
