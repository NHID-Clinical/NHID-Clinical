"""
How much does the share-safe scan catch? A planted-value measurement.

``nhid pilot --share-safe`` scans the evidence pack before it may leave the
payer's machine (``src/pilot_share_safe.scan_pack``). The kit README calls that
scan "a pattern-and-overlap check, not de-identification". This module puts
numbers on that sentence, using the method of OpenMed's synthetic HL7 v2 leakage
harness (plant known values with a truth manifest, run the scrubber, count what
gets through). No OpenMed code is used; the call-turn format here is our own.

Two questions, answered separately:

``probe_scanner``   *Would the scan stop it?* Each planted value is written, in
                    several realistic forms, into a staged pack file, and the
                    real ``scan_pack`` decides. A miss means: if this text ever
                    reached a pack file, the pack would still be released.
``pipeline_check``  *Does the real kit leak?* The real ``nhid pilot
                    --share-safe`` runs on the planted calls, and the released
                    pack is searched for every planted value in every form.

Everything is synthetic and seeded: the same seed gives the same calls, the
same manifest and the same figures. Standard library only, no network.

Run it::

    python -m src.share_safe_leakage --out share-safe-leakage/ [--calls 40] [--seed 7]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import platform
import random
import string
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

DEFAULT_SEED = 7
DEFAULT_CALLS = 40

_FIRST = ["Marisol", "Dorian", "Henrike", "Talib", "Oksana", "Benedetta", "Caspian", "Wilhelmina"]
_LAST = ["Quintero", "Vasquez-Hale", "Okonkwo", "Lindqvist", "Abernathy", "Petrakis", "Moreau", "Szabo"]
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


@dataclass(frozen=True)
class Planted:
    """One value placed into the synthetic input: the truth manifest's row."""
    session_id: str
    kind: str
    field: str
    value: str


# ── forms: how a planted value might reappear in a pack file ─────────────────

def _forms(kind: str, value: str) -> Dict[str, str]:
    """Realistic renderings of one planted value, keyed by form name."""
    if kind == "person name":
        return {"full name": value, "last name alone": value.split()[-1]}
    if kind in {"member id (letters and digits)", "claim number"}:
        return {"as captured": value, "lower case": value.lower()}
    if kind in {"member id (digits only)", "MRN", "NPI"}:
        return {"as captured": value}
    if kind == "SSN":
        return {"dashed": value, "no dashes": value.replace("-", ""),
                "spaced": value.replace("-", " ")}
    if kind == "date of birth":
        month, day, year = value.split("/")
        return {"as captured (MM/DD/YYYY)": value,
                "ISO (YYYY-MM-DD)": f"{year}-{month}-{day}",
                "spelled out": f"{_MONTHS[int(month) - 1]} {int(day)}, {year}"}
    if kind == "phone number":
        digits = "".join(c for c in value if c.isdigit())
        return {"as captured": value,
                "dotted": f"{digits[:3]}.{digits[3:6]}.{digits[6:]}",
                "digits only": digits}
    if kind == "email address":
        return {"as captured": value}
    if kind == "session id":
        return {"as captured": value}
    if kind == "transcript run":
        words = value.split()
        return {"6 consecutive words": " ".join(words[:6]),
                "5 consecutive words": " ".join(words[:5])}
    if kind == "identifier never in the input":
        return {"as written": value}
    raise ValueError(f"unknown kind {kind!r}")


def _luhn_npi(rng: random.Random) -> str:
    """A 10-digit number with a valid NPI check digit (prefix 80840, ISO 7812)."""
    body = "1" + "".join(rng.choice(string.digits) for _ in range(8))
    digits = [int(c) for c in "80840" + body]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return body + str((10 - total % 10) % 10)


def _mixed_id(rng: random.Random, prefix: str, length: int) -> str:
    pool = string.ascii_uppercase + string.digits
    while True:
        tail = "".join(rng.choice(pool) for _ in range(length))
        if any(c.isdigit() for c in tail):
            return prefix + tail


# ── generation ───────────────────────────────────────────────────────────────

def generate_calls(n: int = DEFAULT_CALLS, seed: int = DEFAULT_SEED
                   ) -> Tuple[List[dict], List[Planted]]:
    """``n`` synthetic calls in the minimal capture format, and their manifest.

    Each call is a caller-agent requesting eligibility from a payer
    representative, with fake identifiers spoken in the turns. Every value is
    generated, not drawn from real records.
    """
    rng = random.Random(seed)
    records: List[dict] = []
    manifest: List[Planted] = []
    for i in range(n):
        sid = f"cap-{rng.randrange(16**8):08x}-{i:03d}"
        name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
        member = _mixed_id(rng, "MBR", 7)
        member_digits = "".join(rng.choice(string.digits) for _ in range(9))
        claim = _mixed_id(rng, "CLM-", 8)
        mrn = "00" + "".join(rng.choice(string.digits) for _ in range(6))
        ssn = f"{rng.randint(100, 665)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
        dob = f"{rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/{rng.randint(1940, 2005)}"
        phone = f"({rng.randint(201, 989)}) 555-{rng.randint(100, 199):04d}"
        email = f"{name.split()[0].lower()}.{i}@example.org"
        npi = _luhn_npi(rng)
        speech = (f"I am an automated assistant calling for Harbor Point Clinic about "
                  f"eligibility for patient {name}")
        hour = 9 + i % 8
        ts = lambda s: f"2026-07-0{1 + i % 9}T{hour:02d}:{s // 60:02d}:{s % 60:02d}Z"  # noqa: E731
        turns = [
            {"speaker": "agent", "speech_text": speech,
             "disclosure_timestamp": ts(1),
             "identity_assertion_text": "I am an automated assistant calling for Harbor Point Clinic."},
            {"speaker": "receiver", "speech_text": "Go ahead with the member details."},
            {"speaker": "agent",
             "speech_text": (f"The member ID is {member}, alternate number {member_digits}, "
                             f"date of birth {dob}, SSN {ssn}, MRN {mrn}."),
             "phi_accessed": ["member_id", "date_of_birth"]},
            {"speaker": "agent",
             "speech_text": (f"The claim is {claim}. Rendering NPI {npi}. Call back at "
                             f"{phone} or {email}.")},
        ]
        for t, turn in enumerate(turns):
            records.append({"session_id": sid, "turn_index": t, "timestamp": ts(15 * t), **turn})
        manifest += [
            Planted(sid, "session id", "session_id", sid),
            Planted(sid, "person name", "speech_text", name),
            Planted(sid, "member id (letters and digits)", "speech_text", member),
            Planted(sid, "member id (digits only)", "speech_text", member_digits),
            Planted(sid, "claim number", "speech_text", claim),
            Planted(sid, "MRN", "speech_text", mrn),
            Planted(sid, "SSN", "speech_text", ssn),
            Planted(sid, "date of birth", "speech_text", dob),
            Planted(sid, "phone number", "speech_text", phone),
            Planted(sid, "email address", "speech_text", email),
            Planted(sid, "NPI", "speech_text", npi),
            Planted(sid, "transcript run", "speech_text", speech),
            Planted(sid, "identifier never in the input", "-", _mixed_id(rng, "ZX", 7)),
        ]
    return records, manifest


# ── question 1: would the scan stop it? ──────────────────────────────────────

def probe_scanner(records: Sequence[dict], manifest: Sequence[Planted]) -> List[dict]:
    """Caught / total for every kind and form, decided by the real ``scan_pack``."""
    from src.pilot_share_safe import scan_pack

    cells: Dict[Tuple[str, str], List[int]] = {}
    with tempfile.TemporaryDirectory(prefix="nhid-leak-probe-") as tmp:
        pack = Path(tmp)
        report = pack / "pilot_report.md"
        for planted in manifest:
            for form, text in _forms(planted.kind, planted.value).items():
                report.write_text(f"# Pilot report\n\nReviewer note: {text}\n", encoding="utf-8")
                caught = bool(scan_pack(pack, records))
                cell = cells.setdefault((planted.kind, form), [0, 0])
                cell[0] += caught
                cell[1] += 1
    return [{"kind": k, "form": f, "caught": c, "total": n}
            for (k, f), (c, n) in cells.items()]


# ── question 2: does the real kit leak? ──────────────────────────────────────

def _pack_text(out: Path) -> str:
    parts = [p.relative_to(out).as_posix() for p in out.rglob("*")]
    parts += [p.read_text(encoding="utf-8") for p in out.rglob("*")
              if p.is_file() and p.suffix in {".md", ".json"}]
    return "\n".join(parts)


def _run_pilot(jsonl: Path, out: Path, *extra: str) -> int:
    from src import cli

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return cli.main(["pilot", str(jsonl), "--share-safe", "--out", str(out), *extra])


def pipeline_check(records: Sequence[dict], manifest: Sequence[Planted]) -> dict:
    """Run the real share-safe flow and search the released pack for every value.

    A second run passes one planted name as ``--organization``: header fields
    are typed by the person running the kit and go into the report as written,
    and this records whether the scan stops that (it cannot recognise a name).
    """
    with tempfile.TemporaryDirectory(prefix="nhid-leak-pipeline-") as tmp:
        tmp = Path(tmp)
        jsonl = tmp / "calls.jsonl"
        jsonl.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

        out = tmp / "pack"
        exit_code = _run_pilot(jsonl, out)
        text = _pack_text(out) if out.exists() else ""
        leaks = sorted({f"{p.kind}: {form}" for p in manifest
                        for form, value in _forms(p.kind, p.value).items()
                        if p.kind != "transcript run" and value in text})
        overlap_leak = any(_forms("transcript run", p.value)["6 consecutive words"] in text
                           for p in manifest if p.kind == "transcript run")

        name = next(p.value for p in manifest if p.kind == "person name")
        header_out = tmp / "pack-header"
        header_exit = _run_pilot(jsonl, header_out, "--organization", name)
        header_text = _pack_text(header_out) if header_out.exists() else ""

    return {
        "released": exit_code == 0,
        "planted_values_searched": sum(len(_forms(p.kind, p.value)) for p in manifest),
        "leaks": leaks + (["transcript run: 6 consecutive words"] if overlap_leak else []),
        "name_typed_as_organization": {
            "released": header_exit == 0,
            "name_in_pack": bool(header_text) and name in header_text,
        },
    }


# ── the run ──────────────────────────────────────────────────────────────────

def run(n: int = DEFAULT_CALLS, seed: int = DEFAULT_SEED) -> dict:
    from src.cli import _kit_version

    records, manifest = generate_calls(n, seed)
    cells = probe_scanner(records, manifest)
    return {
        "measurement": "share-safe scan leakage (planted synthetic values)",
        "seed": seed,
        "calls": n,
        "turns": len(records),
        "planted_values": len(manifest),
        "probe": cells,
        "pipeline": pipeline_check(records, manifest),
        "versions": {"python": platform.python_version(), "nhid_kit": _kit_version()},
        "synthetic": "All values are generated. No real patient data is read or written.",
    }


def render_report(results: dict) -> str:
    rows = "\n".join(
        f"| {c['kind']} | {c['form']} | {c['caught']}/{c['total']} | "
        f"{'caught' if c['caught'] == c['total'] else 'MISSED' if c['caught'] == 0 else 'partly'} |"
        for c in results["probe"])
    pipe = results["pipeline"]
    header = pipe["name_typed_as_organization"]
    return f"""# Share-safe scan: planted-value measurement

Seed {results['seed']} · {results['calls']} synthetic calls · {results['turns']} turns ·
{results['planted_values']} planted values · Versions: python {results['versions']['python']},
kit {results['versions']['nhid_kit']}

{results['synthetic']}

## Would the scan stop it?

Each value was written into a staged `pilot_report.md` and judged by the real `scan_pack`.
Forms always caught: {sum(c['caught'] == c['total'] for c in results['probe'])} of
{len(results['probe'])}; planted renderings caught: {sum(c['caught'] for c in results['probe'])} of
{sum(c['total'] for c in results['probe'])}.

| Planted value | Form in the pack file | Caught | Verdict |
| :-- | :-- | :-- | :-- |
{rows}

## Does the real kit leak?

- Pack released: {'yes' if pipe['released'] else 'no'}
- Planted values searched for in the released pack (all forms): {pipe['planted_values_searched']}
- Found in the pack: {len(pipe['leaks'])}{''.join(chr(10) + '  - ' + leak for leak in pipe['leaks'])}
- A planted name typed as `--organization`: pack released {'yes' if header['released'] else 'no'},
  name in the pack {'yes' if header['name_in_pack'] else 'no'}
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.share_safe_leakage",
        description="Measure what the share-safe scan catches, with planted synthetic values.")
    parser.add_argument("--out", default="share-safe-leakage", help="output directory")
    parser.add_argument("--calls", type=int, default=DEFAULT_CALLS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    results = run(args.calls, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    report = render_report(results)
    (out / "report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
