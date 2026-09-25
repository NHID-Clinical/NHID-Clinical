# Contributing
1. Fork the repo
2. Make changes
3. Run tests: `python -m pytest tests/ -q` (1116 expected)
4. Before pushing, run the complete verification: `make verify` (or `python
   scripts/verify_all.py`). It runs the suite the way CI runs it — against a
   live API, so the 18 integration tests actually execute — plus the drift,
   control-set, fixture and integrity guards, and it checks that published
   files under `specs/` are in the index. That last one matters: `.gitignore`
   ignores `*.pdf` repository-wide and the published PDFs are kept by
   `git add -f`, so a regenerated one can sit on disk, pass every local test,
   and be missing from a clean checkout.
5. Open a PR — big changes: open an Issue first
Discussions: https://github.com/NHID-Clinical/NHID-Clinical/discussions
