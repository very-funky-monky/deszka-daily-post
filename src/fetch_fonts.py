"""
Letölti az Urbanist betűtípust (OFL licenc, szabadon használható), és a
fonts/ mappába menti a renderer által várt fájlnevekkel:

    Urbanist-Regular.ttf   Urbanist-Medium.ttf
    Urbanist-Bold.ttf      Urbanist-Italic.ttf

Több forrást próbál sorban (az első működő nyer):
  1. Google Fonts CSS API - régi böngésző-azonosítóval TTF-et ad vissza
  2. a google/fonts GitHub tároló változó (variable) fontja
  3. az Urbanist eredeti tervezői tárolója (coreyhu/Urbanist)
Ha a letöltött fájl változó font (több vastagság egyben), a megfelelő
vastagságú statikus példányt készíti belőle (fontTools), mert a renderer
statikus fájlokat vár.

Futtatás:  python fonts/fetch_fonts.py
Kimenet: kiírja, melyik fájl melyik forrásból jött. Ha valamelyik nem
sikerül, a renderer DejaVu Sans tartalékra esik vissza, és a workflow
futás oldalán figyelmeztetés jelenik meg.
"""

from __future__ import annotations

import io
import os
import re
import sys
import urllib.request

FONTS_DIR = os.path.dirname(os.path.abspath(__file__))

# helyi fájlnév -> (dőlt?, vastagság)
TARGETS = {
    "Urbanist-Regular.ttf": (0, 400),
    "Urbanist-Medium.ttf": (0, 500),
    "Urbanist-Bold.ttf": (0, 700),
    "Urbanist-Italic.ttf": (1, 400),
}
REQUIRED = ("Urbanist-Regular.ttf", "Urbanist-Bold.ttf", "Urbanist-Italic.ttf")

CSS_URL = "https://fonts.googleapis.com/css2?family=Urbanist:ital,wght@0,400;0,500;0,700;1,400&display=swap"
GOOGLE_FONTS_RAW = "https://raw.githubusercontent.com/google/fonts/main/ofl/urbanist/"
COREYHU_RAW = [
    "https://raw.githubusercontent.com/coreyhu/Urbanist/main/fonts/",
    "https://raw.githubusercontent.com/coreyhu/Urbanist/master/fonts/",
]
STATIC_NAMES = {"Urbanist-Regular.ttf": "Regular", "Urbanist-Medium.ttf": "Medium",
                "Urbanist-Bold.ttf": "Bold", "Urbanist-Italic.ttf": "Italic"}


def http_get(url: str, user_agent: str | None = None, timeout: int = 40) -> bytes:
    headers = {"User-Agent": user_agent} if user_agent else {}
    req = urllib.request.Request(url, headers=headers)
    # user_agent=None esetén is a Python alap azonosítóját kapja a szerver,
    # ami a Google Fonts-nál TTF formátumot eredményez (woff2 helyett)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_css(css: str) -> list[dict]:
    """A Google Fonts CSS @font-face blokkjaiból (dőlt?, vastagság-tartomány, url)."""
    blocks = []
    for m in re.finditer(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.S):
        subset, body = m.group(1), m.group(2)
        blocks.append((subset, body))
    if not blocks:  # megjegyzés nélküli forma
        blocks = [("", m.group(1)) for m in re.finditer(r"@font-face\s*\{(.*?)\}", css, re.S)]

    out = []
    for subset, body in blocks:
        style = re.search(r"font-style:\s*(\w+)", body)
        weight = re.search(r"font-weight:\s*(\d+)(?:\s+(\d+))?", body)
        url = re.search(r"url\(([^)]+)\)", body)
        if not (style and weight and url):
            continue
        lo = int(weight.group(1))
        hi = int(weight.group(2) or lo)
        out.append({
            "italic": 1 if style.group(1) == "italic" else 0,
            "lo": lo, "hi": hi,
            "url": url.group(1).strip("'\""),
            "subset": subset,
            "format": "ttf" if ".ttf" in url.group(1) else "other",
        })
    return out


def pick_from_css(blocks: list[dict], italic: int, weight: int) -> str | None:
    cands = [b for b in blocks if b["italic"] == italic and b["lo"] <= weight <= b["hi"] and b["format"] == "ttf"]
    if not cands:
        return None
    # a magyar ő/ű a latin-ext készletben van: ha vannak részhalmazok, azt részesítjük előnyben
    for b in cands:
        if b["subset"] == "latin-ext":
            return b["url"]
    return cands[0]["url"]


def is_font(data: bytes) -> bool:
    return len(data) > 20_000 and data[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO")


def to_static(data: bytes, weight: int) -> bytes:
    """Ha változó font, a kért vastagságú statikus példányt adja vissza."""
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(data))
    if "fvar" not in font:
        return data
    from fontTools.varLib import instancer

    static = instancer.instantiateVariableFont(font, {"wght": weight}, inplace=False)
    buf = io.BytesIO()
    static.save(buf)
    return buf.getvalue()


def candidate_urls(local_name: str, italic: int, weight: int, css_blocks: list[dict]):
    url = pick_from_css(css_blocks, italic, weight)
    if url:
        yield "Google Fonts CSS", url
    var_name = "Urbanist-Italic%5Bwght%5D.ttf" if italic else "Urbanist%5Bwght%5D.ttf"
    yield "google/fonts (változó font)", GOOGLE_FONTS_RAW + var_name
    yield "google/fonts (statikus)", GOOGLE_FONTS_RAW + "static/" + f"Urbanist-{STATIC_NAMES[local_name]}.ttf"
    for base in COREYHU_RAW:
        yield "coreyhu/Urbanist (statikus)", base + "ttf/" + f"Urbanist-{STATIC_NAMES[local_name]}.ttf"
        yield "coreyhu/Urbanist (változó)", base + "variable/" + var_name


def fetch_all() -> bool:
    css_blocks: list[dict] = []
    try:
        css = http_get(CSS_URL).decode("utf-8", "replace")
        css_blocks = parse_css(css)
        print(f"Google Fonts CSS: {len(css_blocks)} @font-face blokk")
    except Exception as exc:  # noqa: BLE001
        print(f"Google Fonts CSS nem elérhető: {exc}")

    ok = set()
    for local_name, (italic, weight) in TARGETS.items():
        dest = os.path.join(FONTS_DIR, local_name)
        for source, url in candidate_urls(local_name, italic, weight, css_blocks):
            try:
                data = http_get(url)
                if not is_font(data):
                    raise ValueError(f"nem betűtípus-fájl ({len(data)} bájt)")
                data = to_static(data, weight)
                with open(dest, "wb") as f:
                    f.write(data)
                print(f"OK   {local_name:22s} <- {source}  ({len(data)//1024} KB)")
                ok.add(local_name)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  ..  {local_name}: {source} nem jó ({exc})")
        else:
            print(f"HIBA {local_name}: egyik forrás sem működött")

    missing = [n for n in REQUIRED if n not in ok]
    if missing:
        print(f"\nHiányzó kötelező fájlok: {', '.join(missing)} -> DejaVu Sans tartalék lesz.", file=sys.stderr)
    return not missing


if __name__ == "__main__":
    sys.exit(0 if fetch_all() else 1)
