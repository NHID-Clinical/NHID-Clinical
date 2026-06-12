import pathlib
R = pathlib.Path(__file__).parent / "alignment"
R.mkdir(exist_ok=True)

R.joinpath("stir-shaken.html").write_text('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STIR/SHAKEN Alignment · NHID-Clinical</title>
<link rel="stylesheet" href="../nhid-clinical-ui.css">
</head>
<body>
<div class="nhid-banner">Note: NHID-Clinical is an early-stage open proposal. It is not an accredited standard or regulatory requirement.</div>
<nav><a href="../index.html">Home</a> / <a href="../specification.html">Specification</a> / STIR/SHAKEN Alignment</nav>
<main>
<h1>STIR/SHAKEN Alignment</h1>
<p>STIR/SHAKEN attests that a number is legitimate — not that the caller is authorized to access protected health information.</p>
<h2>Trust Stack</h2>
<table>
  <thead><tr><th>Layer</th><th>Standard</th><th>What it proves</th></tr></thead>
  <tbody>
    <tr><td>Carrier</td><td>STIR/SHAKEN</td><td>Number is legitimate</td></tr>
    <tr><td>Disclosure</td><td>NHID-Clinical v1.3</td><td>AI status declared before PHI exchange</td></tr>
    <tr><td>Authorization</td><td>NHID-Auth v2</td><td>Cryptographic delegation from provider</td></tr>
  </tbody>
</table>
<p>For cross-framework mapping see the <a href="https://ai-governance-map.vercel.app">AI Governance Map</a></p>
<p><a href="../specification.html">specification.html</a></p>
</main>
</body>
</html>''', encoding='utf-8')

R.joinpath("cms-0057-f.html").write_text('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CMS-0057-F Prior Authorization Rule Alignment · NHID-Clinical</title>
<link rel="stylesheet" href="../nhid-clinical-ui.css">
</head>
<body>
<div class="nhid-banner">Note: NHID-Clinical is an early-stage open proposal. It is not an accredited standard or regulatory requirement.</div>
<nav><a href="../index.html">Home</a> / <a href="../specification.html">Specification</a> / CMS-0057-F Alignment</nav>
<main>
<h1>CMS-0057-F Prior Authorization Rule Alignment</h1>
<p>This page maps NHID-Clinical v1.3 controls to the CMS Prior Authorization Final Rule (CMS-0057-F) requirements for AI transparency in prior authorization workflows.</p>
<h2>NHID-Clinical Alignment</h2>
<table>
  <thead><tr><th>CMS-0057-F Requirement</th><th>NHID-Clinical Control</th><th>Artifact</th></tr></thead>
  <tbody>
    <tr><td>FHIR API for PA transactions</td><td>ATR-01</td><td>FHIR AuditEvent R4 mapping</td></tr>
    <tr><td>AI transparency in decisions</td><td>IDG-01</td><td>CTS conformance test suite</td></tr>
    <tr><td>Human review availability</td><td>EIT-01</td><td>Safe escalation phrases</td></tr>
  </tbody>
</table>
<p><a href="../specification.html">specification.html</a></p>
</main>
</body>
</html>''', encoding='utf-8')

R.joinpath("nist-ai-agent-standards.html").write_text('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NIST AI Agent Standards Alignment · NHID-Clinical</title>
<link rel="stylesheet" href="../nhid-clinical-ui.css">
</head>
<body>
<div class="nhid-banner">Note: NHID-Clinical is an early-stage open proposal. It is not an accredited standard or regulatory requirement.</div>
<nav><a href="../index.html">Home</a> / <a href="../specification.html">Specification</a> / NIST AI Agent Standards</nav>
<main>
<h1>NIST AI Agent Standards Alignment</h1>
<p>This is an open proposal submitted to NIST docket NIST-2025-0035-0026.</p>
<h2>NIST AI RMF Alignment</h2>
<table>
  <thead><tr><th>NIST AI RMF Function</th><th>NHID-Clinical Control</th></tr></thead>
  <tbody>
    <tr><td>GOVERN 1.1</td><td>IDG-01 — AI system status disclosed</td></tr>
    <tr><td>MANAGE 2.2</td><td>EIT-01 — Human escalation path</td></tr>
    <tr><td>MEASURE 2.5</td><td>ATR-01 — Auditable trail</td></tr>
  </tbody>
</table>
<p>For cross-framework mapping see the <a href="https://ai-governance-map.vercel.app">AI Governance Map</a></p>
<p><a href="../specification.html">specification.html</a></p>
</main>
</body>
</html>''', encoding='utf-8')

R.joinpath("vendor-evidence-pack.html").write_text('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vendor Evidence Pack · NHID-Clinical</title>
<link rel="stylesheet" href="../nhid-clinical-ui.css">
</head>
<body>
<div class="nhid-banner">Note: NHID-Clinical is an early-stage open proposal. It is not an accredited standard or regulatory requirement.</div>
<nav><a href="../index.html">Home</a> / <a href="../specification.html">Specification</a> / Vendor Evidence Pack</nav>
<main>
<h1>Vendor Evidence Pack</h1>
<p>Minimum evidence a voice AI vendor should produce to demonstrate NHID-Clinical conformance.</p>
<ul>
  <li>CTS conformance test results (pass/fail for all 5 tests)</li>
  <li>Sample disclosure transcript</li>
  <li>Escalation phrase list</li>
  <li>FHIR AuditEvent sample</li>
  <li>NPI binding documentation</li>
</ul>
<p><a href="../specification.html">specification.html</a></p>
</main>
</body>
</html>''', encoding='utf-8')

print("Created 4 alignment HTML files.")
print("Now run: python -m pytest tests/ -q")