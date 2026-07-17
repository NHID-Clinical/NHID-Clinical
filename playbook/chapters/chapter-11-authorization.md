# Chapter 11 — Authorization

*Part III: Implementation*

---

## The Contract That Ended Three Weeks Ago

Return to the most uncomfortable caller in this book — Chapter 3's
truthful, unauthorized agent. It disclosed perfectly: automated system,
named vendor, calling for a named practice. Every word true, except the
practice had terminated that vendor's contract three weeks earlier, and
one workflow's worth of agents never got the memo.

Now run the same call against an organization operating the framework's
cryptographic layer with production-hardened key custody and persistent
revocation — the deployment state this chapter's migration path describes,
not the in-process reference implementation on its own. At call setup,
alongside its spoken disclosure, the agent's runtime presents its **agent
passport**: a signed object asserting that the practice — identified by
its ten-digit NPI — delegated claims-inquiry authority to this vendor,
which sub-delegated it to this specific agent keypair, valid through a
stated window, bound to this call's SID. The payer's verifier checks the
signature chain against the practice's known public key and returns a
one-word answer.

Three weeks ago, that answer was *valid*. Today it is *revoked* — the
practice's offboarding checklist included one new line, "revoke vendor
delegations," and revocation is permanent by design and, in this
production configuration, propagates to verification immediately. The
call gates exactly as Chapter 10's Rung 3 prescribes:
no data, verified-callback offer, complete trace — and this time the
trace contains the *reason* in cryptographic form: a passport that
verified against a revoked delegation. The dispute that took Chapter 3's
compliance officer ninety days to not-resolve is now a log line.

Notice what changed and what didn't. The agent was equally truthful in
both worlds. The difference is that truth became *checkable* — and the
checking took milliseconds, not months.

---

## Executive Summary

NHID-Auth v2 is the framework's answer to Chapter 3's second and third
questions — representation and authorization — and it answers them with
five interlocking mechanisms, published as working reference code:

- **Ed25519 agent passports**: compact signed objects (32-byte keys,
  64-byte signatures) carrying a delegation plus the provider's signature
  and the agent's co-signature.
- **NPI anchoring**: every delegation names the granting provider's NPI
  as a required, format-validated field *inside the signed payload* — a
  delegation cannot omit or alter it without invalidating the signature.
- **Scoped, expiring delegation**: each delegation states what the agent
  may do (`claims_inquiry`, `eligibility_check`), with a TTL recommended
  at call-duration to hours scale.
- **Chains with monotonic narrowing**: up to three hops (provider →
  vendor → sub-vendor → agent), where each hop can only narrow scope,
  never expand it — enforced structurally, so a compromised middle hop
  cannot grant itself authority the provider never gave.
- **Per-call binding and permanent revocation**: delegations bind to the
  call-SID (replayed passports from other calls fail with a nonce
  mismatch), and revocation of an agent or delegation is irreversible.

Equally important is the division of labor the design draws. NHID-Auth
proves the *delegation* is authentic; it deliberately does not assert
that the NPI itself is legitimate and in good standing — that check
belongs to the payer's existing provider-enrollment system, the
authoritative source for it. And the layer coexists with, rather than
replaces, OAuth2/OIDC: bearer tokens authorize software clients to reach
APIs; passports authorize *this agent, on this call, for this provider,
in this scope*. A leaked API token plus a replayed passport still fails,
because OAuth was never designed to express per-call authority — which
is precisely the gap the call-SID nonce closes.

The chapter is equally explicit about maturity, because this layer is
where overclaiming would be easiest: the reference implementation is a
working trust *primitive*, not deployed trust *infrastructure*.
Revocation state is in-memory (a documented demo limitation); key
custody, per-tenant isolation, JWKS discovery, and registry-based
NPI-to-key resolution are laid out as a production migration path — each
step independently shippable — not shipped fact.

## Why It Matters

This is the layer that makes Chapter 3's "verification gets easier while
detection gets harder" claim good. Detection fights an adversary's
improving generator; verification checks a signature — a flat,
milliseconds-cheap operation whose reliability *rises* as the ecosystem
matures (more counterparties with known keys, better custody, eventually
registry discovery). The asymmetry is structural, and it is the entire
long-term case for authorization over detection.

It also matters for who carries the burden. Every mechanism in this
chapter runs at call setup, machine-to-machine, invisible to the humans
on the call. The practice signs delegations when it engages a vendor;
the vendor's runtime presents passports; the payer's verifier checks
them. Nobody's front office learns cryptography. Compare the
representative in Chapter 1, personally interrogating callers with folk
heuristics — the identity workload moves from the least-equipped point
in the system (a human, mid-call, in real time) to the best-equipped
(infrastructure, at setup, with keys).

And it matters commercially: delegation is the artifact that finally
gives Chapter 2's delegated adopter a paper trail. The billing vendor
deploying agents "under the provider's name" either holds a delegation
naming that NPI or it does not. The ambiguity that let adoption outrun
accountability — was this authorized? by whom? for what? — becomes a
signed, scoped, expiring, revocable object.

## The Trust Architecture, Walked Through

**Two keys, two questions.** Every flow involves exactly two kinds of key
material, and keeping their questions separate dissolves most confusion.
The *provider root key* answers: did the organization whose NPI is named
actually authorize this delegation? It is the trust anchor — everything
downstream derives from a signature chain rooted here. The *agent key*
answers: is the entity on this call actually the agent the delegation
names? Generated and held by whoever runs the agent runtime — almost
always the vendor — because the provider should never operate vendor
infrastructure, and the vendor never needs the provider's private key.
The provider signs a delegation *naming the vendor's agent public key*:
the cryptographic form of "I authorize the holder of this key, within
this scope, for this period." Compromise of either key never
compromises the other's signing capability — only the delegations
between them.

**The chain, and why three hops.** Real voice-AI supply chains are
layered — a clinic-facing SaaS product running on a white-labeled voice
platform is the normal case, not the exotic one. The chain permits
provider → vendor → sub-vendor → agent, and the safety property that
makes depth tolerable without a central registry is **monotonic scope
narrowing**: each hop may only restrict, never expand, what the next hop
can do — with violations rejected structurally (the reference
implementation's chain-narrowing and chain-length errors). A deployment
that wants a fourth hop is hearing an architectural signal — move to
registry-based trust discovery — not a parameter to raise.

**Binding and revocation, the two anti-replay walls.** A delegation
carries the call-SID it was issued for; presenting a valid passport from
a *different* call fails on nonce mismatch. TTLs bound exposure in time;
revocation bounds it in trust — permanent by design, checked
synchronously at verification (the production guidance treats
sub-second revocation visibility as a security SLA, not a
nice-to-have). Between them, short TTLs and permanent revocation also
keep the revocation list prunable: expired delegations fail on their
own, no list required.

**What verification hands back — and hands off.** A verified passport
returns the provider NPI it proved delegation from. The payer then asks
its *own* enrollment system whether that NPI is real, active, and
enrolled — deliberately outside NHID-Auth's claims. This seam (Chapter
3's implementation homework) is where the cryptographic layer plugs
into the healthcare identity infrastructure that already exists, rather
than duplicating it badly.

**Coexistence with OAuth2.** The integration pattern is two checks,
architecturally separate, neither substituting for the other: the OAuth
bearer token gets the vendor's backend through the API gateway (*may
this client talk to me at all?*); the passport authorizes the specific
call (*was this call delegated?*). A valid token with a missing or
invalid passport is still a non-conformant call. The common integration
error — treating "the client authenticated" as "the caller is
authorized" — is the exact conflation Chapter 3 diagnosed in the
industry at large, reappearing inside an integration diagram.

## From Reference to Production, Honestly

The migration path is documented as five independently shippable steps,
and their order is the risk order: persist revocation (durability fix,
no API change); move signing into KMS/HSM custody so private keys never
exist in plaintext outside the boundary, with rotation windows (30–90
days for agent keys, delegation-scale TTLs making key and delegation
rotation one event); isolate keys per provider-tenant on multi-tenant
platforms — one leaked shared key must not let an attacker impersonate
*every* provider a vendor serves; add JWKS-style discovery when a
provider outgrows bilateral static key exchange; and finally,
registry-backed NPI-to-key resolution — the only step requiring new
*shared* infrastructure and a neutral operator, and therefore explicitly
future work (Chapter 18's subject). Pilot-stage participants exchange
keys statically, with delegation objects shaped so that later migration
changes how keys are *fetched*, not what delegations *are*.

For payers, one production obligation deserves this chapter's emphasis
because it cannot be retrofitted: **retain the evidence, not the
verdict.** To resolve a disputed call months later you need the full
presented passport, the provider key (or the JWKS document *as it
existed at call time* — keys rotate), the verification result with the
scope checked, the call-SID match, and the behavioral audit bundle
beside it. Cryptographic proof of who was authorized and behavioral
proof of what they actually did are both required for most real
disputes — a stored `verified: true` boolean answers nothing. This is
Chapter 12's retention set, previewed here because the decision to keep
it is made at integration time.

## Real-World Examples

*(Composite illustrations built from the delegation mechanics described
above, not reported incidents.)*

**The offboarding line-item.** The opening scenario's quiet hero is a
checklist: the practice's vendor-termination procedure gained one step,
"revoke delegations." Authorization infrastructure is only as good as
the administrative moments that operate it — engagement (sign
delegation), termination (revoke), renewal (reissue). The example's
lesson for implementers: wire these three moments into existing
contract-lifecycle process, because no one will remember a separate
ceremony.

**The compromised middle.** A sub-vendor platform is breached. The
attacker holds a real, validly-delegated key — and can still only act
within the narrowest scope above it, only until TTL or revocation, only
on calls whose SIDs match issued delegations. The blast radius is a
scope, not an identity. Contrast the same breach in the
knowledge-based world of Chapter 3, where a breached billing platform's
identifiers still faced each payer's own authentication ritual, but
authorized whatever that ritual accepted — unscoped and unexpiring,
against every payer relying on the same knowledge-match check —
rather than a chain-narrowed, TTL-bound, revocable scope. Narrowing
chains don't prevent compromise; they price it.

**The two-tenant near-miss.** A vendor platform provisions one signing
key across all its provider tenants "for simplicity." Nothing goes
wrong — until a security review reads the multi-tenant guidance and
prices the counterfactual: that one key, leaked, would have let a
forger claim delegation from every provider the vendor serves. The fix
(per-tenant key aliases in KMS, mapping held in the control plane, away
from the call runtime) lands before the incident it would have
prevented. Included because the anti-pattern is the *default* thing a
hurried platform team builds, and the guidance exists because of it.

## Diagrams to Include

1. **Figure 11-1 — The chain, lit.** Chapter 3's Figure 3-4 (the
   delegation chain, unlit) redrawn with the signatures in place:
   provider signs scope to vendor, vendor narrows to sub-vendor,
   sub-vendor issues to agent keypair; NPI anchored at the root, TTL
   and call-SID at the leaf. The paired commission promised in Chapter
   3 — same layout, holes filled.
2. **Figure 11-2 — Two keys, two questions.** Provider root key and
   agent key with their respective questions, custody, and what each
   signs — the table from the trust architecture rendered as the
   figure integrators pin up.
3. **Figure 11-3 — Verification sequence at call setup.** Machine-to-
   machine lane diagram: passport presented → signature chain checked
   against known provider key → revocation checked → call-SID matched →
   NPI handed to enrollment system → verdict to policy engine. Elapsed
   time annotated as milliseconds; the humans' lane empty, on purpose.
4. **Figure 11-4 — OAuth and NHID-Auth, side by side.** The two-check
   pattern: token at the gateway, passport at the policy engine, with
   the failure matrix (token valid/passport invalid → non-conformant,
   etc.). The figure that prevents the conflation error.

## Operational Guidance

- **Providers: make delegation a contract-lifecycle event.** Sign at
  engagement, revoke at termination, reissue at renewal — as checklist
  items in the processes you already run. Your delegation hygiene is
  the ecosystem's trust anchor; nothing downstream can be stronger
  than it.
- **Payers: verify the passport, then interrogate your own directory.**
  Budget the enrollment-system integration (Chapter 3's homework) as
  part of adoption — the layer's design assumes it, and the NPI a
  passport proves delegation *from* is only as meaningful as your
  check that the NPI is real and in good standing.
- **Vendors: per-tenant keys from day one.** The shared-key shortcut is
  the layer's most dangerous default; the near-miss example is your
  design review. And treat the three-hop cap as a ceiling you
  architect below, not toward.
- **Everyone: stage it.** The behavioral baseline (Tiers 0–1) needs
  none of this chapter. Adopt cryptographic identity when the
  counterparty relationships justify key exchange — the ladder exists
  so that the strongest layer is never the price of entry.

## Implementation Guidance

1. **Run the reference flow end-to-end first.** The repository ships a
   worked issue-and-verify example and an identity test suite; an
   engineer can execute delegation issuance, passport presentation,
   verification, and revocation on a laptop in an afternoon. Do this
   before any architecture meeting — the object model (delegation,
   passport, verification result) is small, and holding it concretely
   collapses most design debate.
2. **Decide key custody before issuing anything real.** The reference
   generates keys in-process for demonstration; production keys belong
   in KMS/HSM custody with signing inside the boundary, separate roles
   for using versus managing keys, every signature logged as an
   ATR-01-grade auditable action, and rate caps as compromise
   tripwires. Custody decisions made after keys exist are migrations;
   made before, they are configuration.

## Key Takeaways

- NHID-Auth v2 answers representation and authorization with a signed,
  NPI-anchored, scoped, expiring, call-bound, revocable delegation —
  presented as an agent passport and verified in milliseconds at call
  setup, invisibly to the humans on the call.
- The chain's safety property is monotonic scope narrowing across at
  most three hops: a compromised hop can never expand its own
  authority. Compromise is priced, not merely hoped against.
- The layer proves delegation authenticity and deliberately defers NPI
  legitimacy to the payer's enrollment system, and it coexists with
  OAuth2 rather than replacing it — tokens admit clients to APIs;
  passports authorize calls. Neither check substitutes for the other.
- Verification's economics beat detection's: signature checking is
  flat-cost and gets more reliable as the ecosystem matures — the
  structural substantiation of Part I's central bet.
- The reference implementation is a primitive, not infrastructure:
  in-memory revocation, in-process keys, static key exchange. The
  production path (persist, custody, per-tenant isolation, JWKS,
  registry) is documented, staged, and honest — adopt accordingly, and
  retain the full evidence set from the first verified call.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Agent passport, Delegation, VerificationResult | Throughout | — (this chapter) |
| NPI anchoring (format-validated, signature-covered) | Executive summary; walked through | Chapters 3, 13 |
| Monotonic narrowing, 3-hop cap, chain errors | The chain | — (this chapter) |
| Call-SID nonce, replay failure | Binding and revocation | Chapters 8, 12 |
| Revocation as security SLA | Binding and revocation | Chapter 16 |
| KMS/HSM custody, rotation windows, per-tenant keys | Production path | Chapter 16 |
| JWKS / registry discovery (future) | Production path | Chapter 18 |
| OAuth2 coexistence, two-check pattern | Trust architecture | Chapter 13 |
| Dispute retention set | Production obligation | Chapter 12 |
| Bot-to-bot mutual verification (open gap) | — deferred | Chapters 18, 20 |

---

*Next — Chapter 12, Audit Trails: the evidence layer — per-turn traces,
FHIR AuditEvent bundles, and the retention discipline that turns
ninety-day disputes into log lines.*
