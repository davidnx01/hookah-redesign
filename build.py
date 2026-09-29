#!/usr/bin/env python3
"""
Generátor webu Smoking Hookah.

    python3 build.py

Zo zdrojov v src/ vyrobí dist/ so všetkými jazykovými verziami,
meta značkami, štruktúrovanými dátami, sitemapou a robots.txt.

Slovenčina v src/ je zdroj aj kľúč do slovníka — preložiteľné prvky
sú označené atribútom data-i18n, preklady sú v i18n/ru.json a i18n/uk.json.
Chýbajúci preklad nespadne, len zostane po slovensky.
"""

import json
import re
import shutil
import sys
import pathlib
from datetime import date
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
I18N = ROOT / 'i18n'

# Web beží na www — overené na živom webe, hookah.sk presmerúva na www.hookah.sk.
# Canonical musí hlásiť presne tú adresu, ktorú Google indexuje.
SITE = 'https://www.hookah.sk'
BUSINESS_ID = f'{SITE}/#lounge'

def asset_version(rel):
    """Krátky odtlačok obsahu. Vďaka nemu sa CSS a JS dajú cachovať natrvalo —
    pri zmene obsahu sa zmení adresa a prehliadač si stiahne novú verziu."""
    import hashlib
    f = SRC / rel
    return hashlib.sha1(f.read_bytes()).hexdigest()[:8] if f.exists() else '0'


FONTS = ('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700'
         '&family=Poppins:wght@300;400;500;600&display=swap')
CDN = 'https://complete-unity-a8415c6467.media.strapiapp.com'

# ---------------------------------------------------------------- jazyky

LANGS = {
    'sk': {'dir': '',   'code': 'sk', 'og': 'sk_SK', 'label': 'SK', 'name': 'Slovenčina'},
    'ru': {'dir': 'ru', 'code': 'ru', 'og': 'ru_RU', 'label': 'RU', 'name': 'Русский'},
    'uk': {'dir': 'ua', 'code': 'uk', 'og': 'uk_UA', 'label': 'UA', 'name': 'Українська'},
}

PAGES = ['index.html', 'vodne-fajky.html', 'menu.html', 'skola-majstra.html',
         'kontakt.html', 'cookies.html', 'ochrana-osobnych-udajov.html']

# Meracie ID Google Analytics. Skript sa načíta AŽ po súhlase — pozri
# assets/suhlas.js. Prázdny reťazec analytiku vypne úplne.
GA_ID = 'G-ZXHSQ5NP3J'

# Testovacie zostavenie:  python3 build.py --test
#
# Rieši dve veci, ktoré testovacie nasadenie inak pokazí:
#   1. Google by testovaciu adresu zaindexoval ako duplikát hookah.sk.
#      Preto noindex na každej stránke a robots.txt so zákazom.
#   2. Testovacia návštevnosť by tiekla do ostrej GA property.
#      Preto sa meracie ID nevloží a gtag sa nenačíta ani po súhlase.
#
# Lišta súhlasu, Consent Mode aj mapa za súhlasom fungujú aj v testovacom
# zostavení — to je práve to, čo sa má odskúšať. Canonical zámerne mieri
# na ostrú doménu: aj keby noindex zlyhal, Google smeruje tam.
TEST = '--test' in sys.argv

# priorita v sitemape
PRIORITY = {'index.html': '1.0', 'vodne-fajky.html': '0.9', 'menu.html': '0.9',
            'skola-majstra.html': '0.7', 'kontakt.html': '0.8',
            'cookies.html': '0.2', 'ochrana-osobnych-udajov.html': '0.2'}

# reťazce, ktoré dopĺňa JavaScript (stavová lišta) — idú priamo do stránky
RUNTIME_KEYS = [
    'Otvorené teraz', 'Momentálne zatvorené', 'Zatvorené',
    'zatvárame o', 'otvárame dnes o',
    'Práve máme otvorené, zatvárame o', 'Práve máme zatvorené, otvárame dnes o',
    'dnes',
]

# ---------------------------------------------------------------- obrázky

IMG_MANIFEST = SRC / 'assets/img/manifest.json'
IMAGES = json.loads(IMG_MANIFEST.read_text(encoding='utf-8')) if IMG_MANIFEST.exists() else {}

# predvolené `sizes`: na mobile fotka cez celú šírku, na tablete polovica, na desktope tretina.
# Bez toho by prehliadač predpokladal 100vw a stiahol zbytočne veľkú verziu.
DEFAULT_SIZES = '(max-width: 680px) 100vw, (max-width: 1080px) 50vw, 33vw'


DICTS = {
    'sk': {},
    'ru': json.loads((I18N / 'ru.json').read_text(encoding='utf-8')),
    'uk': json.loads((I18N / 'uk.json').read_text(encoding='utf-8')),
}

# ---------------------------------------------------------------- pomocné


def norm(s):
    """BeautifulSoup serializuje prázdne prvky ako <br/>, slovník ich má ako <br>."""
    return re.sub(r'<br\s*/>', '<br>', re.sub(r'\s+', ' ', s)).strip()


def tr(text, lang):
    """Preloží reťazec; bez prekladu vráti slovenský originál."""
    return DICTS[lang].get(norm(text), text)


def path_for(page, lang):
    """Adresa stránky bez prípony .html — presne tak, ako ju má starý web
    a ako ju má Google zaindexovanú. Vercel to rieši cez cleanUrls."""
    d = LANGS[lang]['dir']
    if page == 'index.html':
        # Bez lomky na konci. vercel.json má trailingSlash: false, takže /ru/
        # by sa presmerovalo na /ru — a canonical aj hreflang by mierili na
        # adresu, ktorá sa presmeruje. cleanUrls podá ru/index.html na /ru.
        return f'/{d}' if d else '/'
    slug = page[:-5]                      # odrezanie .html
    return f'/{d}/{slug}' if d else f'/{slug}'


def url_for(page, lang):
    return SITE + path_for(page, lang)


def rel_url(page, from_lang, to_lang):
    """Odkaz na tú istú stránku v inom jazyku."""
    return path_for(page, to_lang)


def rel_prefix(lang):
    """Podstránky v podpriečinku musia siahať na zdroje o úroveň vyššie."""
    return '../' if LANGS[lang]['dir'] else ''


# ---------------------------------------------------------------- hlavička


def json_ld(page, lang, title, desc):
    base = rel_prefix(lang)
    business = {
        '@type': 'BarOrPub',
        '@id': BUSINESS_ID,
        'name': 'Smoking Hookah',
        'alternateName': ['Smoking Hookah Lounge', 'SmoKing hookah lounge'],
        'description': desc,
        'url': url_for('index.html', lang),
        'telephone': '+421919370232',
        'email': 'info@hookah.sk',
        'priceRange': '€€',
        'currenciesAccepted': 'EUR',
        'paymentAccepted': 'Hotovosť, platobná karta',
        'image': f'{SITE}/assets/og-image.jpg',
        'logo': f'{SITE}/assets/icon-512.png',
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': 'Štefánikova 107/17',
            'addressLocality': 'Trnava',
            'postalCode': '917 01',
            'addressCountry': 'SK',
        },
        # presná poloha podľa profilu podniku na Google Mapách
        'geo': {
            '@type': 'GeoCoordinates',
            'latitude': 48.3801748,
            'longitude': 17.584455,
        },
        'hasMap': 'https://www.google.com/maps/place/SmoKing+hookah+lounge/'
                  '@48.3801748,17.584455,17z',
        'openingHoursSpecification': [
            {'@type': 'OpeningHoursSpecification',
             'dayOfWeek': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'],
             'opens': '15:00', 'closes': '01:00'},
            {'@type': 'OpeningHoursSpecification',
             'dayOfWeek': ['Friday', 'Saturday'],
             'opens': '15:00', 'closes': '02:00'},
        ],
        'hasMenu': url_for('menu.html', lang),
        'sameAs': [
            'https://instagram.com/smoking.hookah.sk',
            'https://facebook.com/smoking.hookah.sk',
        ],
        'award': [
            '1. miesto — Worldwide Championship Extreme Hookah Battle 2024',
            '2. miesto — Eurocup Frankfurt 2024',
            'Cena divákov — Frankfurt Shishamesse 2024',
        ],
        'knowsLanguage': ['sk', 'ru', 'uk'],
    }

    graph = []

    if page == 'index.html':
        graph.append(business)
        graph.append({
            '@type': 'WebSite',
            '@id': f'{SITE}/#web',
            'url': f'{SITE}/',
            'name': 'Smoking Hookah',
            'inLanguage': LANGS[lang]['code'],
            'publisher': {'@id': BUSINESS_ID},
        })
    else:
        graph.append({
            '@type': 'WebPage',
            '@id': url_for(page, lang) + '#page',
            'url': url_for(page, lang),
            'name': title,
            'description': desc,
            'inLanguage': LANGS[lang]['code'],
            'isPartOf': {'@id': f'{SITE}/#web'},
            'about': {'@id': BUSINESS_ID},
        })
        graph.append({
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1,
                 'name': tr('Domov', lang), 'item': url_for('index.html', lang)},
                {'@type': 'ListItem', 'position': 2, 'name': title},
            ],
        })

    return json.dumps({'@context': 'https://schema.org', '@graph': graph},
                      ensure_ascii=False, separators=(',', ':'))


# Consent Mode v2 od Googlu. Musí stáť v hlavičke a musí bežať skôr,
# než sa čokoľvek od Googlu načíta — preto nie je v suhlas.js, ale priamo
# v HTML. Všetko je predvolene zamietnuté; suhlas.js to prepne na granted
# až keď človek klikne. Keďže gtag.js sa bez súhlasu vôbec nevkladá,
# tento blok len pripraví frontu v dataLayer.
CONSENT_DEFAULT = """<script>
window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}
gtag('consent','default',{ad_storage:'denied',ad_user_data:'denied',
ad_personalization:'denied',analytics_storage:'denied',
functionality_storage:'granted',security_storage:'granted',
wait_for_update:500});gtag('set','ads_data_redaction',true);
</script>"""


def font_links(base):
    """Fonty zo serverov Googlu odosielajú IP adresu návštevníka ešte skôr,
    než sa stihne rozhodnúť v lište súhlasu — obišli by nám celý súhlas.
    Ak sú fonty stiahnuté u nás (tools/stiahnut-fonty.sh), použijeme tie
    a na Google sa už nesiahne. Ak nie sú, ostáva Google a build to nahlási."""
    if (SRC / 'assets' / 'fonts.css').exists():
        v = asset_version('assets/fonts.css')
        return (f'<link rel="stylesheet" href="{base}assets/fonts.css?v={v}" '
                f'media="print" onload="this.media=\'all\'">\n'
                f'<noscript><link rel="stylesheet" href="{base}assets/fonts.css?v={v}"></noscript>')
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{FONTS}" media="print" onload="this.media=\'all\'">\n'
            f'<noscript><link rel="stylesheet" href="{FONTS}"></noscript>')


def build_head(page, lang, title, desc):
    base = rel_prefix(lang)
    L = LANGS[lang]
    canonical = url_for(page, lang)

    alts = '\n'.join(
        f'<link rel="alternate" hreflang="{LANGS[l]["code"]}" href="{url_for(page, l)}">'
        for l in LANGS
    )

    others = ''.join(
        f'\n<meta property="og:locale:alternate" content="{LANGS[l]["og"]}">'
        for l in LANGS if l != lang
    )

    runtime = json.dumps({k: tr(k, lang) for k in RUNTIME_KEYS}, ensure_ascii=False,
                         separators=(',', ':'))

    # Consent Mode patrí do stránky vždy — je to mechanizmus súhlasu,
    # nie analytika. Meracie ID sa v testovacom zostavení nevkladá.
    ga_id = f"window.SH_GA='{GA_ID}';" if (GA_ID and not TEST) else ''
    consent_default = CONSENT_DEFAULT
    fonty = font_links(base)
    robots_meta = ('<meta name="robots" content="noindex, nofollow">' if TEST else
                   '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">')

    return f'''<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{title}</title>
<meta name="description" content="{desc}">
{robots_meta}
<meta name="theme-color" content="#040405">
<meta name="author" content="Smoking Hookah">

<link rel="canonical" href="{canonical}">
{alts}
<link rel="alternate" hreflang="x-default" href="{url_for(page, 'sk')}">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Smoking Hookah">
<meta property="og:locale" content="{L['og']}">{others}
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:alt" content="Smoking Hookah — shisha lounge v srdci Trnavy">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE}/assets/og-image.jpg">

<link rel="icon" href="{base}assets/logo.svg" type="image/svg+xml">
<link rel="icon" href="{base}assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{base}assets/apple-touch-icon.png">
<link rel="manifest" href="{base}site.webmanifest">

<link rel="preconnect" href="{CDN}" crossorigin>
<link rel="preload" as="image" href="{base}assets/logo.svg" fetchpriority="high">

<link rel="stylesheet" href="{base}assets/style.css?v={asset_version('assets/style.css')}">
{fonty}

<script>window.RT={runtime};{ga_id}</script>
{consent_default}
<script src="{base}assets/hours.js?v={asset_version('assets/hours.js')}" defer></script>
<script src="{base}assets/main.js?v={asset_version('assets/main.js')}" defer></script>
<script src="{base}assets/suhlas.js?v={asset_version('assets/suhlas.js')}" defer></script>

<script type="application/ld+json">{json_ld(page, lang, title, desc)}</script>'''


# ---------------------------------------------------------------- telo


def lang_switcher(page, current, mobile=False):
    cls = 'lang lang--mobile' if mobile else 'lang lang--header'
    links = ''.join(
        f'<a href="{rel_url(page, current, l)}" hreflang="{LANGS[l]["code"]}" lang="{LANGS[l]["code"]}"'
        + (' aria-current="true"' if l == current else '')
        + f' title="{LANGS[l]["name"]}">{LANGS[l]["label"]}</a>'
        for l in LANGS
    )
    return (f'<div class="{cls}" role="group" aria-label="Jazyk / Язык / Мова">'
            f'{links}</div>')


def translate_body(soup, lang):
    for el in soup.select('[data-i18n]'):
        src = norm(el.decode_contents())
        out = DICTS[lang].get(src)
        if out:
            el.clear()
            el.append(BeautifulSoup(out, 'html.parser'))
        del el['data-i18n']
    return soup


def expand_images(soup, lang):
    """<img src="assets/img-source/NAME.jpg"> nahradí za <picture> s AVIF,
    WebP a JPEG vo viacerých šírkach. Zdroj tak zostáva čitateľný a otvoriteľný,
    optimalizácia vzniká až pri zostavení."""
    base = rel_prefix(lang)

    for img in soup.find_all('img', src=True):
        src = img['src']
        if 'assets/img-source/' not in src:
            continue

        name = src.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        info = IMAGES.get(name)
        if not info:
            print(f'    ! fotka "{name}" nie je optimalizovaná — spusti optimize_images.py')
            continue

        widths = info['widths']
        sizes = img.get('data-sizes', DEFAULT_SIZES)
        eager = img.has_attr('data-priority')

        def srcset(ext):
            return ', '.join(f'{base}assets/img/{name}-{w}.{ext} {w}w' for w in widths)

        picture = soup.new_tag('picture')
        for mime, ext in (('image/avif', 'avif'), ('image/webp', 'webp')):
            source = soup.new_tag('source')
            source['type'] = mime
            source['srcset'] = srcset(ext)
            source['sizes'] = sizes
            picture.append(source)

        fallback = soup.new_tag('img')
        fallback['src'] = f'{base}assets/img/{name}-{widths[-1]}.jpg'
        fallback['srcset'] = srcset('jpg')
        fallback['sizes'] = sizes
        fallback['alt'] = img.get('alt', '')
        fallback['width'] = str(info['width'])
        fallback['height'] = str(info['height'])
        fallback['decoding'] = 'async'
        if eager:
            fallback['loading'] = 'eager'
            fallback['fetchpriority'] = 'high'
        else:
            fallback['loading'] = 'lazy'
        for keep in ('class', 'id'):
            if img.has_attr(keep):
                fallback[keep] = img[keep]
        picture.append(fallback)

        # rozmazaný náhľad drží miesto a farbu, kým sa fotka stiahne
        holder = img.parent
        if holder and holder.name == 'figure':
            style = holder.get('style', '')
            holder['style'] = f"{style};--lqip:url({info['lqip']})".lstrip(';')
            holder['class'] = ' '.join(filter(None, [' '.join(holder.get('class', [])), 'has-lqip']))

        img.replace_with(picture)

    return soup


def vloz_suhlas(soup):
    """Lišta súhlasu žije v src/_suhlas.html, aby bola na jednom mieste.
    Vkladá sa pred prekladom, takže prejde tým istým slovníkom ako zvyšok."""
    kus = (SRC / '_suhlas.html').read_text(encoding='utf-8')
    body = soup.find('body')
    if body:
        body.append(BeautifulSoup(kus, 'html.parser'))
    return soup


def localize_maps(soup, lang):
    """Vloženej mape nastaví jazyk popisiek a preloží titulok rámu.
    Titulok číta odčítavač obrazovky, takže nesmie zostať po slovensky."""
    code = LANGS[lang]['code']
    for ram in soup.select('[data-map-src]'):
        ram['data-map-src'] = re.sub(r'hl=[a-z-]+', f'hl={code}', ram['data-map-src'])
        if ram.get('data-map-title'):
            ram['data-map-title'] = tr(ram['data-map-title'], lang)
    return soup


def build_page(page, lang):
    soup = BeautifulSoup((SRC / page).read_text(encoding='utf-8'), 'html.parser')

    # názov a popis ešte pred odstránením značiek
    title_el = soup.find('title')
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    title = tr(norm(title_el.get_text()), lang)
    desc = tr(norm(meta_desc['content']), lang)

    # skripty patria do hlavičky s defer — staré na konci tela odstránime
    for sc in soup.find_all('script', src=True):
        sc.decompose()

    vloz_suhlas(soup)
    expand_images(soup, lang)
    localize_maps(soup, lang)
    translate_body(soup, lang)
    for el in soup.select('[data-i18n-content]'):
        del el['data-i18n-content']

    # prepínač jazyka ako odkazy, nie tlačidlá — funguje aj bez JavaScriptu
    for sel, mobile in [('.lang--header', False), ('.lang--mobile', True)]:
        node = soup.select_one(sel)
        if node:
            node.replace_with(BeautifulSoup(lang_switcher(page, lang, mobile), 'html.parser'))

    html = str(soup)

    # hlavička sa generuje nanovo
    html = re.sub(r'<head>.*?</head>',
                  lambda m: '<head>\n' + build_head(page, lang, title, desc) + '\n</head>',
                  html, count=1, flags=re.S)

    html = re.sub(r'<html lang="[^"]*">', f'<html lang="{LANGS[lang]["code"]}">', html, count=1)


    # aktívna položka navigácie
    html = html.replace('class="is-active"', 'class="is-active" aria-current="page"')

    # vnútorné odkazy na čisté adresy v rámci toho istého jazyka
    for name in PAGES:
        html = html.replace(f'href="{name}"', f'href="{path_for(name, lang)}"')

    # cesty k zdrojom v podpriečinku
    base = rel_prefix(lang)
    if base:
        html = html.replace('href="assets/', f'href="{base}assets/')
        html = html.replace('src="assets/', f'src="{base}assets/')

    html = re.sub(r'<br\s*/>', '<br>', html)

    out_dir = DIST / LANGS[lang]['dir'] if LANGS[lang]['dir'] else DIST
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / page).write_text(html, encoding='utf-8')
    return len(html)


# ---------------------------------------------------------------- doplnky


def write_sitemap():
    today = date.today().isoformat()
    rows = []
    for page in PAGES:
        for lang in LANGS:
            alts = '\n'.join(
                f'    <xhtml:link rel="alternate" hreflang="{LANGS[l]["code"]}" href="{url_for(page, l)}"/>'
                for l in LANGS
            )
            rows.append(
                f'  <url>\n'
                f'    <loc>{url_for(page, lang)}</loc>\n'
                f'    <lastmod>{today}</lastmod>\n'
                f'    <changefreq>monthly</changefreq>\n'
                f'    <priority>{PRIORITY[page]}</priority>\n'
                f'{alts}\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url_for(page, "sk")}"/>\n'
                f'  </url>'
            )
    (DIST / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + '\n'.join(rows) + '\n</urlset>\n', encoding='utf-8')


def write_robots():
    if TEST:
        # testovacia adresa sa nesmie dostať do indexu ako duplikát hookah.sk
        (DIST / 'robots.txt').write_text(
            'User-agent: *\n'
            'Disallow: /\n', encoding='utf-8')
        return
    (DIST / 'robots.txt').write_text(
        'User-agent: *\n'
        'Allow: /\n\n'
        f'Sitemap: {SITE}/sitemap.xml\n', encoding='utf-8')


def write_manifest():
    (DIST / 'site.webmanifest').write_text(json.dumps({
        'name': 'Smoking Hookah — shisha lounge v Trnave',
        'short_name': 'Smoking Hookah',
        'description': 'Prémiové vodné fajky, autorské limonády a degustačný lounge v srdci Trnavy.',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#040405',
        'theme_color': '#040405',
        'lang': 'sk',
        'icons': [
            {'src': '/assets/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': '/assets/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': '/assets/logo.svg', 'sizes': 'any', 'type': 'image/svg+xml'},
        ],
    }, ensure_ascii=False, indent=2), encoding='utf-8')


def write_404():
    head = build_head('index.html', 'sk', 'Stránka sa nenašla | Smoking Hookah',
                      'Táto stránka neexistuje. Vráť sa na úvod alebo si pozri našu ponuku.')
    head = head.replace('<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',
                        '<meta name="robots" content="noindex, follow">')
    # chybová stránka nemá čo hlásiť ako kanonickú ani ponúkať jazykové varianty
    head = re.sub(r'<link rel="canonical"[^>]*>\n', '', head)
    head = re.sub(r'<link rel="alternate"[^>]*>\n?', '', head)
    head = re.sub(r'<meta property="og:url"[^>]*>\n', '', head)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>', '', head, flags=re.S)
    (DIST / '404.html').write_text(f'''<!DOCTYPE html>
<html lang="sk">
<head>
{head}
</head>
<body>

<div class="smoke" aria-hidden="true">
  <div class="smoke__noise"></div>
  <span class="plume plume--1"></span>
  <span class="plume plume--2"></span>
  <span class="plume plume--3"></span>
  <div class="smoke__vignette"></div>
</div>

<main id="main" class="page-hero" style="min-height:100svh;display:flex;align-items:center">
  <div class="shell page-hero__inner">
    <p class="eyebrow">Chyba 404</p>
    <h1>TÁTO STRÁNKA<br><span class="mark">NEEXISTUJE</span></h1>
    <p class="lead">
      Odkaz je zrejme starý alebo v adrese vznikla preklep. Skús to odznova z úvodnej stránky.
    </p>
    <div class="closing__actions" style="justify-content:flex-start;margin-top:32px">
      <a class="btn btn--primary btn--lg" href="/">Späť na úvod</a>
      <a class="btn btn--ghost btn--lg" href="/menu.html">Naše menu</a>
    </div>
  </div>
</main>

</body>
</html>
''', encoding='utf-8')


# ---------------------------------------------------------------- beh


def minify_css(css):
    """Bezpečná minifikácia: odstráni komentáre a odsadenie, nesiaha
    do vnútra riadkov, aby nerozbila data URI ani obsah reťazcov."""
    out = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out = '\n'.join(line.strip() for line in out.splitlines())
    out = re.sub(r'\n{2,}', '\n', out)
    return out.strip() + '\n'


def main():
    # Priečinok čistíme, ak sa dá. Ak to prostredie nedovolí (napr. zamknuté
    # súbory alebo obmedzené práva), pokračujeme prepisom — výstup je rovnaký,
    # len tam môžu zostať staré súbory z predchádzajúceho behu.
    if DIST.exists():
        try:
            shutil.rmtree(DIST)
        except OSError as e:
            print(f'  (priečinok dist sa nedal vyčistiť: {e.strerror} — prepisujem)')
    DIST.mkdir(exist_ok=True)

    # originály fotiek a manifest sa nenasadzujú — do dist ide len to,
    # čo prehliadač naozaj sťahuje
    shutil.copytree(SRC / 'assets', DIST / 'assets', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('img-source', 'manifest.json'))

    css_src = SRC / 'assets/style.css'
    css_out = DIST / 'assets/style.css'
    before = css_src.stat().st_size
    css_out.write_text(minify_css(css_src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'  CSS  {before/1024:.1f} → {css_out.stat().st_size/1024:.1f} KB')

    total = 0
    for lang in LANGS:
        sizes = [build_page(p, lang) for p in PAGES]
        total += sum(sizes)
        where = LANGS[lang]['dir'] or '.'
        print(f'  {LANGS[lang]["label"]:3} → dist/{where:<4} {len(sizes)} stránok, {sum(sizes)/1024:6.1f} KB')

    write_sitemap()
    write_robots()
    write_manifest()
    write_404()

    if not (SRC / 'assets' / 'fonts.css').exists():
        print()
        print('  !! Fonty sa stále ťahajú z fonts.googleapis.com.')
        print('     Googlu tak odchádza IP adresa návštevníka EŠTE PRED súhlasom,')
        print('     čím sa obchádza cookie lišta. Spusti raz:')
        print('         bash tools/stiahnut-fonty.sh')
        print('     a potom build znova — odkaz na Google z hlavičky vypadne.')

    if TEST:
        print('\n  TESTOVACIE ZOSTAVENIE — noindex, robots.txt zakazuje všetko,')
        print('  meracie ID GA sa nevložilo. Na ostro spusti build.py bez --test.')
    print(f'\n  sitemap.xml · robots.txt · site.webmanifest · 404.html')
    print(f'  spolu {total/1024:.1f} KB HTML v {len(LANGS) * len(PAGES)} stránkach')


if __name__ == '__main__':
    main()
