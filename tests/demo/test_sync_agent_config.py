"""
Tests for scripts/sync_agent_config.py's push_voice_and_model / pull_voice_and_model.

Website demo feature test (NOT part of the NHID-Clinical governance framework's
270-passed conformance baseline). Run via `make test-demo` /
`python -m pytest tests/demo/ -v`, never via the default `pytest tests/` invocation.

All HTTP calls are monkeypatched — no real network access, no ElevenLabs credits spent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src import elevenlabs_client as elc
from src.elevenlabs_client import ElevenLabsClient

import scripts.sync_agent_config as sac


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


class TestPushVoiceAndModel:
    def test_pushes_text_only_when_set(self, monkeypatch):
        patched = {}

        def fake_patch(url, headers, json, timeout):
            patched["payload"] = json
            return _FakeResponse({"ok": True})

        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sac.push_voice_and_model(
            client, AGENT_ID, {"voice_id": None, "llm": None, "text_only": True}, dry_run=False
        )

        assert report["pushed"] is True
        assert patched["payload"]["conversation_config"]["conversation"]["text_only"] is True

    def test_pushes_text_only_false_explicitly(self, monkeypatch):
        patched = {}

        def fake_patch(url, headers, json, timeout):
            patched["payload"] = json
            return _FakeResponse({"ok": True})

        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sac.push_voice_and_model(
            client, AGENT_ID, {"voice_id": None, "llm": None, "text_only": False}, dry_run=False
        )

        assert report["pushed"] is True
        assert patched["payload"]["conversation_config"]["conversation"]["text_only"] is False

    def test_no_push_when_all_fields_unset(self, monkeypatch):
        def fake_patch(*args, **kwargs):
            raise AssertionError("patch should not be called when nothing is set")

        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sac.push_voice_and_model(
            client, AGENT_ID, {"voice_id": None, "llm": None, "text_only": None}, dry_run=False
        )

        assert report["pushed"] is False

    def test_dry_run_does_not_call_patch(self, monkeypatch):
        def fake_patch(*args, **kwargs):
            raise AssertionError("patch should not be called during dry-run")

        monkeypatch.setattr(elc.httpx, "patch", fake_patch)
        client = ElevenLabsClient("test-key")

        report = sac.push_voice_and_model(
            client, AGENT_ID, {"voice_id": None, "llm": None, "text_only": True}, dry_run=True
        )

        assert report["pushed"] is False
        assert report["payload"]["conversation_config"]["conversation"]["text_only"] is True


class TestPullVoiceAndModel:
    def test_pulls_text_only_into_config(self, tmp_path, monkeypatch):
        def fake_get(url, headers, timeout):
            return _FakeResponse(
                {
                    "conversation_config": {
                        "agent": {"prompt": {"llm": "gemini-2.5-flash"}},
                        "tts": {"voice_id": "voice_abc"},
                        "conversation": {"text_only": True},
                    }
                }
            )

        monkeypatch.setattr(elc.httpx, "get", fake_get)
        monkeypatch.setattr(sac, "AGENTS_DIR", tmp_path)
        client = ElevenLabsClient("test-key")

        updated = sac.pull_voice_and_model(client, "compass", AGENT_ID, {"voice_id": None, "llm": None, "text_only": None})

        assert updated["text_only"] is True
        assert updated["voice_id"] == "voice_abc"
        assert updated["llm"] == "gemini-2.5-flash"
        saved = (tmp_path / "compass.config.json").read_text(encoding="utf-8")
        assert '"text_only": true' in saved
