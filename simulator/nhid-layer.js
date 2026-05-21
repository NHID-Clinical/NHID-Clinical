(function () {
  'use strict';

  // ── EU reference softening ────────────────────────────────
  // Replace EU AI Act-specific strings with neutral US-framing
  // after each React render pass.
  var REPLACEMENTS = [
    [/Article\s+14\s+[Oo]versight\s+[Ss]imulator/g, 'Human Oversight Simulator'],
    [/\bArticle\s+14\b/g,              'Human Oversight'],
    [/\bArt\.\s*14\b/g,                'Human Oversight'],
    [/\bArt\.\s*12\s*\/\s*19\s*\/\s*72\b/g, 'Audit / Logging / Incidents'],
    [/\bArt\.\s*12\b/g,                'Audit Logging'],
    [/\bArt\.\s*19\b/g,                'Logging Req.'],
    [/\bArt\.\s*72\b/g,                'Incident Reporting'],
    [/\bEU\s+AI\s+Act\b/gi,            'risk-based oversight framework'],
    [/\bEU\s+AI\s+Regulation\b/gi,     'risk-based oversight framework'],
  ];

  function softenNode(node) {
    if (node.nodeType === 3) {
      var v = node.nodeValue, u = v;
      for (var i = 0; i < REPLACEMENTS.length; i++) {
        u = u.replace(REPLACEMENTS[i][0], REPLACEMENTS[i][1]);
      }
      if (u !== v) node.nodeValue = u;
    } else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
      for (var j = 0; j < node.childNodes.length; j++) softenNode(node.childNodes[j]);
    }
  }

  function hideEULinks() {
    document.querySelectorAll(
      '#root a[href*="artificialintelligenceact"], #root a[href*="eur-lex.europa"]'
    ).forEach(function (a) {
      var li = a.closest('li');
      if (li) li.style.display = 'none';
      else a.style.display = 'none';
    });
  }

  // ── Layer classification keyword lists ────────────────────
  var L3 = [
    'article 12', 'article 14', 'article 19', 'article 72',
    'event metadata', 'retention', 'required log', 'use period',
    'post-market', 'capa', 'source article', 'regulatory-review',
    'reviewer id', 'event id', 'regulatory'
  ];

  var L2 = [
    'autonomy tier', 'autonomy score', 'model confidence', 'harm severity',
    'residual harm', 'pre-intervention', 'ai proposed', 'input classification',
    'run result', 'risk trigger', 'primary risk', 'automation-bias',
    'phi sensitivity', 'identity assurance', 'output / recommendation',
    'active triggers', 'model ', 'ai system', 'ai model'
  ];

  var isWorking = false;
  var debounce = null;

  // ── Classify one card element ─────────────────────────────
  function classify(card) {
    var h = card.querySelector(
      'h1,h2,h3,h4,[class*="font-semibold"],[class*="font-bold"],[class*="CardTitle"]'
    );
    var text = (h ? h.textContent : card.textContent.slice(0, 120)).toLowerCase();

    if (L3.some(function (k) { return text.indexOf(k) !== -1; })) return '3';
    if (L2.some(function (k) { return text.indexOf(k) !== -1; })) return '2';
    return '1';
  }

  // ── Inject toggle buttons after last card ─────────────────
  function buildToggles() {
    if (document.getElementById('nhid-controls')) return;

    var cards = document.querySelectorAll('.shadcn-card');
    if (!cards.length) return;

    var has2 = document.querySelector('[data-nl="2"]');
    var has3 = document.querySelector('[data-nl="3"]');
    if (!has2 && !has3) return;

    var wrap = document.createElement('div');
    wrap.id = 'nhid-controls';

    function makeBtn(label, layer) {
      var btn = document.createElement('button');
      btn.className = 'nhid-toggle';
      var open = document.body.getAttribute('data-nl' + layer) === '1';
      btn.textContent = open ? label.replace('▸', '▾') : label;
      btn.setAttribute('data-for', layer);
      btn.addEventListener('click', function () {
        var isOpen = document.body.getAttribute('data-nl' + layer) === '1';
        document.body.setAttribute('data-nl' + layer, isOpen ? '0' : '1');
        btn.textContent = isOpen ? label : label.replace('▸', '▾');
      });
      return btn;
    }

    if (has2) wrap.appendChild(makeBtn('View Analysis ▸', '2'));
    if (has3) wrap.appendChild(makeBtn('View Audit Log ▸', '3'));

    var last = cards[cards.length - 1];
    last.parentNode.insertBefore(wrap, last.nextSibling);
  }

  // ── Main pass ─────────────────────────────────────────────
  function run() {
    if (isWorking) return;
    isWorking = true;

    var old = document.getElementById('nhid-controls');
    if (old) old.remove();

    // Soften EU references in rendered text
    var root = document.getElementById('root');
    if (root) softenNode(root);
    hideEULinks();

    document.querySelectorAll('.shadcn-card').forEach(function (card) {
      card.setAttribute('data-nl', classify(card));
    });

    document.body.setAttribute('data-nhid-ready', '1');
    buildToggles();
    isWorking = false;
  }

  // ── MutationObserver — reapply after React re-renders ─────
  function observe() {
    var root = document.getElementById('root');
    if (!root) return;
    new MutationObserver(function (mutations) {
      if (isWorking) return;
      var relevant = mutations.some(function (m) {
        return !m.target.id || m.target.id !== 'nhid-controls';
      });
      if (!relevant) return;
      clearTimeout(debounce);
      debounce = setTimeout(run, 250);
    }).observe(root, { childList: true, subtree: true });
  }

  // ── Bootstrap ─────────────────────────────────────────────
  function boot() {
    var root = document.getElementById('root');
    if (!root || !root.children.length) return setTimeout(boot, 150);
    run();
    observe();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 400); });
  } else {
    setTimeout(boot, 400);
  }
})();
