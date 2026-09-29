/* Správca súhlasu — GDPR (nariadenie 2016/679) a § 109 zákona č. 452/2021 Z. z.
   o elektronických komunikáciách.

   Pravidlá, ktoré z toho plynú a sú tu zámerne dodržané:

   1. Pred súhlasom neodíde na tretiu stranu ani jeden request. Skript Google
      Analytics sa do stránky vôbec nevloží, mapa Google sa nenačíta.
   2. Odmietnuť musí byť rovnako ľahké ako prijať — obe tlačidlá sú na prvej
      vrstve, majú rovnakú triedu, veľkosť aj kontrast. Žiadne krížiky, ktoré
      by sa dali vykladať ako súhlas, a scrollovanie súhlas neudeľuje.
   3. Nič nie je predvolene zapnuté. Voliteľné kategórie štartujú vypnuté.
   4. Súhlas sa dá kedykoľvek odvolať — odkaz „Nastavenia cookies“ je
      v pätičke každej stránky.
   5. Súhlas sa ukladá aj s časom a verziou. Po 12 mesiacoch sa pýtame znova,
      a keď sa zmení verzia (pribudne kategória), tiež.

   Uloženie samotného súhlasu je nevyhnutné spracúvanie, na to sa súhlas
   nevyžaduje. Držíme ho v localStorage, takže neodchádza na server. */

(function () {
  'use strict';

  var KLUC = 'sh-suhlas';
  var VERZIA = 1;
  var PLATNOST = 365 * 24 * 60 * 60 * 1000;

  var lista = document.getElementById('suhlas');
  if (!lista) return;

  var volby = document.getElementById('suhlasVolby');
  var prijat = document.getElementById('suhlasPrijat');
  var odmietnut = document.getElementById('suhlasOdmietnut');
  var nastavenia = document.getElementById('suhlasNastavenia');
  var ulozit = document.getElementById('suhlasUlozit');
  var prepAnalytika = document.getElementById('suhlasAnalytika');
  var prepExterne = document.getElementById('suhlasExterne');

  function gtag() { (window.dataLayer = window.dataLayer || []).push(arguments); }

  /* ---------------------------------------------------------------- úložisko */

  function nacitaj() {
    try {
      var s = JSON.parse(localStorage.getItem(KLUC));
      if (!s || s.v !== VERZIA) return null;
      if (!s.ts || Date.now() - s.ts > PLATNOST) return null;
      return s;
    } catch (e) { return null; }
  }

  function uloz(analytika, externe) {
    var s = { v: VERZIA, ts: Date.now(), analytika: !!analytika, externe: !!externe };
    try { localStorage.setItem(KLUC, JSON.stringify(s)); } catch (e) {}
    return s;
  }

  /* ------------------------------------------------------------------ Google */

  function zapniAnalytiku() {
    if (!window.SH_GA || window.SH_GA_NACITANE) return;
    window.SH_GA_NACITANE = true;

    gtag('consent', 'update', { analytics_storage: 'granted' });

    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + window.SH_GA;
    document.head.appendChild(s);

    gtag('js', new Date());
    gtag('config', window.SH_GA);
  }

  function vypniAnalytiku() {
    gtag('consent', 'update', { analytics_storage: 'denied' });
    /* Po odvolaní súhlasu nesmú cookies zostať ležať v prehliadači. */
    var host = location.hostname;
    var domeny = ['', host, '.' + host, '.' + host.split('.').slice(-2).join('.')];
    document.cookie.split(';').forEach(function (c) {
      var meno = c.split('=')[0].trim();
      if (meno.indexOf('_ga') !== 0 && meno.indexOf('_gid') !== 0) return;
      domeny.forEach(function (d) {
        document.cookie = meno + '=; max-age=0; path=/' + (d ? '; domain=' + d : '');
      });
    });
  }

  /* -------------------------------------------------------------------- mapy */

  function vlozMapu(ram) {
    if (ram.querySelector('iframe')) return;
    var f = document.createElement('iframe');
    f.src = ram.getAttribute('data-map-src');
    f.title = ram.getAttribute('data-map-title') || '';
    f.loading = 'lazy';
    f.referrerPolicy = 'no-referrer-when-downgrade';
    f.allowFullscreen = true;
    ram.appendChild(f);
    ram.classList.add('map--nacitana');
  }

  function zapniMapy() {
    document.querySelectorAll('.map[data-map-src]').forEach(vlozMapu);
  }

  /* Kliknutie na samotnú náhradu je súhlas pre tú jednu mapu a pre toto
     načítanie stránky. Neukladá sa — kto chce mapu natrvalo, zapne si
     kategóriu v nastaveniach. */
  document.querySelectorAll('.map__tlacidlo').forEach(function (b) {
    b.addEventListener('click', function () {
      vlozMapu(b.closest('.map'));
    });
  });

  /* ------------------------------------------------------------------ lišta */

  function pouzi(s) {
    if (s.analytika) zapniAnalytiku(); else vypniAnalytiku();
    if (s.externe) zapniMapy();
  }

  function zobraz(nastavenieOtvorene) {
    var s = nacitaj();
    if (prepAnalytika) prepAnalytika.checked = !!(s && s.analytika);
    if (prepExterne) prepExterne.checked = !!(s && s.externe);
    prepniVolby(!!nastavenieOtvorene);
    lista.hidden = false;
    document.documentElement.classList.add('ma-suhlas');
    /* Fokus ide na nadpis, aby o lište vedel aj odčítavač obrazovky. */
    var nadpis = document.getElementById('suhlasNadpis');
    if (nadpis) { nadpis.setAttribute('tabindex', '-1'); nadpis.focus(); }
  }

  function skry() {
    lista.hidden = true;
    document.documentElement.classList.remove('ma-suhlas');
  }

  function prepniVolby(otvorene) {
    if (!volby) return;
    volby.hidden = !otvorene;
    if (nastavenia) nastavenia.hidden = otvorene;
    if (ulozit) ulozit.hidden = !otvorene;
    if (nastavenia) nastavenia.setAttribute('aria-expanded', otvorene ? 'true' : 'false');
  }

  function rozhodni(analytika, externe) {
    pouzi(uloz(analytika, externe));
    skry();
  }

  if (prijat) prijat.addEventListener('click', function () { rozhodni(true, true); });
  if (odmietnut) odmietnut.addEventListener('click', function () { rozhodni(false, false); });
  if (nastavenia) nastavenia.addEventListener('click', function () { prepniVolby(true); });
  if (ulozit) ulozit.addEventListener('click', function () {
    rozhodni(prepAnalytika && prepAnalytika.checked, prepExterne && prepExterne.checked);
  });

  /* Odvolanie súhlasu — odkaz v pätičke a kdekoľvek inde. */
  document.querySelectorAll('[data-suhlas-otvor]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); zobraz(true); });
  });

  /* ------------------------------------------------------------------ štart */

  var stav = nacitaj();
  if (stav) pouzi(stav); else zobraz(false);
})();
