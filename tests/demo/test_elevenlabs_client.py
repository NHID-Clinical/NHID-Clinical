"""
Tests for src/elevenlabs_client.py — agent-config-as-code.

Website demo feature test (NOT part of the NHID-Clinical governance framework's
270-passed conformance baseline). Run via `make test-demo` /
`python -m pytest tests/demo/ -v`, never via the default `pytest tests/` invocation.

All HTTP calls are monkeypatched — no real network access, no ElevenLabs credits spent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from src import elevenlabs_client as elc
from src.elevenlabs_client import ElevenLabsClient, pull_prompt, sync_prompt


AGENT_ID = "agent_test1234567890"


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json = json_body
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json


def _live_config(prompt: str = "Hello, I am Beacon.", first_message: str = "Hi there.") -> dict:
    return {
        "name": "Beacon",
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": prompt},
                "first_message": first_message,
            }
        },
    }


# ── ElevenLabsClient ──────────────────────────────────────────────────────────

class TestElevenLabsClient:
    def test_get_agent_config_calls_correct_url(self, monkeypatch):
        captured = {}

        def fake_get(url, headers, timeout):
            captured["url"] = url
            captured["headers"] = headers
            return _FakeResponse(_live_config())

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        client = ElevenLabsClient("test-key")
        result = client.get_agent_config(AGENT_ID)

        assert captured["url"] == f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
        assert captured["headers"]["xi-api-key"] == "test-key"
        assert result["name"] == "Beacon"

    def test_patch_agent_config_calls_correct_url(self, monkeypatch):
        captured = {}

        def fake_patch(url, headers, json, timeout):
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse({"ok": True})

        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")
        payload = {"conversation_config": {"agent": {"prompt": {"prompt": "new prompt"}}}}
        result = client.patch_agent_config(AGENT_ID, payload)

        assert captured["url"] == f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
        assert captured["json"] == payload
        assert result == {"ok": True}

    def test_get_conversation_calls_correct_url(self, monkeypatch):
        captured = {}

        def fake_get(url, headers, timeout):
            captured["url"] = url
            return _FakeResponse({"conversation_id": "conv_1"})

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        client = ElevenLabsClient("test-key")
        result = client.get_conversation("conv_1")

        assert captured["url"] == "https://api.elevenlabs.io/v1/convai/conversations/conv_1"
        assert result["conversation_id"] == "conv_1"

    def test_raises_without_httpx(self, monkeypatch):
        monkeypatch.setattr(elc, "_HTTPX_OK", False)
        with pytest.raises(ImportError):
            ElevenLabsClient("test-key")


# ── _extract_canonical_prompt ─────────────────────────────────────────────────

class TestExtractCanonicalPrompt:
    def test_extracts_fenced_prompt_block(self, tmp_path):
        path = tmp_path / "agent_system_prompt.md"
        path.write_text(
            "# Agent — Reference Prompt\n\n## System prompt\n\n```prompt\nYou are a helpful agent.\nAlways disclose.\n```\n",
            encoding="utf-8",
        )
        assert elc._extract_canonical_prompt(path) == "You are a helpful agent.\nAlways disclose."

    def test_returns_none_if_file_missing(self, tmp_path):
        path = tmp_path / "missing.md"
        assert elc._extract_canonical_prompt(path) is None

    def test_falls_back_to_stripped_headers_without_fence(self, tmp_path):
        path = tmp_path / "agent_system_prompt.md"
        path.write_text("# Title\nplain prompt text\nmore text\n", encoding="utf-8")
        assert elc._extract_canonical_prompt(path) == "plain prompt text\nmore text"


# ── sync_prompt ───────────────────────────────────────────────────────────────

class TestSyncPrompt:
    def test_writes_canonical_baseline_when_missing(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "agents" / "test_system_prompt.md"

        def fake_get(url, headers, timeout):
            return _FakeResponse(_live_config(prompt="Live prompt content."))

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        client = ElevenLabsClient("test-key")

        report = sync_prompt(client, AGENT_ID, prompt_path)

        assert report["canonical_found"] is False
        assert "written from live config as new baseline" in report["divergences"][0]
        assert prompt_path.exists()
        assert "Live prompt content." in prompt_path.read_text(encoding="utf-8")

    def test_no_divergence_when_matching(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "test_system_prompt.md"
        prompt_path.write_text("```prompt\nSame prompt text.\n```\n", encoding="utf-8")

        def fake_get(url, headers, timeout):
            return _FakeResponse(_live_config(prompt="Same prompt text."))

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        client = ElevenLabsClient("test-key")

        report = sync_prompt(client, AGENT_ID, prompt_path)

        assert report["divergences"] == []
        assert report["pushed"] is False

    def test_pushes_canonical_on_divergence(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "test_system_prompt.md"
        prompt_path.write_text("```prompt\nCanonical version.\n```\n", encoding="utf-8")

        patched = {}

        def fake_get(url, headers, timeout):
            return _FakeResponse(_live_config(prompt="Old live version."))

        def fake_patch(url, headers, json, timeout):
            patched["payload"] = json
            return _FakeResponse({"ok": True})

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sync_prompt(client, AGENT_ID, prompt_path)

        assert report["divergences"]
        assert report["pushed"] is True
        assert patched["payload"]["conversation_config"]["agent"]["prompt"]["prompt"] == "Canonical version."

    def test_dry_run_does_not_push(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "test_system_prompt.md"
        prompt_path.write_text("```prompt\nCanonical version.\n```\n", encoding="utf-8")

        def fake_get(url, headers, timeout):
            return _FakeResponse(_live_config(prompt="Old live version."))

        def fake_patch(*args, **kwargs):
            raise AssertionError("patch should not be called during dry-run")

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sync_prompt(client, AGENT_ID, prompt_path, dry_run=True)

        assert report["divergences"]
        assert report["pushed"] is False


# ── pull_prompt ───────────────────────────────────────────────────────────────

class TestPullPrompt:
    def test_overwrites_canonical_from_live(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "test_system_prompt.md"
        prompt_path.write_text("```prompt\nStale local copy.\n```\n", encoding="utf-8")

        def fake_get(url, headers, timeout):
            return _FakeResponse(_live_config(prompt="Fresh live prompt.", first_message="Hello!"))

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        client = ElevenLabsClient("test-key")

        report = pull_prompt(client, AGENT_ID, prompt_path)

        assert report["live_name"] == "Beacon"
        assert report["prompt_chars"] == len("Fresh live prompt.")
        content = prompt_path.read_text(encoding="utf-8")
        assert "Fresh live prompt." in content
        assert "Hello!" in content
        assert "Stale local copy." not in content
