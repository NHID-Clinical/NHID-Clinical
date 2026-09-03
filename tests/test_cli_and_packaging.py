"""
CLI surface, packaging metadata, and conformance-suite integrity
================================================================
The CLI holds no logic of its own — these tests check that it dispatches to the
existing code and reports its results faithfully, not that it computes anything.

The suite-integrity tests exist because the repository carries two copies of
the conformance suite: the published `conformance/` copy that reviewers read,
and the `tests/` copy that `run_cts()` actually executes. They agree today and
nothing was enforcing that they continue to.
"""
import json
import tomllib
from pathlib import Path

import pytest
import yaml

from src.cli import build_parser, main

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_SUITE = REPO_ROOT / "conformance" / "nhid_conformance_test_suite_v1.yaml"
EXECUTED_SUITE = REPO_ROOT / "tests" / "nhid_conformance_test_suite_v1.yaml"


def _load_cases(path: Path) -> dict:
    cases = {}
    for doc in yaml.safe_load_all(path.read_text()):
        if isinstance(doc, list):
            cases.update({c["test_id"]: c for c in doc if isinstance(c, dict) and "test_id" in c})
        elif isinstance(doc, dict) and "test_id" in doc:
            cases[doc["test_id"]] = doc
    return cases


# ── Conformance suite integrity ────────────────────────────────────────────

def test_both_suite_copies_exist():
    assert PUBLISHED_SUITE.exists() and EXECUTED_SUITE.exists()


def test_published_and_executed_suites_are_semantically_identical():
    """The suite a reviewer reads must be the suite that runs.

    The files differ in bytes — the published copy carries a suite_metadata
    header — but every test case must match exactly. If this fails, the project
    is publishing conformance criteria it does not execute.
    """
    published = _load_cases(PUBLISHED_SUITE)
    executed = _load_cases(EXECUTED_SUITE)
    assert set(published) == set(executed), "test_id sets diverged"
    for test_id in sorted(published):
        assert published[test_id] == executed[test_id], f"case {test_id} diverged"


def test_runner_executes_the_expected_suite_file():
    from src.cts_runner import _YAML_PATH

    assert Path(_YAML_PATH).resolve() == EXECUTED_SUITE.resolve()


def test_published_suite_metadata_matches_the_real_count():
    """suite_metadata claimed '173 passed' long after the suite had grown."""
    from scripts.validate_ci import UNIT_PUBLISHED

    metadata = next(
        doc["suite_metadata"]
        for doc in yaml.safe_load_all(PUBLISHED_SUITE.read_text())
        if isinstance(doc, dict) and "suite_metadata" in doc
    )
    assert metadata["unit_tests"]["count"] == UNIT_PUBLISHED
    assert str(UNIT_PUBLISHED) in metadata["invariant"]


# ── Packaging metadata ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pyproject():
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())


def test_project_declares_a_console_entry_point(pyproject):
    assert pyproject["project"]["scripts"]["nhid"] == "src.cli:main"


def test_core_dependencies_stay_minimal(pyproject):
    """A vendor embedding the engine must not inherit a web stack."""
    deps = {d.split(">")[0].split("=")[0].strip() for d in pyproject["project"]["dependencies"]}
    assert deps == {"cryptography", "pyyaml"}
    for heavy in ("fastapi", "uvicorn", "openai", "pytest"):
        assert not any(heavy in d for d in pyproject["project"]["dependencies"])


def test_api_and_dev_extras_carry_the_heavier_dependencies(pyproject):
    extras = pyproject["project"]["optional-dependencies"]
    assert any("fastapi" in d for d in extras["api"])
    assert any("pytest" in d for d in extras["dev"])


def test_pytest_config_is_not_duplicated(pyproject):
    """pytest.ini is the single source of truth; pyproject must not shadow it."""
    assert "pytest" not in pyproject.get("tool", {})
    assert (REPO_ROOT / "pytest.ini").exists()


# ── CLI dispatch ───────────────────────────────────────────────────────────

def test_parser_exposes_the_two_documented_subcommands():
    parser = build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]
    assert set(actions[0].choices) == {"conformance", "export-evidence"}


def test_conformance_subcommand_reports_real_results(capsys):
    assert main(["conformance"]) == 0
    out = capsys.readouterr().out
    assert "18 cases" in out and "0 failed" in out


def test_conformance_json_output_is_machine_readable(capsys):
    main(["conformance", "--json"])
    results = json.loads(capsys.readouterr().out)
    assert results["total"] == 18 and results["failed"] == 0


def test_conformance_ci_flag_passes_when_the_suite_passes():
    assert main(["conformance", "--ci"]) == 0


def test_conformance_ci_flag_fails_the_build_on_a_failing_case(monkeypatch, capsys):
    """The --ci contract: a regression in the controls breaks the vendor's build."""
    import src.cli

    monkeypatch.setattr(
        "src.cts_runner.run_cts",
        lambda **kw: {
            "passed": 17, "failed": 1, "skipped": 0, "total": 18,
            "results": [{"test_id": "IDG-01-PASS", "status": "fail", "detail": "drifted"}],
        },
    )
    assert src.cli.main(["conformance", "--ci"]) == 1
    captured = capsys.readouterr()
    assert "IDG-01-PASS" in captured.out
    assert "no longer behave" in captured.err


def test_conformance_without_ci_flag_does_not_fail_on_failures(monkeypatch):
    import src.cli

    monkeypatch.setattr(
        "src.cts_runner.run_cts",
        lambda **kw: {"passed": 17, "failed": 1, "skipped": 0, "total": 18, "results": []},
    )
    assert src.cli.main(["conformance"]) == 0


def test_export_evidence_subcommand_writes_a_bundle(tmp_path):
    assert main(["export-evidence", "--out", str(tmp_path), "--no-conformance"]) == 0
    assert (tmp_path / "evidence-pack.json").exists()


def test_export_evidence_records_the_suite_it_actually_ran(tmp_path):
    main(["export-evidence", "--out", str(tmp_path)])
    bundle = json.loads((tmp_path / "evidence-pack.json").read_text())
    artifact = bundle["artifacts"]["conformance_results"]
    assert artifact["suite"] == "tests/nhid_conformance_test_suite_v1.yaml"
    assert "two copies" in artifact["suite_note"]
