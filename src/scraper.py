"""Cikkek lekérése a WordPress REST API-n: csak a 'Főoldali fókusz cikk' kategóriások."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import (WP_API_POSTS_URL, FOCUS_CATEGORY_NAME, ROVAT_TEMPLATES, DEFAULT_ROVAT,
                    PARAGRAPHS_PER_ARTICLE, MIN_PARAGRAPH_CHARS)

LOCAL_TZ = ZoneInfo("Europe/Budapest")
HEADERS = {"User-Agent": "Deszkavizio-Instagram/1.0"}
TIMEOUT = 30
log = logging.getLogger(__name__)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass
class Article:
    title: str
    url: str
    author: str
    rovat: str
    image_url: str | None
    published_local_date: date
    paragraphs: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


def get_target_date(reference: datetime | None = None) -> date:
    now = (reference or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)
    return (now - timedelta(days=1)).date()


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=LOCAL_TZ)


def pick_rovat(categories: list[str]) -> str:
    known = {norm(k): k for k in ROVAT_TEMPLATES}
    for c in categories:
        if norm(c) in known:
            return known[norm(c)]
    return DEFAULT_ROVAT


def fetch_articles_for_date(target_date: date, ignore_focus: bool = False,
                            max_pages: int = 4) -> list[Article]:
    start = datetime.combine(target_date - timedelta(days=1), datetime.min.time())
    end = datetime.combine(target_date + timedelta(days=2), datetime.min.time())
    out: list[Article] = []
    seen_cats: set[str] = set()
    day_total = 0
    for page in range(1, max_pages + 1):
        resp = requests.get(WP_API_POSTS_URL, params={
            "per_page": 50, "page": page, "_embed": 1, "orderby": "date", "order": "desc",
            "after": start.isoformat(), "before": end.isoformat(),
        }, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        posts = json.loads(resp.content.decode("utf-8-sig", errors="replace").strip())
        if not posts:
            break
        for post in posts:
            if _parse_date(post["date"]).date() != target_date:
                continue
            day_total += 1
            a = _article_from_post(post)
            if not a:
                continue
            seen_cats.update(a.categories)
            if ignore_focus or any(norm(c) == norm(FOCUS_CATEGORY_NAME) for c in a.categories):
                out.append(a)
        if len(posts) < 50:
            break
    if day_total and not out and not ignore_focus:
        log.warning("Aznap %d cikk volt, de egyik sem '%s'. Látott kategóriák: %s",
                    day_total, FOCUS_CATEGORY_NAME, ", ".join(sorted(seen_cats)))
    return out


def _article_from_post(post: dict) -> Article | None:
    title = BeautifulSoup(post.get("title", {}).get("rendered", ""), "html.parser").get_text().strip()
    url = post.get("link", "")
    if not title or not url:
        return None
    emb = post.get("_embedded", {})
    author = "Deszkavízió"
    if emb.get("author"):
        author = emb["author"][0].get("name") or author
    cats = [t["name"] for grp in (emb.get("wp:term") or []) for t in grp
            if t.get("taxonomy") == "category" and t.get("name")]
    image_url = None
    media = emb.get("wp:featuredmedia") or []
    if media:
        m = media[0]
        sizes = (m.get("media_details") or {}).get("sizes") or {}
        image_url = (sizes.get("full") or sizes.get("large") or {}).get("source_url") or m.get("source_url")
    return Article(title=title, url=url, author=author, rovat=pick_rovat(cats),
                   image_url=image_url, published_local_date=_parse_date(post["date"]).date(),
                   paragraphs=extract_paragraphs(post.get("content", {}).get("rendered", "")),
                   categories=cats)


_CREDIT = re.compile(r"^\s*\(?\s*(kiemelt\s*kép|fotó|fotók|képek?|forrás|illusztráció|borítókép)\s*[:\-–]", re.I)
_URL = re.compile(r"https?://|www\.", re.I)


def extract_paragraphs(html: str, n: int = PARAGRAPHS_PER_ARTICLE) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup.select("figure, figcaption, blockquote, script, style, .wp-caption, .wp-caption-text"):
        t.decompose()
    res: list[str] = []
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True).replace("\xa0", " ")).strip()
        text = re.sub(r"\s+([,.;:!?…])", r"\1", text)
        if len(text) < MIN_PARAGRAPH_CHARS or _CREDIT.match(text) or _URL.search(text):
            continue
        if re.fullmatch(r"\(?\s*(fotó|kép)\s*:.*\)?", text, re.I):
            continue
        res.append(text)
        if len(res) >= n:
            break
    return res
