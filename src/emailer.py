"""E-mail küldés Brevo API-n (képek GitHub raw URL-ről)."""
from __future__ import annotations
import logging
import requests
from config import (EMAIL_TO_LIST, EMAIL_FROM, EMAIL_FROM_NAME, BREVO_API_KEY,
                    EMAIL_SUBJECT_PREFIX, ROVAT_COLORS)

log = logging.getLogger(__name__)
LABELS = {"cover": "1/3 · Borító", "p1": "2/3 · Első bekezdés", "p2": "3/3 · Második bekezdés"}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_html(items: list[dict], date_str: str) -> str:
    blocks = []
    for it in items:
        col = ROVAT_COLORS.get(it["rovat"], (41, 234, 215))
        hexc = "#%02x%02x%02x" % col
        imgs = []
        n = len(it["images"])
        for i, im in enumerate(it["images"], 1):
            label = LABELS.get(im["kind"], im["kind"]).replace("/3", f"/{n}")
            imgs.append(f'''<div style="margin:12px 0 4px;font-size:12px;color:#6b7280;">{label}</div>
<a href="{im["url"]}" target="_blank"><img src="{im["url"]}" alt="{_esc(it["title"])}" style="width:100%;max-width:420px;display:block;border-radius:8px;"></a>''')
        blocks.append(f'''<tr><td style="padding:0 0 36px;font-family:Arial,sans-serif;">
<span style="display:inline-block;background:{hexc};color:#111;font-size:11px;font-weight:bold;padding:3px 10px;border-radius:999px;">{_esc(it["rovat"].upper())}</span>
<div style="color:#6b7280;font-style:italic;font-size:13px;margin-top:6px;">{_esc(it["author"])}</div>
<a href="{it["url"]}" style="color:#111827;font-size:18px;font-weight:bold;text-decoration:none;display:block;margin:4px 0;">{_esc(it["title"])}</a>
<a href="{it["url"]}" style="color:#0d9488;font-size:12px;">{_esc(it["url"])}</a>
{"".join(imgs)}</td></tr>''')
    body = "".join(blocks) or '<tr><td style="font-family:Arial,sans-serif;color:#555;">Tegnap nem jelent meg főoldali fókusz cikk.</td></tr>'
    return f'''<html><body style="background:#f4f4f5;margin:0;padding:24px 0;"><table role="presentation" width="100%"><tr><td align="center">
<table role="presentation" width="480" style="background:#fff;border-radius:10px;padding:24px;">
<tr><td style="font-family:Arial,sans-serif;font-size:20px;font-weight:bold;padding-bottom:20px;color:#111827;">Instagram posztok – {_esc(date_str)}</td></tr>
{body}</table></td></tr></table></body></html>'''


def send(items: list[dict], date_str: str) -> None:
    if not BREVO_API_KEY: raise RuntimeError("Hiányzik a BREVO_API_KEY.")
    if not EMAIL_TO_LIST: raise RuntimeError("Hiányzik a DIGEST_EMAIL_TO.")
    if not EMAIL_FROM: raise RuntimeError("Hiányzik a DIGEST_EMAIL_FROM.")
    payload = {"sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM},
               "to": [{"email": a} for a in EMAIL_TO_LIST],
               "subject": f"{EMAIL_SUBJECT_PREFIX} – {date_str}",
               "htmlContent": build_html(items, date_str)}
    r = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, timeout=30,
                      headers={"accept": "application/json", "api-key": BREVO_API_KEY})
    log.info("Brevo: %s %s", r.status_code, r.text[:200])
    if r.status_code >= 300:
        raise RuntimeError(f"Brevo hiba: {r.status_code} {r.text}")
