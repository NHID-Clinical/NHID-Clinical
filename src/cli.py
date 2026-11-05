"""
NHID-Clinical command-line interface
====================================
A thin dispatcher over functionality that already exists. It defines no policy,
computes no result, and holds no logic of its own — each subcommand calls the
same code the test suite exercises.

    nhid conformance            run the 18-case conformance suite
    nhid conformance --ci       ...and exit non-zero if any case fails
    nhid export-evidence --out DIR
                                assemble a reproducible evidence pack

The `--ci` flag exists so a vendor can gate their own pipeline on the controls
still behaving as specified after a change to their integration. A failing
build means a case that used to pass no longer does; it does not mean the
vendor is non-conformant with anything, and nothing here issues a pass/fail
judgement about a product.
"""
from __future__ import annotations

import argparse
import json
import sys


def _cmd_conformance(args: argparse.Namespace) -> int:
    from src.cts_runner import run_cts

    results = run_cts(yaml_path=args.suite, test_ids=args.test_id or None)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(
            f"Conformance: {results['passed']} passed, {results['failed']} failed, "
            f"{results['skipped']} skipped ({results['total']} cases)"
        )
        for case in results["results"]:
            if case["status"] == "fail":
                print(f"  FAIL {case['test_id']}: {case['detail']}")

    if args.ci and results["failed"]:
        print(
            f"\n{results['failed']} conformance case(s) failed. The controls no "
            f"longer behave as the suite specifies.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_audio_robustness(args: argparse.Namespace) -> int:
    """Run the phone-audio robustness measurement (src/phone_audio.py).

    Imported lazily: the module calls external speech engines, and this file is
    on the offline Tier 0 kit's guarded import path.
    """
    from pathlib import Path

    from src import phone_audio

    try:
        tts = phone_audio.make_synthesizer(args.tts, args.piper_model)
        asr = phone_audio.make_transcriber(args.asr, error_rate=args.stub_error_rate,
                                           seed=args.seed, whisper_model=args.whisper_model)
    except (RuntimeError, ValueError) as exc:
        print(f"nhid audio-robustness: {exc}", file=sys.stderr)
        return 2
    results = phone_audio.run(tts=tts, asr=asr, out_dir=Path(args.out), limit=args.limit,
                              noise=args.noise, seed=args.seed)
    print(phone_audio.render_report(results))
    print(f"Written to {args.out}/ (report.md, results.json)")
    return 0


def _cmd_export_evidence(args: argparse.Namespace) -> int:
    from scripts.export_evidence_pack import main as export_main

    argv = ["--out", args.out]
    if args.audit_db:
        argv += ["--audit-db", args.audit_db]
    if args.session_id:
        argv += ["--session-id", args.session_id]
    if args.audit_secret_key:
        argv += ["--audit-secret-key", args.audit_secret_key]
    if args.no_conformance:
        argv.append("--no-conformance")
    return export_main(argv)


def _cmd_pilot(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone
    from pathlib import Path

    from src.pilot_measure import (
        demo_records, dropped_record_count, load_jsonl, measure_records,
        print_summary, write_per_call_results,
    )
    from src.pilot_report import generate_report

    if args.demo:
        records = demo_records()
        source = "built-in demo records (synthetic, fictional)"
    elif args.jsonl:
        records = load_jsonl(args.jsonl)
        source = Path(args.jsonl).name
    else:
        print("nhid pilot: provide a capture JSONL file or --demo", file=sys.stderr)
        return 2

    if not records:
        print(f"nhid pilot: no usable records in {source}. Nothing was measured, so "
              f"no report was written — an empty pack would read as a clean result.",
              file=sys.stderr)
        return 1

    calls, summary = measure_records(records)
    if not calls:
        print("nhid pilot: no record carried a session_id, so no call could be "
              "assembled. Check the capture mapping against "
              "docs/pilot-kit/minimal-event-schema.json.", file=sys.stderr)
        return 1

    if args.share_safe:
        return _pilot_share_safe(args, records, calls, summary, source)

    now = datetime.now(timezone.utc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    report_md = generate_report(
        calls, summary,
        organization=args.organization,
        workflow=args.workflow,
        date_range=args.date_range,
        prepared_by=args.prepared_by,
        source_label=source,
        dropped_records=dropped_record_count(records),
        generated_at=now,
    )
    (out / "pilot_report.md").write_text(report_md, encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_per_call_results(calls, out / "per-call")

    print_summary(summary)
    print(f"\nEvidence pack written to {out}/")
    print(f"  pilot_report.md   the report, with every unmeasured field marked")
    print(f"  metrics.json      the same figures, machine-readable")
    print(f"  per-call/         one conformance result per call, no transcripts")

    _render_pilot_pdf(args, report_md, out / "pilot_report.pdf", now)
    return 0


def _render_pilot_pdf(args, report_md: str, target, now) -> bool:
    """Render the report PDF if reportlab is installed. False if it is not."""
    # The PDF is the artifact that circulates, but reportlab is an optional
    # extra. A missing extra must not cost the user the report they just
    # computed, so the markdown is already on disk before we try.
    try:
        from src.pilot_pdf import render_markdown_pdf
    except ImportError as exc:
        print(f"\n  pilot_report.pdf  NOT written — {exc.name or exc} is not installed.")
        print("  The report and metrics above are complete. For the PDF:")
        print("      pip install 'nhid-clinical[pdf]'")
        return False

    subtitle = " — ".join(p for p in (args.organization, args.workflow) if p)
    render_markdown_pdf(
        report_md, target,
        title="Tier 0 Shadow Pilot Report",
        subtitle=subtitle or "NHID-Clinical Tier 0 measurement",
        version="v1.3 Tier 0",
        footer_note="Measurements against this organization's own traffic — "
                    "not a conformance certification",
        author=args.prepared_by or "NHID-Clinical Tier 0 kit",
        cover_date=now.strftime("%B %Y"),
    )
    print(f"  pilot_report.pdf  the same report, for circulation")
    return True


def _pilot_share_safe(args, records, calls, summary, source) -> int:
    """Build the pack in staging, scan it, and release it only if it passes.

    See src/pilot_share_safe.py for what the scan does and does not catch.
    """
    import shutil
    import tempfile
    from datetime import datetime, timezone
    from pathlib import Path

    from src import pilot_share_safe as safe
    from src.pilot_measure import dropped_record_count, print_summary, write_per_call_results
    from src.pilot_report import generate_report

    out = Path(args.out)
    local = Path(str(out).rstrip("/\\") + ".local")
    if out.exists() and any(out.iterdir()):
        print(f"nhid pilot: {out} already exists and is not empty. A share-safe pack is "
              f"only released into an empty directory, so an older pack's files "
              f"cannot ride along unscanned.", file=sys.stderr)
        return 2

    try:
        key = safe.load_or_create_key(args.pseudonym_key_file, local)
    except (OSError, ValueError) as exc:
        print(f"nhid pilot: cannot use the pseudonym key: {exc}", file=sys.stderr)
        return 2
    safe.write_session_map(calls, key, local)
    shared_calls = safe.pseudonymise_calls(calls, key)

    now = datetime.now(timezone.utc)
    report_md = generate_report(
        shared_calls, summary,
        organization=args.organization,
        workflow=args.workflow,
        date_range=args.date_range,
        prepared_by=args.prepared_by,
        # The capture file's name is the payer's, and can say anything.
        source_label="capture file (name withheld in a share-safe pack)",
        dropped_records=dropped_record_count(records),
        generated_at=now,
    )
    report_md = report_md.replace(
        "\n\n", "\n\n**Share-safe pack:** call ids are pseudonymised and every "
        "text file was scanned before release; see `manifest.json`.\n\n", 1)

    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".nhid-pack-", dir=out.parent))
    try:
        (staging / "pilot_report.md").write_text(report_md, encoding="utf-8")
        (staging / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        write_per_call_results(shared_calls, staging / "per-call")
        safe.write_manifest(staging, kit_version=_kit_version(), calls=len(calls))

        findings = safe.scan_pack(staging, records)
        if findings:
            print("nhid pilot: the pack was NOT released. Its scan found:", file=sys.stderr)
            for finding in findings:
                print(f"  {finding}", file=sys.stderr)
            print("Nothing was written to the output directory. The matched text is "
                  "deliberately not shown.", file=sys.stderr)
            return 1

        print_summary(summary)
        if _render_pilot_pdf(args, report_md, staging / "pilot_report.pdf", now):
            # The manifest lists file hashes, so it is rewritten to include the PDF.
            safe.write_manifest(staging, kit_version=_kit_version(), calls=len(calls))

        if out.exists():
            out.rmdir()
        shutil.move(str(staging), str(out))
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    print(f"\nShare-safe pack released to {out}/ (scan passed; see manifest.json)")
    print(f"Kept locally, NOT part of the pack, do not send: {local}/")
    print(f"  session-map.csv   pseudonym -> your call ids")
    if not args.pseudonym_key_file:
        print(f"  pseudonym.key     reuse with --pseudonym-key-file for stable pseudonyms")
    return 0


def _kit_version() -> str:
    try:
        from importlib.metadata import version
        return version("nhid-clinical")
    except Exception:  # not installed from a distribution: running from a checkout
        return "checkout"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nhid",
        description=(
            "NHID-Clinical — policy and evidence tooling for healthcare "
            "administrative AI voice interactions."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    conf = sub.add_parser("conformance", help="run the conformance test suite")
    conf.add_argument("--ci", action="store_true", help="exit non-zero on any failure")
    conf.add_argument("--json", action="store_true", help="emit results as JSON")
    conf.add_argument("--suite", default=None, help="override the suite YAML path")
    conf.add_argument(
        "--test-id", action="append", default=None,
        help="run only this case (repeatable)",
    )
    conf.set_defaults(func=_cmd_conformance)

    exp = sub.add_parser("export-evidence", help="assemble an evidence pack")
    exp.add_argument("--out", required=True, help="output directory")
    exp.add_argument("--audit-db", default=None, help="path to the audit store")
    exp.add_argument("--session-id", default=None, help="session to export")
    exp.add_argument(
        "--audit-secret-key", default=None,
        help="hex HMAC key the audit events were signed with",
    )
    exp.add_argument("--no-conformance", action="store_true", help="skip the suite run")
    exp.set_defaults(func=_cmd_export_evidence)

    pilot = sub.add_parser(
        "pilot",
        help="measure a Tier 0 shadow pilot and write an evidence pack",
        description=(
            "Replay captured call turns through the policy engine and write the "
            "Tier 0 evidence pack: the report, a PDF of it, the metrics as JSON, "
            "and one result file per call. Runs entirely locally and transmits "
            "nothing."
        ),
    )
    pilot.add_argument(
        "jsonl", nargs="?",
        help="capture-schema JSONL file (one record per turn); see "
             "docs/pilot-kit/minimal-event-schema.json",
    )
    pilot.add_argument("--demo", action="store_true",
                       help="run against the built-in synthetic demo calls")
    pilot.add_argument("--out", default="pilot-evidence",
                       help="directory for the evidence pack (default: pilot-evidence/)")
    # Context the kit cannot observe. Anything omitted is marked unrecorded in
    # the report rather than guessed or defaulted to zero.
    pilot.add_argument("--organization", default=None, help="organization running the pilot")
    pilot.add_argument("--workflow", default=None,
                       help="workflow sampled, e.g. prior auth / claims status / billing")
    pilot.add_argument("--date-range", default=None,
                       help="date range of the sampled traffic")
    pilot.add_argument("--prepared-by", default=None, help="who prepared the report")
    pilot.add_argument(
        "--share-safe", action="store_true",
        help="write a pack meant to leave this machine: call ids pseudonymised, every "
             "text file scanned for transcript text and identifiers, released only if "
             "the scan passes; the pseudonym key and lookup table go to <out>.local/",
    )
    pilot.add_argument(
        "--pseudonym-key-file", default=None,
        help="with --share-safe: a 32-byte (or 64-hex) key, so pseudonyms stay stable "
             "across runs",
    )
    pilot.set_defaults(func=_cmd_pilot)

    audio = sub.add_parser(
        "audio-robustness",
        help="measure what a phone line and a transcriber do to detection (research)",
        description=(
            "Speak the voice-stress corpus with a TTS engine, pass it through a "
            "300-3400 Hz, 8 kHz, mu-law phone channel, transcribe it, and "
            "report detection on the transcripts next to detection on the authored "
            "text. A research measurement, not a headline rate. See "
            "docs/validation/phone-audio-robustness.md."
        ),
    )
    audio.add_argument("--tts", choices=["espeak", "piper", "stub"], default="espeak")
    audio.add_argument("--asr", choices=["faster-whisper", "stub", "identity"],
                       default="faster-whisper")
    audio.add_argument("--piper-model", default="", help="voice .onnx file for --tts piper")
    audio.add_argument("--whisper-model", default="small", help="faster-whisper model size")
    audio.add_argument("--noise", type=float, default=0.0,
                       help="white-noise standard deviation added on the line (0 = none)")
    audio.add_argument("--limit", type=int, default=None, help="first N scenarios only")
    audio.add_argument("--seed", type=int, default=0)
    audio.add_argument("--stub-error-rate", type=float, default=0.1,
                       help="word error rate for --asr stub (plumbing checks only)")
    audio.add_argument("--out", default="phone-audio-results")
    audio.set_defaults(func=_cmd_audio_robustness)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
