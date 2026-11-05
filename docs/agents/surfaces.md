# Every change reaches every surface

When the code, the data or the stage changes, everything a reader sees must say
so in the same pull request: the website pages, the PDFs, the README, the docs,
the launch drafts and the generated fixtures. The site deploys from `main`
(`.github/workflows/pages.yml` → `scripts/build_pages_site.sh`), so a stale page
goes live the moment the PR merges.

## The loop, every PR

1. **Change the thing.**
2. **Facts.** If a reader should hear about it, add or edit a fact in
   [`surfaces.json`](surfaces.json): the sentence, every surface that must
   state it, and any phrase that must no longer appear. Then update those
   surfaces until `python scripts/check_surfaces.py` passes.
3. **Generated output.** Rebuild whatever the change feeds, using the commands
   in the `generated` list of `surfaces.json`:
   - gateway, walkthrough, API-sample and evidence fixtures;
   - the PDFs (`python scripts/generate_pdfs.py`);
   - the README's Trust Gateway still;
   - the published test count.
4. **Run the checks** (all in the suite, or in `scripts/verify_all.py`):

| Check | Catches |
| :-- | :-- |
| `tests/test_surfaces.py` (`scripts/check_surfaces.py`) | A public fact missing from a surface that must state it, or a retired phrase still present |
| `tests/test_call_direction.py` | Any agent line, page, doc or launch draft where the call runs backwards (the agent answering, or asking the payer for the patient's own identifiers) |
| `tests/test_pdf_freshness.py` | A PDF source edited without rebuilding the PDFs |
| `scripts/check_number_drift.py` | A published number that disagrees with its source |
| the generators' `--check` modes | A fixture or generated page that no longer matches the engine |
| `scripts/check_control_set.py` | A surface that misstates the five controls |

Wording on every surface follows [`docs/claim-boundaries.md`](../claim-boundaries.md)
for the current stage.

## What is not automatic

- **The Trust Gateway screenshot** (`assets/images/trust-gateway.png`) is
  recaptured by hand with `scripts/visual/capture_trust_gateway.cjs` after the
  gateway fixture changes. CI has no browser step.
- **New surfaces.** A new page or document is only checked once it is listed in
  `surfaces.json` (for facts) or matched by `tests/test_call_direction.py` (for
  direction). Add it when you create it.
