"""
Call-scoped verification prototype (candidate VER-01), tested without telephony.

Two halves:

* one group per requirement in docs/proposals/verification-and-nonverbal-disclosure.md
  §10, so a requirement with no test is visible as a missing group;
* the PR 1 fixtures (fixtures/verification-nonverbal/scenarios.json): each
  scenario's expected `call_verification` block is reproduced by driving the
  prototype into that situation. Only VER-01 is asserted. IDG-01, PDX-01 and
  DBC-01 expectations in those fixtures are outside this module and stay
  unmeasured.

This is candidate code. Nothing here changes the v1.3 engine or its baselines.
"""
from __future__ import annotations

import base64
import json
import threading
from pathlib import Path

import jsonschema
import pytest
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from src.agent_identity import AgentIdentityManager, PresentationProof
from src.call_verification import (
    BINDING_CHECKS,
    EXCEPTION,
    ENROLLMENT_REVOKED,
    ENROLLMENT_SUSPENDED,
    PASS,
    UNKNOWN,
    CallContext,
    CallVerificationService,
    InMemoryTokenStore,
    PortalEnrollmentRegistry,
    SqliteTokenStore,
    content_digest,
    new_intent_nonce,
    requires_out_of_band,
    serialize_signature_params,
    sign_call_intent,
    signature_base,
    verify_call_intent_signature,
)
from src.trust_anchor import StaticTrustAnchorResolver
from src.udap_agent_extension import EXTENSION_KEY, build_extension, key_fingerprint

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "verification-nonverbal" / "scenarios.json"
SCHEMA = ROOT / "schema" / "nhid_trace_schema_v1.json"

NPI = "1234567893"          # passes the NPI check digit
PAYER = "payer.example"
NUMBER = "+15555550142"
HMAC_KEY = b"k" * 32


class Clock:
    """Injected clock, so expiry is tested without sleeping."""

    def __init__(self, start: int) -> None:
        self.t = start

    def __call__(self) -> int:
        return self.t


class World:
    """A provider, an agent and one payer's verification service."""

    def __init__(self, store=None, scope=("eligibility",), handle_source=None, ttl=86400):
        import time as _time
        self.m = AgentIdentityManager()
        self.prov_priv, self.prov_pub = self.m.generate_agent_keys()
        self.agent_priv, self.agent_pub = self.m.generate_agent_keys()
        self.delegation = self.m.create_delegation(
            self.prov_priv, "agent-ava-01", self.agent_pub, scope=list(scope),
            provider_npi=NPI, ttl_seconds=ttl)
        sig = self.m.sign_delegation(self.prov_priv, self.delegation)
        self.passport = self.m.create_agent_passport(self.delegation, sig, self.agent_priv)
        self.anchors = StaticTrustAnchorResolver(
            {NPI: self.m.public_key_to_b64(self.prov_pub)})
        self.registry = PortalEnrollmentRegistry()
        self.fingerprint = key_fingerprint(self.delegation.agent_public_key_b64)
        self.registry.enroll(NPI, self.fingerprint, scope)
        self.clock = Clock(int(_time.time()))
        kwargs = {"clock": self.clock}
        if handle_source is not None:
            kwargs["handle_source"] = handle_source
        self.svc = CallVerificationService(
            PAYER, self.m, self.anchors, self.registry, store or InMemoryTokenStore(),
            HMAC_KEY, **kwargs)

    def body(self, **over):
        b = {
            "delegation_id": self.delegation.delegation_id,
            "originating_number": NUMBER,
            "purpose": "eligibility",
            "payer_audience": PAYER,
            "member_ref": "M-0042",
            "claim_ref": "",
            EXTENSION_KEY: build_extension(self.passport),
        }
        b.update(over)
        return b

    def request(self, body=None, priv=None, keyid=None, created=None, expires=None,
                nonce=None, target=None):
        now = self.clock()
        return sign_call_intent(
            priv or self.agent_priv, body or self.body(), target or self.svc.target_uri,
            keyid or self.fingerprint,
            created if created is not None else now,
            expires if expires is not None else now + 120, nonce)

    def issue(self, **kw):
        return self.svc.issue(self.request(**kw), [self.passport])

    def proof(self, nonce, priv=None, issued_at=None):
        p = PresentationProof(self.delegation.delegation_id, nonce,
                              issued_at if issued_at is not None else self.clock(), "")
        p.signature_b64 = base64.b64encode(
            (priv or self.agent_priv).sign(p.signing_payload())).decode()
        return p

    def redeem(self, handle, call_sid="CA-1", number=NUMBER, purpose="eligibility",
               priv=None, with_proof=True):
        nonce = self.svc.new_challenge()
        proof = self.proof(nonce, priv) if with_proof else None
        return self.svc.redeem(handle, CallContext(call_sid, number, purpose), nonce, proof)


@pytest.fixture
def world():
    return World()


# ── RFC 9421: checked against the RFC, not only against ourselves ────────────

# RFC 9421 Appendix B.1.4 test key "test-key-ed25519" and the Appendix B.2.6
# example (request "POST /foo?param=Value&Pet=dog" to example.com, body
# {"hello": "world"}). Ed25519 is deterministic, so the RFC's signature value
# is reproducible exactly from the key and the signature base. Taken from the
# Apache-2.0 test suite of the independent `http-message-signatures` package
# (test/test.py, test_http_message_signatures_B26).
RFC9421_ED25519_PRIVATE = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIJ+DYvh6SEqVTm50DFtMDoQikTmiCqirVv9mWG9qfSnF
-----END PRIVATE KEY-----
"""
RFC9421_B26_SIGNATURE = (
    "wqcAqbmYJ2ji2glfAMaRy4gruYYnx2nEFN2HN6jrnDnQCK1u02Gb04v9EDgwUPiu4A0w6vuQv5lIp5WPpBKRCw==")


def test_signature_base_reproduces_rfc9421_appendix_b26():
    key = load_pem_private_key(RFC9421_ED25519_PRIVATE, None)
    components = ("date", "@method", "@path", "@authority", "content-type", "content-length")
    params = serialize_signature_params(
        components, [("created", 1618884473), ("keyid", "test-key-ed25519")])
    assert params == ('("date" "@method" "@path" "@authority" "content-type" '
                      '"content-length");created=1618884473;keyid="test-key-ed25519"')
    base = signature_base([
        ("date", "Tue, 20 Apr 2021 02:07:55 GMT"), ("@method", "POST"), ("@path", "/foo"),
        ("@authority", "example.com"), ("content-type", "application/json"),
        ("content-length", "18"),
    ], params)
    assert base64.b64encode(key.sign(base)).decode() == RFC9421_B26_SIGNATURE


def test_content_digest_is_rfc9530_sha256():
    # RFC 9530 §2 example body {"hello": "world"} with a trailing newline.
    assert content_digest(b'{"hello": "world"}\n') == (
        "sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=:")


def test_request_carries_the_stated_profile(world):
    req = world.request()
    si = req.headers["Signature-Input"]
    assert si.startswith('nhid=("@method" "@target-uri" "content-digest");created=')
    for param in (";expires=", ";nonce=", f';keyid="{world.fingerprint}"',
                  ';alg="ed25519"', ';tag="nhid-call-intent"'):
        assert param in si
    assert req.headers["Signature"].startswith("nhid=:")
    assert verify_call_intent_signature(req, world.agent_pub).valid


# ── Requirement 1: provider-signed delegation and registry status ────────────

def test_issues_for_an_enrolled_provider_signed_delegation(world):
    res = world.issue()
    assert res.ok, res.reason
    assert res.dtmf_handle.isdigit() and len(res.dtmf_handle) == 8


def test_an_untrusted_provider_key_is_refused(world):
    world.svc.trust_anchors = StaticTrustAnchorResolver({})
    assert world.issue().reason == "PROVIDER_NOT_TRUSTED"


def test_a_self_signed_delegation_is_refused(world):
    # The agent signs its own delegation, as the outside blueprint allowed.
    d = world.m.create_delegation(world.agent_priv, "agent-ava-01", world.agent_pub,
                                  scope=["eligibility"], provider_npi=NPI)
    forged = world.m.create_agent_passport(d, world.m.sign_delegation(world.agent_priv, d),
                                           world.agent_priv)
    res = world.svc.issue(world.request(body=world.body(**{
        "delegation_id": d.delegation_id, EXTENSION_KEY: build_extension(forged)})), [forged])
    assert not res.ok and res.reason.startswith("DELEGATION_INVALID")


@pytest.mark.parametrize("status", [None, ENROLLMENT_SUSPENDED, ENROLLMENT_REVOKED])
def test_registry_status_gates_issuance(world, status):
    if status is None:
        world.svc.registry = PortalEnrollmentRegistry()
        expected = "NOT_ENROLLED"
    else:
        world.registry.set_status(NPI, world.fingerprint, status)
        expected = f"ENROLLMENT_{status.upper()}"
    assert world.issue().reason == expected


def test_the_agents_self_description_must_agree_with_the_delegation(world):
    ext = build_extension(world.passport)
    ext["scope"] = ["eligibility", "claim_status"]
    res = world.issue(body=world.body(**{EXTENSION_KEY: ext}))
    assert not res.ok and res.reason.startswith("EXTENSION_INVALID")


def test_purpose_outside_the_delegation_is_refused_at_issuance(world):
    assert world.issue(body=world.body(purpose="claim_status")).reason == "SCOPE_MISMATCH"


# ── Requirement 2: proof of possession at redemption ─────────────────────────

def test_redemption_without_proof_fails(world):
    res = world.redeem(world.issue().dtmf_handle, with_proof=False)
    assert res.binding_checks["proof_of_possession"] == EXCEPTION
    assert res.reason_code == "PROOF_OF_POSSESSION_FAILED"


def test_a_captured_handle_without_the_agent_key_fails(world):
    other_priv, _ = world.m.generate_agent_keys()
    res = world.redeem(world.issue().dtmf_handle, priv=other_priv)
    assert res.result == EXCEPTION
    assert res.binding_checks["proof_of_possession"] == EXCEPTION


def test_a_proof_for_another_challenge_fails(world):
    handle = world.issue().dtmf_handle
    stale = world.proof("an-earlier-challenge")
    res = world.svc.redeem(handle, CallContext("CA-1", NUMBER, "eligibility"),
                           world.svc.new_challenge(), stale)
    assert res.binding_checks["proof_of_possession"] == EXCEPTION


# ── Requirement 3: nonce, created/expires, audience, signed ──────────────────

def test_another_payers_intent_is_refused(world):
    assert world.issue(body=world.body(payer_audience="other-payer.example")).reason == \
        "AUDIENCE_MISMATCH"


def test_an_edited_body_breaks_the_signature(world):
    req = world.request()
    body = json.loads(req.body)
    body["originating_number"] = "+15555550199"
    req.body = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert world.svc.issue(req, [world.passport]).reason == "DIGEST_MISMATCH"


def test_a_signature_by_another_key_is_refused(world):
    other_priv, _ = world.m.generate_agent_keys()
    assert world.issue(priv=other_priv).reason == "SIGNATURE_INVALID"


def test_keyid_must_be_the_delegated_key_fingerprint(world):
    assert world.issue(keyid="sha256:" + "0" * 64).reason == "KEYID_MISMATCH"


@pytest.mark.parametrize("created_off,expires_off,reason", [
    (-400, -10, "INTENT_EXPIRED"),
    (+120, +240, "INTENT_NOT_YET_VALID"),
    (0, +3600, "INTENT_WINDOW_TOO_LONG"),
])
def test_intent_window_is_enforced(world, created_off, expires_off, reason):
    now = world.clock()
    assert world.issue(created=now + created_off, expires=now + expires_off).reason == reason


def test_a_tampered_signature_param_fails(world):
    req = world.request()
    req.headers["Signature-Input"] = req.headers["Signature-Input"].replace(
        'tag="nhid-call-intent"', 'tag="other"')
    assert not world.svc.issue(req, [world.passport]).ok


# ── Requirement 4: random nonces, and intent replay ──────────────────────────

def test_intent_nonces_are_random_and_distinct():
    nonces = {new_intent_nonce() for _ in range(2000)}
    assert len(nonces) == 2000
    assert all(len(base64.urlsafe_b64decode(n + "==")) == 24 for n in nonces)


def test_a_replayed_intent_is_refused(world):
    req = world.request()
    assert world.svc.issue(req, [world.passport]).ok
    assert world.svc.issue(req, [world.passport]).reason == "INTENT_NONCE_REPLAYED"


# ── Requirement 5: atomic single redemption, binding checks first ────────────

def test_a_failed_binding_does_not_consume_the_token(world):
    handle = world.issue().dtmf_handle
    wrong = world.redeem(handle, number="+15555550199")
    assert wrong.result == EXCEPTION and wrong.reason_code == "NUMBER_MISMATCH"
    assert world.svc.store.get(handle).consumed_at is None
    assert world.redeem(handle).result == PASS


def test_a_withheld_number_is_unknown_not_pass(world):
    res = world.redeem(world.issue().dtmf_handle, number=None)
    assert res.result == UNKNOWN
    assert res.binding_checks["originating_number"] == UNKNOWN
    assert res.reason_code == "NUMBER_UNAVAILABLE"
    assert res.restriction() == "DENY_DATA"


def test_sqlite_store_lets_exactly_one_concurrent_redemption_win(tmp_path):
    w = World(store=SqliteTokenStore(str(tmp_path / "tokens.db")))
    handle = w.issue().dtmf_handle
    results, barrier = [], threading.Barrier(8)

    def go(i):
        barrier.wait()
        results.append(w.redeem(handle, call_sid=f"CA-{i}"))

    threads = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r.result for r in results) == [EXCEPTION] * 7 + [PASS]
    assert {r.reason_code for r in results if r.result == EXCEPTION} == {"TOKEN_ALREADY_REDEEMED"}


def test_a_second_store_connection_sees_the_consume(tmp_path):
    path = str(tmp_path / "shared.db")
    w = World(store=SqliteTokenStore(path))
    handle = w.issue().dtmf_handle
    assert w.redeem(handle).result == PASS
    w.svc.store = SqliteTokenStore(path)      # another node, same database
    assert w.redeem(handle).reason_code == "TOKEN_ALREADY_REDEEMED"


def test_a_transfer_keeps_the_result_without_redeeming_again(world):
    handle = world.issue().dtmf_handle
    assert world.redeem(handle, call_sid="CA-77").result == PASS
    kept = world.svc.result_for_call("CA-77")
    assert kept is not None and kept.result == PASS
    assert world.svc.result_for_call("CA-other") is None


# ── Requirement 6: DTMF handles server-side, collisions checked ──────────────

@pytest.mark.parametrize("make_store", [lambda p: InMemoryTokenStore(),
                                        lambda p: SqliteTokenStore(str(p / "t.db"))])
def test_a_colliding_handle_is_retried(tmp_path, make_store):
    seq = iter(["11111111", "11111111", "22222222"])
    w = World(store=make_store(tmp_path), handle_source=lambda n: next(seq))
    assert w.issue().dtmf_handle == "11111111"
    assert w.issue().dtmf_handle == "22222222"


def test_handle_space_exhaustion_fails_closed():
    w = World(handle_source=lambda n: "12345678")
    assert w.issue().ok
    assert w.issue().reason == "HANDLE_SPACE_EXHAUSTED"


def test_an_unknown_handle_is_an_exception(world):
    res = world.redeem("00000000")
    assert res.result == EXCEPTION and res.reason_code == "TOKEN_NOT_FOUND"


# ── Requirement 7: intent_hmac is keyed, and no identifier is stored ─────────

def test_intent_hmac_is_keyed(world):
    other = CallVerificationService(PAYER, world.m, world.anchors, world.registry,
                                    InMemoryTokenStore(), b"z" * 32)
    assert world.svc.intent_hmac("M-0042") != other.intent_hmac("M-0042")
    import hashlib
    assert world.svc.intent_hmac("M-0042") != hashlib.sha256(b"M-0042").hexdigest()


def test_the_token_record_holds_no_member_or_claim_id(world):
    res = world.issue(body=world.body(member_ref="M-0042", claim_ref="CLM-9"))
    record = world.svc.store.get(res.token_ref)
    assert "M-0042" not in json.dumps(record.__dict__)
    assert "CLM-9" not in json.dumps(record.__dict__)
    assert world.svc.matches_intent(record, "M-0042", "CLM-9")
    assert not world.svc.matches_intent(record, "M-0043", "CLM-9")


def test_a_short_hmac_key_is_refused(world):
    with pytest.raises(ValueError):
        CallVerificationService(PAYER, world.m, world.anchors, world.registry,
                                InMemoryTokenStore(), b"short")


# ── Requirements 8 and 9: key-derived fingerprint, nhid-agent kept ───────────

def test_fingerprint_is_derived_from_the_key(world):
    import hashlib
    raw = base64.b64decode(world.delegation.agent_public_key_b64)
    assert world.fingerprint == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert world.svc.store.get(world.issue().token_ref).agent_key_fingerprint == world.fingerprint


def test_agent_metadata_is_the_existing_nhid_agent_object():
    w = World()
    d = w.m.create_delegation(w.prov_priv, "agent-ava-01", w.agent_pub, scope=["eligibility"],
                              provider_npi=NPI, call_sid="CA-preset")
    passport = w.m.create_agent_passport(d, w.m.sign_delegation(w.prov_priv, d), w.agent_priv)
    ext = build_extension(passport)
    assert ext["agent_id"] == "agent-ava-01" and ext["call_sid"] == "CA-preset"
    assert ext["agent_key_fingerprint"] == key_fingerprint(d.agent_public_key_b64)


# ── Requirement 10 and the trace schema ──────────────────────────────────────

def test_module_makes_no_registration_or_version_claims():
    text = (ROOT / "src" / "call_verification.py").read_text()
    for banned in ("ietf.org", "iana.org", "nhid_version", "2.0", "certified", "compliant"):
        assert banned not in text, banned


def _call_verification_validator():
    schema = json.loads(SCHEMA.read_text())
    sub = schema["properties"]["healthcare_governance"]["properties"]["call_verification"]
    sub = dict(sub, **{"$schema": schema["$schema"]})
    return jsonschema.Draft202012Validator(sub, format_checker=jsonschema.FormatChecker())


def test_results_validate_against_the_trace_schema(world):
    v = _call_verification_validator()
    handle = world.issue().dtmf_handle
    for res in (world.redeem(handle, number=None), world.redeem(handle), world.redeem(handle),
                world.redeem("nope")):
        v.validate(res.to_trace_field())


def test_high_risk_writes_need_out_of_band_confirmation():
    assert requires_out_of_band("eft_update")
    assert not requires_out_of_band("eligibility")


# ── The PR 1 fixtures ────────────────────────────────────────────────────────

def _fixtures():
    data = json.loads(FIXTURES.read_text())
    return {s["scenario_id"]: s for s in data["scenarios"]}


def _expected(scenario):
    return scenario["turns"][0]["healthcare_governance"]["call_verification"]


def _run_fixture(sid, tmp_path):
    """Drive the prototype into the fixture's situation. Returns the result
    whose call_verification the fixture describes, plus extras to assert."""
    extras = {}
    if sid == "FIX-VER-012":
        w = World(scope=("eligibility", "eft_update"))
        handle = w.issue(body=w.body(purpose="eft_update")).dtmf_handle
        res = w.redeem(handle, purpose="eft_update")
        extras["out_of_band"] = requires_out_of_band("eft_update")
        return res, extras
    if sid == "FIX-VER-009":
        w = World(store=SqliteTokenStore(str(tmp_path / f"{sid}.db")))
        handle = w.issue().dtmf_handle
        results, barrier = [], threading.Barrier(2)

        def go(i):
            barrier.wait()
            results.append(w.redeem(handle, call_sid=f"CA-9-{i}"))

        threads = [threading.Thread(target=go, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        winners = [r for r in results if r.result == PASS]
        losers = [r for r in results if r.result != PASS]
        extras["loser_reasons"] = [r.reason_code for r in losers]
        assert len(winners) == 1, results
        return winners[0], extras

    w = World()
    handle = w.issue().dtmf_handle
    if sid == "FIX-VER-005":
        w.clock.t += w.svc.token_ttl + 1
    elif sid == "FIX-VER-006":
        w.m.revoke_delegation(w.delegation.delegation_id)
    elif sid == "FIX-VER-007":
        return w.redeem(handle, purpose="claim_status"), extras
    elif sid == "FIX-VER-008":
        first = w.redeem(handle, call_sid="CA-ver-0008-a")
        extras["first"] = first
        return w.redeem(handle, call_sid="CA-ver-0008-b"), extras
    return w.redeem(handle), extras


FIXTURE_IDS = sorted(_fixtures())


@pytest.mark.parametrize("sid", FIXTURE_IDS)
def test_prototype_reproduces_the_fixture_ver01_expectation(sid, tmp_path):
    scenario = _fixtures()[sid]
    expected = _expected(scenario)
    res, extras = _run_fixture(sid, tmp_path)
    assert scenario["expected"]["VER-01"] == expected["result"]
    assert res.result == expected["result"], (sid, res)
    assert res.reason_code == expected["reason_code"], (sid, res)
    assert res.binding_checks == expected["binding_checks"], (sid, res)
    assert list(res.binding_checks) == list(BINDING_CHECKS)
    _call_verification_validator().validate(res.to_trace_field())

    if sid == "FIX-VER-008":
        assert extras["first"].result == PASS      # the first redemption passes
    if sid == "FIX-VER-009":
        assert extras["loser_reasons"] == ["TOKEN_ALREADY_REDEEMED"]
    if sid == "FIX-VER-012":
        assert extras["out_of_band"] is True       # verified, still needs confirmation


def test_every_fixture_with_a_call_verification_block_is_covered():
    assert len(FIXTURE_IDS) == 12
    assert all("call_verification" in s["turns"][0]["healthcare_governance"]
               for s in _fixtures().values())
