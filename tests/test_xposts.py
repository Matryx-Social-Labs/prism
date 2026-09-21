"""The pure pieces of the X layer: what the client keeps from a post, what the
embedding sees, the since_id watermark, and the two rules that keep one post
from being credited to a whole saga."""
import uuid

from xposts.client import permalink, post_text, post_urls
from xposts.match import Hit, cap_per_event, one_per_story
from xposts.poll import embed_text, newest_id


def _post(**kw):
    base = {"id": "1001", "text": "RBI announces OMO sale https://t.co/abc", "entities": {"urls": [
        {"url": "https://t.co/abc", "expanded_url": "https://rbi.org.in/x?prid=1", "unwound_url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1"},
        {"url": "https://t.co/self", "expanded_url": "https://x.com/RBI/status/1000"},
    ]}}
    base.update(kw)
    return base


def test_the_whole_text_wins_over_the_truncated_one():
    """A long post arrives truncated in `text`; the display rules and the
    product agree the words are never altered, so the note_tweet is the text."""
    assert post_text(_post()) == "RBI announces OMO sale https://t.co/abc"
    assert post_text(_post(note_tweet={"text": "the whole 800-character release"})) == "the whole 800-character release"


def test_links_are_unwound_past_tco_and_never_point_back_at_x():
    assert post_urls(_post()) == ["https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=1"]
    assert post_urls({"id": "1", "text": "no links"}) == []


def test_the_embedding_sees_words_not_links_or_handles():
    assert embed_text("Big news @PIB_India: #GST cut https://t.co/x  today") == "Big news : GST cut today"


def test_since_id_is_the_newest_snowflake_seen():
    """Snowflakes compare as integers; as strings '999' > '1000'."""
    assert newest_id([{"id": "1000"}, {"id": "999"}], None) == "1000"
    assert newest_id([{"id": "999"}], "1000") == "1000", "an empty page never moves the watermark back"
    assert newest_id([], None) is None


def test_permalink_is_the_post_on_x():
    assert permalink("RBI", "1001") == "https://x.com/RBI/status/1001"


def _hit(ev, post, handle="PIB_India", score=0.9, method="judge", story=""):
    return Hit(ev, post, handle, score, method, story or str(ev))


def test_a_post_backs_one_event_per_story_the_best_one():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    hits = [_hit(a, "p1", score=0.86, story="saga"), _hit(b, "p1", score=0.91, story="saga"), _hit(c, "p1", score=0.85, story="other")]
    kept = one_per_story(hits)
    assert {h.event_id for h in kept} == {b, c}


def test_an_event_keeps_its_best_posts_one_per_account():
    """PIB posts the Hindi twin of every English release; the reader sees one."""
    ev = uuid.uuid4()
    hits = [_hit(ev, "en", score=0.90), _hit(ev, "hi", score=0.88), _hit(ev, "mea", handle="MEAIndia", score=0.85),
            _hit(ev, "url", handle="RBI", score=1.0, method="url")]
    per = cap_per_event(hits, limit=3)
    assert [h.post_id for h in per[ev]] == ["url", "en", "mea"], "best first; the Hindi twin yields to another account"
    assert [h.post_id for h in cap_per_event(hits, limit=2)[ev]] == ["url", "en"]
