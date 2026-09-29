/* =========================================================
   PREPÍNANIE JAZYKOV
   Slovenčina je priamo v HTML a slúži zároveň ako kľúč do slovníka.
   Vďaka tomu je slovník čitateľný a chýbajúci preklad nespadne —
   len sa zobrazí pôvodný slovenský text.

   Preklady: assets/i18n-ru.js, assets/i18n-uk.js
   Prvok sa preloží, ak má atribút data-i18n.
   ========================================================= */
window.I18N = (() => {
  'use strict';

  const STORAGE_KEY = 'hookah-lang';
  const DEFAULT = 'sk';

  const LANGS = {
    sk: { label: 'SK', htmlLang: 'sk', dict: null },
    ru: { label: 'RU', htmlLang: 'ru', dict: () => window.I18N_RU },
    uk: { label: 'UA', htmlLang: 'uk', dict: () => window.I18N_UK },
  };

  let current = DEFAULT;

  /* ---------- pomocné ---------- */

  const normalize = (s) => s.replace(/\s+/g, ' ').trim();

  const dictFor = (lang) => {
    const entry = LANGS[lang];
    return entry && entry.dict ? entry.dict() || {} : null;
  };

  /** Preloží reťazec do práve zvoleného jazyka. */
  const t = (text) => {
    const dict = dictFor(current);
    if (!dict) return text;
    return dict[normalize(text)] || text;
  };

  /* ---------- aplikácia na DOM ---------- */

  const nodes = () => document.querySelectorAll('[data-i18n], [data-i18n-content]');

  /** Slovenský originál si držíme priamo na prvku, aby sa dal vrátiť späť. */
  const sourceOf = (el, attr) => {
    const store = attr ? 'i18nSrcContent' : 'i18nSrc';
    if (el.dataset[store] === undefined) {
      el.dataset[store] = attr ? el.getAttribute('content') : el.innerHTML;
    }
    return el.dataset[store];
  };

  const apply = (lang) => {
    const dict = dictFor(lang);

    nodes().forEach((el) => {
      const isMeta = el.hasAttribute('data-i18n-content');
      const src = sourceOf(el, isMeta);
      const value = dict ? dict[normalize(src)] || src : src;

      if (isMeta) {
        el.setAttribute('content', value);
      } else if (el.innerHTML !== value) {
        el.innerHTML = value;
      }
    });

    document.documentElement.lang = LANGS[lang].htmlLang;

    document.querySelectorAll('[data-lang]').forEach((btn) => {
      btn.setAttribute('aria-pressed', String(btn.dataset.lang === lang));
    });

    // texty, ktoré vznikajú až v JS (stav otvorenia, rozpis hodín)
    document.dispatchEvent(new CustomEvent('languagechange', { detail: { lang } }));
  };

  const set = (lang) => {
    if (!LANGS[lang]) return;
    current = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* súkromné okno */ }
    apply(lang);
  };

  /* ---------- štart ---------- */

  const stored = (() => {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  })();

  const initial = LANGS[stored] ? stored : DEFAULT;

  const boot = () => {
    current = initial;
    apply(initial);

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-lang]');
      if (btn) set(btn.dataset.lang);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  return { t, set, get current() { return current; } };
})();
