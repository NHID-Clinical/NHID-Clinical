#!/usr/bin/env python3
"""
Tier 0 evidence pack — the pilot report, filled from measured values
====================================================================
Renders `docs/pilot-kit/pilot-report-template.md` from a real aggregate, so a
pilot produces the document a health plan actually circulates instead of a
template plus a terminal screenshot.

THE ONE RULE THIS FILE EXISTS TO ENFORCE
----------------------------------------
A pilot report is read by people deciding whether to trust a vendor. Several
rows in the template are things the kit CANNOT know from transcripts — who ran
it, over which workflow, across which dates, how many calls were dropped as
unmappable, how many flagged calls a human actually re-read, and how many of
those were false positives.

Every one of those is emitted as `NOT_RECORDED`, never as `0`.

That is not pedantry. "Flagged calls hand-reviewed: 0 · confirmed: 0 · false
positives: 0" reads as *reviewed, none were false* — a clean bill of health
nobody issued. A zero in an unmeasured cell is a fabricated control assertion,
and it is fabricated in the direction that flatters the vendor. So the only
numbers in this document are measured ones, and the rest say so.

For the same reason the report carries its limitations in the body rather than
a footnote: ATR-01 is not exercisable by transcript replay, DBC-01 reads text
and not audio, and every figure is bounded by a transcription whose accuracy
NHID-Clinical does not establish.

SENDS NOTHING. Guarded by `scripts/check_offline_kit.py`.

NHID-Clinical is a voluntary open proposal. This module is licensed
Apache-2.0 (see LICENSE); the control text it reports against is CC BY 4.0
(see LICENSE-DOCS).
Metrics are measurements, not conformance certifications.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.pilot_measure import ATTESTATIONS, CONTROLS, DISCLOSURE_BANDS

# The single marker for "the kit cannot know this". Tests assert on it, so it
# lives here once rather than being retyped per row.
NOT_RECORDED = "_not recorded — fill in_"

CONTROL_NAMES = {
    "IDG-01": "Identity Disclosure Gate",
    "PDX-01": "Pre-Data Exchange Gate",
    "DBC-01": "Deceptive Behavior Check",
    "EIT-01": "Escalation Implementation Test",
    "ATR-01": "Audit Trail Requirements",
}

ATTESTATION_LABELS = {
    "measured": "`measured` — word error rate measured on this corpus",
    "attested": "`attested` — a WER figure asserted by the vendor, not measured here",
    "unattested": "`unattested` — nothing known about transcript accuracy",
    "conflicting": "`conflicting` — turns of one call disagree (capture pipeline issue)",
    "not_recorded": "not recorded — the capture did not carry this field",
}

# Verbatim from docs/pilot-kit/README.md. They belong in the generated document
# because the document travels without the README.
LIMITATIONS = [
    ("ATR-01 is not exercised by this report.",
     "Audit Trail Requirements cannot be assessed from transcript replay — the "
     "kit synthesizes complete audit envelopes by construction, so an ATR-01 "
     "count of zero here means *not assessed*, not *clean*. Audit completeness "
     "is assessed at Tier 1+ against a real event pipeline."),
    ("DBC-01 reads text, not audio.",
     "It evaluates the agent's own identity assertion for claims of human or "
     "licensed-professional status. Its former acoustic-artifact tier was "
     "withdrawn. Residual implicit-impersonation cases are a known "
     "human-review area, not a solved detection problem."),
    ("Every figure depends on your transcription.",
     "A disclosure that was spoken but mis-transcribed reads as a missing "
     "disclosure; a mis-transcribed escalation request produces no finding at "
     "all. NHID-Clinical does not establish ASR accuracy — see the "
     "transcription attestation section and treat it as a limit on everything "
     "else here."),
]


def _pct(n: int, total: int) -> str:
    return f"{n / total:.1%}" if total else NOT_RECORDED


def _or_unrecorded(value) -> str:
    """Render a caller-supplied field, or the marker when it was not given."""
    text = str(value).strip() if value is not None else ""
    return text or NOT_RECORDED


def generate_report(
    calls: list[dict],
    summary: dict,
    *,
    organization: str | None = None,
    workflow: str | None = None,
    date_range: str | None = None,
    prepared_by: str | None = None,
    source_label: str | None = None,
    dropped_records: int | None = None,
    generated_at: datetime | None = None,
    framework_version: str = "1.3",
) -> str:
    """Render the Tier 0 pilot report as markdown.

    Only `calls` and `summary` carry measured values. Everything else is
    context the person running the pilot supplies; anything they leave out is
    marked, not guessed.
    """
    total = summary["calls_total"]
    when = (generated_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    bands = summary["disclosure_bands"]
    att = summary.get("transcription_attestation", {})

    mit = summary["median_impersonation_latency_turns"]
    mis = summary["median_impersonation_latency_seconds"]
    # Censored calls (never disclosed) are included at their lower bound, so
    # the median is itself a lower bound and has to be written as one.
    bound = "≥ " if summary.get("median_impersonation_latency_is_lower_bound") else ""
    il = "n/a — no calls measured" if mit is None else (
        f"{bound}{mit} turns"
        + (f" / {bound}{mis:.1f}s" if mis is not None else " (no time anchor)")
    )
    ehr = summary["escalation_honor_rate"]
    ehr_text = "n/a — no escalation requested" if ehr is None else f"{ehr:.1%}"

    L: list[str] = [
        "# NHID-Clinical Tier 0 Shadow Pilot Report",
        "",
        f"**Organization:** {_or_unrecorded(organization)}  ",
        f"**Workflow:** {_or_unrecorded(workflow)}  ",
        f"**Sample size:** {total} calls  ",
        f"**Date range of traffic:** {_or_unrecorded(date_range)}  ",
        f"**Prepared by:** {_or_unrecorded(prepared_by)}  ",
        f"**Report generated:** {when} (UTC)  ",
        f"**Capture source:** {_or_unrecorded(source_label)}",
        "",
        "> Measurements from a shadow pilot against this organization's own call",
        f"> traffic using the NHID-Clinical v{framework_version} Tier 0 kit. NHID-Clinical is a",
        "> voluntary open baseline (CC BY 4.0) — these are **measurements, not",
        "> certifications**, and nothing here is an accredited standard or a",
        "> regulatory finding.",
        "",
        "## Key metrics",
        "",
        "| Metric | Value | Denominator |",
        "| :--- | :--- | :--- |",
        f"| Median Impersonation Latency | {il} | {total} calls |",
        f"| First-turn disclosure rate | {summary['first_turn_disclosure_rate']:.1%} | {total} calls |",
        f"| Never-disclosed rate | {summary['never_disclosed_rate']:.1%} | {total} calls |",
        f"| Calls with pre-disclosure PHI | {summary['calls_with_pre_disclosure_phi_rate']:.1%} | {total} calls |",
        f"| Escalation honor rate | {ehr_text} | requests, not calls |",
        "",
        "Each figure carries its own denominator and none is blended into a",
        "composite. The former composite score, its trust tiers and its badges",
        "are withdrawn, and nothing replaces them.",
        "",
        "## Disclosure timeliness",
        "",
        "| Band | Definition | Calls | % |",
        "| :--- | :--- | ---: | ---: |",
    ]

    for band, definition in DISCLOSURE_BANDS.items():
        n = bands.get(band, 0)
        L.append(f"| `{band}` | {definition} | {n} | {_pct(n, total)} |")

    L += [
        "",
        "Bands are a reporting convention, not an enforcement threshold — the",
        "normative target is `IL(turns) = 0`. Every pass/fail verdict above comes",
        "from the policy engine, which has no seconds-based rule. Use this table",
        "to separate agents that disclose slowly from agents that do not disclose",
        "at all; they warrant different conversations with the vendor.",
        "",
        "## Transcription attestation",
        "",
        "Every figure in this report is bounded by the transcripts it was computed",
        "over. NHID-Clinical does not establish ASR accuracy; this records what is",
        "known.",
        "",
        "| Attestation | Calls | % |",
        "| :--- | ---: | ---: |",
    ]

    for key in list(ATTESTATIONS) + ["conflicting", "not_recorded"]:
        n = att.get(key, 0)
        L.append(f"| {ATTESTATION_LABELS[key]} | {n} | {_pct(n, total)} |")

    not_recorded = att.get("not_recorded", 0)
    if not_recorded == total and total:
        L += [
            "",
            "**No call in this sample carried a transcription attestation.** That is",
            "reported as *not recorded* rather than as `unattested`, because the two",
            "are different facts: `unattested` is this organization stating nothing is",
            "known about transcript accuracy, and *not recorded* is this organization",
            "not having said. Until it is recorded, treat every figure above as",
            "resting on transcripts of unmeasured accuracy.",
        ]
    elif att.get("conflicting"):
        L += [
            "",
            f"**{att['conflicting']} call(s) carried conflicting attestations across their",
            "own turns.** That points at the capture pipeline rather than at the agent",
            "under evaluation, and is worth resolving before these numbers are relied on.",
        ]

    L += [
        "",
        "## Violations by control",
        "",
        "| Control | Name | Calls affected | % |",
        "| :--- | :--- | ---: | ---: |",
    ]

    by_control = summary["violations_by_control"]
    for control in CONTROLS:
        n = by_control.get(control, 0)
        name = CONTROL_NAMES[control]
        if control == "ATR-01":
            name += " — **not assessed by replay**"
        L.append(f"| {control} | {name} | {n} | {_pct(n, total)} |")
    for rule, n in sorted(by_control.items()):
        if rule not in CONTROLS:
            L.append(f"| {rule} | (not a published v1.3 control) | {n} | {_pct(n, total)} |")

    L += [
        "",
        "A count is the number of calls on which the control was violated at least",
        "once, not the number of violating turns.",
        "",
        "## Data quality",
        "",
        "| Check | Value |",
        "| :--- | :--- |",
        f"| Records dropped for a missing `session_id` | "
        f"{dropped_records if dropped_records is not None else NOT_RECORDED} |",
        f"| Calls dropped for unmappable or missing fields | {NOT_RECORDED} |",
        f"| Flagged calls hand-reviewed by a person | {NOT_RECORDED} |",
        f"| …of those, violations confirmed | {NOT_RECORDED} |",
        f"| …of those, false positives | {NOT_RECORDED} |",
        "",
        "The marked rows are deliberately **not** zero. The kit cannot observe",
        "whether anyone re-read a flagged call, and printing `0` there would read",
        "as *reviewed, none false* — a clean finding nobody issued. Fill them in",
        "from your own review log, or leave them marked and say so.",
        "",
        "## What this report does not establish",
        "",
    ]

    for i, (headline, body) in enumerate(LIMITATIONS, 1):
        L += [f"{i}. **{headline}** {body}", ""]

    L += [
        "## Observations",
        "",
        f"{NOT_RECORDED}",
        "",
        "## Recommendations",
        "",
        f"{NOT_RECORDED}",
        "",
        "---",
        "",
        "Generated by `nhid pilot` from this organization's own capture records.",
        "The kit runs locally and transmits nothing; no part of this report was",
        "sent anywhere in producing it.",
        "",
        "NHID-Clinical is a voluntary open proposal — not an accredited standard,",
        "not a regulatory requirement, and not a certification of any product.",
        "",
    ]
    return "\n".join(L)
