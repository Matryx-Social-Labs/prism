"""Branded email HTML. Email clients strip <style>/web fonts, so everything is
inline-styled with table layout and safe font stacks (serif for the Fraunces
display voice, monospace for provenance) — following DESIGN.md: monochrome
chrome, colour only in the signature spectrum bar.
"""

import html as _html

# Product palette, taken from DESIGN.md rather than approximated — these had
# drifted cool (#f6f4f0 ground, #17161a ink) against the warm ivory the rest of
# the product uses, which is exactly what the share cards were doing too.
_BG = "#faf8f5"
_CARD = "#ffffff"
_INK = "#191613"
_MUTED = "#6d675e"
_FAINT = "#a39c90"
_LINE = "#e5dfd5"
_AMBER = "#f59e0b"  # general lens
_CYAN = "#06b6d4"  # cyber lens
_VIOLET = "#8b5cf6"  # markets lens

_SERIF = "'Fraunces', Georgia, 'Times New Roman', serif"
_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def magic_link_email(*, link: str, ttl_min: int, to: str) -> tuple[str, str]:
    """Return (plaintext, html) for the sign-in email."""
    safe_link = _html.escape(link, quote=True)
    text = (
        f"Sign in to Prism\n\nTap to finish signing in:\n{link}\n\n"
        f"This link expires in {ttl_min} minutes and can be used once.\n"
        f"If you didn't request it, ignore this email.\n\nPrism — One story. Every perspective."
    )
    # Three discrete lens hues as the spectrum bar (never a gradient).
    bar = "".join(
        f'<td width="33.33%" height="4" style="background:{c};font-size:0;line-height:0;">&nbsp;</td>'
        for c in (_AMBER, _CYAN, _VIOLET)
    )
    html = f"""\
<!doctype html><html><body style="margin:0;padding:0;background:{_BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your one-time Prism sign-in link — expires in {ttl_min} minutes.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:32px 16px;">
<tr><td align="center">
  <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;background:{_CARD};border:1px solid {_LINE};border-radius:16px;overflow:hidden;">
    <tr><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{bar}</tr></table></tr>
    <tr><td style="padding:36px 40px 40px;">
      <div style="font-family:{_SERIF};font-size:22px;font-weight:600;color:{_INK};letter-spacing:-0.01em;">Prism</div>
      <h1 style="margin:22px 0 0;font-family:{_SERIF};font-size:26px;line-height:1.2;font-weight:600;color:{_INK};">Sign in to Prism</h1>
      <p style="margin:14px 0 0;font-family:{_SANS};font-size:15px;line-height:1.6;color:{_MUTED};">
        Tap the button to finish signing in. No password needed.
      </p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;">
        <tr><td style="border-radius:999px;background:{_INK};">
          <a href="{safe_link}" style="display:inline-block;padding:13px 28px;font-family:{_SANS};font-size:15px;font-weight:600;color:{_CARD};text-decoration:none;border-radius:999px;">Sign in to Prism</a>
        </td></tr>
      </table>
      <p style="margin:20px 0 0;font-family:{_SANS};font-size:13px;line-height:1.6;color:{_FAINT};">
        Or paste this link into your browser:
      </p>
      <p style="margin:6px 0 0;font-family:{_MONO};font-size:12px;line-height:1.5;color:{_MUTED};word-break:break-all;">{safe_link}</p>
      <hr style="border:none;border-top:1px solid {_LINE};margin:28px 0 0;">
      <p style="margin:18px 0 0;font-family:{_MONO};font-size:11px;line-height:1.6;color:{_FAINT};">
        Expires in {ttl_min} minutes · one-time use<br>
        Sent to {_html.escape(to)} because someone requested a sign-in link. If that wasn't you, ignore this email.
      </p>
      <p style="margin:16px 0 0;font-family:{_SERIF};font-size:13px;color:{_FAINT};">Prism — One story. Every perspective.</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>"""
    return text, html
