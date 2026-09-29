# Smoking Hookah — web

> [!danger] NENASADZOVAŤ, kým to David neodovzdá
> Web je technicky hotový a otestovaný, ale **nenahadzuje sa live**.
> Nepushovať do `hookah-web`, nenasadzovať na Vercel, nemeniť doménu.
> Čaká sa na fotografie a na cenu sandwichov a panini.

Statický web bez frameworku. Slovenčina sa edituje ručne v `src/`,
ruská a ukrajinská verzia sa z nej generujú.

## Štruktúra

```
src/                 zdroj — TU SA EDITUJE
  index.html         úvod
  vodne-fajky.html   vodné fajky
  menu.html          menu
  skola-majstra.html kurzy
  kontakt.html       kontakt
  assets/            CSS, JS, logo, ikony, náhľadový obrázok
  assets/img-source/ originály fotiek (nenasadzujú sa)
  assets/img/        vygenerované varianty + manifest.json

i18n/
  ru.json            ruský slovník
  uk.json            ukrajinský slovník

optimize_images.py   spracovanie fotografií
build.py             generátor stránok
vercel.json          konfigurácia nasadenia
tools/               nahlad.py, stiahnut-fotky.sh
dist/                VÝSTUP — toto sa nasadzuje na server
```

## Zostavenie

```bash
python3 optimize_images.py   # len keď pribudli alebo sa zmenili fotky
python3 build.py
```

Potrebuje Python 3 a dve knižnice:

```bash
pip3 install --upgrade beautifulsoup4 Pillow
```

Vygeneruje `dist/` — 15 stránok (5 × 3 jazyky), `sitemap.xml`, `robots.txt`,
`site.webmanifest` a `404.html`. Nasadzuje sa obsah priečinka `dist/`.

## Fotografie

Originály sa hádžu do `src/assets/img-source/` tak, ako prišli z foťáku —
neorezané, nezmenšené, v plnom rozlíšení. Zvyšok spraví skript:

```bash
python3 optimize_images.py           # spracuje len to, čo pribudlo
python3 optimize_images.py --force   # pregeneruje všetko
```

Z každej fotky vyrobí päť šírok (480, 768, 1200, 1800, 2400 px) v troch
formátoch (AVIF, WebP, JPEG) a rozmazaný náhľad. Väčšie šírky než originál
preskočí; ak originál padne medzi kroky (napr. 1440 px), pridá aj jeho
natívnu šírku — inak by sa najväčšie miesto na stránke škálovalo nahor.

V HTML sa fotka píše ako obyčajný `<img>`, ktorý ukazuje na originál:

```html
<figure class="shot card__shot">
  <img src="assets/img-source/karta-fajky.jpg" alt="Prémiová vodná fajka">
</figure>
```

`build.py` z toho vyrobí kompletné `<picture>` so všetkými variantmi.
Zdroj tak zostáva čitateľný a otvoriteľný v prehliadači.

Voliteľné atribúty na `<img>`:

| atribút | význam |
|---|---|
| `data-priority` | fotka je nad ohybom — načíta sa prednostne, bez lazy loadingu |
| `data-sizes` | ako široko sa fotka zobrazuje, napr. `100vw` pre hero |

**Kvalita.** Nastavenie je zvolené tak, aby vernosť neklesla pod úroveň
JPEG 90. Merané cez SSIM, teda štrukturálnu podobnosť s originálom:

| formát | kvalita | SSIM |
|---|---|---|
| JPEG | 90 | 0,9936 |
| WebP | 92 | 0,9904 |
| AVIF | 85 | 0,9936 |

Čísla kvality nie sú medzi formátmi porovnateľné — každý kodek má vlastnú
stupnicu. AVIF 85 dosahuje rovnakú nameranú vernosť ako JPEG 90, ale
za polovičnú veľkosť. Nastavenie je v `optimize_images.py`, slovník `QUALITY`.

### Stiahnutie fotiek zo starého webu

Dvanásť fotiek sa zatiaľ načítava zo Strapi CDN. Stiahni ich k sebe:

```bash
bash tools/stiahnut-fotky.sh
python3 optimize_images.py
```

Potom v `src/*.html` prepíš `src="https://complete-unity-…/nieco.jpg"`
na `src="assets/img-source/nazov.jpg"`. Názvy sú v tom skripte.

## Nasadenie na Vercel

Web je statický. Na Verceli sa nič nebuilduje — `dist/` je v repozitári
a nasadzuje sa presne to, čo si otestoval lokálne.

### Prvé nastavenie projektu

Repozitár `hookah-web` bol Next.js. Pred prepnutím **odstráň** všetko, čo by
Vercel donútilo hľadať framework:

```
package.json  package-lock.json  next.config.js  next-env.d.ts
tsconfig.json  .next/  node_modules/  app/  pages/  public/  components/
```

Ak tam zostane `package.json`, Vercel deteguje Next.js a build spadne.

V nastaveniach projektu na Verceli:

| Položka | Hodnota |
|---|---|
| Framework Preset | **Other** |
| Build Command | *(prázdne)* |
| Output Directory | `dist` |
| Install Command | *(prázdne)* |

`vercel.json` v koreni repozitára nastaví zvyšok sám.

### Čo rieši vercel.json

**`cleanUrls: true`** — adresy bez prípony. Nový web tak beží na **presne tých
istých adresách ako starý**:

```
/            /menu       /vodne-fajky
/kontakt     /skola-majstra
```

Toto je dôležité. Google má tieto adresy zaindexované a bez toho by
po spustení vracali 404 a stratilo by sa doterajšie SEO.

**Presmerovanie `/drinky` → `/menu`** (301). Stránka drinkov zanikla, jej obsah
je v menu. Bez presmerovania by tá adresa vracala 404.

**Hlavičky** — CSS a JS sa cachujú na rok (v adrese majú `?v=` odtlačok obsahu,
takže pri zmene si prehliadač stiahne novú verziu), obrázky na 30 dní.
Plus bezpečnostné hlavičky.

### Postup pri zmene

```bash
python3 optimize_images.py   # len keď pribudli fotky
python3 build.py
python3 tools/nahlad.py      # http://localhost:8000 — overenie
git add -A && git commit -m "..." && git push
```

Vercel nasadí automaticky po pushnutí.

> [!warning] Lokálny náhľad nespúšťaj cez `dist/index.html`
> Odkazy smerujú na `/menu`, nie na `menu.html`. Otvorenie súboru z disku
> ich nerozchodí. Použi `python3 tools/nahlad.py` — správa sa rovnako ako Vercel.

### Pred prvým spustením

- [ ] Fotky: zostáva **6 šrafovaných rámov** (13 fotiek + 2 mapy osadené) + 12 fotiek
      chuťových mixov a ocenení, ktoré sa stále ťahajú zo Strapi
- [ ] **Fonty k nám:** `bash tools/stiahnut-fonty.sh` z normálneho terminálu.
      Kým to nebeží, `fonts.googleapis.com` sa načíta ešte PRED súhlasom
      a obchádza cookie lištu. Build to vypisuje ako varovanie.
- [ ] **Právne údaje** v `src/ochrana-osobnych-udajov.html` — tri `[DOPLNIŤ]`
      (obchodné meno, sídlo, IČO) a dátum účinnosti.
- [ ] **Právna kontrola** zásad ochrany osobných údajov.
- [ ] **V GA admin** uchovávanie údajov na 14 mesiacov, vypnúť Google Signals.
- [ ] Po nasadení skontrolovať `/menu`, `/vodne-fajky`, `/drinky` (musí presmerovať)
- [ ] Odoslať `https://hookah.sk/sitemap.xml` do Google Search Console

> [!caution] Strapi vypínaj až po stiahnutí fotiek
> 12 fotiek sa načítava z `complete-unity-….media.strapiapp.com`. Kým ich
> nestiahneš cez `tools/stiahnut-fotky.sh`, nový web na starom CMS závisí.

## Ako fungujú preklady

Slovenský text v `src/` je zároveň kľúčom do slovníka:

```json
{ "Prémiové vodné fajky": "Премиальные кальяны" }
```

Prvok sa preloží, ak má atribút `data-i18n`. Chýbajúci preklad nespadne —
zostane slovenský originál, čo je hneď vidieť.

**Keď zmeníš slovenský text**, zmeníš tým aj kľúč. Nový reťazec doplň
do oboch slovníkov, inak sa v RU a UA verzii zobrazí po slovensky.

**Keď pridáš nový text**, ktorý sa má prekladať, daj mu `data-i18n`
a pridaj ho do slovníkov.

Osem reťazcov pre stavovú lištu (napr. „Otvorené teraz") generuje JavaScript.
Sú v `build.py` v zozname `RUNTIME_KEYS` a vkladajú sa priamo do stránky
ako `window.RT`, takže sa slovníky do prehliadača vôbec nesťahujú.

## Otváracie hodiny

Jediné miesto, kde sa menia, je `src/assets/hours.js`:

```js
const OPEN_HOUR = 15;
const closingHour = (day) => (day === 5 || day === 6 ? 2 : 1);
```

Odtiaľ sa počíta stavová lišta aj zvýraznenie dnešného dňa v rozpise.
Schéma pre Google je v `build.py` vo funkcii `json_ld` — pri zmene hodín
uprav obe miesta.

## Nasadenie

Obsah `dist/` nahraj do koreňa domény. Web je statický, nepotrebuje Node,
PHP ani databázu. Nastav na serveri, aby chyba 404 vracala `/404.html`.

Pre Apache stačí do `.htaccess`:

```apache
ErrorDocument 404 /404.html
```

## Súhlas, cookies a Google Analytics

Meracie ID je `GA_ID` v `build.py`. Prázdny reťazec analytiku vypne celú
vrátane Consent Mode.

```
src/_suhlas.html        značkovanie lišty — build ho vkladá do každej stránky
src/assets/suhlas.js    správca súhlasu
build.py CONSENT_DEFAULT  Consent Mode v2, všetko denied, v hlavičke
```

**Pravidlo, ktoré sa nesmie porušiť:** „Prijať všetko“ a „Odmietnuť všetko“
zdieľajú triedu `.suhlas__btn` a nemajú ani jedno pravidlo navyše. Keby
odmietnutie vyzeralo slabšie alebo sa schovalo o úroveň nižšie, súhlas
prestáva byť slobodný a celá lišta je na nič.

`gtag.js` sa do stránky nevkladá, kým nie je súhlas — nie je to tak, že by
sa načítal a nič nerobil. Pri odvolaní sa `_ga*` cookies mažú.

Keď pribudne ďalšia kategória, zvýš `VERZIA` v `suhlas.js`. Uložené súhlasy
sa tým zneplatnia a ľudia sa spýtajú znova, čo je správne.

Po každej zmene textov spusti `python3 tools/oznac.py` — bez toho sa nové
reťazce zobrazia v ruskej a ukrajinskej verzii po slovensky.

## Pred nasadením

```bash
python3 build.py
python3 tools/kontrola.py     # musí prejsť bez chyby
```

`tools/kontrola.py` je brána. Kontroluje nedoplnené `[DOPLNIŤ]`, fonty
ťahané od Googlu, závislosť na starom Strapi, gtag mimo súhlasu, rozbité
odkazy, canonical, sitemap aj to, či všetkých šesť adries zo starého webu
niekde končí. Keď skončí nenulovým kódom, nenasadzuj — a je jedno, ako to
vyzerá inak.

Celý postup migrácie vrátane nastavení Vercelu a návratu späť je
v **[MIGRACIA.md](MIGRACIA.md)**.

## Čo ešte zostáva

1. **Fotografie** — 6 šrafovaných rámov čaká na skutočné zábery,
   rozmer je napísaný priamo v ráme. Nahraď `<figure class="ph">`
   za `<figure class="shot"><img ...></figure>` s rovnakým pomerom strán
   (`shot--sq` = 1:1, `shot--45` = 4:5, `card__shot` = 1:1).
   Chýbajú: bar pri príprave, panini, ovocná misa (Menu) · mixovanie
   príchutí, súťažná váza (Škola majstra) · ulica s orientačným bodom
   (Kontakt).

   Mapy sú hotové — obe stránky majú vložený Google Maps embed
   (`loading="lazy"`, jazyk popisiek rieši `localize_maps()`
   v `build.py`, na mobile berie dotyk až po kliknutí).
   Pozor: embed je tretia strana s cookies — ak pribudne cookie lišta,
   mapa patrí pod ňu.

   Fotka Alexa (`alex-majster.jpg`) je výnimka: rám má jej **natívny
   pomer 561/810**, nie zaokrúhlený, aby bol majster vidieť po celej
   výške bez orezu. Ak príde nový originál s iným pomerom, uprav aj
   `aspect-ratio` v `.shot--majster`.

2. **Fotky z CDN** — 12 fotiek sa načítava zo starého Strapi.
   Rieši to `bash tools/stiahnut-fotky.sh`, pozri kapitolu Fotografie.

3. **Cena sandwichov a panini** — jediná chýbajúca položka cenníka.
   Ostatné ceny sú prevzaté zo starého webu (modal na `/menu`) a sedia.

4. **Fonty** sa načítavajú z Google Fonts. Pre rýchlejšie načítanie
   ich stiahni k sebe:

   ```bash
   curl -H "User-Agent: Mozilla/5.0" \
     "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Poppins:wght@300;400;500;600&display=swap" \
     -o src/assets/fonts.css
   # stiahni .woff2 súbory, na ktoré sa fonts.css odkazuje, do src/assets/fonts/
   # prepíš v nej cesty a v build.py nahraď konštantu FONTS za "assets/fonts.css"
   ```

5. **Súradnice podniku** — do `build.py`, funkcia `json_ld`, sa dá doplniť
   presná poloha pre Google Maps:

   ```python
   'geo': {'@type': 'GeoCoordinates', 'latitude': 48.xxxx, 'longitude': 17.xxxx},
   ```

6. **Analytika** — pôvodný web mal Google Analytics `G-ZXHSQ5NP3J`.
   Ak ho vrátiš, pribudne povinnosť mať cookie lištu a stránku o ochrane
   osobných údajov. Web teraz neukladá žiadne cookies.
