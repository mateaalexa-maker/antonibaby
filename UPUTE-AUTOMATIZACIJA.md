# Antoni Baby — automatski cjenik i Netlify

## Što je GitHub repozitorij?
To je online mapa s datotekama web stranice, uz povijest promjena. GitHub Actions je alat u toj mapi koji automatski izvršava `scripts/generate_cjenik.py`. Netlify se povezuje s GitHub mapom i automatski objavljuje nove verzije stranice.

## Postavljanje (jednom)
1. Otvori https://github.com/ i kreiraj račun ako ga nemaš.
2. Klikni **New repository** i nazovi ga `antoni-baby-web`. Preporuka: **private** (privatno). Nemoj dodavati automatski README/initial files.
3. Raspakiraj ZIP na računalo. Najjednostavnije je prebaciti sadržaj repozitorija putem GitHub Desktop aplikacije (https://desktop.github.com/) ili naredbi `git init`, `git add .`, `git commit -m "Prva verzija"`, `git branch -M main`, `git remote add origin URL_REPOZITORIJA`, `git push -u origin main`. **Nemoj** na GitHub učitati samu ZIP datoteku; učitaj njezin sadržaj.
4. U GitHub repozitoriju otvori **Settings → Actions → General → Workflow permissions** i omogući **Read and write permissions**, zatim Save.
5. Otvori Netlify → **Add new project → Import an existing project → GitHub**, odaberi `antoni-baby-web`. Kao **publish directory** upiši `.` (točka), build command ostavi prazno, zatim Deploy.
6. Na GitHubu otvori **Actions → Antoni Baby — jutarnji cjenik → Run workflow** za prvu provjeru. Provjeri na Netlify linku `.../pricelists/cjenik.csv` i `.../pricelists/arhiva/`.

**VAŽNO:** Ako postojeći Netlify web već postoji kao ručni Drop, to je zaseban site. Po potrebi u Netlify dashboardu prilagodi naziv nove stranice i koristi novu GitHub-povezanu adresu. Za prvu objavu koristi novu testnu adresu.

## Što radi automatika?
- GitHub Actions po rasporedu pokreće skriptu **radnim danom u 05:15 i 06:15 po vremenu Europe/Zagreb** (drugi poziv je rezervni). GitHub može odgoditi zakazane workflowe; nije stroga garancija roka.
- Skripta učitava podatke iz **`data/cijene.json`** i prepisuje aktualne cijene na webu (`app.js`), generira `pricelists/cjenik.csv` i `pricelists/dostava.csv` i javnu arhivu.
- U arhivi je svaka objavljena verzija cijena, s datumom i satom; javni popis `pricelists/arhiva/` sadrži zadnjih 30 kalendarskih dana. Stare verzije ostaju u Git povijesti repozitorija.
- GitHub commit s datotekama inicira novi Netlify deployment preko GitHub integracije. Ako se deploy ne dogodi, treba provjeriti Netlify build/deploy status i GitHub integraciju.
- Možeš bilo kada ručno pokrenuti **Actions → Run workflow**. Promjena datoteke `data/cijene.json` također pokreće workflow.

## Kako se mijenjaju cijene?
Na GitHubu otvori **data/cijene.json → olovka Edit**. Promijeni samo `price_eur` (aktualnu cijenu) i klikni **Commit changes**. Polje **`anchor_eur`** je sidrena cijena i ostaje fiksno na 10. 9. 2026. Ne smije se automatski mijenjati zajedno s aktualnom cijenom. Ako cijenu promijeniš, provjeri da je GitHub Action završila i da Netlify prikazuje novu cijenu.

## Dostupnost proizvoda — obavezno pregledati prije službene objave
Za svih šest proizvoda u početnoj datoteci privremeno je upisano `"availability": "nedostupno"` jer su opisani kao proizvodi izrađeni po narudžbi, a stanje zaliha nije potvrđeno. **To nije potvrđena činjenica.** Za svaki proizvod provjeri je li stvarno na stanju i u prodaji u prodajnom objektu. Ako jest, upiši `"dostupno"`; ako nije, ostavi `"nedostupno"`. Generiranje ne može samo otkriti stanje zaliha.

## Šifre i barkodovi
Interne šifre AB-001 do AB-006 su generirane za ovaj katalog jer obrt nema svoje. Mogu se zadržati kao službene interne šifre ako ih vlasnica prihvati. `barcode` je `null` jer barkodovi ne postoje; ne izmišljamo EAN/GTIN.

## Pravni i operativni oprez
Ovo je gotova *tehnička automatizacija*, a ne pravna potvrda usklađenosti. Provjeri konačne provedbene pravilnike i klasifikaciju proizvod/usluga te format imena datoteka prije produkcije. Prema Odluci NN 101/2026, cijene, sidrene cijene, raspoloživost i arhiva su bitni. GitHub schedule nije SLA i može zakasniti, pa je nužno periodično provjeriti jesu li Actions i Netlify deploy završili; u kritičnoj uporabi dodaj vanjski nadzor i upozorenje. Povezivanje GitHuba/Netlifyja moraš odraditi na vlastitim računima.

## Datoteke
- `data/cijene.json` — jedino mjesto za promjene cijena.
- `scripts/generate_cjenik.py` — generator CSV-a, arhive, cijena na webu.
- `.github/workflows/cjenik.yml` — automatski raspored.
- `pricelists/cjenik.csv` — javni CSV aktualnih cijena proizvoda.
- `pricelists/dostava.csv` — javni CSV usluga dostave.
- `pricelists/arhiva/` — javna arhiva.

