"""A fetched page is only the article if it is about the article's headline.

Measured on production 2026-09-27: trafilatura returned the AUTHOR'S BIO instead
of the story for 56 of 255 Indian Express articles in 30 days, and the RBI site
navigation for 11 of 47 press releases. Identical bodies embed identically, so
unrelated stories merged into one event at score 1.000 ("Journalist Biography
Profile", 5 stories; a railway reporter's bio, 11), and the extractor then wrote
commentary about the text as the record's summary.
"""

import pytest

from common.text import is_model_commentary, title_share
from enrichment import fulltext

IE_BIO = (
    "Jayprakash S Naidu is a Principal Correspondent for The Indian Express, currently serving as the "
    "state correspondent for Chhattisgarh. With an extensive career in frontline journalism, he reports on "
    "the political, security, and humanitarian landscape of Central India. Expertise and Experience "
    "Specialized Conflict Reporting: Jayprakash is a leading voice on the Maoist/Naxalite conflict in the "
    "Bastar region. ... Read More - Tags: - Chhattisgarh Police - Raipur"
)
IE_STORY = (
    "The Enforcement Directorate has filed a chargesheet against the promoter of EaseMyTrip in the Mahadev "
    "betting app case and has sought to confiscate his shares, officials said on Friday."
)


def test_the_article_covers_its_headline():
    share = title_share("ED chargesheets EaseMyTrip promoter in Mahadev betting app case", IE_STORY)
    assert share is not None and share >= 0.5


def test_the_bio_does_not_cover_the_headline():
    assert title_share("ED chargesheets EaseMyTrip promoter in Mahadev betting app case", IE_BIO) == 0.0


def test_indic_words_are_not_split_at_their_vowel_signs():
    """`\\w` in Python's re does not match a Kannada vowel sign, so a naive
    tokenizer breaks every word into fragments and finds no overlap at all —
    1,798 of prajavani's 5,383 articles scored zero that way."""
    title = "ಗದಗ ರೈತರ ಕಿಡಿ ಸಚಿವರ ಪತ್ರ ಶಾಸಕರ ರಾಜೀನಾಮೆ ಎಚ್ಚರಿಕೆ"
    text = "ಗದಗ: ರೈತರ ತೀವ್ರ ಆಕ್ರೋಶ, ಶಾಸಕರ ರಾಜೀನಾಮೆ ಎಚ್ಚರಿಕೆ, ಜಿಲ್ಲಾ ಉಸ್ತುವಾರಿ ಸಚಿವರ ‘ಪತ್ರ’ದೊತ್ತಡ ಕಾರಣ"
    assert title_share(title, text) >= 0.8


def test_a_short_title_is_too_little_to_judge():
    assert title_share("Watch: live", IE_BIO) is None


@pytest.mark.parametrize(
    "line",
    [
        "The provided text contains the biographical profile of a journalist and does not report on any "
        "Enforcement Directorate chargesheet.",
        "The article contains author biography information rather than reporting on a kidnapping incident.",
        "This article is a biographical profile of journalist Shubham Tigga rather than a news report.",
        "The article describes the author's professional background and does not provide information.",
        "The article profiles Anand Mohan J, a Senior Correspondent for The Indian Express based in Bhopal.",
        "This article profiles Anindya Chattopadhyay, a photo editor at The Times of India in Delhi.",
        "The article serves as an author profile rather than news about a government decision.",
        "Journalist Biography Profile",
        "Author bio of journalist Anish Mondal",
        "These stories carry no direct market catalyst in the provided text.",
    ],
)
def test_model_commentary_is_recognised(line):
    assert is_model_commentary(line)


@pytest.mark.parametrize(
    "line",
    [
        # Real summaries from the same scan that a looser pattern flagged.
        "The Delhi High Court ruled that marriage under Muslim personal law does not provide immunity from "
        "prosecution under the POCSO Act.",
        "Delhi Police warns users of fake profiles, blackmail in 1980s AI trend",
        "Why is Kishore Kumar biography classified as best cinema book HC asks Centre",
        "Nandita Das marked the seventh anniversary of her biographical film Manto on social media.",
        "The provided materials allegedly include an eyewitness statement and video evidence.",
        # Briefs naming what the reports leave open, or framing a story: the product working.
        "The reports do not yet say whether rescue operations are under way.",
        "While the article does not specify the exact global trigger, prices fell sharply.",
        "The article provides no scale figures such as the number of petitioners.",
        "Readers should treat this as a remembrance story rather than a news development in itself.",
        "The article profiles his background as part of the ABVP's campus campaign.",
    ],
)
def test_news_is_not_model_commentary(line):
    assert not is_model_commentary(line)


# ── the wiring: retrieve_fulltext itself must refuse the bio ────────────────


class _Doc:
    def __init__(self, text: str):
        self.text, self.image = text, "https://example.test/og.jpg"


class _Resp:
    text = "<html>stubbed</html>"

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
        return _Resp()


@pytest.mark.asyncio
async def test_an_off_title_page_falls_back_to_the_feed_body(monkeypatch):
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(IE_BIO * 2))

    text, tier, _image = await fulltext.retrieve_fulltext(
        "https://example.test/ed", "ED files chargesheet in betting case.",
        "ED chargesheets EaseMyTrip promoter in Mahadev betting app case",
    )

    assert tier == "body"
    assert text == "ED files chargesheet in betting case."


@pytest.mark.asyncio
async def test_an_off_title_page_with_no_feed_body_returns_nothing(monkeypatch):
    """The caller falls back to the title — thin, but about the right story."""
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(IE_BIO * 2))

    text, tier, _image = await fulltext.retrieve_fulltext(
        "https://example.test/ed", None, "ED chargesheets EaseMyTrip promoter in Mahadev betting app case",
    )

    assert (text, tier) == ("", "none")


@pytest.mark.asyncio
async def test_an_on_title_page_is_kept(monkeypatch):
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(IE_STORY * 4))

    text, tier, _image = await fulltext.retrieve_fulltext(
        "https://example.test/ed", None, "ED chargesheets EaseMyTrip promoter in Mahadev betting app case",
    )

    assert tier == "direct" and text == IE_STORY * 4
