/* NHID-Clinical — shared site JS */
(function () {
  'use strict';

  /* ── Dark mode ─────────────────────────────────────────────────────────── */
  function syncThemeImages(theme) {
    document.querySelectorAll('.theme-img-light').forEach(function (img) {
      img.style.display = theme === 'dark' ? 'none' : 'block';
    });
    document.querySelectorAll('.theme-img-dark').forEach(function (img) {
      img.style.display = theme === 'dark' ? 'block' : 'none';
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('nhid-theme', theme); } catch (e) {}
    document.querySelectorAll('.mobile-theme-label').forEach(function (el) {
      el.textContent = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    });
    syncThemeImages(theme);
  }

  /* Set correct images on initial load */
  syncThemeImages(document.documentElement.getAttribute('data-theme') || 'light');

  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') || 'light';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  });

  /* ── Mobile navigation drawer ─────────────────────────────────────────── */
  var mobileNav   = document.getElementById('mobile-nav');
  var navBackdrop = document.getElementById('nav-backdrop');
  var menuBtn     = document.querySelector('.menu-button');

  function openDrawer() {
    if (!mobileNav) return;
    mobileNav.classList.add('open');
    if (navBackdrop) navBackdrop.classList.add('open');
    document.body.style.overflow = 'hidden';
    if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
  }

  function closeDrawer() {
    if (!mobileNav) return;
    mobileNav.classList.remove('open');
    if (navBackdrop) navBackdrop.classList.remove('open');
    document.body.style.overflow = '';
    if (menuBtn) { menuBtn.setAttribute('aria-expanded', 'false'); menuBtn.focus(); }
  }

  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      if (mobileNav && mobileNav.classList.contains('open')) closeDrawer(); else openDrawer();
    });
  }

  if (navBackdrop) navBackdrop.addEventListener('click', closeDrawer);

  if (mobileNav) {
    mobileNav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeDrawer);
    });
  }

  /* ── Search ────────────────────────────────────────────────────────────── */
  var SEARCH_INDEX = [
    {
      title: 'Home',
      url: '/',
      keywords: 'nhid clinical non-human identity disclosure healthcare voice standard ai automated impersonation data exchange b2b payer provider behavioral baseline',
      excerpt: 'NHID-Clinical — open proposal for AI voice agent disclosure, escalation, and audit trace in B2B healthcare voice workflows.'
    },
    {
      title: 'About',
      url: '/about.html',
      keywords: 'about origin impersonation latency problem healthcare voice ai payer provider call center history background brianna baynard open proposal',
      excerpt: 'NHID-Clinical defines a minimum behavioral baseline for AI voice agents in B2B healthcare administrative workflows.'
    },
    {
      title: 'Governance Simulator',
      url: '/governance-simulator.html',
      keywords: 'governance simulator policy engine playground idg-01 dbc-01 eit-01 atr-01 test scenario synthetic call evaluation interactive',
      excerpt: 'Test NHID-Clinical v1.3 controls against synthetic call scenarios in real time — no setup required.'
    },
    {
      title: 'For Payers',
      url: '/for-payers.html',
      keywords: 'payers shadow evaluation pilot 90 day baseline operations call center ai voice agent transparency vendor assessment',
      excerpt: 'A starting point for payer operations teams evaluating AI voice agent transparency — shadow mode, no vendor changes required.'
    },
    {
      title: 'Specification',
      url: '/specification.html',
      keywords: 'specification v1.3 controls idg-01 dbc-01 eit-01 atr-01 event schema conformance test suite policy engine open source',
      excerpt: 'The NHID-Clinical v1.3 specification: four controls, the event schema, and the machine-readable conformance test suite.'
    },
    {
      title: 'Developers',
      url: '/developers.html',
      keywords: 'developers technical reference implementation api policy engine fastapi twilio voice webhook audit log event schema github open source',
      excerpt: 'Technical reference for the NHID-Clinical reference implementation: architecture, API, event schema, and failure injection harness.'
    },
    {
      title: 'Regulatory Alignment',
      url: '/regulatory-alignment.html',
      keywords: 'regulatory alignment cms-0057-f macpac doj fca state ai laws nist hipaa compliance mapping controls federal mandate',
      excerpt: 'How NHID-Clinical controls map to CMS-0057-F, MACPAC 2026, DOJ FCA enforcement, and state AI laws.'
    },
    {
      title: 'Technical Stack',
      url: '/technical-stack.html',
      keywords: 'technical stack trust layers stir shaken nhid-clinical nhid-auth voice carrier payer system five-layer architecture',
      excerpt: 'The five-layer trust stack for B2B healthcare voice AI — from carrier to payer system.'
    },
    {
      title: 'Shadow Evaluation Guide',
      url: '/shadow-evaluation-guide.html',
      keywords: 'shadow evaluation guide 90 day behavioral baseline payer operations ai voice agent disclosure escalation audit no cost observe only',
      excerpt: 'A structured 90-day process for payers to establish a behavioral baseline for incoming AI voice calls — no vendor changes required.'
    },
    {
      title: 'Evidence Pack',
      url: '/evidence-pack.html',
      keywords: 'evidence pack technical proof deterministic guarantees failure trace idg-01 audit readiness risk register procurement enterprise evaluation',
      excerpt: 'System behavior guarantees, anonymized failure trace example, and audit readiness model for the NHID-Clinical reference implementation.'
    },
    {
      title: 'Conformance Test Suite',
      url: '/conformance.html',
      keywords: 'conformance tests cts idg-01 dbc-01 eit-01 atr-01 pass fail deterministic disclosure identity escalation human audit',
      excerpt: 'Deterministic pass/fail tests for NHID-Clinical v1.3 conformance.'
    },
    {
      title: 'Community',
      url: '/community.html',
      keywords: 'community discord reddit contribution feedback technical compliance payer provider help contact get involved',
      excerpt: 'Join the NHID-Clinical community to give feedback and help shape the next version of the proposal.'
    },
    {
      title: 'FAQ',
      url: '/faq.html',
      keywords: 'faq frequently asked questions who what why how cost hipaa tcpa nist mandatory volunteer impersonation latency background',
      excerpt: 'Frequently asked questions about NHID-Clinical, the scope, HIPAA, NIST, and how to get involved.'
    }
  ];

  var searchToggle  = document.getElementById('search-toggle');
  var searchOverlay = document.getElementById('search-overlay');
  var searchInput   = document.getElementById('search-input');
  var searchResults = document.getElementById('search-results');
  var searchClose   = document.getElementById('search-close');

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function highlight(text, query) {
    if (!query) return escapeHtml(text);
    var re = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    return escapeHtml(text).replace(re, '<mark>$1</mark>');
  }

  function doSearch(query) {
    if (!searchResults) return;
    query = (query || '').trim().toLowerCase();
    searchResults.innerHTML = '';
    if (!query) return;
    var results = SEARCH_INDEX.filter(function (item) {
      return (item.title + ' ' + item.keywords + ' ' + item.excerpt)
        .toLowerCase().indexOf(query) !== -1;
    });
    if (!results.length) {
      searchResults.innerHTML = '<p class="search-empty">No results for “' + escapeHtml(query) + '”</p>';
      return;
    }
    results.forEach(function (item) {
      var a = document.createElement('a');
      a.className = 'search-result-item';
      a.href = item.url;
      a.innerHTML =
        '<span class="search-result-title">' + highlight(item.title, query) + '</span>' +
        '<span class="search-result-excerpt">' + highlight(item.excerpt, query) + '</span>';
      a.addEventListener('click', closeSearch);
      searchResults.appendChild(a);
    });
  }

  function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.hidden = false;
    if (searchInput) { searchInput.focus(); searchInput.select(); }
  }

  function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.hidden = true;
    if (searchInput) searchInput.value = '';
    if (searchResults) searchResults.innerHTML = '';
  }

  if (searchToggle) {
    searchToggle.addEventListener('click', function () {
      if (!searchOverlay) return;
      if (searchOverlay.hidden) openSearch(); else closeSearch();
    });
  }
  if (searchClose) searchClose.addEventListener('click', closeSearch);
  if (searchInput) searchInput.addEventListener('input', function () { doSearch(this.value); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (searchOverlay && !searchOverlay.hidden) { closeSearch(); return; }
      if (mobileNav && mobileNav.classList.contains('open')) closeDrawer();
    }
  });

  /* ── Dropdown nav ──────────────────────────────────────────────────────── */
  document.querySelectorAll('.nav-dropdown-trigger').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var dropdown = btn.closest('.nav-dropdown');
      var isOpen = dropdown.classList.contains('is-open');
      document.querySelectorAll('.nav-dropdown.is-open').forEach(function (d) {
        d.classList.remove('is-open');
        var t = d.querySelector('.nav-dropdown-trigger');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        dropdown.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  document.addEventListener('click', function () {
    document.querySelectorAll('.nav-dropdown.is-open').forEach(function (d) {
      d.classList.remove('is-open');
      var t = d.querySelector('.nav-dropdown-trigger');
      if (t) t.setAttribute('aria-expanded', 'false');
    });
  });

  /* ── Active nav link ───────────────────────────────────────────────────── */
  var path  = window.location.pathname.replace(/\/$/, '') || '/';
  var links = document.querySelectorAll('.nav-links a, .mobile-nav a');
  links.forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0].replace(/\/$/, '') || '/';
    if (href === path || (href.length > 1 && path.startsWith(href))) {
      a.classList.add('is-active');
    }
  });
  document.querySelectorAll('.nav-dropdown').forEach(function (dropdown) {
    if (dropdown.querySelector('a.is-active')) {
      var trigger = dropdown.querySelector('.nav-dropdown-trigger');
      if (trigger) trigger.classList.add('is-active');
    }
  });
})();

/* ── ElevenLabs Conversational AI widget (Nadine) ─────────────────────── */
(function () {
  var s = document.createElement('script');
  s.src = 'https://elevenlabs.io/convai-widget/index.js';
  s.async = true;
  document.head.appendChild(s);

  var w = document.createElement('elevenlabs-convai');
  w.setAttribute('agent-id', 'agent_4001krn32nmwe5t8mqzgee0w84rj');
  document.body.appendChild(w);
})();
