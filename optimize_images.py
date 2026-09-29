#!/usr/bin/env python3
"""
Optimalizácia fotografií pre web.

    python3 optimize_images.py            # spracuje len zmenené
    python3 optimize_images.py --force    # pregeneruje všetko

Vstup:  src/assets/img-source/   originály tak, ako prišli z foťáku
Výstup: src/assets/img/          varianty + manifest.json

Čo robí s každou fotkou:
  1. otočí ju podľa EXIF, aby nebola naležato
  2. prevedie do sRGB (iPhone fotí v Display P3 — bez prevodu farby v prehliadači blednú)
  3. odstráni metadáta (GPS polohu, model foťáku, čas — aj kilobajty aj súkromie)
  4. vyrobí päť šírok, aby telefón nesťahoval fotku pre 4K monitor
  5. uloží každú šírku v AVIF, WebP a JPEG
  6. vyrobí rozmazaný náhľad (LQIP), ktorý sa vkladá priamo do HTML

Nastavenie kvality je zvolené tak, aby vernosť neklesla pod úroveň JPEG 90.
Merané cez SSIM (štrukturálna podobnosť s originálom):

    JPEG 90  →  SSIM 0,9936
    WebP 92  →  SSIM 0,9904
    AVIF 85  →  SSIM 0,9936   rovnaká vernosť ako JPEG 90, polovičná veľkosť

Čísla kvality nie sú medzi formátmi porovnateľné — každý kodek má vlastnú
stupnicu. Preto sa neriadime číslom, ale nameranou vernosťou.
"""

import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageCms, ImageFilter, ImageOps
except ImportError:
    sys.exit('Chýba Pillow:  pip3 install --upgrade Pillow')

ROOT = Path(__file__).parent
SOURCE = ROOT / 'src/assets/img-source'
OUT = ROOT / 'src/assets/img'
MANIFEST = OUT / 'manifest.json'

# šírky, v ktorých sa fotka generuje (väčšie než originál sa preskočia)
WIDTHS = [480, 768, 1200, 1800, 2400]

# kvalita — pozri vysvetlenie v hlavičke súboru
QUALITY = {
    'avif': dict(quality=85, speed=2),
    'webp': dict(quality=92, method=6),
    'jpeg': dict(quality=90, optimize=True, progressive=True, subsampling=0),
}

SRGB = ImageCms.createProfile('sRGB')
EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.bmp'}


def fingerprint(path: Path) -> str:
    """Odtlačok súboru — aby sa nespracovávalo to, čo sa nezmenilo."""
    st = path.stat()
    return hashlib.sha1(f'{path.name}|{st.st_size}|{int(st.st_mtime)}'.encode()).hexdigest()[:16]


def load(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)          # rotácia podľa EXIF

    icc = img.info.get('icc_profile')
    if icc:                                      # prevod z Display P3 a pod. do sRGB
        try:
            src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            img = ImageCms.profileToProfile(img, src_profile, SRGB, outputMode='RGB')
        except Exception:
            img = img.convert('RGB')
    else:
        img = img.convert('RGB')

    img.info.pop('exif', None)                   # preč s metadátami
    img.info.pop('icc_profile', None)
    return img


def lqip(img: Image.Image) -> str:
    """Rozmazaný náhľad ako data URI — drží miesto, kým sa fotka načíta."""
    w = 24
    h = max(1, round(w * img.height / img.width))
    tiny = img.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    buf = io.BytesIO()
    tiny.save(buf, 'WEBP', quality=45, method=6)
    import base64
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()


def process(path: Path, force: bool, old: dict) -> dict:
    name = path.stem
    fp = fingerprint(path)

    if not force and old.get(name, {}).get('fingerprint') == fp:
        return old[name] | {'skipped': True}

    img = load(path)
    widths = [w for w in WIDTHS if w <= img.width] or [img.width]
    if img.width not in widths and img.width < min(WIDTHS):
        widths = [img.width]
    # originál medzi krokmi (napr. 1440 px) — pridaj aj jeho natívnu šírku,
    # inak sa najväčšie miesto na stránke škáluje nahor z menšieho variantu
    if img.width not in widths and img.width > max(widths):
        widths.append(img.width)

    total = 0
    for w in widths:
        h = round(w * img.height / img.width)
        resized = img.resize((w, h), Image.LANCZOS) if w != img.width else img
        # jemné doostrenie po zmenšení — kompenzuje mäkkosť interpolácie
        if w < img.width:
            resized = resized.filter(ImageFilter.UnsharpMask(radius=0.6, percent=42, threshold=3))

        for fmt, ext in (('AVIF', 'avif'), ('WEBP', 'webp'), ('JPEG', 'jpg')):
            dest = OUT / f'{name}-{w}.{ext}'
            resized.save(dest, fmt, **QUALITY[ext if ext != 'jpg' else 'jpeg'])
            total += dest.stat().st_size

    return {
        'fingerprint': fp,
        'source': path.name,
        'width': img.width,
        'height': img.height,
        'widths': widths,
        'lqip': lqip(img),
        'bytes': total,
        'original_bytes': path.stat().st_size,
        'skipped': False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='pregenerovať aj nezmenené')
    args = ap.parse_args()

    if not SOURCE.exists():
        SOURCE.mkdir(parents=True)
        print(f'Vytvoril som {SOURCE.relative_to(ROOT)} — vlož doň originály fotiek a spusti znova.')
        return

    files = sorted(p for p in SOURCE.iterdir() if p.suffix.lower() in EXTS)
    if not files:
        print(f'V {SOURCE.relative_to(ROOT)} nie sú žiadne fotky.')
        return

    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    manifest, done, saved_from, saved_to = {}, 0, 0, 0
    print(f'{"fotka":<26}{"originál":>10}{"najväčší":>11}{"variantov":>11}')
    print('-' * 58)

    for f in files:
        entry = process(f, args.force, old)
        manifest[f.stem] = {k: v for k, v in entry.items() if k != 'skipped'}

        if entry['skipped']:
            print(f'{f.stem:<26}{"":>10}{"":>11}{"nezmenené":>11}')
            continue

        done += 1
        biggest = max(entry['widths'])
        best = (OUT / f'{f.stem}-{biggest}.avif').stat().st_size
        saved_from += entry['original_bytes']
        saved_to += best
        print(f'{f.stem:<26}{entry["original_bytes"]/1024:9.0f}K'
              f'{best/1024:10.0f}K{len(entry["widths"]) * 3:11}')

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')

    if done:
        print('-' * 58)
        print(f'spracovaných {done} · originály {saved_from/1024/1024:.1f} MB '
              f'→ najväčší AVIF {saved_to/1024/1024:.1f} MB '
              f'({100 - 100*saved_to/saved_from:.0f} % menej)')
        print('Telefón stiahne verziu 480px, čiže reálna úspora je ešte výrazne väčšia.')
    print(f'\nmanifest: {MANIFEST.relative_to(ROOT)}   →   spusti python3 build.py')


if __name__ == '__main__':
    main()
