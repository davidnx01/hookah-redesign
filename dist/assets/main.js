/* =========================================================
   SMOKING HOOKAH — interakcie
   ========================================================= */
(() => {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Sticky hlavička ----------
     Scroll udalosti chodia v Safari veľmi husto. Zápis do DOM preto beží
     najviac raz za snímok a len vtedy, keď sa stav naozaj zmenil. */
  const header = document.getElementById('header');

  if (header) {
    let stuck = null;
    let ticking = false;

    const applyHeader = () => {
      ticking = false;
      const next = window.scrollY > 24;
      if (next === stuck) return;
      stuck = next;
      header.classList.toggle('is-stuck', next);
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(applyHeader);
    };

    applyHeader();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- Dym pauzuje na neaktívnej karte ---------- */
  const smokeLayers = document.querySelectorAll('.plume, .smoke__noise');

  document.addEventListener('visibilitychange', () => {
    const paused = document.visibilityState !== 'visible';
    smokeLayers.forEach((el) => {
      el.style.animationPlayState = paused ? 'paused' : '';
    });
  });

  /* ---------- Mobilné menu ---------- */
  const burger = document.getElementById('burger');
  const mobileNav = document.getElementById('mobileNav');

  if (burger && mobileNav) {
    const setMenu = (open) => {
      burger.setAttribute('aria-expanded', String(open));
      mobileNav.hidden = !open;
    };

    burger.addEventListener('click', () => {
      setMenu(burger.getAttribute('aria-expanded') !== 'true');
    });
    mobileNav.addEventListener('click', (e) => {
      if (e.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setMenu(false);
    });

    const desktop = window.matchMedia('(min-width: 1081px)');
    const syncMenu = (e) => { if (e.matches) setMenu(false); };
    desktop.addEventListener('change', syncMenu);
    syncMenu(desktop);
  }

  /* ---------- Otváracie hodiny v reálnom čase ----------
     Rozvrh je v assets/hours.js — jediné miesto, kde sa mení. */
  const hours = window.HOOKAH_HOURS;
  // Behové texty (stavová lišta) prináša stránka v window.RT — generuje ich build.py.
  // Slovníky sa tak do prehliadača vôbec nesťahujú.
  const tr = (text) => (window.RT && window.RT[text]) || text;

  if (hours) {
    const bar = document.getElementById('statusbar');
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    const note = document.getElementById('hoursNote');
    const closingMeta = document.getElementById('closingHours');
    const hoursList = document.getElementById('hoursList');

    const paint = () => {
      const now = new Date();
      const state = hours.status(now);

      if (bar) bar.classList.toggle('is-open', state.open);
      if (dot) dot.setAttribute('aria-hidden', 'true');

      /* Keď máme otvorené, netreba hneď pripomínať, kedy zatvárame. */
      const headline = state.open
        ? `<b>${tr('Otvorené teraz')}</b>`
        : `<b>${tr('Momentálne zatvorené')}</b> · ${tr('otvárame dnes o')} ${state.opensAt}`;

      if (text) text.innerHTML = headline;

      if (note) {
        note.textContent = state.open
          ? `${tr('Práve máme otvorené.')}`
          : `${tr('Práve máme zatvorené, otvárame dnes o')} ${state.opensAt}.`;
      }

      if (closingMeta) {
        closingMeta.textContent = state.open
          ? `${tr('Otvorené teraz')}`
          : `${tr('Zatvorené')} · ${tr('otvárame dnes o')} ${state.opensAt}`;
      }

      // zvýraznenie dnešného riadku v rozpise
      if (hoursList) {
        const today = String(now.getDay());
        hoursList.querySelectorAll('li').forEach((li) => {
          const days = (li.dataset.days || '').split(',');
          const isToday = days.includes(today);
          li.classList.toggle('is-today', isToday);
          if (isToday) li.dataset.today = tr('dnes');
        });
      }
    };

    paint();
    setInterval(paint, 60000);
  }

  /* ---------- Reveal pri scrollovaní ---------- */
  const revealables = document.querySelectorAll('.reveal');

  if (reducedMotion || !('IntersectionObserver' in window)) {
    revealables.forEach((el) => el.classList.add('is-in'));
  } else {
    const revealObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        obs.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.12 });

    revealables.forEach((el) => revealObserver.observe(el));
  }

  /* ---------- Počítadlá ---------- */
  const formatNumber = (value, decimals) =>
    decimals
      ? value.toFixed(decimals).replace('.', ',')
      : Math.round(value).toLocaleString('sk-SK').replace(/ /g, ' ');

  const runCount = (el) => {
    const target = parseFloat(el.dataset.to);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const suffix = el.dataset.suffix || '';
    const duration = 1600;
    const start = performance.now();

    const step = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = formatNumber(target * eased, decimals) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  };

  const counters = document.querySelectorAll('.count');

  if (reducedMotion || !('IntersectionObserver' in window)) {
    counters.forEach((el) => {
      el.textContent =
        formatNumber(parseFloat(el.dataset.to), parseInt(el.dataset.decimals || '0', 10)) +
        (el.dataset.suffix || '');
    });
  } else {
    const countObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        runCount(entry.target);
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.5 });

    counters.forEach((el) => countObserver.observe(el));
  }

  /* ---------- Aktívna položka v navigácii ---------- */
  const sections = [...document.querySelectorAll('main section[id]')];
  const navLinks = new Map(
    [...document.querySelectorAll('.nav a[href^="#"]')].map((a) => [a.getAttribute('href').slice(1), a])
  );

  if ('IntersectionObserver' in window && navLinks.size) {
    const navObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const link = navLinks.get(entry.target.id);
        if (!link) return;
        if (entry.isIntersecting) {
          navLinks.forEach((el) => el.classList.remove('is-active'));
          link.classList.add('is-active');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });

    sections.forEach((section) => navObserver.observe(section));
  }

  /* ---------- Náhrada za nenačítané fotky ---------- */
  const markMissing = (img) => {
    const figure = img.closest('.shot');
    if (!figure) return;
    figure.dataset.alt = img.alt || 'Fotka';
    figure.classList.add('is-missing');
  };

  document.querySelectorAll('.shot img').forEach((img) => {
    img.addEventListener('error', () => markMissing(img));
    if (img.complete && img.naturalWidth === 0) markMissing(img);
  });

  /* ---------- Rok v pätičke ---------- */
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})();
