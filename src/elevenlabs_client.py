"""
ElevenLabs Conversational AI agent-config client — agent-agnostic.

Manages an agent's system prompt (and, via the CLI in scripts/sync_agent_config.py,
its voice/model config) against the live ElevenLabs API, with a file in this repo
as the source of truth. Any agent can be synced this way instead of through the
ElevenLabs dashboard — pass its agent_id and the path to its canonical prompt file.

Relocated from tests/elevenlabs_cts_runner.py (which hardcoded these for Beacon)
so the conformance test runner and the agent-config sync CLI share one client.
"""

from __future__ import annotations

import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

API_BASE = "https://api.elevenlabs.io"


def _agent_url(agent_id: str) -> str:
    return f"{API_BASE}/v1/convai/agents/{agent_id}"


class ElevenLabsClient:
    def __init__(self, api_key: str) -> None:
        if not _HTTPX_OK:
            raise ImportError("httpx is required: pip install httpx")
        self._key = api_key
        self._headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }

    # ── Agent config ──────────────────────────────────────────────────────

    def get_agent_config(self, agent_id: str) -> dict:
        """Fetch an agent's live configuration."""
        resp = httpx.get(_agent_url(agent_id), headers=self._headers, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def patch_agent_config(self, agent_id: str, payload: dict) -> dict:
        """Push updated configuration to an agent."""
        resp = httpx.patch(_agent_url(agent_id), headers=self._headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Conversation fetch ────────────────────────────────────────────────

    def get_conversation(self, conv_id: str) -> dict:
        """Fetch a completed conversation including transcript with time_in_call_secs."""
        resp = httpx.get(
            f"{API_BASE}/v1/convai/conversations/{conv_id}",
            headers=self._headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


# ── Prompt sync ───────────────────────────────────────────────────────────────

def _extract_canonical_prompt(prompt_path: Path) -> Optional[str]:
    """Load a canonical system prompt from its markdown file."""
    if not prompt_path.exists():
        return None
    text = prompt_path.read_text(encoding="utf-8")
    # Extract content between ```prompt ... ``` fences if present
    m = re.search(r"```prompt\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Otherwise use the full file, stripping markdown headers
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    return "\n".join(lines).strip() or None


def _extract_canonical_first_message(prompt_path: Path) -> Optional[str]:
    """Load the canonical first message from its ```first_message fence, if present."""
    if not prompt_path.exists():
        return None
    text = prompt_path.read_text(encoding="utf-8")
    m = re.search(r"```first_message\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_canonical_name(prompt_path: Path) -> Optional[str]:
    """Load the canonical agent display name from its '- **Name**: X' line, if present."""
    if not prompt_path.exists():
        return None
    text = prompt_path.read_text(encoding="utf-8")
    m = re.search(r"^\s*-\s*\*\*Name\*\*:\s*(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _write_canonical_from_live(prompt_path: Path, agent_id: str, prompt: str, first_message: str) -> None:
    """Persist a live prompt as the canonical baseline file."""
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = prompt_path.stem.replace("_system_prompt", "").replace("_", " ").title()
    header = textwrap.dedent(f"""\
        # {title} — NHID-Clinical Reference System Prompt
        > Canonical source of truth for agent `{agent_id}`.
        > Last synced from live: {now}
        > Repo is source of truth. Push changes here; the sync CLI pushes to ElevenLabs.

        ## First message

        {first_message}

        ## System prompt

        ```prompt
    """)
    footer = "\n```\n"
    prompt_path.write_text(header + prompt + footer, encoding="utf-8")


def sync_prompt(
    client: ElevenLabsClient,
    agent_id: str,
    prompt_path: Path,
    *,
    dry_run: bool = False,
) -> dict:
    """
    1. Pull the agent's live system prompt, first message, and display name.
    2. Diff each against its canonical counterpart in the prompt file.
    3. Report every divergence.
    4. If canonical exists and differs, push it (unless dry_run).
    Returns a dict summarising what changed.

    first_message and name are pushed alongside the prompt because ElevenLabs
    treats them as separate fields the LLM never sees — a stale dashboard
    default in either (e.g. a leftover placeholder greeting/name) survives a
    prompt-only sync and is never visible to the LLM-driven diff above.
    """
    live_config = client.get_agent_config(agent_id)
    live_prompt = (
        live_config
        .get("conversation_config", {})
        .get("agent", {})
        .get("prompt", {})
        .get("prompt", "")
    ) or ""
    live_first_msg = (
        live_config
        .get("conversation_config", {})
        .get("agent", {})
        .get("first_message", "")
    ) or ""
    live_name = live_config.get("name", "") or ""

    canonical_prompt = _extract_canonical_prompt(prompt_path)
    canonical_first_msg = _extract_canonical_first_message(prompt_path)
    canonical_name = _extract_canonical_name(prompt_path)

    report: dict[str, Any] = {
        "live_name": live_name,
        "live_first_message": live_first_msg,
        "live_prompt_chars": len(live_prompt),
        "canonical_found": canonical_prompt is not None,
        "divergences": [],
        "pushed": False,
    }

    if canonical_prompt is None:
        # Write current live prompt as the canonical baseline
        _write_canonical_from_live(prompt_path, agent_id, live_prompt, live_first_msg)
        report["divergences"].append(
            "canonical file not found — written from live config as new baseline"
        )
        return report

    # Line-level diff of the system prompt
    live_lines = live_prompt.splitlines()
    canon_lines = canonical_prompt.splitlines()
    for i, (l, c) in enumerate(zip(live_lines, canon_lines)):
        if l.strip() != c.strip():
            report["divergences"].append(
                f"line {i + 1}: live={l[:80]!r}  canonical={c[:80]!r}"
            )
    if len(live_lines) != len(canon_lines):
        report["divergences"].append(
            f"line count: live={len(live_lines)} canonical={len(canon_lines)}"
        )

    if canonical_first_msg is not None and live_first_msg.strip() != canonical_first_msg.strip():
        report["divergences"].append(
            f"first_message: live={live_first_msg[:80]!r}  canonical={canonical_first_msg[:80]!r}"
        )
    if canonical_name is not None and live_name.strip() != canonical_name.strip():
        report["divergences"].append(
            f"name: live={live_name[:80]!r}  canonical={canonical_name[:80]!r}"
        )

    if report["divergences"] and not dry_run:
        # Repo is source of truth — push canonical prompt + first_message + name
        agent_patch: dict[str, Any] = {"prompt": {"prompt": canonical_prompt}}
        if canonical_first_msg is not None:
            agent_patch["first_message"] = canonical_first_msg
        patch: dict[str, Any] = {"conversation_config": {"agent": agent_patch}}
        if canonical_name is not None:
            patch["name"] = canonical_name
        client.patch_agent_config(agent_id, patch)
        report["pushed"] = True

    return report


def pull_prompt(client: ElevenLabsClient, agent_id: str, prompt_path: Path) -> dict:
    """Overwrite the canonical prompt file from the live agent (reverse of sync_prompt)."""
    live_config = client.get_agent_config(agent_id)
    live_prompt = (
        live_config
        .get("conversation_config", {})
        .get("agent", {})
        .get("prompt", {})
        .get("prompt", "")
    ) or ""
    live_first_msg = (
        live_config
        .get("conversation_config", {})
        .get("agent", {})
        .get("first_message", "")
    ) or ""
    _write_canonical_from_live(prompt_path, agent_id, live_prompt, live_first_msg)
    return {
        "live_name": live_config.get("name", ""),
        "prompt_chars": len(live_prompt),
    }
