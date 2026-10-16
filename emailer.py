"""
Az Instagram-képek elküldése e-mailben a Brevo API-n keresztül.

Cikkenként: rovat-címke, szerző, cím (linkként), alatta a három kép
egymás alatt (borító, 1. bekezdés, 2. bekezdés) - ugyanabban a sorrendben,
ahogy a karuszel-posztba érdemes őket betenni. A képre kattintva teljes
méretben megnyílik (onnan menthető).
"""

from __future__ import annotations

import logging

import requests

from config import (
    EMAIL_TO_LIST, EMAIL_FROM, EMAIL_FROM_NAME, BREVO_API_KEY,
    EMAIL_SUBJECT_PREFIX, ROVAT_COLORS,
)

log = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
REQUEST_TIMEOUT = 30
LABELS = {"cover": "Borító", "p1": "Első bekezdés", "p2": "Második bekezdés"}


def send_digest(items: list[dict], target_date_str: str) -> None:
    """items: manifest-elemek, a képeknél kiegészítve 'url' mezővel."""
    if not BREVO_API_KEY:
        raise RuntimeError("Hiányzik a BREVO_API_KEY.")
    if not EMAIL_TO_LIST:
        raise RuntimeError("Hiányzik a DIGEST_EMAIL_TO (vesszővel elválasztott lista).")
    if not EMAIL_FROM:
        raise RuntimeError("Hiányzik a DIGEST_EMAIL_FROM.")

    payload = {
        "sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM},
        "to": [{"email": addr} for addr in EMAIL_TO_LIST],
        "subject": f"{EMAIL_SUBJECT_PREFIX} – {target_date_str}",
        "htmlContent": build_html(items),
    }
    resp = requests.post(
        BREVO_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT,
        headers={"accept": "application/json", "content-type": "application/json", "api-key": BREVO_API_KEY},
    )
    log.info("Brevo válasz: %s %s", resp.status_code, resp.text[:300])
    if resp.status_code >= 300:
        raise RuntimeError(f"Brevo hibát adott vissza: {resp.status_code} {resp.text}")


def build_html(items: list[dict]) -> str:
    blocks = []
    for item in items:
        rovat = item["rovat"]
        r, g, b = ROVAT_COLORS.get(rovat, (41, 234, 215))
        accent = f"#{r:02x}{g:02x}{b:02x}"
        imgs = []
        total = len(item["images"])
        for n, img in enumerate(item["images"], start=1):
            label = LABELS.get(img["kind"], img["kind"])
            imgs.append(f"""
            <div style="font-size:12px;color:#888;margin:18px 0 6px;">{n}/{total} · {label}</div>
            <a href="{img['url']}" target="_blank">
              <img src="{img['url']}" alt="{_esc(label)}" width="480"
                   style="width:100%;max-width:480px;display:block;border-radius:6px;" />
            </a>""")
        blocks.append(f"""
        <tr><td style="padding:0 0 40px 0;border-bottom:1px solid #e5e5e5;">
          <div style="margin-bottom:8px;">
            <span style="display:inline-block;background:#111;color:{accent};font-size:11px;
                         font-weight:bold;padding:4px 12px;border-radius:999px;letter-spacing:.5px;">{_esc(rovat.upper())}</span>
          </div>
          <div style="font-style:italic;color:#555;font-size:13px;">{_esc(item['author'])}</div>
          <a href="{item['url']}" target="_blank"
             style="color:#111827;font-size:19px;font-weight:bold;text-decoration:none;line-height:1.3;display:block;margin-top:4px;">{_esc(item['title'])}</a>
          <a href="{item['url']}" target="_blank" style="color:#0d9488;font-size:12px;">{_esc(item['url'])}</a>
          {''.join(imgs)}
        </td></tr>""")

    body = "".join(blocks) or (
        '<tr><td style="font-family:Arial,sans-serif;color:#555;">'
        "Tegnap nem jelent meg főoldali fókusz cikk.</td></tr>"
    )
    return f"""
    <html><body style="background:#f4f4f5;margin:0;padding:24px 0;font-family:Arial,sans-serif;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
        <table role="presentation" width="520" cellpadding="0" cellspacing="0"
               style="background:#fff;border-radius:10px;padding:24px;">
          <tr><td style="font-size:20px;font-weight:bold;padding-bottom:6px;color:#111827;">
            Instagram posztok – főoldali fókusz cikkek</td></tr>
          <tr><td style="font-size:12px;color:#888;padding-bottom:22px;">
            Koppints a képre a teljes méretű megnyitáshoz, onnan menthető.</td></tr>
          {body}
        </table>
      </td></tr></table>
    </body></html>"""


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
