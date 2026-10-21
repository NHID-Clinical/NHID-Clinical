"""
Which module is the conformance engine, and which surfaces run it
=================================================================
This repository contains three policy modules and three HTTP surfaces, and
until now nothing recorded which was which:

| module | size | actions | runs the five controls |
| :-- | --: | :-- | :-- |
| `src/nhid_policy_engine_v1.py` | ~2,070 lines | the enforcement ladder | **yes** |
| `nhid_policy.py` | ~120 lines | DISCLOSE/ESCALATE/BLOCK/ROUTE_LLM/ERROR | no |
| `src/voice_policy.py` | ~230 lines | rule-evaluator decisions | no |

`README.md` previously grouped the root-level modules as "the deterministic
policy engine, conformance API, event store, and call handling" and described
`src/` as "modules used by the engine". A reviewer following that would look in
the root for the engine, find the 120-line state machine, and conclude the five
controls were not implemented. The engine is in `src/`, and only
`functions/handler.py` serves it over HTTP.

These tests pin the boundary rather than the prose: they assert from the code
which module carries the controls, that the voice pipeline genuinely does not,
and that the README still says so. A future refactor that wires the voice
pipeline into the conformance engine should delete the tests here that say it
does not — deliberately, with the README updated in the same change.
"""
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")


# ── The conformance engine is the one in src/ ─────────────────────────────────

def test_the_conformance_engine_implements_every_control():
    import src.nhid_policy_engine_v1 as engine

    for control in CONTROLS:
        evaluator = f"evaluate_{control.replace('-', '').lower()}"
        assert hasattr(engine, evaluator), (
            f"{control} has no {evaluator} in src/nhid_policy_engine_v1.py"
        )
    assert hasattr(engine, "evaluate_all")
    assert hasattr(engine, "evaluate_dlg01"), "the opt-in DLG-01 gate"


def test_the_engines_enforcement_ladder_is_the_published_one():
    from src.nhid_policy_engine_v1 import PolicyAction

    assert {action.name for action in PolicyAction} == {
        "DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY",
        "CONTINUE_AI",
    }


# ── The voice pipeline is a different thing, and says so ──────────────────────

def test_the_voice_pipeline_state_machine_is_not_the_conformance_engine():
    """Distinct action vocabularies, so the two cannot be confused in code."""
    from nhid_policy import PolicyAction as VoiceAction
    from src.nhid_policy_engine_v1 import PolicyAction as EngineAction

    voice = {a.name for a in VoiceAction}
    engine = {a.name for a in EngineAction}
    assert voice == {"DISCLOSE", "ESCALATE", "BLOCK", "ROUTE_LLM", "ERROR"}
    assert not (voice & engine), (
        "the two policy vocabularies now overlap; if the voice pipeline has "
        "been wired to the conformance engine, update the README row and "
        "delete this test deliberately"
    )


def test_the_voice_pipeline_implements_none_of_the_five_controls():
    """Asserted from the module's own source, not from documentation."""
    import nhid_policy

    source = inspect.getsource(nhid_policy)
    named = [control for control in CONTROLS if control in source]
    assert named == [], (
        f"nhid_policy.py now references {named}; it is documented as "
        f"implementing none of the controls"
    )


def test_the_voice_app_does_not_import_the_conformance_engine():
    """The fact the README row turns on. If this starts failing, the voice
    pipeline has gained real conformance enforcement and the README must stop
    saying it has none."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "nhid_policy_engine_v1" not in source


# ── Only one HTTP surface runs the engine ─────────────────────────────────────

def test_the_conformance_api_is_the_surface_that_runs_the_engine():
    source = (ROOT / "functions" / "handler.py").read_text(encoding="utf-8")
    assert "nhid_policy_engine_v1" in source
    assert "evaluate_all" in source


def test_the_lambda_template_deploys_the_conformance_api():
    """The deployed artifact is the Lambda, not either ASGI app."""
    template = (ROOT / "template.yaml").read_text(encoding="utf-8")
    assert "functions.handler.lambda_handler" in template


# ── The README reflects all of the above ──────────────────────────────────────

def test_the_readme_names_the_engine_module_explicitly():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "src/nhid_policy_engine_v1.py" in readme, (
        "the README must name the module that carries the controls; grouping "
        "it under 'src/ — modules used by the engine' sent readers to the "
        "120-line state machine in the root instead"
    )


def test_the_readme_distinguishes_the_voice_pipeline_from_the_engine():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "nhid_policy.py" in readme
    # The row has to state the relationship, not merely list the file.
    assert "not the conformance engine" in readme.lower() or (
        "implements none of the five controls" in readme.lower()
    )


@pytest.mark.parametrize("module", ["src/nhid_policy_engine_v1.py", "nhid_policy.py",
                                    "src/voice_policy.py"])
def test_each_policy_module_still_exists_where_documented(module):
    assert (ROOT / module).is_file(), f"{module} is referenced but absent"
