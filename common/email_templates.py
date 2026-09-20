"""Branded email HTML — the record's own voices in a mail client.

Email clients strip <style> and most web fonts, so everything is inline-styled
table layout with the DESIGN.md palette and the three voices as font stacks:
Newsreader (display) → Georgia; Hind (reading) → the system sans; JetBrains
Mono (provenance) → the system mono. Apple Mail honours the @import and sets
the real faces; Gmail falls through to the stacks. One shape for every email:
masthead (the mark and "Prism", the host in mono) · a mono meta line · the
title in the record voice · the paragraphs · a facts list on hairlines with
mono labels · one primary pill · a rule · why you got this, in mono.

The Prism Rule holds here too: no colour but the accent on the one button and
the spectrum in the mark itself. The old three-hue bar was a gradient by
another name and is gone (2026-09-21).
"""

from __future__ import annotations

import html as _html

from common.config import get_settings

# design/tokens.json, light. Email has no dark mode we control; the meta tags
# below ask clients not to invent one.
BG = "#FAFAF7"
SURFACE = "#FFFFFF"
INK = "#15151A"
INK_2 = "#4B4D57"
INK_3 = "#6C6F7A"
LINE = "#E6E6E1"
ACCENT_FILL = "#6B4EF6"

DISPLAY = "Newsreader, Georgia, 'Times New Roman', serif"
SANS = "Hind, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

FONTS_CSS = "https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500&family=Hind:wght@400;600&family=JetBrains+Mono&display=swap"
PROMISE = "Follow the story, not the headlines."
ENTITY = "Prism Media Intelligence LLP"

_MONO_LABEL = f"font-family:{MONO};font-size:11px;line-height:1.5;letter-spacing:0.03em;text-transform:uppercase;color:{INK_3};"


def _web() -> str:
    return get_settings().prism_web_url.rstrip("/")


def _host() -> str:
    return _web().split("://", 1)[-1].removeprefix("www.")


def shell(
    *,
    title: str,
    meta: str,
    paragraphs: list[str],
    cta: tuple[str, str] | None,
    footer: str,
    facts: list[tuple[str, str]] | None = None,
    aside: str | None = None,
    preheader: str | None = None,
) -> str:
    """One email. `paragraphs`, `facts` values and `footer` are taken as already
    escaped HTML (callers escape their own strings, so a value may carry a <b>);
    `title`, `meta`, the labels and the button are escaped here."""
    web = _web()
    body = "".join(
        f'<p style="margin:12px 0 0;font-family:{SANS};font-size:16px;line-height:1.6;color:{INK_2};">{p}</p>' for p in paragraphs
    )
    facts_html = ""
    if facts:
        rows = "".join(
            f'<tr><td style="padding:10px 0;border-top:1px solid {LINE};{_MONO_LABEL}white-space:nowrap;vertical-align:top;width:38%;">{_html.escape(k)}</td>'
            f'<td style="padding:10px 0 10px 16px;border-top:1px solid {LINE};font-family:{SANS};font-size:14.5px;line-height:1.5;color:{INK};vertical-align:top;">{v}</td></tr>'
            for k, v in facts
        )
        facts_html = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0 0;border-bottom:1px solid {LINE};">{rows}</table>'
    cta_html = ""
    if cta:
        label, href = cta
        cta_html = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:26px 0 0;"><tr>'
            f'<td style="border-radius:999px;background:{ACCENT_FILL};">'
            f'<a href="{_html.escape(href, quote=True)}" style="display:inline-block;padding:13px 26px;font-family:{SANS};font-size:15px;font-weight:600;line-height:1.2;color:#FFFFFF;text-decoration:none;border-radius:999px;">{_html.escape(label)}</a>'
            f"</td></tr></table>"
        )
    aside_html = (
        f'<p style="margin:22px 0 0;font-family:{MONO};font-size:12px;line-height:1.6;color:{INK_2};word-break:break-all;">{aside}</p>' if aside else ""
    )
    pre = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">{_html.escape(preheader)}</div>' if preheader else ""
    )
    return f"""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{_html.escape(title)}</title>
<style>@import url('{FONTS_CSS}');</style>
</head>
<body style="margin:0;padding:0;background:{BG};-webkit-text-size-adjust:100%;">
{pre}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};padding:32px 12px;">
<tr><td align="center">
  <table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;background:{SURFACE};border:1px solid {LINE};border-radius:14px;">
    <tr><td style="padding:22px 32px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="vertical-align:middle;">
          <img src="{web}/brand/prism-mark-512.png" width="22" height="22" alt="" style="display:inline-block;vertical-align:-4px;border:0;">
          <span style="display:inline-block;margin-left:8px;font-family:{DISPLAY};font-size:20px;font-weight:500;letter-spacing:-0.01em;color:{INK};vertical-align:middle;">Prism</span>
        </td>
        <td align="right" style="vertical-align:middle;{_MONO_LABEL}">{_html.escape(_host())}</td>
      </tr></table>
      <div style="height:1px;background:{LINE};margin:18px 0 0;font-size:0;line-height:0;">&nbsp;</div>
    </td></tr>
    <tr><td style="padding:22px 32px 32px;">
      <p style="margin:0;{_MONO_LABEL}">{_html.escape(meta)}</p>
      <h1 style="margin:10px 0 0;font-family:{DISPLAY};font-size:28px;line-height:1.2;font-weight:500;letter-spacing:-0.01em;color:{INK};">{_html.escape(title)}</h1>
      {body}
      {facts_html}
      {cta_html}
      {aside_html}
      <div style="height:1px;background:{LINE};margin:28px 0 0;font-size:0;line-height:0;">&nbsp;</div>
      <p style="margin:16px 0 0;font-family:{MONO};font-size:11px;line-height:1.6;letter-spacing:0.02em;color:{INK_3};">{footer}</p>
      <p style="margin:14px 0 0;font-family:{SANS};font-size:13px;line-height:1.5;color:{INK_3};">Prism · {ENTITY} · {PROMISE}</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>"""


def magic_link_email(*, link: str, ttl_min: int, to: str) -> tuple[str, str]:
    """Return (plaintext, html) for the sign-in email."""
    safe_link = _html.escape(link, quote=True)
    text = (
        f"Sign in to Prism\n\nTap to finish signing in:\n{link}\n\n"
        f"This link expires in {ttl_min} minutes and can be used once.\n"
        f"If you didn't request it, ignore this email.\n\nPrism — {PROMISE}"
    )
    html = shell(
        title="Sign in to Prism",
        meta=f"Sign in · one-time link · {ttl_min} min",
        paragraphs=["Tap the button to finish signing in. No password needed."],
        cta=("Sign in to Prism", link),
        aside=f"Or paste this link into your browser:<br>{safe_link}",
        footer=(
            f"Expires in {ttl_min} minutes · one-time use<br>"
            f"Sent to {_html.escape(to)} because someone asked to sign in with this address. If that wasn't you, ignore this email."
        ),
        preheader=f"Your one-time Prism sign-in link — expires in {ttl_min} minutes.",
    )
    return text, html
