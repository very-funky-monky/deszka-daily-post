"""
A Brevo API nem támogat valódi beágyazott (cid) képet, csak nyilvános URL-t.
Ezért a generált képeket a repóba mentjük (images/latest/), a workflow
commitolja és pusholja őket, az e-mail pedig a raw.githubusercontent.com
linkjeikre hivatkozik.

A linkek a commit azonosítójára (SHA) mutatnak a branch helyett, így:
  - nincs CDN-gyorsítótár miatti "tegnapi kép" probléma,
  - a régi levelekben is az eredeti képek látszanak (a fájlokat minden nap
    felülírjuk, de a régi commit tartalma megmarad).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from PIL import Image

from config import GITHUB_REPOSITORY, GITHUB_BRANCH, IMAGES_COMMIT, IMAGES_REPO_DIR
from scraper import Article

log = logging.getLogger(__name__)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
IMAGES_DIR_ABS = os.path.join(REPO_ROOT, IMAGES_REPO_DIR)
MANIFEST_PATH = os.path.join(IMAGES_DIR_ABS, "manifest.json")


@dataclass
class RenderedArticle:
    article: Article
    images: list[tuple[str, Image.Image]]  # (kind, kép): cover / p1 / p2


def save_rendered_images(rendered: list[RenderedArticle], target_date_str: str) -> None:
    os.makedirs(IMAGES_DIR_ABS, exist_ok=True)
    for name in os.listdir(IMAGES_DIR_ABS):  # előző napi képek törlése
        if name.endswith(".jpg"):
            os.remove(os.path.join(IMAGES_DIR_ABS, name))

    manifest = {"target_date": target_date_str, "items": []}
    for ai, item in enumerate(rendered):
        a = item.article
        entry = {"title": a.title, "author": a.author, "rovat": a.rovat, "url": a.url, "images": []}
        for kind, img in item.images:
            filename = f"{ai}_{kind}.jpg"
            img.save(os.path.join(IMAGES_DIR_ABS, filename), format="JPEG", quality=90, optimize=True)
            entry["images"].append({"filename": filename, "kind": kind})
        manifest["items"].append(entry)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log.info("Elmentve: %d cikk képei + manifest.json (%s)", len(rendered), IMAGES_DIR_ABS)


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return {"target_date": "", "items": []}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def public_url_for(filename: str) -> str:
    if not GITHUB_REPOSITORY:
        raise RuntimeError(
            "Hiányzik a GITHUB_REPOSITORY környezeti változó (GitHub Actions-ben automatikus)."
        )
    ref = IMAGES_COMMIT or GITHUB_BRANCH
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{ref}/{IMAGES_REPO_DIR}/{filename}"
