"""
Cikkenként három Instagram-képet készít a Te saját sablonjaidból:

  cover  - fotó a fotódobozba + szerző (dőlt) + cím (félkövér), középre zárva
  p1/p2  - az első/második bekezdés az idézetkeretben

A sablonok (fejléc, logó, színes sáv, rovat-címke, idézetkeret) érintetlenek
maradnak, csak a fotó és a szöveg kerül rájuk.
"""

from __future__ import annotations

import io
import logging
import os

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import (
    COVER, TEXT_CARD, TEXT_COLOR, FONT_CANDIDATES, TEMPLATE_DIR,
    ROVAT_TEMPLATES, DEFAULT_ROVAT, CANVAS_SIZE,
)
from scraper import Article

log = logging.getLogger(__name__)
REQUEST_TIMEOUT = 30

_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
_FONT_USED: dict[str, str] = {}
_TEMPLATE_CACHE: dict[str, Image.Image] = {}


# ---------------------------------------------------------------------------
# Betűtípus
# ---------------------------------------------------------------------------

def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _FONT_CACHE:
        last_err = None
        for path in FONT_CANDIDATES[kind]:
            try:
                _FONT_CACHE[key] = ImageFont.truetype(path, size)
                _FONT_USED[kind] = os.path.basename(path)
                break
            except OSError as exc:
                last_err = exc
        else:
            raise last_err
    return _FONT_CACHE[key]


def font_report() -> dict[str, str]:
    """Melyik fájlból töltődik be ténylegesen az egyes betűstílus."""
    for kind in FONT_CANDIDATES:
        _font(kind, 20)
    return dict(_FONT_USED)


def uses_fallback_font() -> bool:
    return any(name.startswith("DejaVu") for name in font_report().values())


# ---------------------------------------------------------------------------
# Sablon és kép betöltés
# ---------------------------------------------------------------------------

def _template(kind: str, rovat: str) -> Image.Image:
    """kind: 'cover' vagy 'text'."""
    pair = ROVAT_TEMPLATES.get(rovat) or ROVAT_TEMPLATES[DEFAULT_ROVAT]
    filename = pair[0] if kind == "cover" else pair[1]
    path = os.path.join(TEMPLATE_DIR, filename)
    if path not in _TEMPLATE_CACHE:
        img = Image.open(path).convert("RGB")
        if img.size != CANVAS_SIZE:
            log.warning("A(z) %s sablon mérete %s, de %s kell - átméretezem. "
                        "(Az elrendezés a %s-es vászonra van mérve.)",
                        filename, img.size, CANVAS_SIZE, CANVAS_SIZE)
            img = img.resize(CANVAS_SIZE, Image.LANCZOS)
        _TEMPLATE_CACHE[path] = img
    return _TEMPLATE_CACHE[path].copy()


def _download_image(url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        log.warning("Nem sikerült letölteni a borítóképet (%s): %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Szöveg-segédek
# ---------------------------------------------------------------------------

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = word if not cur else f"{cur} {word}"
        if font.getlength(trial) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
            cur = ""
        if font.getlength(word) <= max_w:
            cur = word
        else:  # a sorszélességnél hosszabb "szó" (pl. URL) - karakterenként törjük
            chunk = ""
            for ch in word:
                if font.getlength(chunk + ch) <= max_w:
                    chunk += ch
                else:
                    lines.append(chunk)
                    chunk = ch
            cur = chunk
    if cur:
        lines.append(cur)
    return lines


_SENTENCE_END = (".", "!", "?", "…", ".”", "!”", "?”", ".\"", "!\"", "?\"", ".»")


def _fit_lines(text: str, kind: str, max_w: float, max_h: float,
               start: int, min_size: int, spacing: float, max_lines: int | None = None):
    """Legnagyobb betűméret, amivel a szöveg elfér; ha a legkisebbel sem, a
    szöveget mondathatárnál (vagy szóhatárnál '…'-tal) csonkolja.
    Visszatér: (sorok, betűméret, csonkolt-e)."""
    def fits(lines, size):
        if max_lines is not None and len(lines) > max_lines:
            return False
        return len(lines) * size * spacing <= max_h

    for size in range(start, min_size - 1, -2):
        lines = _wrap(text, _font(kind, size), max_w)
        if fits(lines, size):
            return lines, size, False

    font = _font(kind, min_size)
    words = text.split()
    lo, hi, best = 1, len(words), 1
    while lo <= hi:  # a legtöbb szó, ami (… -tal) még elfér
        mid = (lo + hi) // 2
        trial = " ".join(words[:mid]) + "…"
        if fits(_wrap(trial, font, max_w), min_size):
            best, lo = mid, mid + 1
        else:
            hi = mid - 1

    cut = best
    for i in range(best, int(best * 0.6), -1):  # inkább mondat végén álljunk meg
        if words[i - 1].endswith(_SENTENCE_END):
            kept = " ".join(words[:i])
            return _wrap(kept, font, max_w), min_size, True
    kept = " ".join(words[:cut]).rstrip(",;:–- ") + "…"
    return _wrap(kept, font, max_w), min_size, True


def _draw_at_cap_top(draw, text, font, x, cap_top_y, fill):
    """A szöveget úgy teszi ki, hogy a nagybetűk teteje cap_top_y-ra essen -
    így a betűtípustól függetlenül ugyanoda kerül."""
    cap_off = font.getbbox("H")[1]
    draw.text((x, cap_top_y - cap_off), text, font=font, fill=fill)


# ---------------------------------------------------------------------------
# 1) Borító
# ---------------------------------------------------------------------------

def render_cover(article: Article) -> Image.Image:
    canvas = _template("cover", article.rovat)
    x0, y0, x1, y1 = COVER["photo_box"]

    photo = _download_image(article.image_url)
    if photo is not None:
        fitted = ImageOps.fit(
            photo, (x1 - x0, y1 - y0), method=Image.LANCZOS,
            centering=(0.5, COVER["photo_focus_y"]),
        )
        canvas.paste(fitted, (x0, y0))
    else:
        log.warning("'%s': nincs borítókép, sötét helykitöltő kerül a fotó helyére", article.title)
        ImageDraw.Draw(canvas).rectangle([x0, y0, x1 - 1, y1 - 1], fill=(30, 30, 36))

    draw = ImageDraw.Draw(canvas)
    cx = COVER["center_x"]

    # szerző (dőlt)
    a = COVER["author"]
    afont = _font("italic", a["font_size"])
    aw = draw.textlength(article.author, font=afont)
    _draw_at_cap_top(draw, article.author, afont, cx - aw / 2, a["cap_top_y"], TEXT_COLOR)

    # cím (félkövér, középre zárt sorok)
    t = COVER["title"]
    avail_h = t["bottom_limit"] - (t["cap_top_y"] - int(t["font_size"] * 0.2))
    lines, size, _ = _fit_lines(
        article.title, "bold", t["max_width"], avail_h,
        t["font_size"], t["min_font_size"], t["line_spacing"], t["max_lines"],
    )
    tfont = _font("bold", size)
    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=tfont)
        _draw_at_cap_top(
            draw, line, tfont, cx - lw / 2,
            t["cap_top_y"] + i * size * t["line_spacing"], TEXT_COLOR,
        )
    return canvas


# ---------------------------------------------------------------------------
# 2-3) Bekezdés-kártya
# ---------------------------------------------------------------------------

def render_text_card(article: Article, text: str) -> Image.Image:
    canvas = _template("text", article.rovat)
    draw = ImageDraw.Draw(canvas)
    c = TEXT_CARD
    x0, y0, x1, y1 = c["box"]
    box_w, box_h = x1 - x0, y1 - y0

    lines, size, truncated = _fit_lines(
        text, "body", box_w, box_h, c["font_size"], c["min_font_size"], c["line_spacing"],
    )
    if truncated:
        log.warning("'%s': a bekezdés túl hosszú, csonkolva lett a kártyán", article.title)

    font = _font("body", size)
    line_h = size * c["line_spacing"]
    block_h = len(lines) * line_h
    y = y0 + (box_h - block_h) / 2 if c["valign"] == "middle" else y0
    for line in lines:
        if c["align"] == "center":
            x = x0 + (box_w - draw.textlength(line, font=font)) / 2
        else:
            x = x0
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += line_h
    return canvas


# ---------------------------------------------------------------------------
# Egy cikk összes képe
# ---------------------------------------------------------------------------

def render_article_images(article: Article) -> list[tuple[str, Image.Image]]:
    images = [("cover", render_cover(article))]
    for i, text in enumerate(article.paragraphs, start=1):
        images.append((f"p{i}", render_text_card(article, text)))
    return images
