#!/usr/bin/env python3
"""
Sync an ElevenLabs Conversational AI agent's prompt + voice/model config
between this repo (source of truth) and the live ElevenLabs agent.

Usage
-----
  export ELEVENLABS_API_KEY=your_key
  python scripts/sync_agent_config.py --agent beacon              # push prompt + config
  python scripts/sync_agent_config.py --agent beacon --dry-run    # show diffs, push nothing
  python scripts/sync_agent_config.py --agent beacon --pull       # pull live -> repo

Adding a new agent
-------------------
  1. Create the agent in the ElevenLabs dashboard (this script does not create agents).
  2. Add agents/<name>_system_prompt.md (prompt, same format as beacon_system_prompt.md)
     and agents/<name>.config.json ({"agent_id": "agent_...", "voice_id": null, "llm": null}).
  3. python scripts/sync_agent_config.py --agent <name> --pull   # populate voice_id/llm once
  4. python scripts/sync_agent_config.py --agent <name>          # push going forward
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.elevenlabs_client import ElevenLabsClient, pull_prompt, sync_prompt  # noqa: E402

AGENTS_DIR = Path(__file__).parent.parent / "agents"


def _config_path(agent_name: str) -> Path:
    return AGENTS_DIR / f"{agent_name}.config.json"


def _prompt_path(agent_name: str) -> Path:
    return AGENTS_DIR / f"{agent_name}_system_prompt.md"


def _load_config(agent_name: str) -> dict:
    path = _config_path(agent_name)
    if not path.exists():
        print(f"ERROR: {path} not found.", file=sys.stderr)
        print('  Create it with at least {"agent_id": "agent_..."}', file=sys.stderr)
        sys.exit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(agent_name: str, config: dict) -> None:
    _config_path(agent_name).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def push_voice_and_model(client: ElevenLabsClient, agent_id: str, config: dict, *, dry_run: bool) -> dict:
    """Push voice_id/llm from the repo's config.json to the live agent, if set."""
    payload: dict = {}
    if config.get("voice_id"):
        payload.setdefault("conversation_config", {}).setdefault("tts", {})["voice_id"] = config["voice_id"]
    if config.get("llm"):
        payload.setdefault("conversation_config", {}).setdefault("agent", {}).setdefault("prompt", {})["llm"] = config["llm"]
    if not payload:
        return {"pushed": False, "reason": "voice_id/llm not set in config — nothing to push"}
    if not dry_run:
        client.patch_agent_config(agent_id, payload)
    return {"pushed": not dry_run, "payload": payload}


def pull_voice_and_model(client: ElevenLabsClient, agent_name: str, agent_id: str, config: dict) -> dict:
    """Pull live voice_id/llm into the repo's config.json."""
    live = client.get_agent_config(agent_id)
    agent_cfg = live.get("conversation_config", {}).get("agent", {})
    tts_cfg = live.get("conversation_config", {}).get("tts", {})
    config["voice_id"] = tts_cfg.get("voice_id", config.get("voice_id"))
    config["llm"] = agent_cfg.get("prompt", {}).get("llm", config.get("llm"))
    _save_config(agent_name, config)
    return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync an ElevenLabs agent's prompt/voice/model config with this repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--agent", required=True, help="Agent name, matches agents/<name>_system_prompt.md")
    parser.add_argument("--dry-run", action="store_true", help="Show diffs without pushing")
    parser.add_argument("--pull", action="store_true", help="Pull live config into the repo instead of pushing")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY is not set.", file=sys.stderr)
        return 2

    config = _load_config(args.agent)
    agent_id = config.get("agent_id")
    if not agent_id:
        print(f'ERROR: {_config_path(args.agent)} is missing "agent_id".', file=sys.stderr)
        return 2

    client = ElevenLabsClient(api_key)
    prompt_path = _prompt_path(args.agent)

    if args.pull:
        prompt_report = pull_prompt(client, agent_id, prompt_path)
        print(f"Pulled prompt for {args.agent} ({prompt_report['live_name']}): "
              f"{prompt_report['prompt_chars']} chars -> {prompt_path}")
        updated_config = pull_voice_and_model(client, args.agent, agent_id, config)
        print(f"Pulled voice/model config -> {_config_path(args.agent)}: "
              f"voice_id={updated_config.get('voice_id')!r} llm={updated_config.get('llm')!r}")
        return 0

    print(f"Syncing {args.agent} ({agent_id})...")
    prompt_report = sync_prompt(client, agent_id, prompt_path, dry_run=args.dry_run)
    if prompt_report["divergences"]:
        for d in prompt_report["divergences"]:
            print(f"  DIFF:    {d}")
        print("  -> pushed canonical prompt" if prompt_report["pushed"] else "  -> dry-run, not pushed")
    else:
        print("  prompt OK — live matches canonical")

    config_report = push_voice_and_model(client, agent_id, config, dry_run=args.dry_run)
    if config_report.get("pushed"):
        print(f"  pushed voice/model config: {config_report['payload']}")
    elif config_report.get("reason"):
        print(f"  config: {config_report['reason']}")
    else:
        print(f"  config: dry-run, would push {config_report.get('payload')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
