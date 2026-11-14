#!/usr/bin/env python3
"""Generate `impersonation-cost.html` from `src/impersonation_cost.py`.

    python scripts/build_impersonation_calculator.py            # write
    python scripts/build_impersonation_calculator.py --check     # fail if stale

## Why generate it

The page does arithmetic in the browser and the authoritative model is Python
(`src/impersonation_cost.py`, tested in `tests/test_impersonation_cost.py`).
Two implementations of the same four multiplications is exactly the drift this
repo already guards against for published numbers
(`scripts/check_number_drift.py`). So the browser's copy is *emitted* from the
model's own constants and field list rather than typed a second time, and
`tests/test_impersonation_calculator_page.py` fails if the committed page stops
matching a fresh render.

## Why the shell is copied from another page

A new page at the site root is enrolled automatically into
`tests/test_site_navigation.py` (anything carrying `id="mobile-nav"`) and into
`tests/test_seo.py` (via `scripts/seo/pages.json`). Hand-writing the header,
drawer and footer would mean this page silently falling behind the next change
to the site chrome. Instead the shell is read from `SHELL_SOURCE` at build
time: whatever the rest of the site does, this page does too, and a rebuild
picks up the change.

Page-specific structured data is stripped from the copied shell;
`scripts/seo/seo_head.py` injects the correct graph for this route afterwards,
which is why that script must run after this one.
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.impersonation_cost import (  # noqa: E402
    DISCLAIMER,
    FIELDS,
    INPUTS,
    MINUTES_PER_HOUR,
    MONTHS_PER_YEAR,
)

ROUTE = "impersonation-cost.html"
SHELL_SOURCE = "privacy.html"
ORIGIN = "https://nhid-clinical.org"

TITLE = "Impersonation handle-time calculator | NHID-Clinical"
# test_seo.py holds every description to 50-160 characters so it is not cut off
# in a result. This one is 149.
DESCRIPTION = (
    "Work out the handle-time cost of undisclosed automated callers from your own "
    "assumptions. Illustrative arithmetic, not a measurement or a saving."
)
HEADLINE = "What undisclosed automated callers cost in handle time"


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


# ── the shell ────────────────────────────────────────────────────────────────

def shell() -> tuple[str, str]:
    """(everything before <main>, everything from </main>) with the head rewritten."""
    text = (ROOT / SHELL_SOURCE).read_text(encoding="utf-8")
    head_body, rest = text.split("<main", 1)
    suffix = "</main" + rest.split("</main", 1)[1]

    # Strip the shell page's own structured data. seo_head.py adds this route's.
    head_body = re.sub(
        r'\s*<!-- seo:structured-data -->.*?<!-- /seo:structured-data -->',
        "", head_body, flags=re.S)
    head_body = re.sub(
        r'\s*<script type="application/ld\+json"[^>]*>.*?</script>',
        "", head_body, flags=re.S)

    url = f"{ORIGIN}/{ROUTE}"
    # og:image and the alts are placeholders; seo_head.py rewrites both from
    # scripts/seo/pages.json, which is the one place a slug is declared.
    replacements = {
        r"<title>[^<]*</title>": f"<title>{_esc(TITLE)}</title>",
        r'(<meta name="description" content=")[^"]*(")': DESCRIPTION,
        r'(<link rel="canonical" href=")[^"]*(")': url,
        r'(<meta property="og:url" content=")[^"]*(")': url,
        r'(<meta property="og:title" content=")[^"]*(")': TITLE,
        r'(<meta property="og:description" content=")[^"]*(")': DESCRIPTION,
        r'(<meta name="twitter:title" content=")[^"]*(")': TITLE,
        r'(<meta name="twitter:description" content=")[^"]*(")': DESCRIPTION,
    }
    for pattern, value in replacements.items():
        if pattern.startswith("<title>"):
            head_body, n = re.subn(pattern, value, head_body, count=1)
        else:
            head_body, n = re.subn(
                pattern, lambda m: m.group(1) + _esc(value) + m.group(2),
                head_body, count=1)
        if n != 1:
            raise SystemExit(
                f"{SHELL_SOURCE}: expected exactly one match for {pattern!r}, got {n}. "
                "The shell page's head changed shape; update this generator.")
    return head_body, suffix


# ── the body ─────────────────────────────────────────────────────────────────

def _input_row(field) -> str:
    suffix = {"percent": "%", "dollars per hour": "$ / hour"}.get(field.unit, field.unit)
    step = ("1" if field.step == int(field.step) else str(field.step))
    default = (f"{field.default:.0f}" if field.default == int(field.default)
               else f"{field.default:g}")
    return f"""        <div class="calc-field">
          <label for="in-{field.name}">{_esc(field.label)}</label>
          <div class="calc-input">
            <input type="number" id="in-{field.name}" name="{field.name}"
                   value="{default}" min="{field.minimum:g}" max="{field.maximum:g}"
                   step="{step}" inputmode="decimal"
                   aria-describedby="help-{field.name}"/>
            <span class="calc-unit" aria-hidden="true">{_esc(suffix)}</span>
          </div>
          <p class="calc-help" id="help-{field.name}">{_esc(field.help)}</p>
        </div>"""


def _output_row(field, headline: bool) -> str:
    cls = "calc-out calc-out-headline" if headline else "calc-out"
    return f"""        <div class="{cls}">
          <dt>{_esc(field.label)}</dt>
          <dd><output id="out-{field.name}" for="{' '.join('in-' + i.name for i in INPUTS)}">&mdash;</output>
            <span class="calc-illustrative">illustrative, not measured</span></dd>
        </div>"""


def script() -> str:
    """The browser's copy of `estimate()`, emitted from the model's constants."""
    places = json.dumps({f.name: f.places for f in FIELDS})
    money = json.dumps({f.name: f.money for f in FIELDS})
    input_names = json.dumps([i.name for i in INPUTS])
    field_names = json.dumps([f.name for f in FIELDS])
    return f"""<script>
/* Generated by scripts/build_impersonation_calculator.py from
   src/impersonation_cost.py. Do not edit here: edit the model and rebuild.
   The arithmetic below is the same four multiplications the Python model
   performs, and tests/test_impersonation_calculator_page.py fails if this
   page stops matching a fresh render of the model. */
(function () {{
  var MINUTES_PER_HOUR = {MINUTES_PER_HOUR}, MONTHS_PER_YEAR = {MONTHS_PER_YEAR};
  var inputs = {input_names}.map(function (n) {{
    return document.getElementById('in-' + n);
  }});
  var places = {places}, money = {money};
  var form = document.getElementById('calc');
  if (!form || inputs.some(function (el) {{ return !el; }})) return;

  function value(el) {{
    var n = parseFloat(el.value);
    return isFinite(n) ? n : 0;
  }}

  function write(name, n) {{
    var el = document.getElementById('out-' + name);
    if (!el) return;
    var text = n.toLocaleString('en-US', {{
      minimumFractionDigits: places[name], maximumFractionDigits: places[name]
    }});
    el.textContent = money[name] ? '$' + text : text;
  }}

  function recompute() {{
    var calls = value(inputs[0]);
    var minutesEach = value(inputs[1]);
    var share = value(inputs[2]) / 100;   /* the page collects a percentage */
    var rate = value(inputs[3]);
    /* Out of range is shown as nothing rather than as a number: the Python
       model raises on these, and a page that quietly computed them would put
       a figure on screen that no reading of the inputs supports. */
    if (calls < 0 || minutesEach < 0 || share < 0 || share > 1 || rate < 0) {{
      {field_names}.forEach(function (n) {{
        var el = document.getElementById('out-' + n);
        if (el) el.textContent = '\\u2014';
      }});
      return;
    }}
    var undisclosed = calls * share;
    var minutes = undisclosed * minutesEach;
    var hours = minutes / MINUTES_PER_HOUR;
    var monthly = hours * rate;
    write('undisclosed_calls_per_month', undisclosed);
    write('hold_minutes_per_month', minutes);
    write('hold_hours_per_month', hours);
    write('monthly_cost', monthly);
    write('annual_cost', monthly * MONTHS_PER_YEAR);
  }}

  form.addEventListener('input', recompute);
  form.addEventListener('submit', function (e) {{ e.preventDefault(); recompute(); }});
  var reset = document.getElementById('calc-reset');
  if (reset) reset.addEventListener('click', function () {{
    inputs.forEach(function (el) {{ el.value = el.defaultValue; }});
    recompute();
  }});
  recompute();
}})();
</script>"""


ACTS = 4


def _act(index: int, slug: str, kicker: str, heading: str, inner: str) -> str:
    return f"""      <section class="act" id="{slug}" aria-labelledby="{slug}-h">
        <div class="act-head">
          <div>
            <p class="section-kicker">{_esc(kicker)}</p>
            <h2 id="{slug}-h">{_esc(heading)}</h2>
          </div>
          <span class="act-index">{index:02d} / {ACTS:02d}</span>
        </div>
        <div class="act-body">
{inner}
        </div>
      </section>"""


SECTIONS = (
    ("assumptions", "Inputs", "Your assumptions"),
    ("implies", "Outputs", "What that implies"),
    ("arithmetic", "Method", "How the figures are worked out"),
    ("limits", "Boundaries", "What this does not show"),
)


def body() -> str:
    inputs = "\n".join(_input_row(f) for f in INPUTS)
    outputs = "\n".join(
        _output_row(f, headline=(f.name == "annual_cost")) for f in FIELDS)
    rail = "\n".join(
        f'            <li><a href="#{slug}"><span>{_esc(heading)}</span></a></li>'
        for slug, _, heading in SECTIONS)

    act_assumptions = f"""          <form id="calc" class="calc-form" novalidate>
            <div class="calc-fields">
{inputs}
            </div>
            <p class="calc-actions">
              <button type="button" id="calc-reset" class="btn btn-ghost">
                Reset to the placeholder numbers
              </button>
            </p>
          </form>
          <p class="calc-note">
            The four starting values are round placeholders, chosen to show the
            arithmetic working. They are not estimates of any real call centre,
            and this project has not surveyed one.
          </p>"""

    act_implies = f"""          <dl class="calc-outputs">
{outputs}
          </dl>
          <noscript>
            <p class="callout" role="note">The arithmetic runs in the browser, so
            the figures above need JavaScript. The formula is written out below;
            it is four multiplications and you can do it on paper.</p>
          </noscript>
          <p class="calc-note calc-note-strong">{_esc(DISCLAIMER)}</p>"""

    act_arithmetic = f"""          <p>Four multiplications, in this order:</p>
          <ol class="calc-steps">
            <li>Inbound calls a month &times; assumed undisclosed share
                = calls from undisclosed agents.</li>
            <li>Those calls &times; average hold time = hold minutes a month.</li>
            <li>Hold minutes &divide; {MINUTES_PER_HOUR} = staffed hours a month.</li>
            <li>Staffed hours &times; loaded cost of a staffed hour
                = handle-time cost a month; &times; {MONTHS_PER_YEAR} for the year.</li>
          </ol>
          <p>
            The fractional call count is kept rather than rounded. A share of a
            volume is legitimately fractional, and rounding it to a whole call
            partway through would give the result a precision the assumption has
            not got.
          </p>
          <p>
            The same arithmetic is implemented once, in
            <code>src/impersonation_cost.py</code>, and this page is generated
            from it, so the figures on screen are the figures its tests check.
          </p>"""

    act_limits = """          <ul class="calc-limits">
            <li><strong>It is not a saving.</strong> The hold time is spent
              whether or not the caller discloses itself. Disclosure changes who
              your staff know they are speaking to, and what the call is allowed
              to cover; it does not shorten the queue. Any figure here read as
              &ldquo;what disclosure would save us&rdquo; has been read wrong.</li>
            <li><strong>It is not a measurement.</strong> NHID-Clinical is an open
              research project and reference implementation. It has run no pilot
              on live payer traffic, so it has no observed share of undisclosed
              callers to offer you, and it does not supply one here.</li>
            <li><strong>It does not compare vendors.</strong> No product,
              platform or supplier is ranked, scored or named on this page.</li>
            <li><strong>It is not a return-on-investment case.</strong> There is
              no price, no payback period and no claim about what any control
              costs or returns.</li>
          </ul>
          <p>
            What the project does have is the open control set and its
            conformance tests. <a href="/specification.html">The specification</a>
            states the controls; <a href="/developers.html">the developer
            pages</a> show the reference implementation;
            <a href="/shadow-evaluation-guide.html">the shadow-evaluation
            guide</a> is how an organisation can measure its own traffic rather
            than borrow an assumption from this page.
          </p>"""

    bodies = (act_assumptions, act_implies, act_arithmetic, act_limits)
    acts = "\n".join(
        _act(i + 1, slug, kicker, heading, inner)
        for i, ((slug, kicker, heading), inner) in enumerate(zip(SECTIONS, bodies)))

    return f"""<main id="main" class="scope-note page-doc">
  <section class="inner-hero hero-band" aria-labelledby="page-h">
    <div class="container hero-grid">
      <div>
        <div class="crumbs"><a href="/">Home</a><span class="sep">/</span><span>Impersonation handle-time</span></div>
        <p class="eyebrow meta-label">Illustrative calculator</p>
        <h1 class="reveal page-heading" id="page-h">{_esc(HEADLINE)}</h1>
        <p class="lede reveal lede-text">
          Nobody can currently count the automated callers that never say they
          are automated, so nobody can price them either. This page does the
          arithmetic from <em>your</em> assumptions instead: change any of the
          four numbers and every figure below changes with it.
        </p>
        <ul class="hero-meta reveal">
          <li><b>Inputs</b><span>Four, all yours to change</span></li>
          <li><b>Basis</b><span>Your assumptions</span></li>
          <li><b>Measurement</b><span>None</span></li>
          <li><b>Stage</b><span>Research</span></li>
        </ul>
      </div>
      <aside class="hero-instrument-card reveal" aria-label="Before you read a number">
        <div class="card-head"><b>Before you read a number</b><span>What this page is</span></div>
        <dl>
          <dt>Is</dt><dd>Arithmetic on four numbers you supply</dd>
          <dt>Is not</dt><dd>A saving, a measurement, or a comparison of suppliers</dd>
          <dt>Defaults</dt><dd>Round placeholders, not estimates of any real call centre</dd>
        </dl>
        <p class="calc-disclaimer">{_esc(DISCLAIMER)}</p>
      </aside>
    </div>
  </section>

  <section class="page-section band-paper">
    <div class="container doc">
      <nav class="doc-rail" aria-label="Sections of this page">
        <details class="doc-rail-fold" open>
          <summary class="doc-rail-label">Contents</summary>
          <ol>
{rail}
          </ol>
        </details>
      </nav>
      <div class="doc-body">
{acts}
      </div>
    </div>
  </section>
{script()}
"""


def _seo_head():
    """`scripts/seo/seo_head.py`, loaded by path (the directory is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "seo_head", ROOT / "scripts" / "seo" / "seo_head.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render() -> str:
    """The finished page, including the head `seo_head.py` would give it.

    Two generators own parts of this one file: this script owns the body and
    the page-specific meta, and `scripts/seo/seo_head.py` owns the og:image,
    the alt text and the JSON-LD graph for every published route. If this
    script stopped at its own output, `--check` here would report the page
    stale the moment `seo_head.py` ran over it, and the two would take turns
    rewriting each other. So this defers: it renders the shell and body, then
    hands the result to `seo_head.render()` for the route's row in
    `scripts/seo/pages.json`. Both checks then pass on the same bytes, and the
    SEO head stays defined in exactly one place.
    """
    prefix, suffix = shell()
    page = prefix + body() + suffix
    row = json.loads(
        (ROOT / "scripts" / "seo" / "pages.json").read_text(encoding="utf-8")
    )[ROUTE]
    return _seo_head().render(ROUTE, row, page)


def main(check: bool) -> int:
    path = ROOT / ROUTE
    new = render()
    if check:
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
        if old != new:
            print(f"STALE: {ROUTE} does not match a fresh render of "
                  "src/impersonation_cost.py "
                  "(run python scripts/build_impersonation_calculator.py)")
            return 1
        print(f"CALCULATOR PAGE PASS: {ROUTE} matches the model")
        return 0
    path.write_text(new, encoding="utf-8")
    print(f"  wrote {ROUTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
