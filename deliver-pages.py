#!/usr/bin/env python3
"""
Delivers: conftest.py, README.md, technical-stack.html, regulatory-alignment.html
Patches:  specification.html, developers.html, roadmap.html, for-payers.html
Commits and pushes to main.
Run from inside C:\Users\bnbay\NHID-Clinical
"""
import os, sys, subprocess

def run(cmd):
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print(f"ERROR: {cmd}"); sys.exit(r.returncode)

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(text)
    print(f"  wrote {path}")

def patch(path, old, new):
    with open(path, "r", encoding="utf-8") as f: text = f.read()
    if old not in text: print(f"  skip (already applied): {path}"); return
    with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(text.replace(old, new, 1))
    print(f"  patched {path}")

if not os.path.isfile("specification.html"):
    print("ERROR: run from inside the NHID-Clinical repo directory."); sys.exit(1)

run('git config user.email "bnbaynard@gmail.com"')
run('git config user.name "Brianna"')

# ── conftest.py ───────────────────────────────────────────────────────────────
write("conftest.py", "import sys, os\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n")

# ── README.md ─────────────────────────────────────────────────────────────────
write("README.md", r"""<div align="center">

<img src="https://nhid-clinical.org/assets/brand-icon.png" alt="NHID-Clinical" width="80"/>

# NHID-Clinical

**The open framework for AI voice agent identity disclosure in B2B healthcare**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Tests](https://img.shields.io/badge/tests-173%20passed-brightgreen)](https://github.com/NHID-Clinical/NHID-Clinical/actions)
[![Version](https://img.shields.io/badge/version-1.3%20open%20core-blue)](https://nhid-clinical.org/specification.html)
[![NIST](https://img.shields.io/badge/NIST-2025--0035--0026-lightgrey)](https://www.regulations.gov/comment/NIST-2025-0035-0026)
[![Status](https://img.shields.io/badge/status-Open%20Proposal-yellow)](https://nhid-clinical.org)
[![Website](https://img.shields.io/badge/website-nhid--clinical.org-0052cc)](https://nhid-clinical.org)

**[Website](https://nhid-clinical.org)** · **[Specification](https://nhid-clinical.org/specification.html)** · **[Technical Stack](https://nhid-clinical.org/technical-stack.html)** · **[Regulatory Alignment](https://nhid-clinical.org/regulatory-alignment.html)** · **[For Payers](https://nhid-clinical.org/for-payers.html)**

</div>

---

## The Problem: Impersonation Latency

An AI calls as *"Sarah from Dr. Smith's office."* It handles several minutes of normal workflow conversation. Only when challenged does it admit it is automated. By then, sensitive operational data has already been exchanged without clear consent or accountability.

**Impersonation latency** (NIST docket NIST-2025-0035-0026): the measurable gap between an AI agent initiating a healthcare voice call and the receiving system knowing it is not talking to a human.

> This is not a regulation, certification program, or compliance requirement. It is an open governance proposal for voluntary adoption.

---

## The Four Controls (v1.3)

| ID | Control | Requirement |
|----|---------|-------------|
| **IDG-01** | Identity Disclosure Gate | AI **MUST** identify as automated before any operational data exchange |
| **DBC-01** | Deceptive Behavior Check | AI **MUST NOT** use fake breathing, typing sounds, or scripted hesitation |
| **EIT-01** | Escalation and Immediate Transfer | AI **MUST** provide immediate human handoff when requested |
| **ATR-01** | Audit Trail Requirements | AI **MUST** log disclosure timestamp vs. first data request timestamp |

---

## Quickstart

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
pytest tests/ -q
Expected: 173 passed, 18 skipped

The 18 skipped tests are integration tests requiring a live FastAPI server.

The Five-Layer Trust Stack
Layer	Standard	Role
0	NPI Gap	The problem — no existing diagram addresses cross-org NPI authorization
1	STIR/SHAKEN (RFC 8224)	Carrier number authentication — A/B/C attestation
2	NHID-Clinical v1.3	Behavioral disclosure baseline — 4 controls, 5 CTS tests
3	NHID-Auth v2 (Ed25519 + DPoP)	Delegation chain + call-nonce binding (v2 roadmap)
4	FHIR AuditEvent R4 / IHE BALP	Healthcare-native audit logging
5	OpenTelemetry spans	SIEM / enterprise observability export
Full technical architecture →

Repository Structure
src/
  voice_policy.py                # Core disclosure + escalation policy engine
  agent_identity.py              # NHID-Auth delegation chain + NPI binding
  nhid_policy_engine_v1.py       # Five CTS rule implementations
  nhid_cas.py                    # NHID-CAS: Call Authorization Score
  npi_registry_validator.py      # NPI format validation + NPPES registry check
tests/
  test_voice_policy.py           # Policy engine (35 tests)
  test_identity.py               # Delegation chain (21 tests)
  test_nhid_cas.py               # CAS scoring engine (38 tests)
  test_npi_registry.py           # NPI validator (17 tests)
  test_version_boundary.py       # v1.3/v2 boundary guards (9 tests)
  test_alignment_pages.py        # Governance page coverage (14 tests)
  failure_injection_harness.py   # Chaos + adversarial tests (18 integration)
conformance/
  nhid_conformance_test_suite_v1.yaml
alignment/
  stir-shaken.html / cms-0057-f.html / nist-ai-agent-standards.html / vendor-evidence-pack.html
Built With
Show Image
Show Image
Show Image
Show Image
Show Image

Regulatory Alignment
Regulatory Driver	Specific Requirement	NHID-Clinical Control
CMS-0057-F	FHIR API, 72hr turnaround, 5yr retention	FHIR AuditEvent + ATR-01
MACPAC May 2026	AI transparency, human review	EIT-01 + ATR-01
DOJ FCA 2026	Explainability + audit trail	LOG + CTS evidence
State AI Laws (CA/TX/MD/NE)	Inspectable, auditable AI decisions	IDG-01 + DBC-01
NIST CAISI 2026	Cross-org agent identity	NHID-Auth v2
Full regulatory alignment matrix →

NIST Submission
Submitted to NIST docket NIST-2025-0035 · Comment ID: NIST-2025-0035-0026

v2 Roadmap
v1.3 closes the disclosure gap. v2 closes the authorization gap — Ed25519 delegation chains, scope attenuation, revocation, call-bound nonces. Targeting Q3 2026.

Full roadmap →

Contributing
Community · Discord · contact@nhid-clinical.org

<div align="center">CC BY 4.0 · Brianna Baynard · <a href="https://nhid-clinical.org">nhid-clinical.org</a></div> """)
── Shared HTML fragments ─────────────────────────────────────────────────────
_DISCLAIMER = '<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px 20px;font-size:.88rem;line-height:1.6"><strong>Note:</strong> NHID-Clinical is an early-stage open proposal by Brianna Baynard. It is not an accredited standard or regulatory requirement.</div>'
_NAV_LINKS = '<a href="/">Home</a><a href="/about.html">About</a><span class="nav-sep"></span><a href="/script-examples.html">Examples</a><span class="nav-sep"></span><a href="/for-payers.html">For Payers</a><span class="nav-sep"></span><a href="/specification.html">Spec</a><a href="/developers.html">Developers</a><a href="/interoperability.html">Interoperability</a><span class="nav-sep"></span><a href="/news.html">News</a><a href="/community.html">Community</a><a href="/faq.html">FAQ</a>'
_FOOTER = '<footer id="contact" class="site-footer"><div class="container footer-inner"><p>© 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0</p><div><a href="mailto:contact@nhid-clinical.org">Contact</a><a href="https://nhid-clinical.org">nhid-clinical.org</a><a href="https://twitter.com/NHIDClinical">@NHIDClinical</a><a href="https://discord.gg/eP8FxXkGU6">Discord</a><a href="https://reddit.com/r/NonHumanAuth">Reddit</a></div><p class="footer-copy">© 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0 | contact@nhid-clinical.org</p></div></footer>'

def page(title, desc, crumbs, eyebrow, h1, lede, body, cta_h, cta_p, cta_label, cta_href):
return f"""<!DOCTYPE html>

<html lang="en"> <head> <meta charset="utf-8"/> <meta name="viewport" content="width=device-width, initial-scale=1"/> <meta name="description" content="{desc}"/> <title>{title}</title> <link rel="icon" href="/assets/brand-icon.png" type="image/png"/> <link rel="preconnect" href="https://fonts.googleapis.com"/> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/> <link href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700;800&display=swap" rel="stylesheet"/> <link rel="stylesheet" href="/nhid-clinical-ui.css"/> <script>try{{document.documentElement.setAttribute('data-theme',localStorage.getItem('nhid-theme')||'light')}}catch(e){{}}</script> </head> <body> {_DISCLAIMER} <header class="site-header"> <nav class="container nav" aria-label="Primary navigation"> <a class="brand" href="/" aria-label="NHID-Clinical home"> <span class="brand-mark" aria-hidden="true"><img src="/assets/brand-icon.png" alt="NHID-Clinical"/></span> <span><strong>NHID-Clinical</strong><small>Building Trust in Healthcare Voice AI</small></span> </a> <div class="nav-links">{_NAV_LINKS}</div> <div class="nav-actions"> <button class="icon-button search-toggle" type="button" aria-label="Search" id="search-toggle"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg></button> <button class="icon-button theme-toggle" type="button" aria-label="Toggle dark mode" id="theme-toggle"><svg class="sun-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg><svg class="moon-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></button> <a class="primary-pill" href="/community.html">Get Involved</a> <button class="icon-button menu-button" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-nav"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button> </div> </nav> <div class="search-overlay" id="search-overlay" hidden> <div class="container search-overlay-inner"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="flex-shrink:0;color:var(--body)"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg><input type="search" id="search-input" class="search-input" placeholder="Search NHID-Clinical…" autocomplete="off" aria-label="Search site"/><button class="icon-button search-close" id="search-close" type="button" aria-label="Close search"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div> <div class="container"><div class="search-results" id="search-results" role="listbox" aria-label="Search results"></div></div> </div> </header> <nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation"> <a href="/">Home</a><a href="/about.html">About</a><a href="/script-examples.html">Examples</a><a href="/for-payers.html">For Payers</a><a href="/specification.html">Spec</a><a href="/developers.html">Developers</a><a href="/interoperability.html">Interoperability</a><a href="/news.html">News</a><a href="/community.html">Community</a><a href="/faq.html">FAQ</a> <div class="mobile-nav-footer"><button class="theme-toggle mobile-theme-toggle" type="button" aria-label="Toggle dark mode"><svg class="sun-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2"/></svg><svg class="moon-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><span class="mobile-theme-label">Switch to dark mode</span></button></div> </nav> <div class="nav-backdrop" id="nav-backdrop"></div> <main> <section class="inner-hero"><div class="container inner-hero-grid"><div> <div class="crumbs">{crumbs}</div> <p class="eyebrow">{eyebrow}</p> <h1>{h1}</h1> <p class="lede">{lede}</p> </div></div></section> <section class="page-section"><div class="container" style="max-width:52rem"> {body} </div></section> <section class="container closing-section"><div class="closing-panel"><div> <p class="section-kicker">{cta_h}</p> <h2>{cta_p}</h2> </div><a class="closing-button" href="{cta_href}">{cta_label}</a></div></section> </main> {_FOOTER} <script src="/site.js"></script> </body> </html>"""
── technical-stack.html body ─────────────────────────────────────────────────
TS_BODY = """

<div class="hero-notice" role="note" style="margin-bottom:2.5rem"><strong>Pre-standardization draft.</strong> Each layer references an existing open standard (RFC / IETF / HL7 / CNCF). NHID-Clinical is the governance spec that connects them for B2B healthcare voice.</div> <h2 style="margin-bottom:1rem">Why STIR/SHAKEN Is Not Enough</h2> <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">STIR/SHAKEN (ATIS-1000074 / RFC 8224) authenticates the originating phone number with A/B/C attestation. It is essential infrastructure. But a STIR/SHAKEN A-attestation only tells you the number was not spoofed. It tells you nothing about whether the caller is human or AI, whether the AI is authorized to represent the provider it claims, whether any NPI cited is bound to that organization, or whether there is any audit record.</p> <div style="margin:1.5rem 0;padding:1.25rem 1.5rem;background:var(--bg-alt);border-left:3px solid #dc3545;border-radius:0 6px 6px 0"><p style="font-weight:700;margin:0 0 .5rem;color:var(--body)">The NPI Gap</p><p style="color:var(--body);font-size:.95rem;line-height:1.75;margin:0">NPI numbers are public (NPPES). Any AI can look one up and cite it. There is no cryptographic binding between an NPI and the AI making the call. NHID-Auth v2 closes this gap — v1.3 already requires disclosure before any NPI is cited.</p></div> <div style="margin:1.5rem 0;padding:1.25rem 1.5rem;background:var(--bg-alt);border-left:3px solid var(--blue);border-radius:0 6px 6px 0"><p style="font-weight:700;margin:0 0 .5rem;color:var(--body)">Pindrop vs. NHID-Clinical</p><p style="color:var(--body);font-size:.95rem;line-height:1.75;margin:0">Pindrop = <strong>detection</strong> (identifies fraudulent calls after the fact). NHID-Clinical = <strong>attestation</strong> (defines what an AI must assert before the call proceeds). Complementary, not competing.</p></div> <h2 style="margin-top:2.5rem;margin-bottom:1.25rem">The Five-Layer Stack</h2> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.75rem;background:var(--paper)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:#dc3545;color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 0</span><strong>The NPI Gap — The Problem</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">No existing infrastructure addresses the cross-org NPI authorization gap. Any AI can cite any NPI without cryptographic proof.<br><small><strong>Mitigated by:</strong> IDG-01 + NHID-Auth v2 Ed25519 delegation</small></p></div> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.75rem;background:var(--paper)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:#6c757d;color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 1</span><strong>STIR/SHAKEN — Carrier Number Authentication</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">FCC-mandated (ATIS-1000074, RFC 8224). A/B/C attestation. Prevents caller-ID spoofing. Does not address AI agent identity.<br><small><strong>Standards:</strong> ATIS-1000074, RFC 8224, RFC 8225 | <strong>Status:</strong> Deployed</small></p></div> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.75rem;background:var(--paper);border-left:3px solid var(--blue)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:var(--blue);color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 2</span><strong>NHID-Clinical v1.3 — Behavioral Disclosure Baseline</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">Four controls (IDG-01, DBC-01, EIT-01, ATR-01) + five CTS tests. Open proposal (NIST-2025-0035-0026).<br><small><a href="/specification.html" style="color:var(--blue)">Specification →</a> · <a href="/developers.html" style="color:var(--blue)">Reference Implementation →</a></small></p></div> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.75rem;background:var(--paper)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:#6610f2;color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 3</span><strong>NHID-Auth v2 — Delegated Authorization + Call Attestation</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">Ed25519 delegation chain + DPoP call-nonce binding. Closes the NPI gap cryptographically. Requires v1.3 as prerequisite.<br><small><strong>Primitives:</strong> Ed25519 (RFC 8037), DPoP (RFC 9449), JWT (RFC 7519) | <strong>Status:</strong> Draft · <a href="/roadmap.html" style="color:var(--blue)">Roadmap →</a></small></p></div> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.75rem;background:var(--paper)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:#28a745;color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 4</span><strong>FHIR AuditEvent R4 / IHE BALP — Healthcare-Native Logging</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">ATR-01 audit records in HL7 FHIR AuditEvent R4 format. Natively parseable by EHR systems, SIEM platforms, and CMS auditors.<br><small><strong>Standards:</strong> HL7 FHIR R4 AuditEvent, IHE ITI-20 BALP | <strong>Required by:</strong> ATR-01, CMS-0057-F</small></p></div> <div style="border:1px solid var(--border);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:2rem;background:var(--paper)"><div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem"><span style="font-size:.7rem;font-weight:700;text-transform:uppercase;background:#17a2b8;color:#fff;padding:.2rem .5rem;border-radius:3px">Layer 5</span><strong>OpenTelemetry Spans — SIEM / Enterprise Observability</strong></div><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">NHID-Clinical traces as OTel spans (CNCF OTel v1.x). Export to Splunk, Datadog, Elastic, Google Cloud — no custom parsers.<br><small><strong>Standards:</strong> CNCF OpenTelemetry v1, OTLP | <strong>Schema:</strong> schema/nhid_trace_schema_v1.json</small></p></div> <h2 style="margin-top:2rem;margin-bottom:1.25rem">Document Family</h2> <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.92rem"><thead><tr style="border-bottom:2px solid var(--border)"><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Layer</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Artifact</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Status</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Role</th></tr></thead><tbody> <tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body)">Governance standard</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--bg-alt);padding:.15rem .4rem;border-radius:3px">NHID-Clinical v1.3</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#e6f4ea;color:#1a7f37;padding:.15rem .45rem;border-radius:10px">Current</span></td><td style="padding:.65rem .75rem;color:var(--body)">Minimum disclosure / escalation baseline</td></tr> <tr style="border-bottom:1px solid var(--border);background:var(--bg-alt)"><td style="padding:.65rem .75rem;color:var(--body)">Companion spec</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--paper);padding:.15rem .4rem;border-radius:3px">NHID-Auth v2</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#fff3cd;color:#856404;padding:.15rem .45rem;border-radius:10px">Draft</span></td><td style="padding:.65rem .75rem;color:var(--body)">Delegated authorization + call attestation</td></tr> <tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body)">Verification infra</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--bg-alt);padding:.15rem .4rem;border-radius:3px">Registry &amp; Badge Model</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#e8f0fe;color:#1a56db;padding:.15rem .45rem;border-radius:10px">In development</span></td><td style="padding:.65rem .75rem;color:var(--body)">Public verification layer</td></tr> <tr><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">Reference software</td><td style="padding:.65rem .75rem;background:var(--bg-alt)"><code style="font-size:.83rem;color:var(--blue);background:var(--paper);padding:.15rem .4rem;border-radius:3px">nhid-clinical-api (Railway)</code></td><td style="padding:.65rem .75rem;background:var(--bg-alt)"><span style="font-size:.78rem;font-weight:600;background:#fce8f3;color:#9c3268;padding:.15rem .45rem;border-radius:10px">Pilot</span></td><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">CTS evaluation + badge generation</td></tr> </tbody></table></div> <p style="margin-top:2rem;font-size:.9rem;color:var(--ink-soft)"><a href="/developers.html" style="color:var(--blue)">← Reference Implementation</a> &nbsp;·&nbsp; <a href="/roadmap.html" style="color:var(--blue)">Roadmap →</a> &nbsp;·&nbsp; <a href="/regulatory-alignment.html" style="color:var(--blue)">Regulatory Alignment →</a></p> """
── regulatory-alignment.html body ───────────────────────────────────────────
RA_BODY = """

<div class="hero-notice" role="note" style="margin-bottom:2rem"><strong>This is not legal advice.</strong> NHID-Clinical is a voluntary open proposal. This mapping helps compliance teams understand how NHID-Clinical controls relate to regulatory requirements. Consult qualified healthcare counsel for compliance determinations.</div> <h2 style="margin-bottom:1.25rem">Compliance Alignment Matrix</h2> <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.89rem"><thead><tr style="border-bottom:2px solid var(--border)"><th style="text-align:left;padding:.65rem .75rem;color:var(--body);font-weight:700;min-width:150px">Regulatory Driver</th><th style="text-align:left;padding:.65rem .75rem;color:var(--body);font-weight:700;min-width:190px">Specific Requirement</th><th style="text-align:left;padding:.65rem .75rem;color:var(--body);font-weight:700">NHID-Clinical Control</th></tr></thead><tbody> <tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body);font-weight:600">CMS-0057-F<br><span style="font-weight:400;font-size:.83rem">Prior Auth Final Rule</span></td><td style="padding:.65rem .75rem;color:var(--body)">FHIR API, 72-hour turnaround, 5-year retention</td><td style="padding:.65rem .75rem;color:var(--body)">FHIR AuditEvent + session trace · ATR-01</td></tr> <tr style="border-bottom:1px solid var(--border);background:var(--bg-alt)"><td style="padding:.65rem .75rem;color:var(--body);font-weight:600">MACPAC May 2026</td><td style="padding:.65rem .75rem;color:var(--body)">AI transparency in prior auth, human review pathway</td><td style="padding:.65rem .75rem;color:var(--body)">PIA + EIT-01 (escalation) + ATR-01 (audit log)</td></tr> <tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body);font-weight:600">DOJ FCA 2026<br><span style="font-weight:400;font-size:.83rem">False Claims Act</span></td><td style="padding:.65rem .75rem;color:var(--body)">Explainability + audit trail for AI-assisted billing</td><td style="padding:.65rem .75rem;color:var(--body)">LOG (structured trace) + CTS conformance · ATR-01</td></tr> <tr style="border-bottom:1px solid var(--border);background:var(--bg-alt)"><td style="padding:.65rem .75rem;color:var(--body);font-weight:600">CMS CRUSH Initiative</td><td style="padding:.65rem .75rem;color:var(--body)">Voice auth in high-risk prior auth transactions</td><td style="padding:.65rem .75rem;color:var(--body)">NHID-Auth v2 delegation chain · IDG-01</td></tr> <tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body);font-weight:600">State AI Laws<br><span style="font-weight:400;font-size:.83rem">CA / TX / MD / NE</span></td><td style="padding:.65rem .75rem;color:var(--body)">Inspectable, auditable AI decisions</td><td style="padding:.65rem .75rem;color:var(--body)">L1/L2/L3 tiered certification · IDG-01 · DBC-01</td></tr> <tr><td style="padding:.65rem .75rem;color:var(--body);font-weight:600;background:var(--bg-alt)">NIST CAISI 2026</td><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">Cross-org agent identity + authorization</td><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">NHID-Auth v2 + NHID-Clinical v1.3 (NIST-2025-0035-0026)</td></tr> </tbody></table></div> <h2 style="margin-top:2.5rem">The False Claims Act Gap</h2> <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">The False Claims Act (31 U.S.C. § 3729) imposes treble damages on fraudulent Medicare/Medicaid claims. The 2026 DOJ enforcement shift focuses on <em>AI-assisted billing workflows</em> — whether organizations can demonstrate that automated systems affecting claim submission have a contemporaneous, inspectable audit record.</p> <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">The gap NHID-Clinical addresses is upstream of billing: the prior authorization voice call. When an AI agent calls a payer to request prior auth, it is acting as the provider's agent. If that call results in a prior auth supporting a subsequent claim, and the AI cannot prove it disclosed its automated status before data exchange — that is an undocumented assumption in the evidentiary chain. NHID-Clinical's ATR-01 closes that gap with a single timestamped log entry.</p> <div style="margin:1.5rem 0;padding:1.25rem 1.5rem;background:var(--bg-alt);border-left:3px solid #dc3545;border-radius:0 6px 6px 0"><p style="font-weight:700;margin:0 0 .5rem;color:var(--body)">The 30-Day Audit Trail Test</p><p style="color:var(--body);font-size:.95rem;line-height:1.75;margin:0">Ask your voice AI vendor: "Can you produce a structured, exportable log of every call in the last 30 days with a per-call timestamp proving AI disclosure occurred before any operational data was exchanged?" If the answer is not an immediate yes with a format specification, your organization is carrying unpriced FCA exposure.</p></div> <h2 style="margin-top:2.5rem">Vendor Evidence Pack Minimum</h2> <p style="color:var(--body);font-size:.95rem;line-height:1.75;margin-top:.75rem">Demand these six items from any vendor making AI-initiated prior auth calls on your behalf:</p> <ol style="margin:1rem 0 1.5rem 1.5rem;color:var(--body);font-size:.95rem;line-height:1.9"> <li><strong>Disclosure timestamp log</strong> — per-call record in JSON, FHIR AuditEvent, or NDJSON proving disclosure before any NPI/Member ID was cited.</li> <li><strong>Escalation path documentation</strong> — evidence a human handoff was available on every call.</li> <li><strong>NPI authorization evidence</strong> — how the AI is authorized to cite provider NPIs. Without NHID-Auth v2: a signed contractual attestation.</li> <li><strong>Deceptive behavior certification</strong> — written attestation: no fake breathing, hesitation, or human-impression scripting.</li> <li><strong>CTS self-assessment results</strong> — output of the five CTS tests against a representative call trace.</li> <li><strong>Data retention policy</strong> — retention period, export format, and audit request process.</li> </ol> <p style="margin-top:2rem;font-size:.9rem;color:var(--ink-soft)"><a href="/for-payers.html" style="color:var(--blue)">← For Payers</a> &nbsp;·&nbsp; <a href="/specification.html" style="color:var(--blue)">Specification →</a> &nbsp;·&nbsp; <a href="/technical-stack.html" style="color:var(--blue)">Technical Architecture →</a></p> """
── write new pages ───────────────────────────────────────────────────────────
print("\n=== Writing new pages ===")
write("technical-stack.html", page(
"Technical Architecture – NHID-Clinical",
"NHID-Clinical Five-Layer Trust Stack — technical architecture for B2B healthcare voice AI identity.",
'<a href="/">Home</a><span>/</span><a href="/developers.html">Developers</a><span>/</span><span>Technical Architecture</span>',
"Technical Architecture · Five Layers · Open Standards",
"The Trust Stack for B2B Healthcare Voice",
"STIR/SHAKEN verifies the phone number. It does not verify the AI agent behind the call. This page explains the five-layer stack that closes that gap.",
TS_BODY,
"Ready to implement",
"Clone the repo and run the reference implementation. 173 tests. Under 1.4 seconds.",
"Developers →", "/developers.html"
))

write("regulatory-alignment.html", page(
"Regulatory Alignment – NHID-Clinical",
"How NHID-Clinical v1.3 maps to CMS-0057-F, MACPAC 2026, DOJ FCA enforcement, NIST CAISI, and state AI laws.",
'<a href="/">Home</a><span>/</span><a href="/for-payers.html">For Payers</a><span>/</span><span>Regulatory Alignment</span>',
"Regulatory Alignment · June 2026",
"How NHID-Clinical Addresses Today's AI Governance Mandates",
"CMS WISeR, MACPAC May 2026, DOJ FCA 2026 enforcement, and state AI laws are all converging on the same gap: AI voice agents in prior auth workflows with no disclosure, no delegation proof, and no audit trail.",
RA_BODY,
"Questions about compliance posture",
"Contact us for a 30-minute briefing on the alignment matrix.",
"Contact →", "mailto:contact@nhid-clinical.org"
))

── patch existing pages ──────────────────────────────────────────────────────
print("\n=== Patching existing pages ===")

specification.html — add Document Family table
patch("specification.html",
'<div style="padding:1.5rem;background:#eff6ff;border-radius:8px;margin-top:2rem">\n <p style="margin:0;color:#1e293b">These behaviors are demonstrated in the <a href="/governance-simulator.html" style="color:#0ea5e9;font-weight:500">Governance Simulator \u2192</a></p>\n </div>\n </div>\n </section>',
'<div style="padding:1.5rem;background:#eff6ff;border-radius:8px;margin-top:2rem">\n <p style="margin:0;color:#1e293b">These behaviors are demonstrated in the <a href="/governance-simulator.html" style="color:#0ea5e9;font-weight:500">Governance Simulator \u2192</a></p>\n </div>\n <h2 style="margin-top:2.5rem;margin-bottom:1.25rem">Document Family</h2>\n <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.92rem"><thead><tr style="border-bottom:2px solid var(--border)"><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Layer</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Artifact</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Status</th><th style="text-align:left;padding:.6rem .75rem;color:var(--body);font-weight:700">Role</th></tr></thead><tbody><tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body)">Governance standard</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--bg-alt);padding:.15rem .4rem;border-radius:3px">NHID-Clinical v1.3</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#e6f4ea;color:#1a7f37;padding:.15rem .45rem;border-radius:10px">Current</span></td><td style="padding:.65rem .75rem;color:var(--body)">Minimum disclosure / escalation baseline</td></tr><tr style="border-bottom:1px solid var(--border);background:var(--bg-alt)"><td style="padding:.65rem .75rem;color:var(--body)">Companion spec</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--paper);padding:.15rem .4rem;border-radius:3px">NHID-Auth v2</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#fff3cd;color:#856404;padding:.15rem .45rem;border-radius:10px">Draft</span></td><td style="padding:.65rem .75rem;color:var(--body)">Delegated authorization + call attestation</td></tr><tr style="border-bottom:1px solid var(--border)"><td style="padding:.65rem .75rem;color:var(--body)">Verification infra</td><td style="padding:.65rem .75rem"><code style="font-size:.83rem;color:var(--blue);background:var(--bg-alt);padding:.15rem .4rem;border-radius:3px">Registry & Badge Model</code></td><td style="padding:.65rem .75rem"><span style="font-size:.78rem;font-weight:600;background:#e8f0fe;color:#1a56db;padding:.15rem .45rem;border-radius:10px">In development</span></td><td style="padding:.65rem .75rem;color:var(--body)">Public verification layer</td></tr><tr><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">Reference software</td><td style="padding:.65rem .75rem;background:var(--bg-alt)"><code style="font-size:.83rem;color:var(--blue);background:var(--paper);padding:.15rem .4rem;border-radius:3px">nhid-clinical-api (Railway)</code></td><td style="padding:.65rem .75rem;background:var(--bg-alt)"><span style="font-size:.78rem;font-weight:600;background:#fce8f3;color:#9c3268;padding:.15rem .45rem;border-radius:10px">Pilot</span></td><td style="padding:.65rem .75rem;color:var(--body);background:var(--bg-alt)">CTS evaluation + badge generation</td></tr></tbody></table></div>\n <p style="margin-top:1.5rem;font-size:.9rem;color:var(--ink-soft)"><a href="/technical-stack.html" style="color:var(--blue)">Five-layer trust architecture \u2192</a>  \xb7  <a href="/regulatory-alignment.html" style="color:var(--blue)">Regulatory alignment matrix \u2192</a></p>\n </div>\n </section>'
)

developers.html — fix test count
patch("developers.html",
"Unit invariant preserved: 95 passed, 0 skipped",
"173 passed, 18 skipped in ~1.4s"
)

developers.html — add technical stack cross-link
patch("developers.html",
'<p style="font-weight:700;margin:0 0 .4rem;color:var(--body)">Vendor Interoperability</p>\n <p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">Vendor format adapters convert vendor-specific call transcripts to NHID-Clinical event traces. See the <a href="/interoperability.html" style="color:var(--blue);font-weight:500">interoperability demo \u2192</a></p>\n </div>',
'<p style="font-weight:700;margin:0 0 .4rem;color:var(--body)">Vendor Interoperability</p>\n <p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">Vendor format adapters convert vendor-specific call transcripts to NHID-Clinical event traces. See the <a href="/interoperability.html" style="color:var(--blue);font-weight:500">interoperability demo \u2192</a></p>\n </div>\n <div style="margin-top:1.5rem;padding:1.25rem 1.5rem;background:var(--bg-alt);border-left:3px solid var(--blue);border-radius:0 6px 6px 0"><p style="font-weight:700;margin:0 0 .4rem;color:var(--body)">How It All Fits Together</p><p style="color:var(--body);font-size:.93rem;line-height:1.75;margin:0">Each layer — from STIR/SHAKEN at the carrier level to OpenTelemetry spans at the SIEM layer — connects through NHID-Clinical. See the <a href="/technical-stack.html" style="color:var(--blue);font-weight:500">five-layer trust architecture \u2192</a></p></div>'
)

roadmap.html — add technical stack cross-link
patch("roadmap.html",
'<a href="/specification.html" style="color:var(--blue)">v1.3 Spec</a>\n </p>',
'<a href="/specification.html" style="color:var(--blue)">v1.3 Spec</a>\n  \xb7 \n <a href="/technical-stack.html" style="color:var(--blue)">Five-layer trust architecture \u2192</a>\n </p>'
)

for-payers.html — add regulatory alignment cross-link
patch("for-payers.html",
'<a href="/proof.html" style="color:var(--blue)">Proof package</a>\n </p>',
'<a href="/proof.html" style="color:var(--blue)">Proof package</a>\n  \xb7 \n <a href="/regulatory-alignment.html" style="color:var(--blue)">Regulatory alignment matrix \u2192</a>\n </p>'
)

── git ───────────────────────────────────────────────────────────────────────
print("\n=== Committing ===")
run("git add conftest.py README.md technical-stack.html regulatory-alignment.html specification.html developers.html roadmap.html for-payers.html")
run('git commit -m "Add technical-stack, regulatory-alignment, conftest.py, enhanced README; patch cross-links"')

print("\n=== Pushing to main ===")
run("git push origin main")

print("\nDone. Visit https://github.com/NHID-Clinical/NHID-Clinical to verify.")

---
**Also, for `gh repo edit` — PowerShell uses backtick not backslash for line continuation. Run these as separate one-liners:**
```powershell
gh repo edit NHID-Clinical/NHID-Clinical --description "Open framework for AI voice agent identity disclosure in B2B healthcare. NIST-2025-0035-0026."
gh repo edit NHID-Clinical/NHID-Clinical --homepage "https://nhid-clinical.org"
gh repo edit NHID-Clinical/NHID-Clinical --add-topic healthcare
gh repo edit NHID-Clinical/NHID-Clinical --add-topic ai-agents
gh repo edit NHID-Clinical/NHID-Clinical --add-topic voice-ai
gh repo edit NHID-Clinical/NHID-Clinical --add-topic prior-authorization
gh repo edit NHID-Clinical/NHID-Clinical --add-topic hipaa
gh repo edit NHID-Clinical/NHID-Clinical --add-topic fhir
gh repo edit NHID-Clinical/NHID-Clinical --add-topic nist
gh repo edit NHID-Clinical/NHID-Clinical --add-topic healthcare-ai