#!/usr/bin/env bash
# Stiahne 12 fotiek, ktoré sú zatiaľ načítavané zo starého Strapi CDN.
# Spusti v Termináli z koreňa projektu:
#
#     bash tools/stiahnut-fotky.sh
#
# Potom:
#     python3 optimize_images.py
#     python3 build.py

set -euo pipefail

CDN="https://complete-unity-a8415c6467.media.strapiapp.com"
DEST="src/assets/img-source"
mkdir -p "$DEST"

# zdrojový súbor na CDN  →  názov, pod ktorým ho chceme mať
declare -a FOTKY=(
  "dsadasdsadas_6201859bee.jpg|hero-interier"
  "section19_a47c9e3fc8.jpg|karta-fajky"
  "section13_2939fe4e3b.jpg|karta-drinky"
  "banner_f2e56ae9d9.png|karta-zapasy"
  "delaw_c74ce8f05e.jpg|mix-delawarsky-punc"
  "RHCP_261e2adf41.jpg|mix-barry-white"
  "citrusgang_9f5596faca.jpg|mix-citrus-gang"
  "sorbet_2001fa5638.jpg|mix-ginger-sorbet"
  "pineapple_dac93c96f7.jpg|mix-mango-masala"
  "sibiria_472ffb2539.jpg|mix-srdce-sibirie"
  "1_14ab408ff9.jpg|ocenenie-1"
  "2_66588945ac.jpg|ocenenie-2"
)

echo "Sťahujem ${#FOTKY[@]} fotiek do $DEST"
echo

for row in "${FOTKY[@]}"; do
  remote="${row%%|*}"
  name="${row##*|}"
  ext="${remote##*.}"
  out="$DEST/$name.$ext"

  if [ -f "$out" ]; then
    printf '  %-24s už existuje\n' "$name"
    continue
  fi

  if curl -fsSL "$CDN/$remote" -o "$out"; then
    printf '  %-24s %s\n' "$name" "$(du -h "$out" | cut -f1)"
  else
    printf '  %-24s ZLYHALO\n' "$name"
    rm -f "$out"
  fi
done

echo
echo "Hotovo. Ďalej:"
echo "  python3 optimize_images.py"
echo "  python3 build.py"
