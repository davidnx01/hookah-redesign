# Migrácia hookah.sk

Postup na výmenu súčasného Next.js frontendu (`hookah-web`) za tento
statický web. Všetko, čo je tu napísané o starom webe, je odmerané
29. 9. 2026, nie odhadnuté.

> [!danger] Nenasadzovať, kým to David neodovzdá klientovi.
> `python3 tools/kontrola.py` musí prejsť bez jedinej chyby. Keď skončí
> nenulovým kódom, nasadenie sa nekoná — a je jedno, ako to vyzerá inak.

---

## 1. Ako na tom je starý web (odmerané)

| | |
|---|---|
| kanonická doména | **`www.hookah.sk`** — apex `hookah.sk` naň presmerúva |
| živé adresy | `/` · `/menu` · `/drinky` · `/vodne-fajky` · `/skola-majstra` · `/kontakt` |
| sitemap.xml | **neexistuje** (404) |
| robots.txt | **neexistuje** (404) |
| canonical | žiadny |
| hreflang | žiadny |
| schema.org | žiadny |
| Google Analytics | `G-ZXHSQ5NP3J`, beží, nastavuje `_ga` a `_ga_ZXHSQ5NP3J` |
| cookie lišta | **žiadna** |
| fotky | `complete-unity-a8415c6467.media.strapiapp.com` |

Dve veci z toho stoja za zapamätanie:

1. **Google nemá od tohto webu sitemap ani robots.** Index si postavil
   výhradne crawlovaním. Tých šesť adries je teda všetko, o čo ide.
2. **GA na starom webe beží bez akéhokoľvek súhlasu.** Cookies sa
   nastavujú hneď pri načítaní. Nový web je v tomto prísne lepší, ale
   znamená to, že terajší stav je právne problém už dnes, nie až po migrácii.

## 2. Čo sa s adresami stane

| stará adresa | nová | |
|---|---|---|
| `/` | `/` | bez zmeny |
| `/menu` | `/menu` | bez zmeny |
| `/vodne-fajky` | `/vodne-fajky` | bez zmeny |
| `/skola-majstra` | `/skola-majstra` | bez zmeny |
| `/kontakt` | `/kontakt` | bez zmeny |
| `/drinky` | `/menu` | **301**, nápoje sú teraz súčasťou menu |

Nová stránka nestráca ani jednu zaindexovanú adresu. Pribúdajú
`/cookies`, `/ochrana-osobnych-udajov` a jazykové verzie na `/ru` a `/ua`.

Jazykové domovské stránky sú zámerne **bez lomky na konci** (`/ru`, nie
`/ru/`). `vercel.json` má `trailingSlash: false`, takže `/ru/` by sa
presmerovalo — a canonical aj hreflang by mierili na adresu, ktorá sa
presmeruje.

## 3. Čo musí byť hotové pred migráciou

Toto všetko kontroluje `tools/kontrola.py`, takže sa na to netreba
spoliehať z hlavy.

- [ ] **Fotky zo Strapi.** `bash tools/stiahnut-fotky.sh`, kým CMS ešte
      beží. Osem fotiek chuťových mixov a ocenení na ňom stále visí.
      V deň, keď sa Strapi vypne, z webu zmiznú.
- [ ] **Fonty k nám.** `bash tools/stiahnut-fonty.sh` z normálneho
      terminálu. Kým to nebeží, `fonts.googleapis.com` sa načíta ešte
      pred súhlasom a obchádza celú cookie lištu.
- [ ] **Právne údaje.** V `src/ochrana-osobnych-udajov.html` sú štyri
      miesta `[DOPLNIŤ]` — obchodné meno, sídlo, IČO, dátum účinnosti.
- [ ] **Právna kontrola** zásad ochrany osobných údajov.
- [ ] **Šesť šrafovaných rámov** — bar pri príprave, panini, ovocná misa
      (Menu) · mixovanie príchutí, súťažná váza (Škola majstra) ·
      ulica s orientačným bodom (Kontakt).
- [ ] **Ceny kurzov** Školy majstra — teraz „na vyžiadanie".

## 4. Samotná výmena

```bash
# 1. posledná kontrola
python3 build.py
python3 tools/kontrola.py        # musí prejsť

# 2. klon existujúceho repozitára vedľa
cd ~/Documents/Personal\ Coding/Trnava
git clone git@github.com:<ucet>/hookah-web.git hookah-web-migracia
cd hookah-web-migracia

# 3. von so starým obsahom, história zostáva
git rm -rq . 

# 4. dnu s novým
rsync -a --exclude '.git' ../smoking/ .

# 5. commit a push
git add -A
git commit -m "Nahradenie Next.js frontendu statickým redesignom"
git push origin main
```

Zámerne cez klon a nie force-push: **história repozitára zostane**
a rovnako zostane aj história nasadení na Verceli. Keby sa niečo
pokazilo, návrat je jedno kliknutie.

## 5. Čo skontrolovať vo Verceli

| nastavenie | hodnota |
|---|---|
| Framework Preset | **Other** — projekt je dnes nastavený na Next.js |
| Build Command | prázdne |
| Output Directory | `dist` |
| Install Command | prázdne |
| primárna doména | `www.hookah.sk` |
| `hookah.sk` | presmerovanie na `www.hookah.sk` |

`vercel.json` má `"framework": null`, čo nastavenie z rozhrania
prebíja — ale keď sa deploy zachová divne, toto je prvé miesto,
kam sa treba pozrieť. Premenné prostredia pre Strapi už nie sú
na nič potrebné.

## 6. Hneď po nasadení

```bash
# adresy zo starého webu musia žiť
for u in / /menu /vodne-fajky /skola-majstra /kontakt; do
  curl -s -o /dev/null -w "%{http_code} $u\n" https://www.hookah.sk$u
done

# /drinky musí presmerovať na /menu
curl -sI https://www.hookah.sk/drinky | grep -i 'location\|HTTP/'

# apex musí presmerovať na www
curl -sI https://hookah.sk/ | grep -i 'location\|HTTP/'
```

Potom v prehliadači:

- lišta súhlasu sa zobrazí, **Odmietnuť všetko** nič nenačíta
  (skontroluj v Sieti, že tam nie je `googletagmanager`)
- po **Prijať všetko** sa GA načíta a v Realtime v GA to vidno
- mapa sa bez súhlasu nenačíta
- `/ru` a `/ua` fungujú

## 7. Google Search Console

1. Poslať `https://www.hookah.sk/sitemap.xml` — starý web žiadnu nemal,
   toto je prvá.
2. Cez „Prehliadka URL" nechať prelieziť `/` a `/menu`.
3. Sledovať `/drinky` — má sa preklopiť na presmerovanie, nie vypadnúť.
4. V GA admin nastaviť uchovávanie údajov na 14 mesiacov a vypnúť
   Google Signals, nech to sedí so zásadami.

## 8. Keby sa niečo pokazilo

Vo Verceli v Deployments nájsť posledné nasadenie pôvodného frontendu
a dať **Promote to Production**. Je to okamžité a nepotrebuje git.
Preto sa migrácia robí cez klon so zachovanou históriou.

Ak by problém bol len v jednej stránke, rýchlejšie je opraviť zdroj,
`python3 build.py`, `python3 tools/kontrola.py` a pushnúť znova.
