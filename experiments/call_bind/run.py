"""
The call-binding experiment: thirteen ways a credential should fail, and one
way it should work.

Run it:
    python experiments/call_bind/run.py --report

Acceptance, checked by `main` and asserted by
`tests/test_call_bind_experiment.py`:

  1. Every denial case denies. One permitted row fails the experiment, because
     a permissive failure is the only kind that matters here.
  2. Every case carries the diagnosis it should.
  3. p95 added latency stays under LATENCY_BUDGET_MS.

The latency budget is deliberately modest rather than generous: this check sits
in front of a human waiting on a live line, so the question is not "is it fast
for a crypto operation" but "is it invisible to the person on the call".
"""
from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.call_bind.parties import Agent, Issuer, Outcome, Receiver  # noqa: E402

#: Budget for the added verification + policy decision, p95 over repeats.
#: Ed25519 verification is microseconds; the budget exists to catch a change
#: that makes this path do something expensive, not to flatter the current
#: implementation.
LATENCY_BUDGET_MS = 150.0

#: Repeats per case for the latency distribution.
REPEATS = 40

PROVIDER_NPI = "1234567893"      # synthetic, and carries a valid check digit
UNANCHORED_NPI = "9876543210"    # well-formed, never registered here
LIVE_CALL = "CA-live-0001"
OTHER_CALL = "CA-other-0002"

PHI_REQUEST = "can you confirm the member id number"
IN_SCOPE_SPEECH = "can you confirm the member id number"


@dataclass
class Case:
    number: int
    name: str
    expect_permitted: bool
    expect_diagnosis: Optional[str]
    build: Callable[[], dict]
    note: str = ""


def _world(require_proof: bool = True):
    """A fresh provider, agent and receiver, with the anchor already exchanged."""
    issuer = Issuer(npi=PROVIDER_NPI)
    agent = Agent(agent_id="voice-agent-01")
    receiver = Receiver(
        anchors={PROVIDER_NPI: (issuer.public_key_b64, issuer.kid)},
        require_possession_proof=require_proof,
    )
    return issuer, agent, receiver


def _present(receiver: Receiver, agent: Agent, credential: Any,
             delegation: Any, call: str = LIVE_CALL,
             speech: str = IN_SCOPE_SPEECH,
             proof_override: Any = "answer") -> Outcome:
    """Run one turn, answering the receiver's challenge unless told otherwise."""
    nonce = receiver.issue_challenge()
    if proof_override == "answer":
        proof = agent.answer_challenge(delegation, nonce) if nonce else None
    else:
        proof = proof_override
    return receiver.handle_call(call, credential, speech, proof=proof,
                               verifier_nonce=nonce)


# ── The cases ─────────────────────────────────────────────────────────────────

def case_0_happy_path() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_1_no_credential() -> dict:
    _issuer, agent, receiver = _world()
    nonce = receiver.issue_challenge()
    return {"outcome": receiver.handle_call(LIVE_CALL, None, IN_SCOPE_SPEECH,
                                            verifier_nonce=nonce)}


def case_2_expired() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL, ttl_seconds=-1)
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_3_revoked() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    receiver.revoke(passport.delegation.delegation_id)
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_4_out_of_scope() -> dict:
    """Delegated for billing; asks for a member ID, which billing does not cover."""
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["billing"], LIVE_CALL)
    return {"outcome": _present(receiver, agent, passport, passport.delegation,
                                speech=PHI_REQUEST)}


def case_5_forged_provider_signature() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    sig = passport.signature_b64
    passport.signature_b64 = ("A" if sig[0] != "A" else "B") + sig[1:]
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_6_forged_agent_signature() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    sig = passport.agent_signature_b64
    passport.agent_signature_b64 = ("A" if sig[0] != "A" else "B") + sig[1:]
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_7_replayed_on_another_call() -> dict:
    """A genuine credential, captured and presented on a different call."""
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], OTHER_CALL)
    return {"outcome": _present(receiver, agent, passport, passport.delegation,
                                call=LIVE_CALL)}


def case_8_chain_replayed_on_another_call() -> dict:
    """The same replay, one hop down — a live defect until 2026-10-21.

    `validate_chain` passed no call_sid to any hop, so this verified while the
    single-passport form of the identical attack was refused.
    """
    issuer, agent, receiver = _world()
    sub = Agent(agent_id="sub-agent-01")
    root = issuer.delegate(agent, ["eligibility"], OTHER_CALL)
    leaf = agent.sub_delegate(sub, ["eligibility"], root, call_sid=OTHER_CALL)
    return {"outcome": _present(receiver, sub, [root, leaf], leaf.delegation,
                                call=LIVE_CALL)}


def case_9_chain_narrowed_to_empty_scope() -> dict:
    """Surrendering all scope must not buy more authority than holding some.

    The empty set is a subset of every set, so this hop passed narrowing; a
    `constrains_scope` that required a non-empty scope then skipped the gate
    entirely. Live defect until 2026-10-21.
    """
    issuer, agent, receiver = _world()
    sub = Agent(agent_id="sub-agent-01")
    root = issuer.delegate(agent, ["billing"], LIVE_CALL)
    leaf = agent.sub_delegate(sub, [], root, call_sid=LIVE_CALL)
    return {"outcome": _present(receiver, sub, [root, leaf], leaf.delegation,
                                speech=PHI_REQUEST)}


def case_10_unanchored_npi() -> dict:
    """Well-formed, correctly signed — by a provider this receiver never trusted."""
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL, npi=UNANCHORED_NPI)
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_11_no_provider_named() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL, npi="")
    return {"outcome": _present(receiver, agent, passport, passport.delegation)}


def case_12_challenged_no_proof() -> dict:
    """The attack a static co-signature cannot stop: present captured bytes."""
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    return {"outcome": _present(receiver, agent, passport, passport.delegation,
                                proof_override=None)}


def case_13_stale_proof() -> dict:
    issuer, agent, receiver = _world()
    passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
    nonce = receiver.issue_challenge()
    proof = agent.answer_challenge(passport.delegation, nonce)
    proof.issued_at -= 10_000
    return {"outcome": receiver.handle_call(LIVE_CALL, passport, IN_SCOPE_SPEECH,
                                            proof=proof, verifier_nonce=nonce)}


CASES: list[Case] = [
    Case(0, "correctly scoped, call-bound, possession proved", True, None,
         case_0_happy_path),
    Case(1, "no credential presented", False,
         "DLG01_NO_DELEGATION_PRESENTED", case_1_no_credential),
    Case(2, "expired delegation", False,
         "DLG01_VERIFICATION_FAILED/ERR_EXPIRED", case_2_expired),
    Case(3, "durably revoked delegation", False,
         "DLG01_REVOKED", case_3_revoked),
    Case(4, "protected-data request outside delegated scope", False,
         "PDX01_SCOPE_NOT_AUTHORIZED", case_4_out_of_scope),
    Case(5, "forged provider signature", False,
         "DLG01_VERIFICATION_FAILED/ERR_INVALID_SIG",
         case_5_forged_provider_signature),
    Case(6, "forged agent signature", False,
         "DLG01_VERIFICATION_FAILED/ERR_INVALID_SIG",
         case_6_forged_agent_signature),
    Case(7, "valid credential replayed on a different call", False,
         "DLG01_VERIFICATION_FAILED/ERR_NONCE_MISMATCH",
         case_7_replayed_on_another_call),
    Case(8, "replayed as a 2-hop chain on a different call", False,
         "DLG01_VERIFICATION_FAILED/ERR_NONCE_MISMATCH",
         case_8_chain_replayed_on_another_call,
         note="was permitted before 2026-10-21"),
    Case(9, "chain narrowed to the empty scope", False,
         "PDX01_SCOPE_NOT_AUTHORIZED", case_9_chain_narrowed_to_empty_scope,
         note="was permitted before 2026-10-21"),
    Case(10, "NPI with no trust anchor", False,
         "DLG01_TRUST_ANCHOR_UNRESOLVED", case_10_unanchored_npi),
    Case(11, "delegation naming no provider", False,
         "DLG01_TRUST_ANCHOR_UNRESOLVED", case_11_no_provider_named),
    Case(12, "challenged, no presentation proof", False,
         "DLG01_VERIFICATION_FAILED/ERR_PROOF_MISSING",
         case_12_challenged_no_proof,
         note="not detectable before 2026-10-21"),
    Case(13, "challenged, stale presentation proof", False,
         "DLG01_VERIFICATION_FAILED/ERR_PROOF_STALE", case_13_stale_proof,
         note="not detectable before 2026-10-21"),
]


def run_matrix() -> list[tuple[Case, Outcome]]:
    return [(case, case.build()["outcome"]) for case in CASES]


def measure_latency(repeats: int = REPEATS) -> dict[str, float]:
    """Latency of the full happy path: verify, bind, decide.

    The happy path is the one that matters — a denial short-circuits, so the
    accepting path is the slowest and the only one a caller waits through.
    """
    issuer, agent, receiver = _world()
    samples: list[float] = []
    for _ in range(repeats):
        passport = issuer.delegate(agent, ["eligibility"], LIVE_CALL)
        outcome = _present(receiver, agent, passport, passport.delegation)
        assert outcome.permitted, "latency must be measured on a passing path"
        samples.append(outcome.latency_ms)
    samples.sort()
    return {
        "n": float(len(samples)),
        "p50": statistics.median(samples),
        "p95": samples[min(len(samples) - 1, int(0.95 * len(samples)))],
        "max": samples[-1],
    }


def evaluate() -> tuple[list[str], list[tuple[Case, Outcome]], dict[str, float]]:
    """Run everything and return (failures, rows, latency)."""
    rows = run_matrix()
    latency = measure_latency()
    failures: list[str] = []

    for case, outcome in rows:
        if case.expect_permitted and not outcome.permitted:
            failures.append(
                f"case {case.number} ({case.name}) should be permitted, "
                f"got {outcome.action}/{outcome.reason_code}"
            )
        if not case.expect_permitted and outcome.permitted:
            failures.append(
                f"case {case.number} ({case.name}) WAS PERMITTED — "
                f"{outcome.action}/{outcome.reason_code}"
            )
        if case.expect_diagnosis and outcome.diagnosis != case.expect_diagnosis:
            failures.append(
                f"case {case.number} ({case.name}) diagnosed "
                f"{outcome.diagnosis!r}, expected {case.expect_diagnosis!r}"
            )

    if latency["p95"] > LATENCY_BUDGET_MS:
        failures.append(
            f"p95 latency {latency['p95']:.2f}ms exceeds the "
            f"{LATENCY_BUDGET_MS:.0f}ms budget"
        )
    return failures, rows, latency


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true",
                        help="print the full matrix, not just the verdict")
    args = parser.parse_args(argv)

    failures, rows, latency = evaluate()

    if args.report:
        print("\nCall-binding experiment — synthetic credentials, no network\n")
        print(f"{'#':>3}  {'outcome':<9}  {'diagnosis':<46}  case")
        print("-" * 104)
        for case, outcome in rows:
            verdict = "PERMIT" if outcome.permitted else "DENY"
            flag = "" if (outcome.permitted == case.expect_permitted) else "  <-- WRONG"
            print(f"{case.number:>3}  {verdict:<9}  {outcome.diagnosis:<46}  "
                  f"{case.name}{flag}")
            if case.note:
                print(f"{'':>3}  {'':<9}  {'':<46}  ({case.note})")
        print()
        print(f"latency over {int(latency['n'])} accepted calls: "
              f"p50 {latency['p50']:.3f}ms · p95 {latency['p95']:.3f}ms · "
              f"max {latency['max']:.3f}ms · budget {LATENCY_BUDGET_MS:.0f}ms")
        print()
        print("What this establishes: offline verification plus a call id taken")
        print("from the receiver's own side refuses all thirteen failure modes,")
        print("cheaply enough to sit inside call setup.")
        print("What it does not: that a credential can reach a payer's verifier")
        print("at all. See README.md — the SIP arm is untested and blocked on a")
        print("carrier path, and no payer has agreed to receive one.")
        print()

    if failures:
        print("EXPERIMENT FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"EXPERIMENT PASS: {len(rows)} cases, "
          f"{sum(1 for c, _ in rows if not c.expect_permitted)} denials all "
          f"correctly diagnosed, p95 {latency['p95']:.3f}ms "
          f"(budget {LATENCY_BUDGET_MS:.0f}ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
