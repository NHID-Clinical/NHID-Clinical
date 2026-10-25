# Adversarial documents for the reading aid

These three files are **never indexed by the reading aid**: they live outside
`docs/`, and `eval/test_spec_rag.py` copies them into a temporary corpus for the
duration of one test. Each plants one threat from the roadmap's security model
and the test asserts what the aid does with it.

| File | Threat | What the test asserts |
| :-- | :-- | :-- |
| `injection.md` | instructions embedded in a document | every line the aid returns is a verbatim quotation of some corpus file; nothing in the document changes how a question is handled |
| `fake-certification.md` | a poisoned source asserting a certification | the aid **does** answer from it, and the citation names this file: a quotation carries the authority of its source and no more, so the only defense against a poisoned source is a trusted-source registry (Phase 3), not the retriever |
| `conflicting-pass-condition.md` | a near-duplicate of a specification table with one row changed | each quoted passage carries its own inline citation, so a conflict between two sources is attributable to a file rather than blended |

None of these statements is true of NHID-Clinical. They are test fixtures.
