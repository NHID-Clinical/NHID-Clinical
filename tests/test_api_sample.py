"""The Developers page's API sample is the handler's answer, not a typed one.

`scripts/build_api_sample.py` runs one synthetic adapter request through
`functions.handler.lambda_handler` and writes the response between markers on
developers.html. If the engine changes, the recorded answer must be
regenerated; this test is what notices.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_api_sample.py"
LADDER = {"DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI"}


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("build_api_sample", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_page_block_is_a_fresh_handler_run(gen):
    html = (ROOT / "developers.html").read_text(encoding="utf-8")
    block = html[html.index(gen.BEGIN):html.index(gen.END) + len(gen.END)]
    assert block == gen.render(gen.build()), "developers.html sample is stale; run scripts/build_api_sample.py"


def test_the_recorded_json_matches_the_handler(gen):
    committed = json.loads(gen.OUT.read_text(encoding="utf-8"))
    fresh = gen.build()
    assert committed["response"] == fresh["response"]
    assert committed["request"] == fresh["request"] == gen.REQUEST


def test_the_answer_is_an_engine_decision(gen):
    sample = gen.build()
    assert sample["status"] == 200
    assert sample["response"]["action"] in LADDER
    assert sample["response"]["reason_code"].startswith(("IDG01_", "PDX01_", "DBC01_", "EIT01_", "ATR01_", "DLG01_"))
    assert sample["response"]["vendor"] == "vapi"


def test_the_panel_says_synthetic_and_links_no_retired_route():
    html = (ROOT / "developers.html").read_text(encoding="utf-8")
    panel = html[html.index('id="try-the-live-api"'):html.index("<!-- END GENERATED api-sample -->")]
    assert "Synthetic data only, never PHI" in panel
    for retired in ("docs.html", "simulator.html", "playground.html"):
        assert retired not in panel


def test_the_request_contains_no_real_identifiers(gen):
    """The NPI in the sample is the documentation placeholder, not a real one."""
    text = json.dumps(gen.REQUEST)
    assert "1234567890" in text
    assert "call_demo" in text
