"""Branded email — the record's own voices in a mail client (Design System v2).

The layout is Claude Design's (outside/emails, 2026-09-24): a paper ground, a
white 520px card, the masthead (the mark and "Prism", the host in mono), a 3px
ink rule, a mono meta line in caps, the title in the record voice, the
paragraphs in the reading voice, a facts table on hairlines with mono caps
labels, ONE cobalt button (with Outlook's VML fallback), an optional mono note,
a hairline, and why you got this.

Email clients strip <style> and most web fonts, so everything is inline-styled
table layout with the voices as font stacks: Georgia leads the record voice
(Newsreader behind it), Anek Latin the reading voice, Geist Mono the provenance.

Every email is built once from its parts by `render`, which returns the plain
text twin and the HTML together, so the two can never say different things.
Parts are PLAIN text: the shell escapes every one of them.
"""

from __future__ import annotations

import html as _html
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from common.config import get_settings

# design/tokens.json, light. Email has no dark mode we control; the meta tags
# below ask clients not to invent one.
PAPER = "#F7F6F2"
SURFACE = "#FFFFFF"
INK = "#111317"
INK_3 = "#5B6069"
LINE = "#DFDDD6"
ACCENT = "#0B57D0"
ON_ACCENT = "#FFFFFF"

RECORD = "Georgia,'Newsreader','Times New Roman',serif"
READ = "'Anek Latin',Arial,Helvetica,sans-serif"
MONO = "'Geist Mono',Menlo,Consolas,monospace"

FONTS_CSS = "https://fonts.googleapis.com/css2?family=Anek+Latin:wght@400;600&family=Geist+Mono&display=swap"
PROMISE = "Follow the story, not the headlines."
ENTITY = "Prism Media Intelligence LLP"
SIGN_OFF = f"Prism · {ENTITY} · {PROMISE}"
WHY = "You are getting this because"

# The newsroom clock: Razorpay bills on it and every date we print is on it.
IST = ZoneInfo("Asia/Kolkata")

# Keeps the body's first words out of the inbox preview after the preheader.
_PREVIEW_FILL = "&#8199;&#65279;&#847; " * 40

_PX = 'class="px"'
_E = _html.escape


def _web() -> str:
    return get_settings().prism_web_url.rstrip("/")


def _host() -> str:
    return _web().split("://", 1)[-1].removeprefix("www.")


def _button(label: str, href: str) -> str:
    h, lab = _E(href, quote=True), _E(label)
    width = max(180, 72 + 9 * len(label))  # Outlook draws the VML at a fixed width
    return (
        f'<tr><td {_PX} style="padding:26px 28px 0">'
        f'<!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{h}" '
        f'style="height:48px;v-text-anchor:middle;width:{width}px;" arcsize="17%" stroke="f" fillcolor="{ACCENT}"><w:anchorlock/>'
        f'<center style="color:{ON_ACCENT};font-family:Arial,sans-serif;font-size:15px;font-weight:bold;">{lab}</center></v:roundrect><![endif]-->'
        f'<!--[if !mso]><!--><a href="{h}" style="display:inline-block;background:{ACCENT};color:{ON_ACCENT};font-family:{READ};font-size:15px;'
        f'font-weight:600;line-height:48px;height:48px;padding:0 24px;border-radius:8px;text-decoration:none;mso-hide:all">{lab}</a><!--<![endif]-->'
        f"</td></tr>"
    )


def _facts(facts: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<tr><td valign="top" width="150" style="width:150px;padding:11px 12px 11px 0;border-bottom:1px solid {LINE};font-family:{MONO};'
        f'font-size:11px;line-height:16px;letter-spacing:.3px;color:{INK_3}">{_E(k.upper())}</td>'
        f'<td valign="top" style="padding:10px 0;border-bottom:1px solid {LINE};font-family:{READ};font-size:15px;line-height:22px;'
        f'color:{INK};word-break:break-word">{_E(v)}</td></tr>'
        for k, v in facts
    )
    return (
        f'<tr><td {_PX} style="padding:20px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="border-top:1px solid {LINE}">{rows}</table></td></tr>'
    )


def _rule(height: int, color: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td height="{height}" style="height:{height}px;line-height:{height}px;font-size:0;background:{color}">&nbsp;</td></tr></table>'
    )


def shell(
    *,
    title: str,
    meta: str,
    paragraphs: list[str],
    cta: tuple[str, str] | None,
    because: str,
    facts: list[tuple[str, str]] | None = None,
    note: str | None = None,
    preheader: str | None = None,
    subject: str | None = None,
) -> str:
    """One email's HTML. Every part is plain text and escaped here. `because`
    finishes the sentence "You are getting this because …"; `subject` is the
    document title when it differs from the heading."""
    body = "".join(
        f'<tr><td {_PX} style="padding:{12 if i == 0 else 10}px 28px 0;font-family:{READ};font-size:16px;line-height:25px;color:{INK}">{_E(p)}</td></tr>'
        for i, p in enumerate(paragraphs)
    )
    pre = (
        f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;color:{PAPER}">{_E(preheader)}{_PREVIEW_FILL}</div>'
        if preheader
        else ""
    )
    note_html = f'<tr><td {_PX} style="padding:18px 28px 0;font-family:{MONO};font-size:12px;line-height:18px;color:{INK_3}">{_E(note)}</td></tr>' if note else ""
    return f"""\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en"><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><meta name="supported-color-schemes" content="light"><title>{_E(subject or title)}</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><style>td,a,p{{font-family:Arial,sans-serif!important}}</style><![endif]-->
<style>@import url('{FONTS_CSS}');:root{{color-scheme:light only}}body{{margin:0!important;padding:0!important}}a{{color:{ACCENT}}}@media (max-width:560px){{.card{{width:100%!important}}.px{{padding-left:20px!important;padding-right:20px!important}}}}</style></head>
<body style="margin:0;padding:0;background:{PAPER};-webkit-text-size-adjust:100%">
{pre}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAPER}" style="background:{PAPER}"><tr><td align="center" style="padding:32px 12px">
<table role="presentation" class="card" width="520" cellpadding="0" cellspacing="0" border="0" bgcolor="{SURFACE}" style="width:520px;max-width:520px;background:{SURFACE};border:1px solid {LINE};border-radius:8px">
<tr><td {_PX} style="padding:24px 28px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td valign="middle" style="font-family:{RECORD};font-size:22px;line-height:24px;font-weight:bold;color:{INK}"><img src="{_web()}/brand/prism-mark-64.png" width="22" height="22" alt="" style="display:inline-block;vertical-align:-3px;margin-right:8px;border:0">Prism</td><td align="right" valign="middle" style="font-family:{MONO};font-size:12px;line-height:16px;color:{INK_3}">{_E(_host())}</td></tr></table></td></tr>
<tr><td {_PX} style="padding:0 28px">{_rule(3, INK)}</td></tr>
<tr><td {_PX} style="padding:20px 28px 0;font-family:{MONO};font-size:12px;line-height:18px;letter-spacing:.4px;color:{INK_3}">{_E(meta.upper())}</td></tr>
<tr><td {_PX} style="padding:8px 28px 0"><h1 style="margin:0;font-family:{RECORD};font-size:28px;line-height:34px;font-weight:bold;color:{INK}">{_E(title)}</h1></td></tr>
{body}
{_facts(facts) if facts else ""}
{_button(*cta) if cta else ""}
{note_html}
<tr><td {_PX} style="padding:26px 28px 0">{_rule(1, LINE)}</td></tr>
<tr><td {_PX} style="padding:16px 28px 26px;font-family:{READ};font-size:13px;line-height:20px;color:{INK_3}">{WHY} {_E(because)}<br><br>{_E(SIGN_OFF)}</td></tr>
</table></td></tr></table></body></html>"""


def plain(
    *,
    title: str,
    meta: str,
    paragraphs: list[str],
    cta: tuple[str, str] | None,
    because: str,
    facts: list[tuple[str, str]] | None = None,
    note: str | None = None,
    **_: object,
) -> str:
    """The plain-text twin, in the design's .txt shape: the same parts, in order."""
    blocks = [title, meta.upper(), *paragraphs]
    if facts:
        blocks.append("\n".join(f"{k}: {v}" for k, v in facts))
    if cta:
        blocks.append(f"{cta[0]}: {cta[1]}")
    if note:
        blocks.append(note)
    blocks += [f"—\n{WHY} {because}", SIGN_OFF]
    return "\n\n".join(blocks)


def render(**parts) -> tuple[str, str]:
    """(plain text, html) for one email, from one set of parts."""
    return plain(**parts), shell(**parts)


def magic_link_email(*, link: str, ttl_min: int, to: str, now: datetime | None = None) -> tuple[str, str]:
    """Return (plaintext, html) for the sign-in email."""
    expires = ((now or datetime.now(UTC)) + timedelta(minutes=ttl_min)).astimezone(IST).strftime("%H:%M")
    return render(
        title="Sign in to Prism",
        meta=f"One-time link · {ttl_min} min",
        paragraphs=[f"Use the button below to sign in as {to}. The link works once and expires in {ttl_min} minutes, at {expires} IST."],
        facts=[("Link", f"One-time · {ttl_min} minutes"), ("If the button does not work", f"Paste this into your browser: {link}")],
        cta=("Sign in to Prism", link),
        note="Did not ask for this? Ignore it. Nobody can sign in without this link.",
        because=f"someone asked to sign in to Prism with {to}.",
        preheader=f"Your one-time link to sign in. It works once, for {ttl_min} minutes.",
    )
