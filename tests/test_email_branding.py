"""Every email is the first thing a reader sees with our name on it away from the site.

The sign-in email has been missed by a rename twice, and the whole shell was
missed by the change of design world once (it kept Fraunces, IBM Plex Mono, the
old ivory and the three-lens bar for three days after DESIGN.md retired them).
Nothing failed, because nothing looked. So these look both ways: the live name,
palette and voices must be present AND the dead ones absent, so a half-applied
change cannot pass.
"""

import re

from api.routes import auth as auth_routes
from common.config import get_settings
from common.email_templates import magic_link_email, shell

LINK = "https://parse.example/auth/verify?token=abc123"


def _email() -> tuple[str, str]:
    return magic_link_email(link=LINK, ttl_min=15, to="reader@example.com")


def test_nothing_in_the_signin_email_still_says_parse():
    text, html = _email()
    assert "Parse" not in text
    assert "Parse" not in html
    # And it does say the live name, so an empty template can't pass this.
    assert "Prism" in text
    assert html.count("Prism") >= 4  # wordmark, heading, button, sign-off


def test_the_from_name_and_subject_carry_the_product_name():
    assert "Parse" not in get_settings().prism_email_from
    assert "Prism" in get_settings().prism_email_from
    # The subject is written at the call site rather than in the template.
    src = (auth_routes.__file__ or "").replace(".pyc", ".py")
    with open(src) as fh:
        body = fh.read()
    assert "Your Prism sign-in link" in body
    assert "Parse sign-in" not in body


def test_the_link_is_escaped_into_both_the_href_and_the_visible_fallback():
    # A magic link is a credential; an unescaped one breaks out of the attribute.
    _, html = magic_link_email(link='https://x.test/a?t=1"><script>alert(1)</script>', ttl_min=15, to="r@x.dev")
    assert "<script>" not in html
    assert "&quot;" in html or "&#x27;" in html


def test_the_shell_speaks_the_spectrum_world_and_none_of_the_retired_one():
    """DESIGN.md (Spectrum, 2026-09-18): the paper's ground and ink, the three
    voices, colour only on the one accent button and in the mark. The old shell's
    three-hue bar was a gradient by another name — the One Gradient Rule."""
    _, html = _email()
    low = html.lower()
    for token in ("#fafaf7", "#15151a", "#4b4d57", "#6c6f7a", "#e6e6e1", "#6b4ef6"):
        assert token in low, f"{token} missing"
    for dead in ("#faf8f5", "#191613", "#f59e0b", "#06b6d4", "#8b5cf6", "fraunces", "plex", "every perspective"):
        assert dead not in low, f"retired token still present: {dead}"
    assert "gradient" not in low
    assert "newsreader" in low and "hind" in low and "jetbrains mono" in low
    assert "/brand/prism-mark-512.png" in html, "the masthead carries the mark"
    assert "Follow the story, not the headlines." in html


def test_the_three_voices_keep_their_jobs():
    """Newsreader sets the title and wordmark only; the button and paragraphs are
    Hind; the meta line, facts labels and footer are mono."""
    html = shell(
        title="A title",
        meta="Plan · ₹1,499 · 21 September 2026",
        paragraphs=["A paragraph."],
        facts=[("Next charge", "21 September 2027")],
        cta=("Do the thing", "https://x.test/do"),
        footer="Why you got this.",
    )
    h1 = re.search(r"<h1[^>]*>", html).group(0)
    assert "Newsreader" in h1
    button = re.search(r'<a href="https://x.test/do"[^>]*>', html).group(0)
    assert "Hind" in button and "Newsreader" not in button and "#6B4EF6" in html
    meta = re.search(r'<p style="margin:0;[^"]*">Plan', html).group(0)
    assert "JetBrains Mono" in meta and "uppercase" in meta
    label = re.search(r"<td[^>]*>Next charge</td>", html).group(0)
    assert "JetBrains Mono" in label
    para = re.search(r"<p[^>]*>A paragraph\.</p>", html).group(0)
    assert "Hind" in para and "Newsreader" not in para
    assert "<b>" not in html  # the value column is plain unless a caller says otherwise


def test_shell_escapes_what_it_is_handed_and_keeps_callers_markup_out_of_the_title():
    html = shell(title="<b>x</b>", meta="<i>m</i>", paragraphs=[], facts=[("<k>", "v")], cta=("<c>", "https://x.test/?a=1&b=2"), footer="f")
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html
    assert "&lt;i&gt;m&lt;/i&gt;" in html
    assert "&lt;k&gt;" in html
    assert "&lt;c&gt;" in html and 'href="https://x.test/?a=1&amp;b=2"' in html


def test_the_reader_is_told_what_expires_and_why_they_got_it():
    text, html = magic_link_email(link=LINK, ttl_min=7, to="reader@example.com")
    assert "7 minutes" in text and "7 minutes" in html
    assert "reader@example.com" in html
    assert re.search(r"ignore this email", text, re.I)
