# Contributing

NHID-Clinical is an open, voluntary reference: not a standard, a certification or a
product. Contributions that keep it honest are the most useful kind.

1. Fork the repository and branch from `main`.
2. Make the change. If it touches a published page, a count or a claim, read
   [`CLAUDE.md`](../CLAUDE.md) and [`docs/claim-boundaries.md`](../docs/claim-boundaries.md)
   first; the guards below enforce both.
3. Run the suite with the API up, which is how CI runs it:
   ```bash
   python -m uvicorn app:app --port 8000 &   # the integration tests need it
   python -m pytest tests/ -q                 # (1996 expected), 0 skipped
   ```
   Without the API the server-dependent integration tests skip themselves; CI
   requires zero skips.
4. Before pushing, run the complete verification: `make verify` (or `python
   scripts/verify_all.py`). It runs the suite against a live API plus the drift,
   control-set, fixture and integrity guards, and checks that published files
   under `specs/` are in the index. That last one matters: `.gitignore` ignores
   `*.pdf` repository-wide and the published PDFs are kept by `git add -f`, so a
   regenerated one can sit on disk, pass every local test, and be missing from a
   clean checkout.
5. Open a pull request. The template asks for the guards you ran and whether any
   public claim changed. For a large change, open an issue first.

Published counts move only through `scripts/bump_published_test_count.py`;
pinned baselines move only with a recorded decision in
`docs/MASTER-KNOWLEDGE-ARCHIVE.md`.

Questions and discussion: https://github.com/NHID-Clinical/NHID-Clinical/discussions
