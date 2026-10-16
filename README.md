# Deszkavízió – Instagram poszt-generátor

Minden reggel lekéri az előző nap "Főoldali fókusz cikk" kategóriás cikkeit,
cikkenként 3 képet készít (borító, 1. bekezdés, 2. bekezdés), és e-mailben elküldi.

## Mappaszerkezet

```
.github/workflows/instagram.yml
requirements.txt
src/            main.py, config.py, scraper.py, renderer.py, image_host.py, emailer.py
fonts/          fetch_fonts.py   (az .ttf fájlokat a workflow tölti le)
templates/      cover_<rovat>.jpg, text_<rovat>.jpg   (1080x1350)
images/latest/  (a workflow hozza létre és commitolja)
```

Sablonnevek (a config.py `ROVAT_TEMPLATES` szerint): `cover_szinhaz.jpg`, `text_szinhaz.jpg`,
`cover_mozgokep.jpg`, `cover_tanc.jpg`, `cover_opera.jpg`, `cover_zene.jpg`,
`cover_kepzomuveszet.jpg`, `cover_konyv.jpg` és mindegyikhez a `text_…` párja.
Mind a 14 fájlnak léteznie kell.

## Beállítás

1. **A repó legyen publikus** – az e-mailben a képek a raw.githubusercontent.com linkjeiről töltődnek be,
   privát repónál nem látszanának.
2. Repo → Settings → Secrets and variables → Actions → *New repository secret*:
   - `BREVO_API_KEY`
   - `DIGEST_EMAIL_TO` – vesszővel elválasztott címek
   - `DIGEST_EMAIL_FROM` – a Brevóban hitelesített feladó cím
3. Settings → Actions → General → Workflow permissions: *Read and write permissions*.

## Tesztelés

Actions → *Instagram posztok* → *Run workflow*:
- `date`: egy konkrét nap (YYYY-MM-DD)
- `ignore_focus`: bepipálva az adott nap minden cikkéből készít képet (ha épp nincs fókusz cikk)

Helyben: `cd src && python main.py render --date 2026-10-15 --ignore-focus --dry-run`
(a képek a `dry_run_output/` mappába kerülnek).

## Finomhangolás

Minden méret és pozíció a `src/config.py`-ban van (`COVER`, `TEXT_CARD`).
Ha a kategória neve eltér: `FOCUS_CATEGORY_NAME`.
