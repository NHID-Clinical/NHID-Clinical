"""
The LLM client on the voice path
================================
`llm.py` was the only production module with no test at all, and it sits on the
main request path: `app.py`'s `/voice/process` calls `call_llm` whenever the
policy decision is `ROUTE_LLM`. It is also the only consumer of the `openai`
dependency, which had drifted two majors past its declared floor (1.x → 3.x)
with nothing exercising the call it makes.

These are the first async tests in the suite. `pytest-asyncio` was a declared
dependency with no async test to serve — `pytest.ini` even set
`asyncio_mode = strict` for a suite that had none.

What is pinned here, in order of how much it matters:

1. **A failure must propagate.** If `call_llm` ever swallowed an API error and
   returned a plausible string, that string would be spoken to a caller as
   though the model had produced it. Fabricated text on a healthcare call is
   the worst failure this module could have, so it is asserted first.
2. **Import must not construct a client.** `OpenAI()` raises without an API
   key, so a non-lazy client makes the module unimportable wherever the key is
   absent — which is every CI run.
3. The request actually sent: the model, and a system message that constrains
   the model to the administrative role.
"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import llm


@pytest.fixture(autouse=True)
def _reset_client():
    """`llm._client` is module-global and cached; leaking it between tests
    would make them order-dependent."""
    original = llm._client
    llm._client = None
    yield
    llm._client = original


def _completion(text):
    """The shape `call_llm` reads: response.choices[0].message.content."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


# ── 1. Failures must not become answers ───────────────────────────────────────

@pytest.mark.asyncio
async def test_an_api_failure_propagates_rather_than_returning_text():
    """The property that matters most.

    A swallowed error here would put invented text into a live healthcare call
    with no indication it was not the model's. `/voice/process` must be allowed
    to fail instead.
    """
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("upstream is down")
    with patch.object(llm, "_client", client):
        with pytest.raises(RuntimeError, match="upstream is down"):
            await llm.call_llm("what is the status of this authorization")


@pytest.mark.asyncio
async def test_a_malformed_response_is_not_silently_turned_into_a_string():
    """An empty `choices` array means the model returned nothing. Reading
    `[0]` must raise rather than yield something speakable."""
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[])
    with patch.object(llm, "_client", client):
        with pytest.raises(IndexError):
            await llm.call_llm("hello")


# ── 2. Laziness ───────────────────────────────────────────────────────────────

def test_importing_the_module_does_not_construct_a_client():
    """`OpenAI()` raises without an API key, so eager construction would make
    this module unimportable in CI — the reason the laziness exists."""
    assert llm._client is None

    with patch.object(llm, "OpenAI") as constructor:
        import importlib

        importlib.reload(llm)
        constructor.assert_not_called()
    # Reload replaced the module object's state; restore the sentinel.
    llm._client = None


def test_the_client_is_constructed_once_and_reused():
    with patch.object(llm, "OpenAI") as constructor:
        constructor.return_value = MagicMock()
        first = llm._get_client()
        second = llm._get_client()
    assert first is second
    assert constructor.call_count == 1


def test_the_client_is_given_the_api_key_from_the_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")
    with patch.object(llm, "OpenAI") as constructor:
        constructor.return_value = MagicMock()
        llm._get_client()
    constructor.assert_called_once()
    assert constructor.call_args.kwargs["api_key"] == "sk-test-not-a-real-key"


# ── 3. The request that is actually sent ──────────────────────────────────────

@pytest.mark.asyncio
async def test_the_response_content_is_returned_unchanged():
    client = MagicMock()
    client.chat.completions.create.return_value = _completion("Prior auth is approved.")
    with patch.object(llm, "_client", client):
        assert await llm.call_llm("status?") == "Prior auth is approved."


@pytest.mark.asyncio
async def test_the_caller_text_is_sent_as_the_user_message():
    client = MagicMock()
    client.chat.completions.create.return_value = _completion("ok")
    with patch.object(llm, "_client", client):
        await llm.call_llm("I need the claim status for date of service July 3")

    messages = client.chat.completions.create.call_args.kwargs["messages"]
    user = [m for m in messages if m["role"] == "user"]
    assert len(user) == 1
    assert user[0]["content"] == "I need the claim status for date of service July 3"


@pytest.mark.asyncio
async def test_a_system_message_constrains_the_model_to_the_administrative_role():
    """The system prompt is the only thing bounding what the model will say on
    a healthcare call, so its presence is a contract, not a detail."""
    client = MagicMock()
    client.chat.completions.create.return_value = _completion("ok")
    with patch.object(llm, "_client", client):
        await llm.call_llm("hello")

    messages = client.chat.completions.create.call_args.kwargs["messages"]
    system = [m for m in messages if m["role"] == "system"]
    assert len(system) == 1
    assert "healthcare administrative" in system[0]["content"].lower()


@pytest.mark.asyncio
async def test_a_model_is_named_explicitly():
    """An unset model would make the request depend on an API-side default."""
    client = MagicMock()
    client.chat.completions.create.return_value = _completion("ok")
    with patch.object(llm, "_client", client):
        await llm.call_llm("hello")

    model = client.chat.completions.create.call_args.kwargs["model"]
    assert isinstance(model, str) and model


# ── The installed SDK still offers the call this module makes ─────────────────

def test_the_installed_openai_sdk_exposes_the_call_this_module_uses():
    """`openai` is declared `>=1.0.0` and resolves to 3.x. The chat-completions
    call survived that, but nothing checked — so this asserts the surface
    rather than trusting the floor.
    """
    import inspect

    from openai import OpenAI
    from openai.resources.chat.completions import Completions

    assert "api_key" in inspect.signature(OpenAI.__init__).parameters
    assert hasattr(Completions, "create")
    params = inspect.signature(Completions.create).parameters
    assert "model" in params and "messages" in params
