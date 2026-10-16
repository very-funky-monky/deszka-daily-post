"""Képek mentése a repóba (images/latest) + manifest; nyilvános URL-ek."""
from __future__ import annotations
import json, logging, os
from dataclasses import dataclass
from PIL import Image
from config import GITHUB_REPOSITORY, GITHUB_BRANCH, IMAGES_REPO_DIR, IMAGES_COMMIT
from scraper import Article

log = logging.getLogger(__name__)
ROOT = os.path.join(os.path.dirname(__file__), "..")
IMG_DIR = os.path.join(ROOT, IMAGES_REPO_DIR)
MANIFEST = os.path.join(IMG_DIR, "manifest.json")


@dataclass
class RenderedArticle:
    article: Article
    images: list  # [(kind, PIL.Image)]


def save_rendered_images(rendered, date_str: str, out_dir: str = IMG_DIR) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for n in os.listdir(out_dir):
        if n.endswith(".jpg"):
            os.remove(os.path.join(out_dir, n))
    items = []
    for idx, r in enumerate(rendered):
        a = r.article
        imgs = []
        for kind, im in r.images:
            fn = f"{idx}_{kind}.jpg"
            im.save(os.path.join(out_dir, fn), "JPEG", quality=92)
            imgs.append({"kind": kind, "filename": fn})
        items.append({"title": a.title, "author": a.author, "rovat": a.rovat,
                      "url": a.url, "images": imgs})
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"target_date": date_str, "items": items}, f, ensure_ascii=False, indent=2)


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST):
        return {"target_date": "", "items": []}
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def public_url_for(filename: str) -> str:
    if not GITHUB_REPOSITORY:
        raise RuntimeError("Hiányzik a GITHUB_REPOSITORY.")
    ref = IMAGES_COMMIT or GITHUB_BRANCH
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{ref}/{IMAGES_REPO_DIR}/{filename}"
