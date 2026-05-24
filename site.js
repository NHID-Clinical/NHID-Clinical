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
      keywords: 'nhid clinical non-human identity disclosure healthcare voice standard ai automated impersonation data exchange b2b payer provider green lane',
      excerpt: 'NHID-Clinical v1.3 — Non-Human Identity Disclosure Standard for Healthcare Voice Workflows.'
    },
    {
      title: 'About',
      url: '/about.html',
      keywords: 'about origin impersonation latency problem healthcare voice ai payer provider tricare call center history background brianna baynard wgu cybersecurity',
      excerpt: 'NHID-Clinical defines a minimum control baseline for AI voice agents in B2B healthcare administrative workflows.'
    },
    {
      title: 'Conformance Test Suite',
      url: '/conformance.html',
      keywords: 'conformance tests cts idg-01 pdx-01 eit-01 pass fail deterministic disclosure identity verification escalation human atr-01',
      excerpt: 'Five deterministic pass/fail tests for NHID-Clinical v1.3 conformance: IDG-01, PDX-01, EIT-01, ATR-01.'
    },
    {
      title: 'Certification Framework',
      url: '/certification.html',
      keywords: 'certification l1 l2 l3 baseline operational enterprise tier attestation audit badge evidence production logs dfr disclosure failure rate',
      excerpt: 'L1 Baseline (self-attestation, free), L2 Operational (30+ days production evidence), L3 Enterprise (independent audit).'
    },
    {
      title: 'Download Specifications',
      url: '/specs/',
      keywords: 'download spec pdf nhid-clinical v1.3 nhid-auth v1.0 specification cc by 4.0 open fhir auditevent authorization attestation',
      excerpt: 'Download NHID-Clinical v1.3 Core Specification and NHID-Auth v1.0. Published CC BY 4.0.'
    },
    {
      title: 'News & Announcements',
      url: '/news.html',
      keywords: 'news release v1.3 nhid-auth community discord reddit nist 2025-0035 program open pilot announcement',
      excerpt: 'Specification releases, proposal updates, and community milestones.'
    },
    {
      title: 'Community',
      url: '/community.html',
      keywords: 'community discord reddit non-human auth contribution feedback technical compliance payer provider help contact',
      excerpt: 'Join the NHID-Clinical Discord and r/NonHumanAuth to help define the standard.'
    },
    {
      title: 'FAQ',
      url: '/faq.html',
      keywords: 'faq frequently asked questions who what why how certification cost hipaa tcpa nist biometrics mandatory volunteer impersonation latency tricare background',
      excerpt: 'Frequently asked questions about NHID-Clinical, certification, HIPAA, NIST connection, and more.'
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

  /* ── Active nav link ───────────────────────────────────────────────────── */
  var path  = window.location.pathname.replace(/\/$/, '') || '/';
  var links = document.querySelectorAll('.nav-links a, .mobile-nav a');
  links.forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0].replace(/\/$/, '') || '/';
    if (href === path || (href.length > 1 && path.startsWith(href))) {
      a.classList.add('is-active');
    }
  });
})();
