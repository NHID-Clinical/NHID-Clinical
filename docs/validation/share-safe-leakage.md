# Share-safe scan: what it catches, measured with planted values

**Status:** research measurement, synthetic data only · **Added:** 2026-11-05 · CC BY 4.0

`nhid pilot --share-safe` scans the evidence pack before it may leave the payer's machine
([`src/pilot_share_safe.py`](../../src/pilot_share_safe.py)). The kit README calls the
scan "a pattern-and-overlap check, not de-identification". This note puts numbers on that
sentence. The scan is unchanged: this only measures it.

The method follows OpenMed's synthetic HL7 v2 leakage harness: plant known values with a
truth manifest, run the scrubber, count what gets through. OpenMed is Apache-2.0; no
OpenMed code is used, and the call-turn format here is our own.

## Run it

```bash
python -m src.share_safe_leakage --out share-safe-leakage/      # --calls 40 --seed 7
```

It writes `report.md` and `results.json` (seed, counts, Python and kit versions). The same
seed gives the same figures. Standard library only, no network, no real data.

## Two questions, kept apart

1. **Does the real kit leak?** The real `nhid pilot --share-safe` runs on 40 synthetic
   calls (160 turns, 520 planted values), and the released pack is searched for every
   value in every form (920 strings).
   - **Found in the pack: 0.** The pack holds aggregates, verdicts and pseudonyms, so
     nothing from the turns reaches it.
   - **The exception is a header field.** A name typed as `--organization` goes into the
     report as written, and the pack is still released. The scan cannot recognise a name.
2. **Would the scan stop it, if it got there?** Each planted value is written, in several
   realistic forms, into a staged `pilot_report.md`, and the real `scan_pack` decides.
   This is the safety net for a future change that puts more text into the pack.

## Results (seed 7, 40 calls)

| Planted value | Form in the pack file | Caught |
| :-- | :-- | :-- |
| session id | as captured | 40/40 |
| member id (letters and digits) | as captured | 40/40 |
| member id (letters and digits) | lower case | **0/40** |
| member id (digits only) | as captured | **0/40** |
| claim number | as captured | 40/40 |
| claim number | lower case | **0/40** |
| MRN (digits only) | as captured | **0/40** |
| NPI | as captured | **0/40** |
| SSN | dashed | 40/40 |
| SSN | no dashes, or spaced | **0/40** |
| date of birth | MM/DD/YYYY | 40/40 |
| date of birth | ISO (YYYY-MM-DD), or spelled out | **0/40** |
| phone number | as captured, or dotted | 40/40 |
| phone number | digits only | **0/40** |
| email address | as captured | 40/40 |
| person name | full name, or last name alone | **0/40** |
| transcript | 6 consecutive words | 40/40 |
| transcript | 5 consecutive words | **0/40** |
| identifier never in the input | as written | **0/40** |

Nine of the 23 forms are always caught; the other 14 never are. The results are
all-or-nothing because each form either matches a rule or does not.

## What the misses mean

- **None of them is a leak today.** The real pack contained none of the 920 strings.
- **They are the limits of the safety net**, and they follow from the rules:
  - identifiers from the input are matched exactly and case-sensitively, and only when they
    mix letters and digits, so all-digit numbers (MRNs, NPIs, digit-only member ids) and
    re-cased ids pass;
  - the patterns cover one format each (dashed SSN, slash date, separated phone);
  - names are never recognised.
- **Header fields** (`--organization`, `--workflow`, `--date-range`, `--prepared-by`) are the
  one route by which free text reaches the pack today. The README already says they "go
  into the report as written"; the privacy officer's review is the control for them.

Widening the rules would change which packs are refused, so it is left as a separate
decision. [`tests/test_share_safe_leakage.py`](../../tests/test_share_safe_leakage.py) pins
every row above, so a change to the scan shows up as a changed test.
