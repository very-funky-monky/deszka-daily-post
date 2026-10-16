"""
Belépési pont - két lépésben fut, mert a képeknek előbb fel kell kerülniük a
GitHub repóba (commit + push), hogy az e-mailben lévő linkjeik működjenek:

    python main.py render [--date YYYY-MM-DD] [--ignore-focus] [--dry-run]
    (git add/commit/push images/latest - ezt a workflow végzi)
    python main.py send

--ignore-focus : teszteléshez; a fókusz kategória szűrést kihagyja, az adott
                 nap MINDEN cikkéből készít képeket.
--dry-run      : (csak render) nem ment a repóba, a dry_run_output/ mappába ír.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime

from config import SEND_EMPTY_DIGEST_NOTICE
from scraper import fetch_articles_for_date, get_target_date
from renderer import render_article_images, font_report, uses_fallback_font
from image_host import RenderedArticle, save_rendered_images, load_manifest, public_url_for
from emailer import send_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("deszka-instagram")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deszkavízió Instagram poszt generátor")
    p.add_argument("phase", choices=["render", "send"])
    p.add_argument("--date", default=None, help="YYYY-MM-DD (alapból: tegnap)")
    p.add_argument("--ignore-focus", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def run_render(args: argparse.Namespace) -> int:
    report = font_report()
    log.info("Betűtípusok: %s", ", ".join(f"{k}={v}" for k, v in report.items()))
    if uses_fallback_font():
        # GitHub Actions-ben ez sárga figyelmeztetésként jelenik meg a futás oldalán
        print("::warning title=Urbanist betűtípus hiányzik::A betűtípus-letöltés nem sikerült, "
              "ezért DejaVu Sans tartalék-betűvel készültek a képek. Lásd a README 'Betűtípus' részét.")

    target: date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else get_target_date()
    log.info("Célnap: %s", target)

    articles = fetch_articles_for_date(target, ignore_focus=args.ignore_focus)

    rendered: list[RenderedArticle] = []
    for article in articles:
        log.info("Renderelés: [%s] %s (%d bekezdés)", article.rovat, article.title, len(article.paragraphs))
        try:
            rendered.append(RenderedArticle(article=article, images=render_article_images(article)))
        except Exception:  # noqa: BLE001
            log.exception("Nem sikerült renderelni: %s", article.url)

    date_str = target.strftime("%Y. %m. %d.")
    if args.dry_run:
        os.makedirs("dry_run_output", exist_ok=True)
        for ai, item in enumerate(rendered):
            for kind, img in item.images:
                path = os.path.join("dry_run_output", f"{ai}_{kind}.jpg")
                img.save(path, quality=90)
                log.info("Mentve: %s", path)
        return 0

    save_rendered_images(rendered, date_str)
    return 0


def run_send() -> int:
    manifest = load_manifest()
    items = manifest.get("items", [])
    date_str = manifest.get("target_date", "") or "-"

    if not items:
        log.info("Nem volt fókusz cikk.")
        if SEND_EMPTY_DIGEST_NOTICE:
            send_digest([], date_str)
        return 0

    for item in items:
        for img in item["images"]:
            img["url"] = public_url_for(img["filename"])
    send_digest(items, date_str)
    log.info("E-mail elküldve (%d cikk).", len(items))
    return 0


def main() -> int:
    args = parse_args()
    return run_render(args) if args.phase == "render" else run_send()


if __name__ == "__main__":
    sys.exit(main())
