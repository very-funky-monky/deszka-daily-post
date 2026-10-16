"""
A "Főoldali fókusz cikk" kategóriába tartozó cikkek lekérése egy adott
naptári napra (alapból "tegnap", Europe/Budapest szerint) a WordPress REST
API-ról - a címmel, szerzővel, borítóképpel, rovattal és az első bekezdésekkel.

Fontos részlet: a cikkeknek több kategóriájuk van (pl. "Hírek, Könyv" vagy
"Főoldali fókusz cikk, Kritikák, Zene"). A sablont a ROVAT dönti el
(Színház, Mozgókép, Tánc, Opera, Zene, Képzőművészet, Könyv), nem az első
kategória - ezért a rovatot a kategórianevek közül külön keressük ki.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import (
    WP_API_POSTS_URL, FOCUS_CATEGORY_NAME, ROVAT_TEMPLATES, DEFAULT_ROVAT,
    PARAGRAPHS_PER_ARTICLE, MIN_PARAGRAPH_CHARS,
)

LOCAL_TZ = ZoneInfo("Europe/Budapest")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DeszkavizioInstagramBot/1.0)"}
REQUEST_TIMEOUT = 30
PER_PAGE = 50

log = logging.getLogger(__name__)


def norm(text: str) -> str:
    """Ékezet-, kis/nagybetű- és írásjel-független összehasonlításhoz."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text)


FOCUS_NORM = norm(FOCUS_CATEGORY_NAME)
ROVAT_BY_NORM = {norm(name): name for name in ROVAT_TEMPLATES}


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
    now_local = (reference or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)
    return (now_local - timedelta(days=1)).date()


# ---------------------------------------------------------------------------
# Lekérés
# ---------------------------------------------------------------------------

def fetch_articles_for_date(target_date: date, ignore_focus: bool = False, max_pages: int = 4) -> list[Article]:
    """A célnapon megjelent fókusz cikkek. ignore_focus=True: az összes cikk
    (teszteléshez, ha épp nincs fókusz cikk)."""
    # a határokat egy-egy nappal kitoljuk, a pontos napot úgyis kliens oldalon szűrjük
    after = (target_date - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    before = (target_date + timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")

    articles: list[Article] = []
    posts_that_day = 0
    seen_categories: set[str] = set()

    for page in range(1, max_pages + 1):
        resp = requests.get(
            WP_API_POSTS_URL,
            params={
                "per_page": PER_PAGE, "page": page, "_embed": 1,
                "orderby": "date", "order": "desc",
                "after": after, "before": before,
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 400:  # elfogytak az oldalak
            break
        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            break

        for post in posts:
            if _parse_wp_date(post["date"]).date() != target_date:
                continue
            posts_that_day += 1
            terms = _terms(post)
            seen_categories.update(name for tax, name in terms if tax == "category")

            is_focus = any(norm(name) == FOCUS_NORM for _, name in terms)
            if not ignore_focus and not is_focus:
                continue

            article = _article_from_post(post, terms)
            if article:
                articles.append(article)

        if len(posts) < PER_PAGE:
            break

    log.info(
        "%s: %d cikk jelent meg, ebből %d került be (fókusz szűrés: %s)",
        target_date, posts_that_day, len(articles), "ki" if ignore_focus else "be",
    )
    if posts_that_day and not articles and not ignore_focus:
        log.warning(
            "Aznap volt cikk, de egyik sem a '%s' kategóriában. A látott kategóriák: %s. "
            "Ha a kategória neve más, add meg a FOCUS_CATEGORY_NAME értékét a config.py-ban.",
            FOCUS_CATEGORY_NAME, ", ".join(sorted(seen_categories)) or "-",
        )
    return articles


def _parse_wp_date(date_str: str) -> datetime:
    # a WP "date" mezője a site helyi ideje, időzóna nélkül
    return datetime.fromisoformat(date_str).replace(tzinfo=LOCAL_TZ)


def _terms(post: dict) -> list[tuple[str, str]]:
    """(taxonómia, név) párok az _embed-ben kapott kifejtett kategóriákból/címkékből."""
    out = []
    for group in post.get("_embedded", {}).get("wp:term") or []:
        for term in group:
            if term.get("name"):
                out.append((term.get("taxonomy", ""), term["name"]))
    return out


def pick_rovat(category_names: list[str]) -> str:
    """Az első olyan kategória, ami egy ismert rovat; különben az alapértelmezett."""
    for name in category_names:
        if norm(name) in ROVAT_BY_NORM:
            return ROVAT_BY_NORM[norm(name)]
    log.warning("Nincs ismert rovat a kategóriák között (%s) -> %s sablon", category_names, DEFAULT_ROVAT)
    return DEFAULT_ROVAT


def _article_from_post(post: dict, terms: list[tuple[str, str]]) -> Article | None:
    title = BeautifulSoup(post.get("title", {}).get("rendered", ""), "html.parser").get_text().strip()
    url = post.get("link", "")
    if not title or not url:
        return None

    embedded = post.get("_embedded", {})
    author = "Deszkavízió"
    authors = embedded.get("author") or []
    if authors and authors[0].get("name"):
        author = authors[0]["name"]

    category_names = [name for tax, name in terms if tax == "category"]

    image_url = None
    media = embedded.get("wp:featuredmedia") or []
    if media:
        m = media[0]
        # az eredeti (full) méret kell: az Instagram-kép 1080 px széles
        image_url = m.get("source_url") or (
            m.get("media_details", {}).get("sizes", {}).get("large", {}).get("source_url")
        )

    paragraphs = extract_paragraphs(post.get("content", {}).get("rendered", ""))
    if len(paragraphs) < PARAGRAPHS_PER_ARTICLE:
        log.warning("'%s': csak %d használható bekezdés van", title, len(paragraphs))

    return Article(
        title=title,
        url=url,
        author=author,
        rovat=pick_rovat(category_names),
        image_url=image_url,
        published_local_date=_parse_wp_date(post["date"]).date(),
        paragraphs=paragraphs,
        categories=category_names,
    )


# ---------------------------------------------------------------------------
# Bekezdések
# ---------------------------------------------------------------------------

_CAPTION_START = re.compile(r"^(kiemelt k[ée]p|fot[óo]k?|k[ée]p|forr[áa]s|borít[óo]k[ée]p)\s*:", re.I)
_CAPTION_PHOTO = re.compile(r"\(\s*fot[óo]\s*:[^)]*\)\s*$", re.I)


def extract_paragraphs(html: str, limit: int = PARAGRAPHS_PER_ARTICLE) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    result: list[str] = []
    for p in soup.find_all("p"):
        # képaláírások, idézetblokkok kihagyása
        if p.find_parent(["figure", "figcaption", "blockquote"]):
            continue
        if any("caption" in " ".join(par.get("class", [])) for par in p.find_parents(True)):
            continue

        for br in p.find_all("br"):
            br.replace_with(" ")
        text = p.get_text("")
        text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()

        if len(text) < MIN_PARAGRAPH_CHARS:
            continue
        if _CAPTION_START.match(text):
            continue
        if _CAPTION_PHOTO.search(text) and len(text) < 220:
            continue
        if re.fullmatch(r"https?://\S+", text):
            continue

        result.append(text)
        if len(result) >= limit:
            break
    return result
