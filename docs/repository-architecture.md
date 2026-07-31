# Repository architecture

Recommended GitHub organization structure for NHID-Clinical, separating the open
framework from the commercial platform layer.

## Principle

**Do not merge open and commercial repositories.**

The open framework is the source of legitimacy for this work. Its credibility depends on
being independently implementable, auditable, and forkable by people who have no commercial
relationship with us — including competitors and regulators. Mixing commercial code into the
same tree makes that claim unverifiable, and makes it impossible to tell what a third party
is actually free to use.

## Open repositories

Published under CC BY 4.0. Public, forkable, no commercial dependency.

| Repository | Contents |
|---|---|
| `nhid-specification` | The normative v1.3 specification, control definitions, event schema, and versioned specification history |
| `nhid-conformance-suite` | Machine-readable test definitions (YAML) and the runner that executes them against any implementation |
| `nhid-reference-implementation` | The Python policy engine, TypeScript middleware, VAPI/Twilio adapters, and PowerShell module |
| `nhid-simulator` | The open simulator that demonstrates the controls (currently `NHID-Clinical/Simulator`) |
| `nhid-auth` | NHID-Auth v2 — Ed25519 agent passports, provider-signed delegation, offline verification |
| `nhid-sdk-python` | Python client SDK |
| `nhid-sdk-js` | JavaScript/TypeScript client SDK |

## Commercial repositories

Private. TrustLayer platform code. Consumes the open repositories as dependencies; the
open repositories never depend on these.

| Repository | Contents |
|---|---|
| `nhid-trustlayer` | The TrustLayer platform — agent registry, trust gateway, evidence center, continuous conformance monitoring |
| `nhid-enterprise-connectors` | SSO, SIEM, ticketing, and GRC integrations |
| `nhid-cloud` | Hosting, tenancy, and operational infrastructure |

## Dependency direction

```
nhid-specification
        ↑
nhid-reference-implementation ← nhid-conformance-suite
        ↑                              ↑
   nhid-auth                     nhid-simulator
        ↑
   nhid-sdk-*
        ↑
  ─────────────────────────────────────────  (open / commercial boundary)
        ↑
   nhid-trustlayer ← nhid-enterprise-connectors
        ↑
    nhid-cloud
```

Dependencies point upward only. No open repository may depend on a commercial one. If
TrustLayer were discontinued tomorrow, every open repository would continue to build, test,
and function unchanged.

## Current state

Today the framework, the website, and the reference implementation all live in a single
repository (`NHID-Clinical/NHID-Clinical`), with the simulator in `NHID-Clinical/Simulator`
and platform work in `NHID-Clinical/NHID-Clinical-SaaS`.

The repositories above have **not** been created yet. Creating them requires permissions the
automation running this change does not hold — the GitHub App installation token cannot
create repositories (`403 Resource not accessible by integration`), and `NHID-Clinical` is a
user account rather than an organization, so there is no org-level repo creation path either.

Creating them is a manual step: either from the GitHub UI while signed in as the account
owner, or with a personal access token carrying the `repo` scope. Until then this document is
the record of intent. `NHID-Clinical/NHID-Clinical` remains the live source of both the
website (GitHub Pages → nhid-clinical.org) and the framework.

## Migration sequence

Splitting a repository with an active Pages deploy, live CI gates, and a substantial merged
history is a project in its own right — it should not be attempted alongside unrelated work.
When it happens, this order minimizes breakage:

1. **`nhid-specification`** — lowest coupling. Move the specification documents and schema;
   leave a pointer in the monorepo.
2. **`nhid-conformance-suite`** — move the YAML definitions and runner. The reference
   implementation consumes it as a dependency rather than a sibling directory.
3. **`nhid-auth`** — self-contained cryptographic layer.
4. **`nhid-reference-implementation`** — the engine, middleware, and adapters. Largest move;
   requires CI to be rebuilt against the extracted dependencies.
5. **`nhid-sdk-python` / `nhid-sdk-js`** — extract client code once the engine has moved.
6. **`nhid-simulator`** — rename the existing `Simulator` repository. Update the redirect at
   `/simulator.html` and the canonical URL in the same change.
7. **Website stays put.** `NHID-Clinical/NHID-Clinical` becomes the website plus the org's
   front door, with the Pages workflow untouched throughout.

Each step should land independently, with the site's links verified before the next begins.

## Constraints

- The specification, conformance suite, and reference implementation must never require a
  commercial account, key, or agreement to obtain, build, or run.
- Commercial repositories may consume open repositories at pinned versions; they may not
  fork them privately and diverge, because that would produce two different control
  definitions with the same name.
- Any control-logic change lands in the open repository first.
