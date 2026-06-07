# save as apply_polish.py, run: python apply_polish.py
import os, subprocess, pathlib

ROOT = pathlib.Path(__file__).parent

def sub(path, old, new):
    p = ROOT / path
    t = p.read_text(encoding='utf-8')
    if old not in t: print(f"SKIP {path} (already done?)"); return
    p.write_text(t.replace(old, new, 1), encoding='utf-8')
    print(f"  OK  {path}")

def run(cmd): subprocess.run(cmd, shell=True, cwd=ROOT, check=False)

# 1. index.html
sub("index.html",
    'content="NHID-Clinical: Observations on AI voice agents calling payers',
    'content="Early non-human identity disclosure standard for payer-provider voice calls. No deceptive audio. Immediate escalation. Auditable traces. v1.3 open proposal by Brianna Baynard.')
sub("index.html", "| Observations on AI Voice Agents Calling Payers", "| Transparent AI Voice Agents in Healthcare")
sub("index.html", "<h1>NHID-Clinical: Observations on AI Voice Agents Calling Payers</h1>", "<h1>NHID-Clinical</h1>")
sub("index.html",
    '<p class="hero-body">I spent months working in payer operations',
    '<p class="hero-body">Early disclosure before PHI exchange. No deceptive audio behaviors. Immediate human escalation. Machine-readable audit traces.</p>\n        <p class="hero-body" style="display:none">I spent months working in payer operations')
# Simpler: just replace the whole long paragraph. Copy from below.
sub("index.html", "Current state (May 2026):", "Current state (v1.3 \u00b7 June 2026):")

# 2. developers.html
sub("developers.html", "https://github.com/thankcheeses/NHID-Clinical.git", "https://github.com/NHID-Clinical/NHID-Clinical.git")
sub("developers.html", "python -m pytest tests/ -v", "python -m pytest tests/ -q\n# Expected: 173 passed, 18 skipped in ~1.4s")
sub("developers.html",
    '    <p class="footer-copy">\u00a9 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0 | contact@nhid-clinical.org | nhid-clinical.org</p>',
    '')

# 3. for-payers.html
sub("for-payers.html",
    '    <p class="footer-copy">\u00a9 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0 | contact@nhid-clinical.org | nhid-clinical.org</p>',
    '')

# 4. community.html
sub("community.html", "discord.gg/3Z2RqbjuDd", "discord.gg/eP8FxXkGU6")

# 5. README.md badges + tagline
sub("README.md",
    "[![Version](https://img.shields.io/badge/Version-v1.3%20Open%20Core-green)](https://nhid-clinical.org/specification.html)\n\nA voluntary",
    """[![Version](https://img.shields.io/badge/Version-v1.3%20Open%20Core-green)](https://nhid-clinical.org/specification.html)
[![Tests](https://img.shields.io/badge/tests-173%20passed-brightgreen)](https://github.com/NHID-Clinical/NHID-Clinical/actions)
[![Status](https://img.shields.io/badge/status-Open%20Proposal-yellow)](https://nhid-clinical.org)
[![Website](https://img.shields.io/badge/website-nhid--clinical.org-0052cc)](https://nhid-clinical.org)

**Transparent AI voice governance for healthcare.** Early disclosure. No deceptive audio. Auditable traces.

A voluntary""")

# 6. .gitignore
gi = (ROOT / ".gitignore").read_text(encoding='utf-8')
additions = "\n.python_history\n*.patch\ngo.py - Copy.py\n"
if ".python_history" not in gi:
    (ROOT / ".gitignore").write_text(gi + additions, encoding='utf-8')
    print("  OK  .gitignore")

# 7. Delete junk
for f in ["go.py - Copy.py", ".python_history", "nhid-173-tests.patch"]:
    p = ROOT / f
    if p.exists(): p.unlink(); print(f"  DEL {f}")

# 8. Create trust files
(ROOT / ".github").mkdir(exist_ok=True)
(ROOT / ".github/SECURITY.md").write_text("""# Security Policy
Report security issues to: contact@nhid-clinical.org
We respond within 48 hours.
This repository contains no live PHI or secrets.
""", encoding='utf-8')
(ROOT / ".github/CONTRIBUTING.md").write_text("""# Contributing
1. Fork the repo
2. Make changes
3. Run tests: `python -m pytest tests/ -q` (173 expected)
4. Open a PR — big changes: open an Issue first
Discord: https://discord.gg/eP8FxXkGU6
""", encoding='utf-8')
(ROOT / "CHANGELOG.md").write_text("""# Changelog
## [v1.3] - 2026-06
- NPI validator + NHID-CAS scoring; 173 tests total
## [v1.2] - 2026-05
- Conformance test suite (18 YAML cases), failure traces
## [v1.1] - 2026-04
- Policy engine (IDG-01, DBC-01, EIT-01, ATR-01, CTS-05)
## [v1.0] - 2026-04
- Initial schema and specification; NIST-2025-0035-0026
""", encoding='utf-8')

print("\nAll changes applied. Now run:")
print("  git add -A && git commit -m 'Polish sprint: hero refresh, trust signals, repo hygiene' && git push origin main")