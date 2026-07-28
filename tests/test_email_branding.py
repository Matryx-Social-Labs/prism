"""The sign-in email is the first thing a new reader sees with our name on it.

It has now been missed by a rename twice — once going out to Parse, once coming
back to Prism. Both times the subject, wordmark, button and sign-off kept the
dead name, and nothing failed, because nothing looked. The assertions run both
ways round on purpose: the live name must be present AND the dead one absent, so
a half-applied rename cannot pass.
"""

import re

from api.routes import auth as auth_routes
from common.config import get_settings
from common.email_templates import magic_link_email

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


def test_the_spectrum_bar_is_three_discrete_hues_never_a_gradient():
    # DESIGN.md: lens hues are discrete and colour only ever means a lens is
    # speaking. A gradient here would be the one thing the rename removed.
    _, html = _email()
    assert "gradient" not in html.lower()
    for hue in ("#f59e0b", "#06b6d4", "#8b5cf6"):
        assert hue in html.lower(), f"{hue} missing from the lens bar"


def test_the_palette_is_the_warm_ground_not_a_cool_approximation():
    _, html = _email()
    # These had drifted to #f6f4f0 / #17161a, which reads cool against every
    # other surface. Same class of drift as the share cards.
    assert "#faf8f5" in html.lower()
    assert "#191613" in html.lower()


def test_the_reader_is_told_what_expires_and_why_they_got_it():
    text, html = magic_link_email(link=LINK, ttl_min=7, to="reader@example.com")
    assert "7 minutes" in text and "7 minutes" in html
    assert "reader@example.com" in html
    assert re.search(r"ignore this email", text, re.I)
