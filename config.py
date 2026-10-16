"""
Központi beállítások - Deszkavízió Instagram poszt generátor.

Cikkenként 3 kép készül (1080x1350, Instagram 4:5):
  1. borító: fotó + rovat-címke + szerző + cím
  2. az első bekezdés idézetkártyán
  3. a második bekezdés idézetkártyán
"""

import os

# ---------------------------------------------------------------------------
# Forrás oldal
# ---------------------------------------------------------------------------
SITE_BASE_URL = "https://deszkavizio.hu"
WP_API_POSTS_URL = f"{SITE_BASE_URL}/wp-json/wp/v2/posts"

# Csak azokat a cikkeket dolgozzuk fel, amelyeknél ez a kategória be van
# pipálva. (Kis/nagybetű és ékezet nem számít az egyezésnél.)
FOCUS_CATEGORY_NAME = os.environ.get("FOCUS_CATEGORY_NAME") or "Főoldali fókusz cikk"

# ---------------------------------------------------------------------------
# Vászon és elrendezés (pixel, 1080x1350) - a sablonképeidről mérve
# ---------------------------------------------------------------------------
CANVAS_SIZE = (1080, 1350)

COVER = {
    # a fotó helye a sablonon (x0, y0, x1, y1) - alatta a színes sáv a sablon része
    "photo_box": (0, 181, 1080, 789),
    # melyik magasságra igazítsa a vágást, ha a fotó magasabb a dobozánál
    # (0 = felső szél, 0.5 = közép) - a portréknál a fej általában felül van
    "photo_focus_y": 0.35,
    "center_x": 540,
    # a szöveg "nagybetű-tető" (cap height) vonala - a betűtípustól függetlenül
    # ide igazodik, a test_1.jpg mintád alapján
    "author": {"cap_top_y": 960, "font_size": 30},
    "title": {
        "cap_top_y": 1024,
        "max_width": 864,
        "font_size": 62,
        "min_font_size": 40,
        "line_spacing": 1.21,
        "max_lines": 4,
        "bottom_limit": 1310,
    },
}

TEXT_CARD = {
    # a szöveg doboza az idézetkereten belül (x0, y0, x1, y1); a bal felső és
    # jobb alsó idézőjelet kikerüli
    "box": (170, 290, 910, 1145),
    "font_size": 54,
    "min_font_size": 30,
    "line_spacing": 1.38,
    "align": "left",      # "left" vagy "center"
    "valign": "middle",   # "top" vagy "middle"
}

TEXT_COLOR = (255, 255, 255)

# ---------------------------------------------------------------------------
# Bekezdés-kinyerés a cikkből
# ---------------------------------------------------------------------------
PARAGRAPHS_PER_ARTICLE = 2
MIN_PARAGRAPH_CHARS = 40   # ennél rövidebb sort nem tekintünk bekezdésnek

# ---------------------------------------------------------------------------
# Betűtípus - Urbanist (a fonts/fetch_fonts.py tölti le), DejaVu a tartalék
# ---------------------------------------------------------------------------
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")


def _fp(name):
    return os.path.join(FONT_DIR, name)


FONT_CANDIDATES = {
    "bold": [_fp("Urbanist-Bold.ttf"), _fp("DejaVuSans-Bold.ttf")],
    "italic": [_fp("Urbanist-Italic.ttf"), _fp("DejaVuSans-Oblique.ttf")],
    # a bekezdésekhez Medium vastagság: sötét háttéren olvashatóbb a Regularnál
    "body": [_fp("Urbanist-Medium.ttf"), _fp("Urbanist-Regular.ttf"), _fp("DejaVuSans.ttf")],
}

# ---------------------------------------------------------------------------
# Sablonok rovatonként: (borító, szöveges kártya)
# ---------------------------------------------------------------------------
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

ROVAT_TEMPLATES = {
    "Színház": ("cover_szinhaz.jpg", "text_szinhaz.jpg"),
    "Mozgókép": ("cover_mozgokep.jpg", "text_mozgokep.jpg"),
    "Tánc": ("cover_tanc.jpg", "text_tanc.jpg"),
    "Opera": ("cover_opera.jpg", "text_opera.jpg"),
    "Zene": ("cover_zene.jpg", "text_zene.jpg"),
    "Képzőművészet": ("cover_kepzomuveszet.jpg", "text_kepzomuveszet.jpg"),
    "Könyv": ("cover_konyv.jpg", "text_konyv.jpg"),
}
# Ha egy cikknek egyik rovat-kategóriája sincs (pl. csak "Hírek"), ezt kapja:
DEFAULT_ROVAT = "Színház"

# Az e-mailben a rovat-címke színe (a sablonok logószínéből mérve)
ROVAT_COLORS = {
    "Színház": (27, 245, 210),
    "Mozgókép": (28, 246, 212),
    "Tánc": (255, 48, 255),
    "Opera": (254, 196, 73),
    "Zene": (131, 118, 255),
    "Képzőművészet": (255, 79, 211),
    "Könyv": (182, 231, 0),
}

# ---------------------------------------------------------------------------
# E-mail (Brevo) - DIGEST_EMAIL_TO: vesszővel elválasztott címek
# ---------------------------------------------------------------------------
EMAIL_TO_LIST = [e.strip() for e in os.environ.get("DIGEST_EMAIL_TO", "").split(",") if e.strip()]
EMAIL_FROM = os.environ.get("DIGEST_EMAIL_FROM", "")
EMAIL_FROM_NAME = os.environ.get("DIGEST_EMAIL_FROM_NAME") or "Deszkavízió Instagram"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
EMAIL_SUBJECT_PREFIX = "Instagram posztok"

# Ha nem volt fókusz cikk, küldjön-e rövid "nincs" levelet, vagy maradjon csendben.
SEND_EMPTY_DIGEST_NOTICE = True

# ---------------------------------------------------------------------------
# Kép-hosztolás a GitHub repóból (a Brevo nem tud beágyazott cid-es képet).
# A linkek a commit azonosítójára (SHA) mutatnak, ezért a régi levelekben is
# az eredeti képek maradnak látszódni.
# ---------------------------------------------------------------------------
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
IMAGES_COMMIT = os.environ.get("IMAGES_COMMIT", "")
IMAGES_REPO_DIR = "images/latest"
