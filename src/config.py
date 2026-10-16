"""Beállítások – Deszkavízió Instagram poszt-generátor."""
import os

SITE_BASE_URL = "https://deszkavizio.hu"
WP_API_POSTS_URL = f"{SITE_BASE_URL}/wp-json/wp/v2/posts"

# Csak azok a cikkek kellenek, amelyeknél ez a kategória be van pipálva.
FOCUS_CATEGORY_NAME = os.environ.get("FOCUS_CATEGORY_NAME") or "Főoldali fókusz cikk"

CANVAS_SIZE = (1080, 1350)

# 1. kép (borító): fotó + szerző (dőlt) + cím (félkövér), fehér szöveg
COVER = {
    "photo_box": (0, 181, 1080, 789),
    "photo_focus_y": 0.35,
    "center_x": 540,
    "author": {"cap_top_y": 960, "font_size": 30},
    "title": {
        "cap_top_y": 1024, "max_width": 864, "font_size": 62, "min_font_size": 40,
        "line_spacing": 1.21, "max_lines": 4, "bottom_limit": 1310,
    },
}

# 2-3. kép: idézetkártya a bekezdéssel
TEXT_CARD = {
    "box": (170, 290, 910, 1145),
    "font_size": 54, "min_font_size": 30, "line_spacing": 1.38,
}

TEXT_COLOR = (255, 255, 255)
PARAGRAPHS_PER_ARTICLE = 2
MIN_PARAGRAPH_CHARS = 40

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
def _f(*names):
    return [os.path.join(FONT_DIR, n) for n in names]
FONT_CANDIDATES = {
    "bold": _f("Urbanist-Bold.ttf", "DejaVuSans-Bold.ttf"),
    "italic": _f("Urbanist-Italic.ttf", "DejaVuSans-Oblique.ttf"),
    "body": _f("Urbanist-Medium.ttf", "Urbanist-Regular.ttf", "DejaVuSans.ttf"),
}

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
DEFAULT_ROVAT = "Színház"
ROVAT_COLORS = {
    "Színház": (27, 245, 210), "Mozgókép": (28, 246, 212), "Tánc": (255, 48, 255),
    "Opera": (254, 196, 73), "Zene": (131, 118, 255),
    "Képzőművészet": (255, 79, 211), "Könyv": (182, 231, 0),
}

EMAIL_TO_LIST = [e.strip() for e in os.environ.get("DIGEST_EMAIL_TO", "").split(",") if e.strip()]
EMAIL_FROM = os.environ.get("DIGEST_EMAIL_FROM", "")
EMAIL_FROM_NAME = os.environ.get("DIGEST_EMAIL_FROM_NAME") or "Deszkavízió Instagram"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
EMAIL_SUBJECT_PREFIX = "Instagram posztok"
SEND_EMPTY_DIGEST_NOTICE = True

GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
IMAGES_COMMIT = os.environ.get("IMAGES_COMMIT", "")
IMAGES_REPO_DIR = "images/latest"
