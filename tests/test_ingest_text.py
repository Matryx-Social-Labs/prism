"""Titles reach the reader as the publisher wrote them.

Found by auditing production: `&#039;` appeared 22 times across 4% of feed
titles and 5% of storyline developments, rendering as a literal "&#039;" where
an apostrophe belonged. Every affected headline was Hindi, so it landed on the
India-first audience specifically. Nothing in the ingest path decoded entities —
rss.py stripped tags with a regex and stopped there.
"""

from ingestion.base import clean_text


def test_decodes_the_entity_that_was_actually_reaching_readers():
    # Verbatim from the production feed.
    raw = "ट्रंप के &#039;एक के बदले एक&#039; वाली धमकी पर ईरान ने दी प्रतिक्रिया"
    out = clean_text(raw)
    assert "&#039;" not in out
    assert "'एक के बदले एक'" in out


def test_decodes_the_common_named_entities():
    assert clean_text("Reliance &amp; Jio") == "Reliance & Jio"
    assert clean_text("&quot;quoted&quot;") == '"quoted"'
    assert clean_text("wait&hellip;") == "wait…"


def test_strips_real_markup():
    assert clean_text("<b>Breaking</b>: markets fall") == "Breaking : markets fall"


def test_strips_before_it_decodes():
    """The ordering is the whole design, and reversing it is silent.

    Decode-then-strip turns `&lt;b&gt;` into a real tag for the stripper to eat,
    deleting text the publisher wrote literally. Strip-then-decode leaves it as
    visible text, which is what was meant — and React escapes it again at
    render, so an escaped tag is never a way in.
    """
    out = clean_text("&lt;script&gt;alert(1)&lt;/script&gt;")
    assert out == "<script>alert(1)</script>"  # literal text, not stripped away
    assert "alert(1)" in out  # decode-first would have eaten the tags AND kept this bare


def test_double_escaped_text_survives_one_pass():
    # A single unescape pass, deliberately: unescaping until stable would turn
    # a publisher's literal "&amp;#039;" into an apostrophe they didn't write.
    assert clean_text("&amp;#039;") == "&#039;"


def test_empty_and_whitespace_are_safe():
    assert clean_text("") == ""
    assert clean_text("   ") == ""
    assert clean_text("  spaced  ") == "spaced"
