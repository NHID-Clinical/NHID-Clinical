# fix-site.ps1 - NHID-Clinical fix pass (run from repo root)
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\bnbay\NHID-Clinical'
function ReadAll($p){ [System.IO.File]::ReadAllText($p) }
function WriteAll($p,$c){ [System.IO.File]::WriteAllText($p,$c,(New-Object System.Text.UTF8Encoding($false))) }

git checkout main
git pull origin main

# ===== FIX 3: restore 16 truncated strings in specification.html =====
$p='specification.html'; $h=ReadAll $p
$pairs=@(
 @('requirements for transparent AI[^\r\n]*','requirements for transparent AI voice agent disclosure in B2B healthcare administrative calls."/>'),
 @('r="8"/><path d="m2[^\r\n]*','r="8"/><path d="m21 21-4.35-4.35"/></svg>'),
 @('operate without disclosing[^\r\n]*','operate without disclosing their automated status before exchanging operational data.</p>'),
 @('impersonation latency</strong>[^\r\n]*','impersonation latency</strong> &mdash; where a payer representative cannot quickly determine whether the caller is human or automated.</p>'),
 @('appearing to be hu[^\r\n]*','appearing to be human.</p>'),
 @('operational data is excha[^\r\n]*','operational data is exchanged.</p>'),
 @('These are not mandatory require[^\r\n]*','These are not mandatory requirements &mdash; they are suggested behaviors for voluntary adoption.</p>'),
 @('<strong>Identify [^\r\n]*','<strong>Identify as an automated system</strong> before any exchange of operational data (NPI, Member ID, Claim Number)</li>'),
 @('<strong>Behave li[^\r\n]*','<strong>Behave like a machine, not a human</strong> &mdash; no fake breathing, typing sounds, or scripted hesitation designed to imply human presence</li>'),
 @('<strong>Provide a[^\r\n]*','<strong>Provide a clear, immediate path to a human agent</strong> when requested</li>'),
 @('<strong>Maintain [^\r\n]*','<strong>Maintain a basic audit log</strong> showing disclosure occurred before data was exchanged</li>'),
 @('They are observable, t[^\r\n]*','They are observable, testable, and do not require vendor architecture changes.</p>'),
 @('would meaningfully change the impersonation latency problem[^\r\n]*','would meaningfully change the impersonation latency problem &mdash; not a comprehensive AI governance framework.</p>'),
 @('calling payer offi[^\r\n]*','calling payer offices on behalf of providers for eligibility verification, claim status, prior authorization, and similar administrative tasks. It does not apply to patient-facing calls, internal tools, or clinical decision support.</p>'),
 @('no audit process, no enforcemen[^\r\n]*','no audit process, no enforcement mechanism, and no regulatory authority. Adoption is entirely voluntary.</p>'),
 @('escalation path, audit[^\r\n]*','escalation paths, and audit logging. It does not address cross-boundary authorization (whether the AI is actually delegated by the provider it claims to represent). That is the scope of v2.</p>')
)
foreach($pr in $pairs){ $h=[regex]::Replace($h,$pr[0],$pr[1]) }
if($h -match '\[\.\.\.\]'){ throw 'truncation markers still present in specification.html' }
WriteAll $p $h
git add specification.html
git commit -m "Restore truncated specification.html section text"

# ===== FIX 1: create pilot.html =====
$pilot=@'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="description" content="NHID-Clinical Pilot Program - a no-cost 90-day shadow mode pilot guide for payers observing incoming AI voice calls against NHID-Clinical v1.3 controls."/>
  <title>Pilot Program - NHID-Clinical</title>
  <link rel="icon" href="/assets/brand-icon.png" type="image/png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="/nhid-clinical-ui.css"/>
  <script>try{document.documentElement.setAttribute('data-theme',localStorage.getItem('nhid-theme')||'light')}catch(e){}</script>
</head>
<body>

<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px 20px;font-size:.88rem;line-height:1.6">
  <strong>Note:</strong> NHID-Clinical is an early-stage open proposal by Brianna Baynard. It is not an accredited standard or regulatory requirement.
</div>

<header class="site-header">
  <nav class="container nav" aria-label="Primary navigation">
    <a class="brand" href="/" aria-label="NHID-Clinical home">
      <span class="brand-mark" aria-hidden="true"><img src="/assets/brand-icon.png" alt="NHID-Clinical" /></span>
      <span>
        <strong>NHID-Clinical</strong>
        <small>Building Trust in Healthcare Voice AI</small>
      </span>
    </a>
    <div class="nav-links">
      <a href="/">Home</a>
      <a href="/about.html">About</a>
      <span class="nav-sep" aria-hidden="true"></span>
      <a href="/script-examples.html">Examples</a>
      <span class="nav-sep" aria-hidden="true"></span>
      <a href="/for-payers.html">For Payers</a>
      <span class="nav-sep" aria-hidden="true"></span>
      <a href="/specification.html">Spec</a>
      <a href="/developers.html">Developers</a>
      <a href="/interoperability.html">Interoperability</a>
      <span class="nav-sep" aria-hidden="true"></span>
      <a href="/news.html">News</a>
      <a href="/community.html">Community</a>
      <a href="/faq.html">FAQ</a>
    </div>
    <div class="nav-actions">
      <button class="icon-button search-toggle" type="button" aria-label="Search" id="search-toggle">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      </button>
      <button class="icon-button theme-toggle" type="button" aria-label="Toggle dark mode" id="theme-toggle">
        <svg class="sun-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
        <svg class="moon-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      </button>
      <a class="primary-pill" href="/community.html">Get Involved</a>
      <button class="icon-button menu-button" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-nav">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
    </div>
  </nav>
</header>

<nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation">
  <a href="/">Home</a>
  <a href="/about.html">About</a>
  <a href="/script-examples.html">Examples</a>
  <a href="/for-payers.html">For Payers</a>
  <a href="/specification.html">Spec</a>
  <a href="/developers.html">Developers</a>
  <a href="/interoperability.html">Interoperability</a>
  <a href="/news.html">News</a>
  <a href="/community.html">Community</a>
  <a href="/faq.html">FAQ</a>
</nav>
<div class="nav-backdrop" id="nav-backdrop"></div>

<main>
  <section class="inner-hero">
    <div class="container">
      <div class="crumbs"><a href="/">Home</a><span>/</span><a href="/for-payers.html">For Payers</a><span>/</span><span>Pilot Program</span></div>
      <p class="eyebrow">Pilot Program - 90-Day Shadow Mode</p>
      <h1>The NHID-Clinical Pilot</h1>
      <p class="lede">A no-cost, 90-day shadow mode pilot for payers. Observe incoming AI voice calls against NHID-Clinical v1.3 controls - no vendor changes, no production risk.</p>
    </div>
  </section>

  <section class="page-section">
    <div class="container" style="max-width:52rem">

      <div class="callout" role="note" style="margin-bottom:2rem">
        <strong>Shadow mode means observe-only.</strong> Nothing in your call flow changes. You measure how today's incoming AI voice traffic behaves against the four NHID-Clinical v1.3 controls, then decide what to do with what you find.
      </div>

      <h2>What the Pilot Is</h2>
      <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">The pilot observes incoming AI voice calls against the NHID-Clinical v1.3 control baseline. It requires <strong>no vendor changes</strong>, runs in <strong>shadow mode</strong> alongside your existing call handling, and has <strong>no cost</strong>.</p>
      <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">The goal is simple: produce a clear, evidence-backed picture of how AI voice agents currently behave when they call your administrative lines - whether they disclose, whether they escalate cleanly, and whether a basic audit trail exists.</p>

      <h2 style="margin-top:2.5rem">What You Need</h2>
      <ul style="list-style:disc;padding-left:1.5rem;margin:.75rem 0;color:var(--body);font-size:.95rem;line-height:1.85">
        <li>Access to call logs or recordings for a sample of incoming administrative calls (eligibility, claim status, prior authorization).</li>
        <li>About 30 minutes of staff time for setup and orientation.</li>
        <li>Willingness to share findings - anonymized - with the NHID-Clinical community.</li>
      </ul>

      <h2 style="margin-top:2.5rem">The 90-Day Structure</h2>
      <div style="display:grid;gap:1rem;margin-top:1rem">
        <div style="padding:1.1rem 1.4rem;border-left:3px solid var(--blue);background:var(--bg-alt);border-radius:0 6px 6px 0">
          <strong>Month 1 - Baseline.</strong>
          <p style="margin:.4rem 0 0;color:var(--body);font-size:.95rem;line-height:1.8">Log incoming calls and identify which callers are AI voice agents. Establish a baseline volume and a sense of which workflows AI is calling about.</p>
        </div>
        <div style="padding:1.1rem 1.4rem;border-left:3px solid var(--blue);background:var(--bg-alt);border-radius:0 6px 6px 0">
          <strong>Month 2 - Gap Analysis.</strong>
          <p style="margin:.4rem 0 0;color:var(--body);font-size:.95rem;line-height:1.8">Evaluate the identified AI calls against the controls. Which calls fail IDG-01 (no disclosure before data exchange)? Which fail EIT-01 (no clean human escalation)? Quantify the gaps.</p>
        </div>
        <div style="padding:1.1rem 1.4rem;border-left:3px solid var(--blue);background:var(--bg-alt);border-radius:0 6px 6px 0">
          <strong>Month 3 - Report.</strong>
          <p style="margin:.4rem 0 0;color:var(--body);font-size:.95rem;line-height:1.8">Compile findings into a short written assessment and share the anonymized results with the NHID-Clinical community to help shape the next version of the proposal.</p>
        </div>
      </div>

      <h2 style="margin-top:2.5rem">How to Start</h2>
      <p style="color:var(--body);font-size:1rem;line-height:1.85;margin-top:.75rem">Email <a href="mailto:contact@nhid-clinical.org?subject=Pilot%20Interest" style="color:var(--blue);font-weight:600">contact@nhid-clinical.org</a> with the subject line <strong>"Pilot Interest"</strong>. Include your role and the workflows you would like to observe, and you will receive the setup guide.</p>

      <div style="margin-top:2.5rem;padding-top:1.5rem;border-top:1px solid var(--line);display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.9rem">
        <a href="/for-payers.html" style="color:var(--blue);font-weight:600">&larr; Back to For Payers</a>
        <span style="color:var(--ink-soft)">Proof Package (coming soon)</span>
      </div>

    </div>
  </section>
</main>

<footer id="contact" class="site-footer">
  <div class="container footer-inner">
    <p>&copy; 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0</p>
    <div>
      <a href="mailto:contact@nhid-clinical.org">Contact</a>
      <a href="https://nhid-clinical.org">nhid-clinical.org</a>
      <a href="https://twitter.com/NHIDClinical">@NHIDClinical</a>
      <a href="https://discord.gg/eP8FxXkGU6">Discord</a>
      <a href="https://reddit.com/r/NonHumanAuth">Reddit</a>
    </div>
  </div>
</footer>

<script src="/site.js"></script>
</body>
</html>
'@
WriteAll 'pilot.html' $pilot
git add pilot.html
git commit -m "Add pilot.html - 90-day shadow mode pilot guide for payers"

# ===== FIX 2: mark Railway demo endpoints offline in developers.html =====
$d=ReadAll 'developers.html'
$d=$d.Replace('Live Demo API <span','Live Demo API (currently offline) <span')
$note='<p style="margin:.5rem 0 .25rem;font-size:.85rem;color:#9a6700;background:#fff8e1;border-left:3px solid #ffc107;padding:.5rem .75rem;border-radius:0 4px 4px 0">&#9888; Live demo endpoint currently offline. Code examples shown for reference only.</p>'
$d=$d.Replace('Rate-limited.</p>','Rate-limited.</p>'+$note)
WriteAll 'developers.html' $d
git add developers.html
git commit -m "Mark Railway demo endpoints as offline in developers.html"

# ===== FIX 4: stale repo URLs (7 files) + remove internal branch line =====
$files = @('developers.html','docs.html','for-payers.html','interoperability.html','news.html','pricing.html','roadmap.html')
foreach($f in $files){
  if(Test-Path $f){
    $c=ReadAll $f
    if($c.Contains('thankcheeses/NHID-Clinical')){
      WriteAll $f ($c.Replace('thankcheeses/NHID-Clinical','NHID-Clinical/NHID-Clinical'))
    }
  }
}
$io=ReadAll 'interoperability.html'
$io=[regex]::Replace($io,'(?m)^git checkout claude/code-review-fixes-98Ir1\r?\n','')
WriteAll 'interoperability.html' $io
git add developers.html for-payers.html interoperability.html news.html pricing.html roadmap.html
git commit -m "Fix stale repo URLs and remove internal branch reference from public pages"

# ===== FIX 5: README =====
$readme=@'
# NHID-Clinical

**Non-Human Identity Disclosure Standard for Healthcare Voice Workflows**
Version: 1.3 | Status: Open Governance Proposal | License: CC BY 4.0

---

## What This Is

NHID-Clinical defines a minimum, voluntary, testable control baseline for non-human identity disclosure in B2B healthcare administrative voice interactions.

It addresses a documented gap in provider-to-payer voice workflows (eligibility, claim status, prior authorization) where AI voice agents operate without disclosing their automated status before exchanging operational data.

**This is not a regulation, certification program, or compliance requirement.** It is an open governance proposal submitted to NIST docket NIST-2025-0035 (Comment ID: NIST-2025-0035-0026).

---

## The Problem: Impersonation Latency

An AI calls as "Sarah from Dr. Smith's office." It handles several minutes of normal workflow conversation. Only when challenged does it admit it is automated. By then, sensitive operational data has already been exchanged without clear consent or accountability.

This is impersonation latency: the measurable trust delay between an AI agent initiating a call and the receiving system verifying the caller is authorized to represent the claimed provider.

---

## The Four Controls (v1.3)

| ID | Name | Requirement |
|----|------|-------------|
| IDG-01 | Identity Disclosure Gate | AI MUST identify as automated before any operational data exchange |
| DBC-01 | Deceptive Behavior Check | AI MUST NOT use fake breathing, typing sounds, or scripted human-like hesitation |
| EIT-01 | Escalation and Immediate Transfer | AI MUST provide immediate human handoff when requested |
| ATR-01 | Audit Trail Requirements | AI MUST log disclosure timestamp vs. first data request timestamp |

---

## Conformance Test Suite

Five deterministic pass/fail tests. All five must pass for NHID-Clinical v1.3 conformance.

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
pytest tests/ -q
```

Expected: `95 passed, 18 skipped`

The 18 skipped tests are integration tests requiring a live FastAPI server. They are optional and do not affect policy engine verification.

---

## Repository Structure

```
src/
  agent_identity.py              # NHID-Auth delegation and NPI binding
  voice_policy.py                # Core disclosure and escalation policy engine
  nhid_policy_engine_v1.py       # Five CTS rule implementations
tests/
  test_identity.py               # Identity and delegation tests
  test_voice_policy.py           # Policy engine tests
  failure_injection_harness.py   # Chaos and adversarial input tests
conformance/
  nhid_conformance_test_suite_v1.yaml   # 18 machine-readable CTS cases
specs/
  NHIDClinicalv1.3_Overview.pdf
  NHID-Clinical-Operational-Blueprint-v1.3.pdf
```

---

## Framework Alignment

| NHID-Clinical Control | NIST AI RMF 1.0 | ISO/IEC 42001:2023 |
|----------------------|-----------------|-------------------|
| Proactive Identity Assertion | MEASURE 2.6, MAP 3.4 | A.7.2, B.9.1 |
| No Deceptive Artifacts | GOV 1.5, MAP 3.4 | A.5.8, A.9.2 |
| Pre-Data Exchange Gate | MANAGE 1.2, GOV 5.1 | A.6.2, A.8.2 |
| Safe Failover / Escalation | MANAGE 4.2, GOV 5.2 | A.8.3, A.6.3 |
| Audit Logging | MANAGE 4.1, MEASURE 2.2 | A.4.2, A.9.3 |

---

## NIST Submission

Submitted to NIST AI Safety Institute public comment docket NIST-2025-0035.
Comment ID: **NIST-2025-0035-0026**
This is a public comment. It does not imply NIST endorsement or recognition.

---

## Website

**[nhid-clinical.org](https://nhid-clinical.org)**

---

## License

CC BY 4.0 - Brianna Baynard-Malone
contact@nhid-clinical.org
'@
WriteAll 'README.md' $readme
git add README.md
git commit -m "Update README - correct repo URL, accurate project status"

# ===== push =====
git log --oneline -6
git push origin main
Write-Host "`nDONE. Verify Pages build at https://github.com/NHID-Clinical/NHID-Clinical/actions" -ForegroundColor Green
