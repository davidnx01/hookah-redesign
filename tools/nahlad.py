#!/usr/bin/env python3
"""
Lokálny náhľad s adresami bez prípony — tak, ako to bude bežať na Verceli.

    python3 tools/nahlad.py          →  http://localhost:8000

Otvorenie dist/index.html priamo z disku už nestačí: odkazy smerujú na /menu,
nie na menu.html. Tento server sa správa rovnako ako Vercel s cleanUrls —
/menu podá menu.html, /ru/ podá ru/index.html, neznáma adresa vráti 404.html.
"""

import http.server
import os
import pathlib
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIST = pathlib.Path(__file__).parent.parent / 'dist'


class CleanUrls(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def translate_path(self, path):
        full = super().translate_path(path)
        p = pathlib.Path(full)

        if p.is_dir():                       # /ru aj /ru/ → ru/index.html
            index = p / 'index.html'
            if index.exists():
                return str(index)
        if not p.exists():                   # /menu → menu.html
            html = p.with_suffix('.html')
            if html.exists():
                return str(html)
        return full

    def send_error(self, code, message=None, explain=None):
        chyba = DIST / '404.html'
        if code == 404 and chyba.exists():
            body = chyba.read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        sys.stderr.write(f'  {args[0]}  →  {args[1]}\n')


if not DIST.exists():
    sys.exit('Priečinok dist/ neexistuje — spusti najprv python3 build.py')

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', PORT), CleanUrls) as httpd:
    print(f'Náhľad beží na http://localhost:{PORT}')
    print('Adresy sú bez prípony, rovnako ako na Verceli. Ukončenie: Ctrl+C\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nkoniec')
