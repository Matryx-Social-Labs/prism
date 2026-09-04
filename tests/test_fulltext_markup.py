"""Markup must not survive into clean_text.

`articles.clean_text` is not just what a reader might see. It is the extractor's
prompt, the text the embeddings are built from, and — since the claims layer
shipped — the string a quote is checked against for a VERBATIM match. A stray
`</p>` inside a sentence can therefore make a real quote fail verification, which
is the one failure enrichment/claims.py exists to prevent.

Measured on production 2026-09-04: 854 of prajavani's 880 direct-tier articles
carried closing HTML tags, while thehindu's 853 on the same path carried none —
a per-site extraction failure, not a general one.
"""

import pytest

from enrichment import fulltext
from enrichment.fulltext import _demarkup, _markup_leaked

PRAJAVANI_SHAPED = (
    "<p>Schools opened two months ago, but students still lack basic facilities "
    "in several districts, according to a survey conducted last week.</p>"
    "<div><a href=\"https://apps.apple.com/in/app/prajavani\">Download the app</a>"
    "</div>"
)


def test_two_real_tags_are_markup():
    assert _markup_leaked(PRAJAVANI_SHAPED)


def test_prose_containing_angle_brackets_is_NOT_markup():
    """The trap that makes a naive fix worse than the bug. A security article
    describing a container escape is prose, and `<pid>` is not an HTML tag — a
    pattern matching anything bracketed would silently eat the sentence."""
    prose = (
        "The attacker mounted the root filesystem, located the target process, "
        "copied the payload through /proc/<pid>/root, then ran it via nsenter. "
        "Compare with /proc/<pid>/cwd, which behaves differently."
    )
    assert not _markup_leaked(prose)
    assert _demarkup(prose, None) == prose.strip()


def test_a_single_stray_tag_is_not_a_document():
    """One could be a literal an author typed. Two is a document."""
    assert not _markup_leaked("He wrote </div> on the whiteboard and left.")


def test_demarkup_recovers_the_sentence_and_drops_the_tags():
    out = _demarkup(PRAJAVANI_SHAPED, None)
    assert "<" not in out and ">" not in out
    assert "Schools opened two months ago" in out
    assert "students still lack basic facilities" in out


def test_entities_are_unescaped_not_left_as_source():
    """&amp;quot; in the middle of a quotation would break the verbatim check
    just as surely as a tag does."""
    out = _demarkup("<p>The minister said &quot;we will double it&quot; today.</p>"
                    "<p>Opposition leaders disagreed with that figure.</p>", None)
    assert '"we will double it"' in out


# ── the wiring, not just the helpers ────────────────────────────────────────
# Testing _demarkup alone is vacuous against the failure that matters: deleting
# the call from retrieve_fulltext left every helper test green. This drives the
# real function.


class _Doc:
    """What trafilatura.bare_extraction hands back — and on the affected site,
    `.text` is the article as an HTML string lifted out of a JSON payload."""

    def __init__(self, text: str):
        self.text, self.image = text, None


class _Resp:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _Client:
    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        return _Resp("<html><body>irrelevant, extraction is stubbed</body></html>")


@pytest.mark.asyncio
async def test_retrieve_fulltext_never_returns_markup(monkeypatch):
    """REGRESSION: 877 production articles carry HTML in clean_text.

    The whole point is the value that reaches the caller, not the helper. With
    the _demarkup call removed from retrieve_fulltext, every other test in this
    file still passes — so this is the one that pins the fix in place.
    """
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(
        fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(PRAJAVANI_SHAPED)
    )

    text, tier, _image = await fulltext.retrieve_fulltext("https://example.test/a", None)

    assert tier == "direct"
    assert "</p>" not in text and "</div>" not in text and "<a " not in text
    assert "Schools opened two months ago" in text


@pytest.mark.asyncio
async def test_retrieve_fulltext_leaves_clean_extraction_untouched(monkeypatch):
    """The repair must be inert on the 26,000 articles that were already fine."""
    clean = (
        "The minister said the state would double its outlay on rural roads. "
        "Opposition leaders disputed the figure, calling it optimistic."
    )
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(clean))

    text, tier, _image = await fulltext.retrieve_fulltext("https://example.test/a", None)

    assert tier == "direct"
    assert text == clean
