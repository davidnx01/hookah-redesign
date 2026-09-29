#!/usr/bin/env python3
"""
Označí preložiteľné prvky v src/ a nahlási, čo chýba v slovníkoch.

    python3 tools/oznac.py            # označí a vypíše chýbajúce preklady
    python3 tools/oznac.py --report   # len nahlási, nič nemení

Prvok dostane atribút data-i18n, ak obsahuje text na preklad. Označuje sa
vždy len najvrchnejší taký prvok, aby sa preklady nevnárali do seba.

Spusti to vždy, keď v src/ pribudne nový text — inak sa v ruskej
a ukrajinskej verzii zobrazí po slovensky.
"""

import argparse
import json
import pathlib
import re
import sys

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    sys.exit('Chýba beautifulsoup4:  pip3 install beautifulsoup4')

ROOT = pathlib.Path(__file__).parent.parent
SRC = ROOT / 'src'
I18N = ROOT / 'i18n'

CANDIDATES = {'h1', 'h2', 'h3', 'h4', 'p', 'li', 'dt', 'dd', 'cite', 'summary',
              'figcaption', 'title', 'a', 'span', 'b', 'em', 'strong', 'button',
              'th', 'td', 'caption'}

SKIP_PARENTS = {'script', 'style', 'svg'}

# čo sa neprekladá: čísla, ceny, značky, vlastné mená
SKIP_TEXT = re.compile(
    r'^(?:'
    r'[\d\s,.–—\-/×+€:]*'
    r'|SK|RU|UA|MMA'
    r'|Instagram|Facebook|WhatsApp'
    r'|Corona|Desperados|Hoegaarden|Kofola|Sprite|Fanta'
    r'|Coca-Cola(?: Classic| Zero)?|Römerquelle(?: \w+)?|Bake Rolls|7Days'
    r'|Pu-erh|Da Hong Pao|Tieguanyin|Oolong ginseng'
    r'|Blond leafs|Classic mix|Egeglass|Shisha originals'
    r'|Irsai Oliver|Rosé Frizzante|Dolfík'
    r'|Barry White feat\. RHCP|Citrus Gang|Just Another Ginger Sorbet'
    r'|SMOKING|HOOKAH|SH|Smoking Hookah|MENU|Trnava'
    r'|Google|Vercel Inc\.|Google Ireland Limited'
    r'|sh-suhlas|sh-jazyk|_ga|_ga_<ID>'
    r'|Eurocup|Frankfurt|Shishamesse'
    r'|info@hookah\.sk|\+421[\d\s]*'
    r')$'
)

# prvky, ktorých obsah dopĺňa JavaScript alebo ktoré sa prekladať nemajú
SKIP_CLASS = {'statusbar__state', 'brand'}
SKIP_ID = {'statusText', 'hoursNote', 'closingHours'}


def norm(s):
    """BeautifulSoup serializuje prázdne prvky ako <br/>, slovník ich má ako <br>."""
    return re.sub(r'<br\s*/>', '<br>', re.sub(r'\s+', ' ', s)).strip()


def skip(el):
    if any(p.name in SKIP_PARENTS for p in el.parents if p.name):
        return True
    if el.get('id') in SKIP_ID:
        return True
    if SKIP_CLASS & set(el.get('class') or []):
        return True
    for p in el.parents:
        if getattr(p, 'has_attr', None) and p.has_attr('data-i18n'):
            return True
    return False


def wrap_texts(el, soup):
    """Prvok so SVG: prehliadač si SVG v innerHTML preformátuje, takže
    kľúč by nikdy nesedel. Označíme preto len jeho priame textové uzly."""
    made = []
    for child in list(el.children):
        if not isinstance(child, NavigableString):
            continue
        text = norm(str(child))
        if not text or SKIP_TEXT.match(text) or not re.search(r'[A-Za-zÀ-ž]', text):
            continue
        span = soup.new_tag('span')
        span['data-i18n'] = ''
        span.string = text
        child.replace_with(span)
        made.append(text)
    return made


def process(path, write=True):
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')

    for el in soup.select('[data-i18n]'):
        del el['data-i18n']
    for el in soup.select('[data-i18n-content]'):
        del el['data-i18n-content']

    klice = set()
    for el in soup.find_all(list(CANDIDATES)):
        if skip(el):
            continue
        if el.find('svg') is not None:
            klice.update(wrap_texts(el, soup))
            continue
        text = norm(el.get_text())
        if not text or SKIP_TEXT.match(text) or not re.search(r'[A-Za-zÀ-ž]', text):
            continue
        el['data-i18n'] = ''
        klice.add(norm(el.decode_contents()))

    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        meta['data-i18n-content'] = ''
        klice.add(norm(meta['content']))

    if write:
        html = str(soup)
        html = html.replace('data-i18n=""', 'data-i18n').replace('data-i18n-content=""', 'data-i18n-content')
        html = re.sub(r'<br\s*/>', '<br>', html)
        path.write_text(html, encoding='utf-8')

    return klice


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true', help='nič nemeniť, len nahlásiť')
    args = ap.parse_args()

    vsetky = set()
    for f in sorted(SRC.glob('*.html')):
        k = process(f, write=not args.report)
        vsetky |= k
        print(f'  {f.name:<22} {len(k):>4} reťazcov')

    print(f'\n  spolu {len(vsetky)} unikátnych\n')

    chyba = False
    for lang in ['ru', 'uk']:
        d = json.loads((I18N / f'{lang}.json').read_text(encoding='utf-8'))
        miss = sorted(vsetky - set(d))
        stale = sorted(set(d) - vsetky)
        print(f'  {lang.upper()}: chýba {len(miss)}, nepoužitých {len(stale)}')
        if miss:
            chyba = True
            (ROOT / f'i18n/_chyba-{lang}.json').write_text(
                json.dumps({k: '' for k in miss}, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f'       → zoznam v i18n/_chyba-{lang}.json')

    if chyba:
        print('\n  Doplň chýbajúce preklady do i18n/ru.json a i18n/uk.json,')
        print('  inak sa tie texty v cudzích jazykoch zobrazia po slovensky.')
    else:
        print('\n  Všetko preložené.')


if __name__ == '__main__':
    main()
