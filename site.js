/* NHID-Clinical — shared site JS */
(function () {
  'use strict';

  /* ── Mobile menu panel ─────────────────────────────────────────────────── */
  var menu   = document.getElementById('mobile-site-menu');
  var button = document.querySelector('.menu-button');

  if (menu && button) {
    var closeTargets = menu.querySelectorAll('[data-menu-close]');

    function openMenu() {
      menu.hidden = false;
      document.body.style.overflow = 'hidden';
      button.setAttribute('aria-expanded', 'true');
      var firstLink = menu.querySelector('a');
      if (firstLink) firstLink.focus();
    }

    function closeMenu() {
      menu.hidden = true;
      document.body.style.overflow = '';
      button.setAttribute('aria-expanded', 'false');
      button.focus();
    }

    button.addEventListener('click', function () {
      if (menu.hidden) openMenu(); else closeMenu();
    });

    closeTargets.forEach(function (t) { t.addEventListener('click', closeMenu); });
    menu.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', closeMenu); });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !menu.hidden) closeMenu();
    });
  }

  /* ── Active nav link ───────────────────────────────────────────────────── */
  var path  = window.location.pathname.replace(/\/$/, '') || '/';
  var links = document.querySelectorAll('.nav-links a, .mobile-menu-card a');
  links.forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0].replace(/\/$/, '') || '/';
    if (href === path || (href.length > 1 && path.startsWith(href))) {
      a.classList.add('is-active');
    }
  });
})();
