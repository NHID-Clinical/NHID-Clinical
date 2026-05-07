/* NHID-Clinical — shared site JS */
(function () {
  'use strict';

  /* ── Dark / light mode ─────────────────────────────────────────────────── */

  const html    = document.documentElement;
  const toggles = document.querySelectorAll('[data-theme-toggle]');

  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    localStorage.setItem('nhid-theme', theme);
    toggles.forEach(function (btn) {
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      const sun  = btn.querySelector('.icon-sun');
      const moon = btn.querySelector('.icon-moon');
      if (sun)  sun.style.display  = theme === 'dark'  ? 'block' : 'none';
      if (moon) moon.style.display = theme === 'light' ? 'block' : 'none';
    });
  }

  // Load saved or system preference
  var saved  = localStorage.getItem('nhid-theme');
  var system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  applyTheme(saved || system);

  toggles.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var current = html.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  });

  /* ── Mobile hamburger ──────────────────────────────────────────────────── */

  var hamburger  = document.getElementById('hamburger');
  var mobileMenu = document.getElementById('mobile-menu');

  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', function () {
      var open = mobileMenu.classList.toggle('open');
      hamburger.setAttribute('aria-expanded', open);
    });
  }

  /* ── Active nav link ───────────────────────────────────────────────────── */

  var path  = window.location.pathname.replace(/\/$/, '') || '/';
  var links = document.querySelectorAll('.nav-links a, .mobile-menu a');
  links.forEach(function (a) {
    var href = a.getAttribute('href').replace(/\/$/, '') || '/';
    if (href === path || (href !== '/' && href !== '/index.html' && path.startsWith(href))) {
      a.classList.add('active');
    }
  });
})();
