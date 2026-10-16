"""python main.py render [--date YYYY-MM-DD] [--ignore-focus] [--dry-run]  /  python main.py send"""
from __future__ import annotations
import argparse, logging, os, sys
from datetime import datetime

from config import SEND_EMPTY_DIGEST_NOTICE
from scraper import fetch_articles_for_date, get_target_date
import renderer
from image_host import RenderedArticle, save_rendered_images, load_manifest, public_url_for
import emailer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("deszka-instagram")


def run_render(a) -> int:
    d = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else get_target_date()
    log.info("Célnap: %s | betűk: %s", d, renderer.font_report())
    if renderer.uses_fallback_font():
        print("::warning::Az Urbanist betűtípus nem töltődött le, DejaVu Sans a tartalék!")
    arts = fetch_articles_for_date(d, ignore_focus=a.ignore_focus)
    log.info("Cikkek: %d", len(arts))
    rendered = []
    for art in arts:
        if len(art.paragraphs) < 1:
            log.warning("Nincs használható bekezdés: %s", art.url)
        try:
            rendered.append(RenderedArticle(art, renderer.render_article_images(art)))
        except Exception:  # noqa: BLE001
            log.exception("Renderelési hiba: %s", art.url)
    date_str = d.strftime("%Y. %m. %d.")
    if a.dry_run:
        os.makedirs("dry_run_output", exist_ok=True)
        for i, r in enumerate(rendered):
            for kind, im in r.images:
                im.save(f"dry_run_output/{i}_{kind}.jpg", quality=92)
        return 0
    save_rendered_images(rendered, date_str)
    return 0


def run_send() -> int:
    m = load_manifest()
    items = m.get("items", [])
    if not items and not SEND_EMPTY_DIGEST_NOTICE:
        return 0
    for it in items:
        for im in it["images"]:
            im["url"] = public_url_for(im["filename"])
    emailer.send(items, m.get("target_date") or "-")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["render", "send"])
    p.add_argument("--date")
    p.add_argument("--ignore-focus", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    return run_render(a) if a.phase == "render" else run_send()


if __name__ == "__main__":
    sys.exit(main())
