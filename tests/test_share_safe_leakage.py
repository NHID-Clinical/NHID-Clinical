"""
Planted-value measurement of the share-safe scan (src/share_safe_leakage.py).

The scan itself is unchanged; these tests pin what it catches and, just as
deliberately, what it misses. If someone widens ``PATTERNS`` or the identifier
rule, a "missed" row here starts failing, so the change to what packs are
refused is a visible decision rather than a silent one. The end-to-end test
holds the property that matters most today: the real share-safe pack carries
none of the planted values.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import share_safe_leakage as leak  # noqa: E402

CAUGHT = {
    ("session id", "as captured"),
    ("member id (letters and digits)", "as captured"),
    ("claim number", "as captured"),
    ("SSN", "dashed"),
    ("date of birth", "as captured (MM/DD/YYYY)"),
    ("phone number", "as captured"),
    ("phone number", "dotted"),
    ("email address", "as captured"),
    ("transcript run", "6 consecutive words"),
}
MISSED = {
    ("person name", "full name"),
    ("person name", "last name alone"),
    ("member id (letters and digits)", "lower case"),
    ("member id (digits only)", "as captured"),
    ("claim number", "lower case"),
    ("MRN", "as captured"),
    ("SSN", "no dashes"),
    ("SSN", "spaced"),
    ("date of birth", "ISO (YYYY-MM-DD)"),
    ("date of birth", "spelled out"),
    ("phone number", "digits only"),
    ("NPI", "as captured"),
    ("transcript run", "5 consecutive words"),
    ("identifier never in the input", "as written"),
}


@pytest.fixture(scope="module")
def corpus():
    return leak.generate_calls(8, seed=11)


@pytest.fixture(scope="module")
def probe(corpus):
    return {(c["kind"], c["form"]): c for c in leak.probe_scanner(*corpus)}


def test_generation_is_seeded(corpus):
    assert leak.generate_calls(8, seed=11) == corpus
    assert leak.generate_calls(8, seed=12) != corpus


def test_every_planted_value_is_in_the_input_or_marked_absent(corpus):
    records, manifest = corpus
    text = "\n".join(r["session_id"] + " " + r.get("speech_text", "") for r in records)
    for planted in manifest:
        if planted.field == "-":
            assert planted.value not in text
        else:
            assert planted.value in text, planted.kind


def test_the_planted_npis_carry_a_valid_check_digit(corpus):
    for planted in corpus[1]:
        if planted.kind == "NPI":
            digits = [int(c) for c in "80840" + planted.value]
            total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2)
                        for i, d in enumerate(reversed(digits)))
            assert total % 10 == 0


def test_every_form_is_pinned(probe):
    assert set(probe) == CAUGHT | MISSED


@pytest.mark.parametrize("cell", sorted(CAUGHT))
def test_what_the_scan_catches(probe, cell):
    assert probe[cell]["caught"] == probe[cell]["total"] > 0


@pytest.mark.parametrize("cell", sorted(MISSED))
def test_what_the_scan_misses_today(probe, cell):
    assert probe[cell]["caught"] == 0 < probe[cell]["total"]


def test_the_real_share_safe_pack_carries_no_planted_value(corpus):
    result = leak.pipeline_check(*corpus)
    assert result["released"] is True
    assert result["leaks"] == []
    # Header fields are typed by the person running the kit and go in as
    # written; the scan cannot recognise a name, so this one gets through.
    assert result["name_typed_as_organization"] == {"released": True, "name_in_pack": True}


def test_the_report_states_its_provenance(tmp_path):
    assert leak.main(["--out", str(tmp_path), "--calls", "2", "--seed", "3"]) == 0
    report = (tmp_path / "report.md").read_text()
    assert "Seed 3" in report and "No real patient data" in report
    assert (tmp_path / "results.json").exists()
