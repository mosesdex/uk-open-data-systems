/* Dexter DCL — Open Data Systems. Progressive enhancement only. */
(function () {
  'use strict';

  /* ---------- Theme ---------- */
  var KEY = 'ddcl-theme';
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem(KEY);
    if (saved === 'dark' || saved === 'light') root.setAttribute('data-theme', saved);
  } catch (e) { /* storage blocked — system preference still applies */ }

  function currentTheme() {
    var explicit = root.getAttribute('data-theme');
    if (explicit) return explicit;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function paintToggle(btn) {
    var dark = currentTheme() === 'dark';
    btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    btn.innerHTML = dark
      ? '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
      : '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.5A8.5 8.5 0 1 1 9.5 3.5a6.8 6.8 0 0 0 11 11z"/></svg>';
  }

  var toggle = document.querySelector('.themetoggle');
  if (toggle) {
    paintToggle(toggle);
    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      paintToggle(toggle);
    });
  }

  /* ---------- Card filters (index) ---------- */
  var filters = document.querySelectorAll('[data-filter]');
  var cards = document.querySelectorAll('[data-themes]');

  if (filters.length && cards.length) {
    filters.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var val = btn.getAttribute('data-filter');
        filters.forEach(function (b) { b.classList.toggle('is-on', b === btn); });

        var shown = 0;
        cards.forEach(function (card) {
          var hit = val === 'all' || (card.getAttribute('data-themes') || '').split(' ').indexOf(val) !== -1;
          card.hidden = !hit;
          if (hit) shown++;
        });

        var count = document.querySelector('[data-filter-count]');
        if (count) {
          count.textContent = shown === cards.length
            ? shown + ' systems'
            : shown + ' of ' + cards.length + ' systems';
        }
      });
    });
  }

  /* ---------- TOC scrollspy (detail pages) ---------- */
  var tocLinks = document.querySelectorAll('.toc a[href^="#"]');
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var byId = {};
    var targets = [];

    tocLinks.forEach(function (link) {
      var id = link.getAttribute('href').slice(1);
      var el = document.getElementById(id);
      if (el) { byId[id] = link; targets.push(el); }
    });

    var visible = new Set();
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) visible.add(entry.target.id);
        else visible.delete(entry.target.id);
      });

      var firstVisible = targets.find(function (t) { return visible.has(t.id); });
      Object.keys(byId).forEach(function (id) {
        byId[id].classList.toggle('is-active', !!firstVisible && id === firstVisible.id);
      });
    }, { rootMargin: '-84px 0px -66% 0px', threshold: 0 });

    targets.forEach(function (t) { obs.observe(t); });
  }

  /* ---------- Year stamp ---------- */
  var y = document.querySelector('[data-year]');
  if (y) y.textContent = new Date().getFullYear();
})();
