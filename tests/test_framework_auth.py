"""Authentication and attestation-gating tests for the reference API.

These are regression tests for four defects that were all live at once:

1. ``get_api_key`` accepted every request when ``NHID_API_KEY`` was unset.
2. ``nhid_attest.router`` was mounted with no authentication dependency, so the
   credential-minting endpoint was reachable even when a key *was* configured.
3. ``/v1/attest`` fell back to the signing secret ``"nhid-dev-secret"``, which
   is published in this repository.
4. It signs HS256, so any verifier can also mint.

``main`` cannot be imported directly: it imports ``app`` -> ``llm`` -> ``openai``.
The stub below satisfies that import without installing the package, so these
tests drive the real ``main.app`` rather than a reconstruction of it.
"""

import os
import sqlite3
import sys
import types

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if "openai" not in sys.modules:  # pragma: no cover - import shim
    _openai = types.ModuleType("openai")

    class _OpenAI:  # noqa: D401 - stand-in for the real client
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _OpenAI
    sys.modules["openai"] = _openai

import main  # noqa: E402
import nhid_attest  # noqa: E402

# A protected route on nhid_api_endpoints. Any of the three authenticated
# routers would do; this one is a GET with no body.
PROTECTED_ROUTE = "/v1/compliance/states"

GOOD_KEY = "test-api-key-value"
GOOD_SECRET = "a" * nhid_attest.MIN_SECRET_LENGTH

ATTEST_BODY = {
    "delegating_entity": "1234567890",
    "authorized_actor": "agent-under-test",
    "scope": ["claims:read"],
    "expires_at": "2030-01-01T00:00:00+00:00",
}


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Start every test from no configuration at all."""
    monkeypatch.delenv("NHID_API_KEY", raising=False)
    monkeypatch.delenv("NHID_JWT_SECRET", raising=False)
    monkeypatch.delenv("NHID_ATTEST_ENABLED", raising=False)
    # DB_PATH is bound at import, so redirect the attribute rather than the env.
    monkeypatch.setattr(nhid_attest, "DB_PATH", str(tmp_path / "attest.db"))


def _attestation_count():
    if not os.path.exists(nhid_attest.DB_PATH):
        return 0
    conn = sqlite3.connect(nhid_attest.DB_PATH)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM attestations").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()
    return rows


# --- fail-open: the original defect -----------------------------------------

def test_unconfigured_server_refuses_protected_route(client):
    """The regression test. This returned 200 before the fix."""
    response = client.get(PROTECTED_ROUTE)
    assert response.status_code == 503
    assert "NHID_API_KEY" in response.json()["detail"]


def test_unconfigured_server_refuses_even_with_a_key_presented(client):
    """An unconfigured server cannot authenticate anyone, so it authenticates no one."""
    response = client.get(PROTECTED_ROUTE, headers={"X-API-Key": "anything"})
    assert response.status_code == 503


# --- configured server -------------------------------------------------------

def test_missing_header_is_unauthorized(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    assert client.get(PROTECTED_ROUTE).status_code == 401


def test_wrong_key_is_forbidden(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    response = client.get(PROTECTED_ROUTE, headers={"X-API-Key": "wrong"})
    assert response.status_code == 403


def test_correct_key_passes_authentication(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    response = client.get(PROTECTED_ROUTE, headers={"X-API-Key": GOOD_KEY})
    assert response.status_code not in (401, 403, 503)


def test_health_needs_no_credential(client):
    assert client.get("/health").status_code == 200


# --- the attestation router was mounted unauthenticated ----------------------

def test_attest_requires_authentication(client):
    """Was 200 before the fix, on a server with no key configured."""
    response = client.post("/v1/attest", json=ATTEST_BODY)
    assert response.status_code == 503
    assert _attestation_count() == 0


def test_attest_rejects_a_wrong_key(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    response = client.post(
        "/v1/attest", json=ATTEST_BODY, headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 403
    assert _attestation_count() == 0


# --- minting is off by default and has no default secret ---------------------

def test_attest_is_disabled_by_default(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    response = client.post(
        "/v1/attest", json=ATTEST_BODY, headers={"X-API-Key": GOOD_KEY}
    )
    assert response.status_code == 410
    assert _attestation_count() == 0


def test_attest_enabled_without_a_secret_refuses_to_sign(client, monkeypatch):
    """The 'nhid-dev-secret' fallback is gone: no secret means no token."""
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    monkeypatch.setenv("NHID_ATTEST_ENABLED", "1")
    response = client.post(
        "/v1/attest", json=ATTEST_BODY, headers={"X-API-Key": GOOD_KEY}
    )
    assert response.status_code == 503
    assert "token" not in response.json()
    assert _attestation_count() == 0


def test_attest_enabled_with_a_short_secret_refuses_to_sign(client, monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    monkeypatch.setenv("NHID_ATTEST_ENABLED", "1")
    monkeypatch.setenv("NHID_JWT_SECRET", "short")
    response = client.post(
        "/v1/attest", json=ATTEST_BODY, headers={"X-API-Key": GOOD_KEY}
    )
    assert response.status_code == 503
    assert _attestation_count() == 0


def test_attest_mints_only_when_deliberately_configured(client, monkeypatch):
    """The one remaining path that issues a token."""
    monkeypatch.setenv("NHID_API_KEY", GOOD_KEY)
    monkeypatch.setenv("NHID_ATTEST_ENABLED", "1")
    monkeypatch.setenv("NHID_JWT_SECRET", GOOD_SECRET)
    response = client.post(
        "/v1/attest", json=ATTEST_BODY, headers={"X-API-Key": GOOD_KEY}
    )
    assert response.status_code == 200
    assert response.json()["token"]
    assert _attestation_count() == 1
