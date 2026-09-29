#!/usr/bin/env bash
# Vyhodí redesign na nový testovací GitHub repozitár a na Vercel.
#
#     bash tools/nasadit-test.sh
#
# Testovacie zostavenie má noindex na každej stránke, robots.txt zakazuje
# všetko a meracie ID GA sa nevkladá. Google teda testovaciu adresu
# nezaindexuje ako duplikát hookah.sk a testovacia návštevnosť netečie
# do ostrej GA property. Lišta súhlasu, Consent Mode aj mapa za súhlasom
# fungujú normálne — to je práve to, čo sa má odskúšať.
#
# Potrebuje: gh (prihlásený) a vercel (prihlásený).
#   brew install gh vercel   &&   gh auth login   &&   vercel login

set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${1:-hookah-redesign-test}"

# ---------------------------------------------------------------- poistky
if [[ "$REPO" == *"hookah-web"* ]]; then
  echo "Toto je skript na TESTOVACIE nasadenie a hookah-web je ostrý web."
  echo "Ostrú migráciu robí postup v MIGRACIA.md, ručne a s rozmyslom."
  exit 1
fi
command -v gh >/dev/null     || { echo "Chýba gh — brew install gh"; exit 1; }
command -v vercel >/dev/null || { echo "Chýba vercel — brew install vercel"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh nie je prihlásený — gh auth login"; exit 1; }

# -------------------------------------------------------------- zostavenie
echo "▸ Testovacie zostavenie"
python3 build.py --test

echo
echo "▸ Kontrola (na testovacom nasadení nie je blokujúca)"
python3 tools/kontrola.py || echo "  ↑ toto musí byť vyriešené PRED ostrým spustením"

# ------------------------------------------------------------------ GitHub
echo
if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "▸ Repozitár $REPO už existuje, len doňho pushnem"
else
  echo "▸ Zakladám súkromný repozitár $REPO"
  gh repo create "$REPO" --private \
    --description "Testovacie nasadenie redesignu hookah.sk — neindexuje sa"
fi

OWNER="$(gh api user --jq .login)"
git remote remove test 2>/dev/null || true
git remote add test "https://github.com/$OWNER/$REPO.git"

git add -A
git commit -q -m "Testovacie zostavenie (noindex, bez GA)" || echo "  (nič nové na commit)"
git push -u test HEAD:main --force
echo "  → https://github.com/$OWNER/$REPO"

# ------------------------------------------------------------------ Vercel
echo
echo "▸ Nasadzujem na Vercel"
vercel deploy --prod --yes

echo
echo "Hotovo. Čo si na testovacej adrese prejsť:"
echo "  · lišta súhlasu — Odmietnuť všetko nesmie načítať nič od Googlu"
echo "  · mapa sa bez súhlasu nenačíta, ukáže náhradu"
echo "  · /ru a /ua fungujú, prepínač jazyka drží stránku"
echo "  · /drinky presmeruje na /menu"
echo "  · robots.txt musí hlásiť Disallow: /"
echo
echo "Až to prejde, ostrá migrácia je v MIGRACIA.md."
echo "Nezabudni potom na ostro zostaviť BEZ --test."
