"""
Tier 0 kit: one command, one evidence pack — and no invented numbers
====================================================================
The kit is the first thing a payer touches, and the two properties that make it
worth touching are easy to lose by accident:

  1. **It transmits nothing.** That is why its security review is short and why
     Tier 0 needs no BAA. A single `requests.post` anywhere in its import
     closure makes "nothing leaves your network" a false sentence.
  2. **It does not assert what it did not measure.** The report template asks
     for things transcripts cannot answer — who ran the pilot, how many flagged
     calls a person actually re-read, how many of those were false positives.
     A `0` in those cells reads as *reviewed, none false*: a clean finding
     nobody issued, in the direction that flatters the vendor.

These tests hold both lines, plus the parity line: the measurement logic moved
out of `docs/pilot-kit/measure_pilot.py` into `src/pilot_measure.py`, and the
documented command must still produce exactly the same figures.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.pilot_measure import (
    ATTESTATIONS, call_attestation, demo_records, dropped_record_count,
    measure_records, write_per_call_results,
)
from src.pilot_report import NOT_RECORDED, generate_report

REPO_ROOT = Path(__file__).resolve().parent.parent
KIT_SCRIPT = REPO_ROOT / "docs" / "pilot-kit" / "measure_pilot.py"

try:  # reportlab is an optional extra — see pyproject [project.optional-dependencies]
    import reportlab  # noqa: F401
    HAVE_REPORTLAB = True
except ImportError:  # pragma: no cover - depends on the install
    HAVE_REPORTLAB = False


@pytest.fixture(scope="module")
def measured():
    calls, summary = measure_records(demo_records())
    return calls, summary


@pytest.fixture(scope="module")
def report(measured):
    calls, summary = measured
    return generate_report(calls, summary, dropped_records=0)


# ──────────────────────────────────────────────────────────────────────────
# Parity: the move must not have changed a single measured value
# ──────────────────────────────────────────────────────────────────────────

def _run(args, cwd=REPO_ROOT):
    return subprocess.run([sys.executable, *args], cwd=cwd,
                          capture_output=True, text=True)


def test_documented_kit_command_still_runs():
    """`python docs/pilot-kit/measure_pilot.py --demo` is written down in the
    kit README, the Playbook and on the website. Moving the logic must not
    break it."""
    r = _run([str(KIT_SCRIPT), "--demo"])
    assert r.returncode == 0, r.stderr
    assert "Tier 0 pilot metrics" in r.stdout


def test_kit_script_and_nhid_pilot_report_identical_metrics(tmp_path):
    """The two entry points go through one measurement path, so they cannot
    disagree. If this ever fails, a second implementation has appeared."""
    shim = _run([str(KIT_SCRIPT), "--demo", "--json"])
    assert shim.returncode == 0, shim.stderr
    # The shim prints warnings to stderr and only JSON to stdout.
    from_shim = json.loads(shim.stdout)

    cli = _run(["-m", "src.cli", "pilot", "--demo", "--out", str(tmp_path / "pack")])
    assert cli.returncode == 0, cli.stderr
    from_cli = json.loads((tmp_path / "pack" / "metrics.json").read_text())

    assert from_shim == from_cli


def test_kit_script_still_accepts_results_dir(tmp_path):
    """`--results-dir` feeds tools/pilot_report_generator.py. It is documented
    as a two-step workflow and still has to work."""
    out = tmp_path / "results"
    r = _run([str(KIT_SCRIPT), "--demo", "--results-dir", str(out)])
    assert r.returncode == 0, r.stderr
    written = sorted(p.name for p in out.glob("*.json"))
    assert written == ["demo-clean.json", "demo-late.json", "demo-noescalate.json"]


# ──────────────────────────────────────────────────────────────────────────
# The evidence pack
# ──────────────────────────────────────────────────────────────────────────

def test_pilot_writes_the_whole_pack(tmp_path):
    out = tmp_path / "pack"
    r = _run(["-m", "src.cli", "pilot", "--demo", "--out", str(out)])
    assert r.returncode == 0, r.stderr
    assert (out / "pilot_report.md").read_text().startswith("# NHID-Clinical")
    assert json.loads((out / "metrics.json").read_text())["calls_total"] == 3
    assert len(list((out / "per-call").glob("*.json"))) == 3


def test_pilot_refuses_to_write_a_pack_from_nothing(tmp_path):
    """An empty capture produces no report. A pack with no findings in it reads
    as a clean result, which is the one thing it must never do by accident."""
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    out = tmp_path / "pack"
    r = _run(["-m", "src.cli", "pilot", str(empty), "--out", str(out)])
    assert r.returncode == 1
    assert not out.exists()
    assert "clean result" in r.stderr


def test_per_call_results_carry_no_transcript(tmp_path):
    """Per-call files get attached to tickets and mailed around. They must hold
    the verdict and nothing that could be PHI."""
    calls, _ = measure_records(demo_records())
    write_per_call_results(calls, tmp_path)
    for path in tmp_path.glob("*.json"):
        data = json.loads(path.read_text())
        assert set(data) == {"session_id", "conformant", "violations"}
        blob = path.read_text().lower()
        for leak in ("speech_text", "transcript", "member id", "mock-123456"):
            assert leak not in blob, f"{path.name} carries {leak!r}"


# ──────────────────────────────────────────────────────────────────────────
# Unrecorded is not zero
# ──────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("row", [
    "Calls dropped for unmappable or missing fields",
    "Flagged calls hand-reviewed by a person",
    "…of those, violations confirmed",
    "…of those, false positives",
])
def test_unmeasurable_rows_are_marked_not_zeroed(report, row):
    line = next(ln for ln in report.splitlines() if ln.startswith(f"| {row} "))
    assert NOT_RECORDED in line
    assert "| 0 |" not in line


def test_caller_supplied_context_is_marked_when_absent(measured):
    calls, summary = measured
    bare = generate_report(calls, summary)
    for label in ("Organization:", "Workflow:", "Date range of traffic:",
                  "Prepared by:", "Capture source:"):
        line = next(ln for ln in bare.splitlines() if label in ln)
        assert NOT_RECORDED in line, label


def test_caller_supplied_context_is_used_when_given(measured):
    calls, summary = measured
    filled = generate_report(
        calls, summary, organization="Northgate Health", workflow="Claims status",
        date_range="2026-06-01 to 2026-06-30", prepared_by="B. Baynard",
        source_label="calls.jsonl",
    )
    assert "**Organization:** Northgate Health" in filled
    assert "**Workflow:** Claims status" in filled
    assert NOT_RECORDED not in filled.split("## Key metrics")[0]


def test_records_without_session_id_are_counted_not_merged():
    """An unattributed turn joined to another call would change that call's
    measured numbers."""
    records = demo_records()
    records.append({"turn_index": 0, "timestamp": "2026-07-01T13:00:00Z",
                    "speaker": "agent", "speech_text": "orphan"})
    assert dropped_record_count(records) == 1
    calls, summary = measure_records(records)
    assert summary["calls_total"] == 3

    report = generate_report(calls, summary, dropped_records=1)
    line = next(ln for ln in report.splitlines()
                if "Records dropped for a missing" in ln)
    assert "| 1 |" in line


# ──────────────────────────────────────────────────────────────────────────
# Transcription attestation
# ──────────────────────────────────────────────────────────────────────────

def test_absent_attestation_is_not_recorded_rather_than_unattested(measured):
    """`unattested` is the organization saying nothing is known. Not recorded is
    the organization not having said. Collapsing them turns a missing field
    into an assertion nobody made."""
    _, summary = measured
    att = summary["transcription_attestation"]
    assert att["not_recorded"] == 3
    assert att["unattested"] == 0


def test_attestation_is_read_from_the_capture_when_present():
    records = demo_records()
    for r in records:
        if r["session_id"] == "demo-clean":
            r["transcription_attestation"] = "measured"
    _, summary = measure_records(records)
    att = summary["transcription_attestation"]
    assert att["measured"] == 1
    assert att["not_recorded"] == 2


def test_turns_disagreeing_about_attestation_report_conflicting():
    """Picking the first value would hide a capture pipeline that does not
    agree with itself about which transcripts have been checked."""
    assert call_attestation([
        {"transcription_attestation": "measured"},
        {"transcription_attestation": "unattested"},
    ]) == "conflicting"
    assert call_attestation([{"transcription_attestation": "attested"}] * 3) == "attested"
    assert call_attestation([{}, {}]) is None


def test_report_warns_when_nothing_is_attested(report):
    assert "No call in this sample carried a transcription attestation" in report


def test_attestation_field_is_in_the_published_capture_schema():
    """The kit README lists transcription attestation under what Tier 0
    measures. That is only true if the capture schema can carry it."""
    schema = json.loads(
        (REPO_ROOT / "docs" / "pilot-kit" / "minimal-event-schema.json").read_text())
    field = schema["properties"]["transcription_attestation"]
    assert set(ATTESTATIONS) <= set(field["enum"])


# ──────────────────────────────────────────────────────────────────────────
# What the report says about itself
# ──────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("claim", [
    "measurements, not",            # never a certification
    "ATR-01 is not exercised",      # not assessable by replay
    "DBC-01 reads text, not audio",
    "does not establish ASR accuracy",
    "not an accredited standard",
])
def test_report_carries_its_own_limitations(report, claim):
    assert claim.lower() in report.lower()


def test_report_does_not_resurrect_the_composite_score(report):
    """CAS, its trust tiers and its badges are withdrawn with no successor.

    The report is allowed — expected — to name them in order to say they are
    withdrawn. What it must not do is present one as a value, so the tier
    labels must be absent entirely, and "composite" may appear only in a
    sentence that withdraws it.
    """
    lowered = report.lower()
    for tier in ("verified trust", "conditional trust", "review required",
                 "denied-degraded", "hard denial"):
        assert tier not in lowered, f"tier label {tier!r} is presented as a value"

    for line in lowered.split("\n\n"):
        if "composite" in line:
            assert "withdrawn" in line, f"composite mentioned without withdrawal: {line}"


def test_atr01_is_labelled_not_assessed_rather_than_clean(report):
    line = next(ln for ln in report.splitlines() if ln.startswith("| ATR-01 |"))
    assert "not assessed by replay" in line


# ──────────────────────────────────────────────────────────────────────────
# The offline promise
# ──────────────────────────────────────────────────────────────────────────

def test_guard_covers_the_kits_whole_import_closure():
    """Guarding only the entry point left the engine free to grow an HTTP
    client while the guard reported PASS."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from check_offline_kit import GUARDED

    for expected in (
        "docs/pilot-kit/measure_pilot.py",
        "src/pilot_measure.py",
        "src/pilot_report.py",
        "src/pilot_pdf.py",
        "src/cli.py",
        "src/nhid_policy_engine_v1.py",
        "src/synthetic_eval_loop.py",
        "src/nhid_audit_trail.py",
        "src/audit_integrity.py",
    ):
        assert expected in GUARDED, f"{expected} is not guarded"


def test_ci_runs_the_guard_that_covers_the_closure():
    """CI used to run `scripts/check_pilot_offline.py`, which inspected only
    `docs/pilot-kit/measure_pilot.py`. Once that file became a shim, the step
    would have gone on passing while guarding almost nothing — the enforced
    check has to be the one that covers the closure, and there must be only
    one of it."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "python scripts/check_offline_kit.py" in ci
    assert "check_pilot_offline" not in ci.replace(
        "scripts/check_pilot_offline.py, which inspected only", "")
    assert not (REPO_ROOT / "scripts" / "check_pilot_offline.py").exists(), (
        "two guards for one promise can disagree, and one passing masks the other"
    )


def test_guard_passes_over_the_kit_as_shipped():
    r = _run([str(REPO_ROOT / "scripts" / "check_offline_kit.py")])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OFFLINE GUARD PASS" in r.stdout


@pytest.mark.parametrize("source, why", [
    ("import requests\n", "an HTTP client"),
    ("from urllib.request import urlopen\n", "a stdlib fetch"),
    ("import subprocess\nsubprocess.run(['curl', 'x'])\n", "shelling out"),
    ("x = __import__('httpx')\n", "a dynamic import"),
])
def test_guard_actually_catches_a_phone_home(source, why):
    """A guard that has only ever passed is not known to work."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import ast

    from check_offline_kit import NetworkReachVisitor

    visitor = NetworkReachVisitor()
    visitor.visit(ast.parse(source))
    assert visitor.findings, f"guard missed {why}"


def test_guard_does_not_trip_on_prose_about_networking():
    """A README that says "this kit does not use requests" is exactly the
    sentence an honest kit should contain. Punishing it teaches people to
    delete the guarantee."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import ast

    from check_offline_kit import NetworkReachVisitor

    visitor = NetworkReachVisitor()
    visitor.visit(ast.parse(
        '"""This kit does not use requests, urllib, or subprocess."""\n'
        'NOTE = "no socket is opened and nothing is posted"\n'))
    assert visitor.findings == []


# ──────────────────────────────────────────────────────────────────────────
# PDF: optional, and never at the cost of the report
# ──────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not HAVE_REPORTLAB, reason="reportlab is an optional extra")
def test_pdf_renders_and_contains_the_measured_figures(tmp_path):
    out = tmp_path / "pack"
    r = _run(["-m", "src.cli", "pilot", "--demo", "--out", str(out),
              "--organization", "Northgate Health"])
    assert r.returncode == 0, r.stderr

    pdf = out / "pilot_report.pdf"
    assert pdf.stat().st_size > 1000

    from pdfminer.high_level import extract_text
    text = extract_text(str(pdf))
    assert "Tier 0 Shadow Pilot Report" in text
    assert "Northgate Health" in text
    # The figures, not just the headings.
    assert "66.7%" in text
    # Markdown syntax must not survive into the rendered page.
    assert "**" not in text


def test_pilot_still_writes_the_report_without_reportlab(tmp_path):
    """A missing optional extra must not cost the user the report they just
    computed, and must not produce a traceback."""
    out = tmp_path / "pack"
    blocker = tmp_path / "no_reportlab.py"
    blocker.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "class Blocker:\n"
        "    def find_spec(self, name, target=None, path=None):\n"
        "        if name == 'reportlab' or name.startswith('reportlab.'):\n"
        "            raise ImportError('blocked', name='reportlab')\n"
        "        return None\n"
        "sys.meta_path.insert(0, Blocker())\n"
        f"sys.argv = ['nhid', 'pilot', '--demo', '--out', {str(out)!r}]\n"
        "from src.cli import main\n"
        "raise SystemExit(main())\n"
    )
    r = _run([str(blocker)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr
    assert (out / "pilot_report.md").exists()
    assert (out / "metrics.json").exists()
    assert not (out / "pilot_report.pdf").exists()
    assert "nhid-clinical[pdf]" in r.stdout


@pytest.mark.skipif(not HAVE_REPORTLAB, reason="reportlab is an optional extra")
def test_shared_renderer_handles_bold_around_an_italic():
    """`**bold with *italic* inside**` used to leak its asterisks into the
    published PDF, including on the Playbook's own opening page."""
    from src.pilot_pdf import inline

    out = inline("**This Playbook answers *how exactly* this works.**")
    assert "**" not in out
    assert "<b>" in out and "<i>" in out


@pytest.mark.skipif(not HAVE_REPORTLAB, reason="reportlab is an optional extra")
def test_shared_renderer_is_reachable_from_the_playbook_build():
    """One markdown renderer, two documents. Two copies drift."""
    import scripts.build_playbook_pdf as playbook

    from src.pilot_pdf import render_markdown_pdf
    assert playbook.render_markdown_pdf is render_markdown_pdf
