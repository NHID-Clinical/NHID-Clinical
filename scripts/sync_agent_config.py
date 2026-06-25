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
     and agents/<name>.config.json ({"agent_id": "agent_...", "voice_id": null, "llm": null,
     "text_only": true|false}) — text_only must be set explicitly: it's what determines
     whether the embedded widget shows a chat entry point or a voice-call entry point,
     and the dashboard default (voice-only) does not match a text-chat-widget agent.
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


def _workflow_path(agent_name: str) -> Path:
    return AGENTS_DIR / f"{agent_name}_workflow.json"


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
    """Push voice_id/llm/text_only from the repo's config.json to the live agent, if set.

    text_only governs whether the embedded widget shows a chat entry point or a
    voice-call entry point (see https://elevenlabs.io/docs/agents-platform/guides/chat-mode) —
    it is not controllable from the <elevenlabs-convai> HTML attributes in site.js, only
    from this field, so it has to be pushed here rather than left as a dashboard default.
    """
    payload: dict = {}
    if config.get("voice_id"):
        payload.setdefault("conversation_config", {}).setdefault("tts", {})["voice_id"] = config["voice_id"]
    if config.get("llm"):
        payload.setdefault("conversation_config", {}).setdefault("agent", {}).setdefault("prompt", {})["llm"] = config["llm"]
    if config.get("text_only") is not None:
        payload.setdefault("conversation_config", {}).setdefault("conversation", {})["text_only"] = config["text_only"]
    if not payload:
        return {"pushed": False, "reason": "voice_id/llm/text_only not set in config — nothing to push"}
    if not dry_run:
        client.patch_agent_config(agent_id, payload)
    return {"pushed": not dry_run, "payload": payload}


def pull_voice_and_model(client: ElevenLabsClient, agent_name: str, agent_id: str, config: dict) -> dict:
    """Pull live voice_id/llm/text_only into the repo's config.json."""
    live = client.get_agent_config(agent_id)
    agent_cfg = live.get("conversation_config", {}).get("agent", {})
    tts_cfg = live.get("conversation_config", {}).get("tts", {})
    conversation_cfg = live.get("conversation_config", {}).get("conversation", {})
    config["voice_id"] = tts_cfg.get("voice_id", config.get("voice_id"))
    config["llm"] = agent_cfg.get("prompt", {}).get("llm", config.get("llm"))
    config["text_only"] = conversation_cfg.get("text_only", config.get("text_only"))
    _save_config(agent_name, config)
    return config


def push_workflow(client: ElevenLabsClient, agent_id: str, workflow_path: Path, *, dry_run: bool) -> dict:
    """Push agents/<name>_workflow.json (the call-flow graph) to the live agent, if present.

    Keys starting with "_" (e.g. "_schema_status") are repo-only annotations and are
    stripped before sending — see that file's own header for why this graph is marked
    unverified against ElevenLabs' real schema.
    """
    if not workflow_path.exists():
        return {"pushed": False, "reason": f"{workflow_path} not found — no workflow graph to push"}
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = {k: v for k, v in workflow.items() if not k.startswith("_")}
    if not workflow:
        return {"pushed": False, "reason": f"{workflow_path} has no nodes/edges — nothing to push"}
    payload = {"conversation_config": {"workflow": workflow}}
    if not dry_run:
        client.patch_agent_config(agent_id, payload)
    return {"pushed": not dry_run, "payload": payload}


def pull_workflow(client: ElevenLabsClient, agent_id: str, workflow_path: Path) -> dict:
    """Pull the live workflow graph into agents/<name>_workflow.json, preserving any
    leading-underscore annotation keys already in the repo file (e.g. "_schema_status")."""
    live = client.get_agent_config(agent_id)
    live_workflow = live.get("conversation_config", {}).get("workflow") or {}
    existing_notes = {}
    if workflow_path.exists():
        existing = json.loads(workflow_path.read_text(encoding="utf-8"))
        existing_notes = {k: v for k, v in existing.items() if k.startswith("_")}
    merged = {**existing_notes, **live_workflow}
    workflow_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return {"node_count": len(live_workflow.get("nodes", [])), "edge_count": len(live_workflow.get("edges", []))}


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
    workflow_path = _workflow_path(args.agent)

    if args.pull:
        prompt_report = pull_prompt(client, agent_id, prompt_path)
        print(f"Pulled prompt for {args.agent} ({prompt_report['live_name']}): "
              f"{prompt_report['prompt_chars']} chars -> {prompt_path}")
        updated_config = pull_voice_and_model(client, args.agent, agent_id, config)
        print(f"Pulled voice/model config -> {_config_path(args.agent)}: "
              f"voice_id={updated_config.get('voice_id')!r} llm={updated_config.get('llm')!r} "
              f"text_only={updated_config.get('text_only')!r}")
        workflow_report = pull_workflow(client, agent_id, workflow_path)
        print(f"Pulled workflow graph -> {workflow_path}: "
              f"{workflow_report['node_count']} node(s), {workflow_report['edge_count']} edge(s)")
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

    workflow_report = push_workflow(client, agent_id, workflow_path, dry_run=args.dry_run)
    if workflow_report.get("pushed"):
        print(f"  pushed workflow graph: {workflow_path}")
    elif workflow_report.get("reason"):
        print(f"  workflow: {workflow_report['reason']}")
    else:
        print(f"  workflow: dry-run, would push {workflow_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
