/* =========================================================
   OTVÁRACIE HODINY — jediný zdroj pravdy
   Nedeľa – Štvrtok   15:00 – 01:00 (zatvára sa nasledujúci deň)
   Piatok – Sobota    15:00 – 02:00 (zatvára sa nasledujúci deň)
   ========================================================= */
window.HOOKAH_HOURS = (() => {
  'use strict';

  const OPEN_HOUR = 15;

  /** Hodina zatvorenia pre zmenu, ktorá začala v daný deň (0 = nedeľa). */
  const closingHour = (day) => (day === 5 || day === 6 ? 2 : 1);

  const pad = (n) => String(n).padStart(2, '0');
  const fmt = (hour) => `${pad(hour)}:00`;

  /**
   * Stav podniku v danom okamihu.
   * Zmena presahuje polnoc, takže sa vyhodnocuje aj zmena z predchádzajúceho dňa.
   */
  const status = (now = new Date()) => {
    const day = now.getDay();
    const hour = now.getHours();

    // ešte beží zmena, ktorá začala včera
    const yesterday = (day + 6) % 7;
    const yesterdayClose = closingHour(yesterday);

    if (hour < yesterdayClose) {
      return { open: true, closesAt: fmt(yesterdayClose), todayRange: rangeFor(day) };
    }

    if (hour >= OPEN_HOUR) {
      return { open: true, closesAt: fmt(closingHour(day)), todayRange: rangeFor(day) };
    }

    return { open: false, opensAt: fmt(OPEN_HOUR), todayRange: rangeFor(day) };
  };

  /** Textový rozsah zmeny začínajúcej v daný deň. */
  function rangeFor(day) {
    return `${fmt(OPEN_HOUR)} – ${fmt(closingHour(day))}`;
  }

  return { status, rangeFor, OPEN_HOUR, closingHour };
})();
