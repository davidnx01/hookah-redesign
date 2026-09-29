#!/usr/bin/env bash
# Stiahne Barlow Condensed a Poppins z Google Fonts k nám do projektu.
#
# Prečo: kým sa fonty ťahajú z fonts.googleapis.com, odchádza Googlu IP adresa
# každého návštevníka ešte predtým, než stihne čokoľvek odsúhlasiť. To je presne
# to, čo cookie lišta rieši — a font by nám ju obchádzal. Súdy to už riešili
# (LG München I, 3 O 17493/20), takže to nie je teoretická vec.
#
# Spusti raz z priečinka projektu:
#     bash tools/stiahnut-fonty.sh
#
# Potom stačí python3 build.py — build si sám všimne, že fonty sú lokálne,
# a odkaz na Google z hlavičky vypadne.

set -euo pipefail
cd "$(dirname "$0")/.."

CIEL="src/assets/fonts"
CSS="src/assets/fonts.css"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
ZDROJ="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Poppins:wght@300;400;500;600&display=swap"

mkdir -p "$CIEL"
echo "Sťahujem zoznam fontov…"
# Chrome-ovská hlavička je dôležitá — bez nej Google pošle staršie formáty
# namiesto woff2, ktoré je asi o tretinu menšie.
curl -sS -A "$UA" "$ZDROJ" -o /tmp/fonty-zdroj.css

pocet=0
while read -r url; do
  meno="$(basename "${url%%\?*}")"
  if [ ! -f "$CIEL/$meno" ]; then
    curl -sS "$url" -o "$CIEL/$meno"
    pocet=$((pocet + 1))
  fi
done < <(grep -o 'https://fonts.gstatic.com/[^)]*\.woff2' /tmp/fonty-zdroj.css | sort -u)

# Prepíšeme adresy na naše a doplníme font-display, aby text nezmizol,
# kým sa font sťahuje.
sed -E 's#https://fonts\.gstatic\.com/[^)]*/([^/)]+\.woff2)#fonts/\1#g' /tmp/fonty-zdroj.css > "$CSS"
grep -q 'font-display' "$CSS" || sed -i '' 's/^}/  font-display: swap;\n}/' "$CSS" 2>/dev/null || true

rm -f /tmp/fonty-zdroj.css
echo "Hotovo: $pocet nových súborov v $CIEL, CSS v $CSS"
echo "Teraz spusti:  python3 build.py"
