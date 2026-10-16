# INSURE-Dial access request — draft for you to send

**Status:** drafted, NOT submitted · **Added:** 2026-10-14 · CC BY 4.0

> INSURE-Dial is the one real, high-fit public benchmark for what NHID-Clinical
> tests (see [`data-sources-inventory.md`](data-sources-inventory.md)). Its
> Hugging Face dataset is **gated** — access requires requesting it and agreeing
> to the dataset's data-sharing terms. **I did not submit this request, create
> an account, or agree to any terms.** That is yours to do, after you have read
> the dataset card's terms yourself.

## Before you send anything

1. Open the dataset card and **read its license and data-use terms in full**:
   <https://huggingface.co/datasets/dataframer/insure-dial>. The 50 real calls
   are de-identified but still sensitive; confirm the terms permit your intended
   research use before requesting.
2. Sign in with the Hugging Face account you want associated with the access
   grant (yours — not one I create).
3. Use the "Request access" / agreement form on that page. Paste the message
   below into any free-text field, or adapt it for an email if the authors
   prefer that.

## Draft message

> Subject: Access request — INSURE-Dial for voice-agent governance research
>
> Hello,
>
> I maintain NHID-Clinical (nhid-clinical.org), an open, voluntary research
> framework that evaluates *observable behaviour* of AI voice agents on
> provider-to-payer healthcare administrative calls — specifically whether an
> automated caller discloses it is AI, sequences protected-data exchange behind
> that disclosure, escalates to a human when asked, and leaves an audit trail.
> It is not a certification, a regulatory standard, or an identity verifier.
>
> I would like access to INSURE-Dial to measure how these controls perform on
> the benchmark's phase-annotated calls, mapping the dataset's agent-
> identification and compliance phases to the framework's disclosure and
> pre-data-exchange controls. Results would be reported as a research
> measurement on INSURE-Dial (third-party data), with denominators stated, and
> would not be presented as production accuracy or as evidence of any
> deployment.
>
> I will handle the data under the dataset's terms: use it only for the stated
> research, keep the real-call split access-controlled, publish no raw records,
> and cite the EACL 2026 paper. Happy to share more about the framework or the
> intended evaluation.
>
> Thank you for releasing this benchmark.
>
> [Your name]
> [Affiliation, if any]
> [Contact]

## After access is granted

- Download under the dataset's terms; keep the **real** split access-controlled
  and out of this repository.
- Any result you produce is **tier 5** evidence in
  [`evidence-provenance-matrix.md`](evidence-provenance-matrix.md): report it as
  "measured on the INSURE-Dial benchmark (third-party data)," with denominator
  and date, never as NHID's production accuracy.
- When you are ready, I can build a read-only adapter that maps INSURE-Dial's
  phase schema onto the corpus scenario shape so the existing engine can score
  it — that is code I will write only once you have the data and its terms in
  hand.

**Recorded non-actions:** I did not create a Hugging Face account, submit this
request, agree to any dataset terms, or download any data.
