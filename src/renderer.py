"""Képgenerálás: borító (fotó + szerző + cím) és idézetkártyák (1-2. bekezdés)."""
from __future__ import annotations

import io
import logging
import os
import re

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import (COVER, TEXT_CARD, TEXT_COLOR, FONT_CANDIDATES, TEMPLATE_DIR,
                    ROVAT_TEMPLATES, DEFAULT_ROVAT)
from scraper import Article

log = logging.getLogger(__name__)
_FONTS: dict = {}
_USED: dict = {}
_TPL: dict = {}


def _font(kind: str, size: int):
    key = (kind, size)
    if key not in _FONTS:
        err = None
        for path in FONT_CANDIDATES[kind]:
            try:
                _FONTS[key] = ImageFont.truetype(path, size)
                _USED[kind] = os.path.basename(path)
                break
            except OSError as e:
                err = e
        else:
            raise err
    return _FONTS[key]


def font_report() -> dict:
    for k in FONT_CANDIDATES:
        _font(k, 20)
    return dict(_USED)


def uses_fallback_font() -> bool:
    return any(v.startswith("DejaVu") for v in font_report().values())


def _template(kind: str, rovat: str) -> Image.Image:
    pair = ROVAT_TEMPLATES.get(rovat) or ROVAT_TEMPLATES[DEFAULT_ROVAT]
    path = os.path.join(TEMPLATE_DIR, pair[0 if kind == "cover" else 1])
    if path not in _TPL:
        _TPL[path] = Image.open(path).convert("RGB")
    return _TPL[path].copy()


def _download_image(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Deszkavizio-Instagram/1.0"})
        r.raise_for_status()
        return ImageOps.exif_transpose(Image.open(io.BytesIO(r.content))).convert("RGB")
    except Exception as e:  # noqa: BLE001
        log.warning("Kép letöltése sikertelen (%s): %s", url, e)
        return None


def _w(draw, text, font):
    return draw.textlength(text, font=font)


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if _w(draw, cand, font) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _cap_offset(font) -> int:
    return font.getbbox("H")[1]


def _draw_at_cap_top(draw, xy, text, font, anchor_x="center"):
    x, cap_top = xy
    y = cap_top - _cap_offset(font)
    if anchor_x == "center":
        x = x - _w(draw, text, font) / 2
    draw.text((x, y), text, font=font, fill=TEXT_COLOR)


def render_cover(article: Article) -> Image.Image:
    img = _template("cover", article.rovat)
    x0, y0, x1, y1 = COVER["photo_box"]
    photo = _download_image(article.image_url)
    if photo is None:
        log.warning("Borítókép nélkül készül a borító: %s (kép: %s)", article.title, article.image_url)
    if photo is not None:
        img.paste(ImageOps.fit(photo, (x1 - x0, y1 - y0), Image.LANCZOS,
                               centering=(0.5, COVER["photo_focus_y"])), (x0, y0))
    draw = ImageDraw.Draw(img)
    cx = COVER["center_x"]
    a = COVER["author"]
    _draw_at_cap_top(draw, (cx, a["cap_top_y"]), article.author, _font("italic", a["font_size"]))
    t = COVER["title"]
    size = t["font_size"]
    while True:
        font = _font("bold", size)
        lines = _wrap(draw, article.title, font, t["max_width"])
        lh = size * t["line_spacing"]
        bottom = t["cap_top_y"] + (len(lines) - 1) * lh + size * 0.75
        if (len(lines) <= t["max_lines"] and bottom <= t["bottom_limit"]) or size <= t["min_font_size"]:
            break
        size -= 2
    y = t["cap_top_y"]
    for line in lines:
        _draw_at_cap_top(draw, (cx, y), line, font)
        y += lh
    return img


def _truncate_to_sentence(text: str, keep: float = 0.85) -> str:
    cut = text[: max(1, int(len(text) * keep))]
    m = list(re.finditer(r"[.!?…](?=\s|$)", cut))
    if m and m[-1].end() > len(cut) * 0.5:
        return cut[: m[-1].end()] + " …"
    return cut.rsplit(" ", 1)[0].rstrip(",;:- ") + "…"


def render_text_card(article: Article, text: str) -> Image.Image:
    img = _template("text", article.rovat)
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = TEXT_CARD["box"]
    bw, bh = x1 - x0, y1 - y0
    while True:
        size = TEXT_CARD["font_size"]
        while True:
            font = _font("body", size)
            lines = _wrap(draw, text, font, bw)
            lh = size * TEXT_CARD["line_spacing"]
            if len(lines) * lh <= bh or size <= TEXT_CARD["min_font_size"]:
                break
            size -= 2
        if len(lines) * lh <= bh:
            break
        text = _truncate_to_sentence(text)
    total = (len(lines) - 1) * lh + size
    y = y0 + (bh - total) / 2
    for line in lines:
        draw.text((x0, y), line, font=font, fill=TEXT_COLOR)
        y += lh
    return img


def render_article_images(article: Article):
    out = [("cover", render_cover(article))]
    for i, p in enumerate(article.paragraphs, 1):
        out.append((f"p{i}", render_text_card(article, p)))
    return out
