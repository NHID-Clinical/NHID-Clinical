# NHID-Clinical — Registry Architecture

**Conceptual design for the public verification layer. Planned for v1.4+.**

---

## Purpose

The NHID-Clinical Registry is a proposed public record of AI voice systems that have achieved verified NHID-Clinical conformance. It serves three functions:

1. **Verification** — Payer procurement teams can confirm a vendor's claimed certification status
2. **Accountability** — Creates a durable record that certification existed at a point in time
3. **Adoption signal** — Provides a public indicator of ecosystem uptake

The registry is defined here as an architectural specification. A live implementation is planned for v1.4.

---

## Registry Record Schema

Each registry entry represents a single certified system at a specific version. A vendor with multiple products would have multiple entries.

```json
{
  "registry_id": "NHID-001",
  "organization": "Example Health AI, Inc.",
  "system_name": "ClaimBot v2.1",
  "system_version": "2.1.4",
  "certification_level": "L2",
  "nhid_version": "1.3",
  "certified_date": "2026-06-01",
  "expiry_date": null,
  "auditor": "self-attestation",
  "evidence_on_file": true,
  "status": "active",
  "contact": "compliance@examplehealthai.com",
  "notes": ""
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `registry_id` | string | yes | Sequential unique identifier assigned by NHID-Clinical maintainer |
| `organization` | string | yes | Legal name of the organization operating the system |
| `system_name` | string | yes | Product or system name as marketed/deployed |
| `system_version` | string | yes | Specific version evaluated for conformance |
| `certification_level` | enum | yes | `L1`, `L2`, or `L3` |
| `nhid_version` | string | yes | NHID-Clinical version the system was evaluated against |
| `certified_date` | ISO 8601 | yes | Date certification was established |
| `expiry_date` | ISO 8601 or null | yes | `null` for L1/L2 (no expiry); date for L3 (annual renewal) |
| `auditor` | string | yes | `"self-attestation"` for L1/L2; auditor name for L3 |
| `evidence_on_file` | boolean | yes | Whether evidence package is held on file |
| `status` | enum | yes | `active`, `expired`, `revoked`, `suspended` |
| `contact` | string | yes | Compliance or technical contact email |
| `notes` | string | no | Any relevant caveats or scope limitations |

---

## Registry Operations

### Registration

1. Organization completes CTS and achieves target certification level
2. Organization submits registration request to NHID-Clinical maintainer with:
   - Completed registry record fields
   - Evidence package (per certification tier requirements)
3. Maintainer reviews and assigns `registry_id`
4. Entry is published to public registry

### Updates

- **Version updates:** When a system is updated to a new version, a new registry entry is created. The prior entry is marked `status: expired` unless evidence supports continued conformance.
- **Certification level upgrades:** New entry created at higher tier; prior entry may remain active or be superseded.
- **Revocation:** If evidence of non-conformance is discovered, status is set to `revoked` with a timestamp and reason.

### Annual Renewal (L3 only)

L3 entries expire after 12 months. Renewal requires:
- Re-execution of CTS (or delta evaluation if system has not changed materially)
- Updated production evidence (Tier 1 + Tier 2 logs from preceding 90 days)
- Updated auditor attestation

---

## Registry Access Model

The registry is designed to be publicly readable and machine-queryable.

### Proposed Interface

| Interface | Format | Access |
|-----------|--------|--------|
| GitHub-hosted JSON file | `registry.json` | Public read |
| GitHub Pages rendered table | Markdown/HTML | Public read |
| REST API (v1.4+ stretch goal) | JSON | Public read, rate-limited |

### Lookup Use Case

A payer procurement team evaluating a vendor's claim of NHID-Clinical L2 conformance queries the registry:

```
GET /registry?org=Example+Health+AI&level=L2
```

Response confirms or denies active certification, the NHID version evaluated against, and the certification date.

---

## Trust Model

The registry is a **disclosure registry**, not a certification authority. It records what organizations have claimed and what evidence exists — it does not independently re-test systems.

| Level | Trust Basis |
|-------|-------------|
| L1 | Self-attestation on file; maintainer has not verified |
| L2 | Self-attestation + evidence package reviewed by maintainer |
| L3 | Third-party auditor attestation; maintainer has confirmed auditor identity |

Payers and procurement teams should treat registry entries as a starting point for due diligence, not a substitute for it.

---

## Implementation Timeline

| Milestone | Target |
|-----------|--------|
| Registry schema finalized (this document) | v1.3 — 2026 |
| Static JSON registry file on GitHub | v1.4 — Q1 2027 |
| GitHub Pages rendered registry table | v1.4 — Q1 2027 |
| First registry entries (L3 pilot certifications) | v1.4 — Q2 2027 |
| REST API (stretch goal) | v1.5+ |

---

## Interested in Early Registration?

If your organization is implementing NHID-Clinical and interested in being among the first registry entries, contact: [bnbaynard@gmail.com](mailto:bnbaynard@gmail.com)

Early registrants will receive a `registry_id` in the `NHID-00X` range and acknowledgement in the v1.4 release notes.

---

*NHID-Clinical · Author: Brianna Baynard · CC-BY 4.0 · v1.3 · 2026*
