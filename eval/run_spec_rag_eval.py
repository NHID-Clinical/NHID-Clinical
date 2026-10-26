"""
Score the specification reading aid against eval/spec_rag_questions.jsonl.

Every number is reported whatever it is, with the backend, corpus hash and
commit it was measured on, because a score without those three is a rumour.

  file hit @ k=4       of the answerable questions, how many retrieved their
                       `expected_source` anywhere in the top 4 chunks
  accepted hit @ k=4   the same, counting any of `accepted_sources` (a corpus
                       that defines EIT-01 in four documents has four right
                       answers; `expected_source` stays what it was so the
                       historical figure remains comparable)
  passage hit          how many *answers* contain `expected_passage_contains`,
                       whitespace-collapsed, case-insensitive. This is the
                       first measure of whether the quoted text is the useful
                       part of the file, not merely from the right file. An
                       answerable question the aid refuses scores 0 here.
  MRR                  mean reciprocal rank of `expected_source` within the
                       top 4 (0 when absent)
  refusals             of the unanswerable questions, how many returned exactly
                       the refusal string
  unsupported answers  unanswerable questions that were answered: the number
                       that must stay at zero

Three checks over every answer the aid gives, answerable or not; each must be 0:

  misattributed quotes         a quoted line that does not appear, whitespace-
                               collapsed, in the file it cites (or a line with
                               no citation at all)
  withdrawn citations          a citation of a file the source registry
                               withdraws, excludes, or does not list
  unlabelled status citations  a quotation from a historical, superseded or
                               draft source without its label, or a current
                               source carrying one

    python eval/run_spec_rag_eval.py                    # table + totals
    python eval/run_spec_rag_eval.py --quiet            # totals only
    python eval/run_spec_rag_eval.py --json out.json    # machine-readable
    python eval/run_spec_rag_eval.py --check eval/baseline-local.json
                                                        # exit 1 on regression

The acceptance rule, from the roadmap and applied by --check: a retrieval gain
that reduces correct refusals or increases unsupported answers is a regression.
So is a drop in file, accepted or passage hits. Nothing here is optimised
alone.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.nhid_spec_rag import (  # noqa: E402
    QUOTED_STATUSES, REFUSAL, STATUS_LABELS, TOP_K, ask, load_index, source_status,
)

QUESTIONS = REPO_ROOT / "eval" / "spec_rag_questions.jsonl"

# The figures --check compares. Higher is better for the first five, lower for
# the last; a change in the dataset size invalidates the baseline outright.
HIGHER_IS_BETTER = ("file_hits", "accepted_hits", "passage_hits", "refusals")
LOWER_IS_BETTER = ("unsupported_answers", "misattributed_quotes",
                   "withdrawn_citations", "unlabelled_status_citations")

# One answer line: the quoted passage, two spaces, then [docs/x.md] or
# [docs/x.md · historical record].
_LINE_RE = re.compile(r"^(?P<passage>.*?)  \[(?P<source>docs/[^\]\s]+)(?: · (?P<label>[^\]]+))?\]$", re.S)


def load_questions():
    rows = []
    for line in QUESTIONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def attribution_problems(answer: str) -> dict:
    """Count the three attribution failures in one answer's text."""
    counts = {"misattributed_quotes": 0, "withdrawn_citations": 0,
              "unlabelled_status_citations": 0}
    for line in answer.split("\n\n"):
        m = _LINE_RE.match(line)
        if not m:
            counts["misattributed_quotes"] += 1
            continue
        source, label = m.group("source"), m.group("label")
        path = REPO_ROOT / source
        if not path.is_file() or _norm(m.group("passage")) not in _norm(
                path.read_text(encoding="utf-8", errors="replace")):
            counts["misattributed_quotes"] += 1
        status = source_status(source)
        if status not in QUOTED_STATUSES:
            counts["withdrawn_citations"] += 1
        if label != STATUS_LABELS.get(status):
            counts["unlabelled_status_citations"] += 1
    return counts


def evaluate(index, rows):
    answerable = [r for r in rows if r["answerable"]]
    refusals = [r for r in rows if not r["answerable"]]

    per_question = []
    attribution = {"misattributed_quotes": 0, "withdrawn_citations": 0,
                   "unlabelled_status_citations": 0}

    def tally(result):
        if result.refused:
            return {}
        found = attribution_problems(result.answer)
        for key, n in found.items():
            attribution[key] += n
        return {k: v for k, v in found.items() if v}

    file_hits = accepted_hits = passage_hits = 0
    rr_sum = 0.0
    for row in answerable:
        t0 = time.perf_counter()
        result = ask(index, row["question"])
        ms = (time.perf_counter() - t0) * 1000.0
        retrieved = [h["source"] for h in result.hits]
        accepted = set(row.get("accepted_sources") or []) | {row["expected_source"]}
        file_ok = row["expected_source"] in retrieved
        accepted_ok = bool(accepted & set(retrieved))
        rank = retrieved.index(row["expected_source"]) + 1 if file_ok else 0
        rr_sum += (1.0 / rank) if rank else 0.0
        needle = row.get("expected_passage_contains")
        passage_ok = bool(needle) and not result.refused and _norm(needle) in _norm(result.answer)
        problems = tally(result)
        file_hits += file_ok
        accepted_hits += accepted_ok
        passage_hits += passage_ok
        per_question.append({
            "id": row["id"], "category": row.get("category"), "answerable": True,
            "file_hit": file_ok, "accepted_hit": accepted_ok, "passage_hit": passage_ok,
            "refused": result.refused, "rank": rank, "coverage": result.coverage,
            "retrieved": retrieved, "cited": result.citations, "ms": round(ms, 1),
            **({"attribution": problems} if problems else {}),
        })

    refused = unsupported = 0
    for row in refusals:
        t0 = time.perf_counter()
        result = ask(index, row["question"])
        ms = (time.perf_counter() - t0) * 1000.0
        ok = result.refused and result.answer == REFUSAL
        problems = tally(result)
        refused += ok
        unsupported += (not ok)
        per_question.append({
            "id": row["id"], "category": row.get("category"), "answerable": False,
            "refused": ok, "coverage": result.coverage,
            "cited": result.citations, "ms": round(ms, 1),
            **({"attribution": problems} if problems else {}),
        })

    n_a, n_r = len(answerable), len(refusals)
    return {
        "backend": index.backend,
        "score_is_openai_score": index.backend == "openai",
        "chunks": index.chunk_count,
        "sources": index.source_count,
        "corpus_hash": index.corpus_hash,
        "commit": index.commit,
        "k": TOP_K,
        "answerable": n_a,
        "unanswerable": n_r,
        "file_hits": file_hits,
        "accepted_hits": accepted_hits,
        "passage_hits": passage_hits,
        "mrr": round(rr_sum / n_a, 4) if n_a else 0.0,
        "refusals": refused,
        "unsupported_answers": unsupported,
        **attribution,
        "per_question": per_question,
    }


def print_report(report, *, quiet: bool) -> None:
    if not quiet:
        print(f"backend: {report['backend']}   chunks: {report['chunks']}   "
              f"sources: {report['sources']}   k={report['k']}")
        print(f"corpus:  {report['corpus_hash'][:12]}   commit: {report['commit']}")
        if report["backend"] == "local":
            print("NOTE: local hashed embedding — this is NOT the "
                  "text-embedding-3-small score.")
        print()
        for q in report["per_question"]:
            if q["answerable"]:
                marks = ("file " if q["file_hit"] else "MISS ") + \
                        ("acc " if q["accepted_hit"] else "--- ") + \
                        ("pass" if q["passage_hit"] else ("REFUSED" if q["refused"] else "wrongpsg"))
                top = q["retrieved"][0] if q["retrieved"] else "(none)"
                print(f"  {q['id']}  {marks:22} -> {top}")
            else:
                mark = "ok      " if q["refused"] else "ANSWERED"
                print(f"  {q['id']}  {mark}  coverage={q['coverage']}  "
                      f"{'cited ' + ', '.join(q['cited']) if q['cited'] else ''}")
        print()

    a, r = report["answerable"], report["unanswerable"]
    print(f"file hit @ k={report['k']}:      {report['file_hits']}/{a}")
    print(f"accepted hit @ k={report['k']}:  {report['accepted_hits']}/{a}")
    print(f"passage hit:          {report['passage_hits']}/{a}")
    print(f"MRR:                  {report['mrr']}")
    print(f"refusals:             {report['refusals']}/{r}")
    print(f"unsupported answers:  {report['unsupported_answers']}/{r}")
    print(f"misattributed quotes:         {report['misattributed_quotes']}")
    print(f"withdrawn citations:          {report['withdrawn_citations']}")
    print(f"unlabelled status citations:  {report['unlabelled_status_citations']}")


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def check(report, baseline_path: Path) -> int:
    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    problems = []
    if base["backend"] != report["backend"]:
        problems.append(f"baseline is the {base['backend']} backend, this run is {report['backend']}; "
                        "the two are not comparable")
    for key in ("answerable", "unanswerable"):
        if base[key] != report[key]:
            problems.append(f"dataset changed ({key}: {base[key]} -> {report[key]}); "
                            "regenerate the baseline deliberately with --json")
    for key in HIGHER_IS_BETTER:
        if report[key] < base[key]:
            problems.append(f"{key} fell {base[key]} -> {report[key]}")
    for key in LOWER_IS_BETTER:
        # A metric the baseline predates was zero by definition then.
        if report[key] > base.get(key, 0):
            problems.append(f"{key} rose {base.get(key, 0)} -> {report[key]}")
    if problems:
        print("\nEVAL FAIL against", _display(baseline_path))
        for p in problems:
            print("  -", p)
        return 1
    better = [k for k in HIGHER_IS_BETTER if report[k] > base[k]] + \
             [k for k in LOWER_IS_BETTER if report[k] < base.get(k, 0)]
    tail = f"; improved: {', '.join(better)} (update the baseline to lock it in)" if better else ""
    print(f"\nEVAL PASS: no regression against {_display(baseline_path)}{tail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    parser.add_argument("--check", metavar="BASELINE", help="exit 1 on any regression against this baseline")
    args = parser.parse_args()

    index = load_index()
    report = evaluate(index, load_questions())
    print_report(report, quiet=args.quiet)

    if args.json:
        out = dict(report)
        out["measured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    if args.check:
        return check(report, Path(args.check))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
