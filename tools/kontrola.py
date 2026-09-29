#!/usr/bin/env python3
"""
Kontrola pred nasadením. Spusti po build.py a pred pushom:

    python3 build.py && python3 tools/kontrola.py

Vracia nenulový kód, keď niečo blokuje spustenie. Nič neopravuje —
len povie, čo nie je hotové. Zámerne sa pýta aj na veci, ktoré sa dajú
prehliadnuť (zvyšné [DOPLNIŤ], fonty od Googlu, závislosť na Strapi),
lebo presne tie sa inak dostanú na produkciu.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent.parent
DIST = ROOT / 'dist'
SRC = ROOT / 'src'

SITE = 'https://www.hookah.sk'

# adresy, ktoré má starý web a musia fungovať aj po migrácii
# (overené na živom webe 29. 9. 2026 — iné tam nie sú)
STARE_ADRESY = ['/', '/menu', '/drinky', '/vodne-fajky', '/skola-majstra', '/kontakt']

chyby = []
varovania = []


def chyba(text):
    chyby.append(text)


def varovanie(text):
    varovania.append(text)


def stranky():
    return sorted(p for p in DIST.rglob('*.html') if p.name != '404.html')


def cesta_pre(p):
    """Adresa stránky bez prípony a bez lomky na konci — presne v tom tvare,
    v akom ju podáva Vercel s cleanUrls a trailingSlash: false."""
    rel = p.relative_to(DIST).as_posix()
    rel = rel[:-len('index.html')] if rel.endswith('index.html') else rel[:-len('.html')]
    rel = rel.strip('/')
    return '/' + rel if rel else '/'


def norm_adresa(u):
    """Porovnávame adresy v jednom tvare, nech /ru a /ru/ nie sú dve veci."""
    u = u.split('#')[0].split('?')[0]
    return '/' + u.strip('/') if u.strip('/') else '/'


# ------------------------------------------------------------------ 1. build
if not DIST.exists() or not (DIST / 'index.html').exists():
    print('dist/ neexistuje — spusti najprv python3 build.py')
    sys.exit(1)

vsetky = stranky()
if len(vsetky) != 21:
    chyba(f'čakal som 21 stránok v dist/, našiel {len(vsetky)}')

# ---------------------------------------------------- 2. nedokončené miesta
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    for znacka in re.findall(r'\[DOPLNIŤ[^\]]*\]', t):
        chyba(f'{cesta_pre(p)}: nedoplnené miesto {znacka}')

# ----------------------------------------------------------- 3. tretie strany
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    if 'fonts.googleapis.com' in t or 'fonts.gstatic.com' in t:
        chyba(f'{cesta_pre(p)}: fonty sa ťahajú od Googlu — obchádza to súhlas. '
              'Spusti bash tools/stiahnut-fonty.sh')
        break
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    if 'strapiapp.com' in t:
        chyba(f'{cesta_pre(p)}: fotky visia na starom Strapi CDN. '
              'Spusti bash tools/stiahnut-fotky.sh, kým CMS ešte beží')
        break

# gtag.js nesmie byť v HTML — vkladá ho až suhlas.js po súhlase
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    if 'googletagmanager.com/gtag/js' in t:
        chyba(f'{cesta_pre(p)}: gtag.js je priamo v HTML, načíta sa bez súhlasu')
        break

# ------------------------------------------------------------ 4. súhlas a GA
index = (DIST / 'index.html').read_text(encoding='utf-8')
if "gtag('consent','default'" not in index.replace(' ', '').replace('"', "'"):
    chyba('chýba Consent Mode default v hlavičke')
if 'window.SH_GA=' not in index:
    varovanie('meracie ID GA nie je v stránke — analytika je vypnutá (GA_ID v build.py)')
if 'id="suhlas"' not in index:
    chyba('lišta súhlasu sa nevložila do stránky')
for p in vsetky:
    if 'id="suhlas"' not in p.read_text(encoding='utf-8'):
        chyba(f'{cesta_pre(p)}: chýba lišta súhlasu')

# ------------------------------------------------------- 5. adresy a odkazy
existujuce = {cesta_pre(p) for p in vsetky}
presmerovania = set()
vercel = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
for r in vercel.get('redirects', []):
    presmerovania.add(r['source'].split('/:')[0])

for adresa in STARE_ADRESY:
    if adresa not in existujuce and adresa not in presmerovania:
        chyba(f'adresa zo starého webu {adresa} nikde nekončí — Google ju má v indexe')

# vnútorné odkazy
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    for href in re.findall(r'href="(/[^"#?]*)"', t):
        if href.startswith('/assets/'):
            if not (DIST / href.lstrip('/')).exists():
                chyba(f'{cesta_pre(p)}: odkaz na neexistujúci súbor {href}')
        elif href.endswith('.html'):
            chyba(f'{cesta_pre(p)}: odkaz s príponou .html — {href}')
        elif href not in existujuce and href not in presmerovania \
                and not href.startswith(('/sitemap', '/robots', '/site.webmanifest')):
            chyba(f'{cesta_pre(p)}: odkaz nikam nevedie — {href}')

# --------------------------------------------------------------- 6. canonical
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    m = re.search(r'<link rel="canonical" href="([^"]+)"', t)
    if not m:
        chyba(f'{cesta_pre(p)}: chýba canonical')
    elif not m.group(1).startswith(SITE):
        chyba(f'{cesta_pre(p)}: canonical mieri inam — {m.group(1)}')
    if len(re.findall(r'<h1[ >]', t)) != 1:
        chyba(f'{cesta_pre(p)}: musí byť práve jeden h1')
    if len(re.findall(r'<link rel="alternate" hreflang=', t)) != 4:
        chyba(f'{cesta_pre(p)}: čakal som 4 hreflang')

# ---------------------------------------------------------------- 7. sitemap
sm = (DIST / 'sitemap.xml').read_text(encoding='utf-8')
v_sitemape = set(re.findall(r'<loc>([^<]+)</loc>', sm))
for u in v_sitemape:
    c = norm_adresa(u.replace(SITE, ''))
    if c not in existujuce:
        chyba(f'sitemap uvádza {c}, ale taká stránka neexistuje')
for c in existujuce:
    if not any(norm_adresa(u.replace(SITE, '')) == c for u in v_sitemape):
        varovanie(f'{c} nie je v sitemape')

# ------------------------------------------------------------------ 8. fotky
for p in vsetky:
    t = p.read_text(encoding='utf-8')
    for img in re.findall(r'<img[^>]*>', t):
        if 'assets/img/' not in img:
            continue
        for atr in ('width=', 'height=', 'alt='):
            if atr not in img:
                chyba(f'{cesta_pre(p)}: obrázku chýba {atr.rstrip("=")}')
                break

# ----------------------------------------------------------------- výsledok
print()
for v in varovania:
    print(f'  · {v}')
if varovania:
    print()

if chyby:
    print(f'  NEPÚŠŤAJ TO LIVE — {len(chyby)} vec' +
          ('í' if len(chyby) > 4 else 'i') + ' treba dorobiť:\n')
    for c in chyby:
        print(f'  ✗ {c}')
    print()
    sys.exit(1)

print(f'  Všetko sedí. {len(vsetky)} stránok, {len(v_sitemape)} v sitemape,')
print(f'  {len(STARE_ADRESY)} starých adries pokrytých, žiadna tretia strana pred súhlasom.')
print()
