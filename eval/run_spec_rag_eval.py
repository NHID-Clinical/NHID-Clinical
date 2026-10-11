"""
Score the specification RAG against eval/spec_rag_questions.jsonl.

Two numbers, both reported whatever they are:

  hit rate @ k=4   of the 20 answerable questions, how many retrieved their
                   expected source file anywhere in the top 4 chunks
  refusals         of the 5 unanswerable questions, how many returned exactly
                   the refusal string

Hit rate measures retrieval only — whether the right document came back. It
says nothing about whether the quoted passage is the *useful* part of that
document, which is a judgement no automated score here makes.

    python eval/run_spec_rag_eval.py            # table + totals
    python eval/run_spec_rag_eval.py --quiet    # totals only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.nhid_spec_rag import TOP_K, ask, load_index  # noqa: E402

QUESTIONS = REPO_ROOT / "eval" / "spec_rag_questions.jsonl"


def load_questions():
    rows = []
    for line in QUESTIONS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    index = load_index()
    rows = load_questions()
    answerable = [r for r in rows if r["answerable"]]
    refusals = [r for r in rows if not r["answerable"]]

    if not args.quiet:
        print(f"backend: {index.backend}   chunks: {index.chunk_count}   "
              f"sources: {index.source_count}   k={TOP_K}")
        if index.backend == "local":
            print("NOTE: local hashed embedding — this is NOT the "
                  "text-embedding-3-small score.")
        print()

    hits = 0
    misses = []
    for row in answerable:
        result = ask(index, row["question"])
        retrieved = [h["source"] for h in result.hits]
        ok = row["expected_source"] in retrieved
        hits += ok
        if not ok:
            misses.append((row["id"], row["expected_source"], retrieved))
        if not args.quiet:
            mark = "hit " if ok else "MISS"
            print(f"  {mark} {row['id']}  {row['question'][:58]:60} "
                  f"-> {retrieved[0] if retrieved else '(none)'}")

    if not args.quiet:
        print()

    refused = 0
    leaked = []
    for row in refusals:
        result = ask(index, row["question"])
        ok = result.refused
        refused += ok
        if not ok:
            leaked.append((row["id"], row["question"], result.citations))
        if not args.quiet:
            mark = "ok  " if ok else "ANSWERED"
            print(f"  {mark} {row['id']}  {row['question'][:58]:60} "
                  f"coverage={result.coverage}")

    print()
    print(f"hit rate @ k={TOP_K}: {hits}/{len(answerable)} "
          f"({100.0 * hits / len(answerable):.0f}%)")
    print(f"refusals:          {refused}/{len(refusals)} "
          f"({100.0 * refused / len(refusals):.0f}%)")

    if misses and not args.quiet:
        print("\nmisses:")
        for qid, expected, got in misses:
            print(f"  {qid}  expected {expected}")
            for g in got:
                print(f"        got {g}")
    if leaked and not args.quiet:
        print("\nanswered when it should have refused:")
        for qid, q, cites in leaked:
            print(f"  {qid}  {q}\n        cited {cites}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
