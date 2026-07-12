# Security Policy

## Scope and maturity

NHID-Clinical is an open governance framework and reference implementation. It is
**not a production-scale product**, and it is not an accredited standard,
certification, or regulatory requirement. Treat the code as a reference: review it
before relying on it, and do not deploy it against real protected health
information without your own security assessment.

## Reporting a vulnerability

If you find a security issue in this repository — in the policy engine,
conformance API, adapters, or any published reference code — please report it
privately so it can be addressed before public disclosure.

- **Email:** contact@nhid-clinical.org
- Include: the affected file or endpoint, a description of the issue, and steps to
  reproduce if you have them.
- Please do **not** open a public GitHub issue for security-sensitive reports.

We aim to acknowledge reports within a few business days. This is a
practitioner-led project, so response times are best-effort rather than
contractual.

## Coordinated disclosure

We ask that you give us a reasonable window to investigate and publish a fix
before disclosing publicly. We will credit reporters who wish to be named once a
fix is available.

## Handling of sensitive data

The reference implementation is designed to operate on call metadata and
machine-readable traces, not on raw PHI. If you are running a shadow pilot, keep
protected data inside your own environment — the
[Tier 0 Shadow Pilot Kit](docs/pilot-kit/README.md) is built to run on your own
logs without sending data anywhere.
