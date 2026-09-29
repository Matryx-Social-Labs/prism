"""A feed summary is not the article, and a list of other headlines is not either.

Measured on production 2026-09-29 (8 days, 19,922 articles):
- 16% of articles were enriched from the feed's summary alone. The page was
  never fetched for a summary of 400+ characters, and Times of India's run
  400-460: 302 of its articles were a 66-word summary while the worker fetches
  the same pages at 635-984 words.
- Aaj Tak's short-video pages come back from trafilatura as a list of OTHER
  videos' headlines. The list carries the story's own headline, so the off-title
  guard passes it; 26 of those lists embedded near each other and one record
  ("Speeding vehicle crushes 3-year-old child in Hyderabad") held 26 unrelated
  Aaj Tak stories.
"""

from pathlib import Path

import pytest

from enrichment import fulltext

TITLE = "मेरठ से सहारनपुर तक चुनाव को लेकर नितिन नवीन का दौरा"
# The first 26 lines trafilatura returned for that page in production.
HEADLINE_LIST = (Path(__file__).parent / "fixtures" / "aajtak_short_video_page.txt").read_text()
SUMMARY = (
    "भाजपा के राष्ट्रीय अध्यक्ष नितिन नवीन ने मेरठ से सहारनपुर तक का दौरा किया और 2027 के चुनाव की तैयारियों की "
    "समीक्षा की। उन्होंने कार्यकर्ताओं से मुलाकात की।"
)
STORY = (
    "Protests at Lovely Professional University turned violent on Sunday after rumours spread among students. "
    "Police said the campus was calm by evening and that examinations had been deferred. "
) * 6
TOI_SUMMARY = (
    "Protests at Lovely Professional University turned violent on Sunday after rumours spread among students, "
    "with vehicles set on fire and a highway blocked for hours. Police said the situation was under control and "
    "exams were deferred while the university set up an inquiry panel to look into the claims made by students "
    "during the protest, officials said on Monday after a meeting with the district administration."
)
assert 400 <= len(TOI_SUMMARY) < fulltext.FULL_BODY_CHARS, "a summary that cleared the old 400 floor"


class _Doc:
    def __init__(self, text: str):
        self.text, self.image = text, None


class _Resp:
    text = "<html>stubbed</html>"

    def raise_for_status(self):
        return None


class _Client:
    fetched: list[str] = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        _Client.fetched.append(url)
        return _Resp()


@pytest.fixture
def page(monkeypatch):
    """Serve `text` as the page trafilatura extracts."""
    _Client.fetched = []
    monkeypatch.setattr(fulltext.httpx, "AsyncClient", _Client)

    def serve(text: str):
        monkeypatch.setattr(fulltext.trafilatura, "bare_extraction", lambda *a, **kw: _Doc(text))

    return serve


def test_the_short_video_page_is_a_headline_list():
    assert fulltext.is_headline_list(HEADLINE_LIST)


def test_the_list_is_caught_without_its_filler_lines():
    """Review 2026-09-29: 10 of the fixture's 26 lines are "Advertisement" and
    "Swipe"; the rule must not depend on the site keeping them."""
    bare = "\n".join(ln for ln in HEADLINE_LIST.splitlines() if ln.strip() not in {"Advertisement", "Swipe"})
    assert fulltext.is_headline_list(bare)


@pytest.mark.parametrize("text", [
    STORY,
    # A story with sub-headings: short lines, but most of it is sentences.
    "\n".join(["Key developments", STORY, "What the police said", STORY, "What happens next", STORY]),
    # A short list is a list inside an article, not a page of headlines.
    "\n".join(f"Candidate {i} from district {i} named for the seat" for i in range(8)),
    # Past the line count, so the shape is what decides:
    "\n".join(["Police said the campus was calm by evening and that the exams were deferred."] * 25),
    "\n".join(f"- Seat {i}: the candidate named on Tuesday is a former district president." for i in range(25)),
], ids=["story", "story-with-subheadings", "short-list", "25-paragraphs", "25-sentence-bullets"])
def test_an_article_is_not_a_headline_list(text):
    assert not fulltext.is_headline_list(text)


@pytest.mark.asyncio
async def test_a_feed_summary_does_not_stop_the_page_fetch(page):
    page(STORY)
    text, tier, _ = await fulltext.retrieve_fulltext("https://toi.test/lpu", TOI_SUMMARY, "Protest violence rocks LPU")
    assert (tier, text) == ("direct", STORY)


@pytest.mark.asyncio
async def test_a_full_text_feed_is_used_without_a_fetch(page):
    page(STORY)
    body = STORY * 2
    assert len(body) >= fulltext.FULL_BODY_CHARS
    text, tier, _ = await fulltext.retrieve_fulltext("https://feed.test/a", body, "Protest violence rocks LPU")
    assert (tier, text) == ("body", body)
    assert _Client.fetched == []


@pytest.mark.asyncio
async def test_a_page_shorter_than_the_summary_keeps_the_summary(page):
    page(TOI_SUMMARY[:410])  # over the old 400 floor, under the summary
    text, tier, _ = await fulltext.retrieve_fulltext("https://toi.test/lpu", TOI_SUMMARY, "Protest violence rocks LPU")
    assert (tier, text) == ("body", TOI_SUMMARY)


@pytest.mark.asyncio
async def test_a_headline_list_page_falls_back_to_the_summary(page):
    page(HEADLINE_LIST)
    text, tier, _ = await fulltext.retrieve_fulltext("https://aajtak.test/short-videos/x", SUMMARY, TITLE)
    assert (tier, text) == ("body", SUMMARY)


@pytest.mark.asyncio
async def test_a_list_page_with_no_summary_is_kept(page):
    """A real list article (a party's appointments) can look like one; with no
    summary to fall back to, the list is still more than nothing."""
    page(HEADLINE_LIST)
    text, tier, _ = await fulltext.retrieve_fulltext("https://aajtak.test/short-videos/x", None, TITLE)
    assert tier == "direct" and text == HEADLINE_LIST
