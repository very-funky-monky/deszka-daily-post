# Deszkavízió – Instagram posztok

Naponta 7:00-kor (Budapest) e-mailt küld a **tegnapi, „Főoldali fókusz cikk” kategóriás** cikkekből,
cikkenként 3 képpel (1080×1350): 1) borító: szerző + fotó + cím, 2) első bekezdés, 3) második bekezdés.

## Beállítás (egyszer)
1. Töltsd fel a mappa tartalmát egy **publikus** GitHub repóba (a `.github` mappa a repó gyökerében legyen!).
   Lehet ugyanaz a repó, mint a story-s szkripté – akkor a két workflow-fájl neve különbözzön (itt: `instagram.yml`),
   de az `images/latest` mappa közös lenne, ezért **külön repót** javaslok.
2. Settings → Secrets and variables → Actions → Secrets: `BREVO_API_KEY`, `DIGEST_EMAIL_FROM` (Brevóban hitelesített feladó),
   `DIGEST_EMAIL_TO` (vesszővel elválasztva).
3. Settings → Actions → General → Workflow permissions: **Read and write**.

## Tesztelés GitHubon belül
Actions → „Instagram posztok” → Run workflow:
- `date`: pl. `2026-10-15` (üresen: tegnap)
- `ignore_focus`: ha be van pipálva, a kategóriától függetlenül minden cikket feldolgoz (a lekérés és kinézet teszteléséhez).

Ha a naplóban „egyik sem 'Főoldali fókusz cikk'” figyelmeztetés van, a kategória neve eltér: add meg a pontos nevet
a Settings → Variables → `FOCUS_CATEGORY_NAME` változóban.

## Megjegyzések
- Az Urbanist betűt a workflow tölti le; ha nem sikerül, DejaVu Sans a tartalék (sárga figyelmeztetés a naplóban).
- A rovat az első felismert rovat-kategória (Színház, Mozgókép, Tánc, Opera, Zene, Képzőművészet, Könyv), különben Színház.
- Hosszú bekezdést mondathatáron rövidít „…”-tal.
- Sablonok: `templates/cover_<rovat>.jpg`, `templates/text_<rovat>.jpg`. Elrendezés: `src/config.py`.
