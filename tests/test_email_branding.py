"""Every email is the first thing a reader sees with our name on it away from the site.

The sign-in email has been missed by a rename twice, and the whole shell was
missed by the change of design world once (it kept Fraunces, IBM Plex Mono, the
old ivory and the three-lens bar for three days after DESIGN.md retired them).
Nothing failed, because nothing looked. So these look both ways: the live name,
palette and voices must be present AND the dead ones absent, so a half-applied
change cannot pass.
"""

import re
from datetime import UTC, datetime

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


def test_the_shell_speaks_design_system_v2_and_none_of_the_retired_worlds():
    """Design System v2 (2026-09-24): paper ground, carbon ink, ONE cobalt accent on
    the one button, colour otherwise only in the mark. Both earlier worlds are
    dead: Spectrum's violet and ivory, and the Reservation Chart's Fraunces/Plex
    and three-hue bar (a gradient by another name — the One Gradient Rule)."""
    _, html = _email()
    low = html.lower()
    for token in ("#f7f6f2", "#111317", "#5b6069", "#dfddd6", "#0b57d0"):
        assert token in low, f"{token} missing"
    retired = ("#fafaf7", "#15151a", "#6b4ef6", "#faf8f5", "#191613", "#f59e0b", "#06b6d4", "#8b5cf6")
    for dead in (*retired, "fraunces", "plex", "hind,", "jetbrains", "every perspective"):
        assert dead not in low, f"retired token still present: {dead}"
    assert "gradient" not in low
    assert "georgia" in low and "anek latin" in low and "geist mono" in low
    assert "/brand/prism-mark-64.png" in html, "the masthead carries the mark"
    assert "color-scheme\" content=\"light only" in html
    assert "Follow the story, not the headlines." in html


def test_the_v2_shell_has_the_ink_rule_the_cobalt_button_and_the_footer():
    html = shell(title="T", meta="m", paragraphs=["p"], cta=("Go", "https://x.test/go"), because="a test asked.", preheader="Pre.")
    # The 3px ink rule under the masthead.
    assert re.search(r'height="3" style="height:3px;[^"]*background:#111317"', html)
    # One cobalt 48px button, with Outlook's VML roundrect beside it.
    assert re.search(r'<a href="https://x.test/go" style="[^"]*background:#0B57D0;[^"]*height:48px', html)
    assert '<v:roundrect' in html and 'fillcolor="#0B57D0"' in html and 'href="https://x.test/go"' in html
    assert html.count("#0B57D0") == 3  # link colour, the button, its VML twin — nothing else
    # Why you got this, then the LLP and the promise.
    assert "You are getting this because a test asked.<br><br>Prism · Prism Media Intelligence LLP · Follow the story, not the headlines." in html
    # The hidden preheader.
    assert re.search(r'<div style="display:none;[^"]*">Pre\.', html)


def test_the_three_voices_keep_their_jobs():
    """The record voice sets the title and wordmark only; the button and paragraphs
    are the reading voice; the meta line, facts labels and the note are mono caps."""
    html = shell(
        title="A title",
        meta="Plan · ₹1,499 · 21 September 2026",
        paragraphs=["A paragraph."],
        facts=[("Next charge", "21 September 2027")],
        cta=("Do the thing", "https://x.test/do"),
        note="A note.",
        because="why.",
    )
    h1 = re.search(r"<h1[^>]*>", html).group(0)
    assert "Georgia" in h1 and "28px" in h1
    button = re.search(r'<a href="https://x.test/do"[^>]*>', html).group(0)
    assert "Anek Latin" in button and "Georgia" not in button
    meta = re.search(r"<td[^>]*>PLAN · ₹1,499 · 21 SEPTEMBER 2026</td>", html).group(0)
    assert "Geist Mono" in meta
    label = re.search(r"<td[^>]*>NEXT CHARGE</td>", html).group(0)
    assert "Geist Mono" in label and "150px" in label
    note = re.search(r"<td[^>]*>A note\.</td>", html).group(0)
    assert "Geist Mono" in note
    para = re.search(r"<td[^>]*>A paragraph\.</td>", html).group(0)
    assert "Anek Latin" in para and "Georgia" not in para


def test_shell_escapes_every_part_it_is_handed():
    html = shell(
        title="<b>x</b>", meta="<i>m</i>", paragraphs=["<p1>"], facts=[("<k>", "<v>")],
        cta=("<c>", "https://x.test/?a=1&b=2"), note="<n>", because="<w>",
    )
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x</b>" not in html
    assert "&lt;I&gt;M&lt;/I&gt;" in html
    for part in ("&lt;p1&gt;", "&lt;K&gt;", "&lt;v&gt;", "&lt;n&gt;", "&lt;w&gt;"):
        assert part in html, part
    assert "&lt;c&gt;" in html and 'href="https://x.test/?a=1&amp;b=2"' in html


def test_the_plain_text_twin_is_the_same_email_in_the_design_txt_shape():
    text, _ = magic_link_email(link=LINK, ttl_min=15, to="reader@example.com", now=datetime(2026, 9, 25, 8, 32, tzinfo=UTC))
    assert text == (
        "Sign in to Prism\n\n"
        "ONE-TIME LINK · 15 MIN\n\n"
        "Use the button below to sign in as reader@example.com. The link works once and expires in 15 minutes, at 14:17 IST.\n\n"
        "Link: One-time · 15 minutes\n"
        f"If the button does not work: Paste this into your browser: {LINK}\n\n"
        f"Sign in to Prism: {LINK}\n\n"
        "Did not ask for this? Ignore it. Nobody can sign in without this link.\n\n"
        "—\nYou are getting this because someone asked to sign in to Prism with reader@example.com.\n\n"
        "Prism · Prism Media Intelligence LLP · Follow the story, not the headlines."
    )


def test_the_reader_is_told_what_expires_and_why_they_got_it():
    text, html = magic_link_email(link=LINK, ttl_min=7, to="reader@example.com")
    assert "7 minutes" in text and "7 minutes" in html
    assert "reader@example.com" in html
    assert re.search(r"ignore it", text, re.I)
