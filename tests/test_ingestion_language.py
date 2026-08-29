"""A collector must not assert a language it cannot know.

ingestion/rss.py stamped `language="en"` on every envelope — including the
Hindi, Tamil and Kannada feeds — so all 1,385 non-Latin production articles were
labelled English. `sources.language` held the correct value the entire time.

This matters well beyond a metadata field: language routes the embedding model,
the display-language filter, and the corroboration count that decides whether a
Hindi and an English report of one event count as two independent sources.
"""

import inspect

import ingestion.base as base
import ingestion.rss as rss


def test_the_source_is_the_authority_not_the_collector():
    src = inspect.getsource(base.persist_envelopes)
    assert "source.language or env.language" in src, (
        "persist_envelopes must prefer the SOURCE's declared language; a "
        "collector cannot know what language a feed publishes in"
    )


def _code_only(module) -> str:
    """Source minus comments. The comments explaining WHY this broke necessarily
    quote the old `language="en"` literal, and that history is worth keeping."""
    lines = [ln for ln in inspect.getsource(module).splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(lines)


def test_no_collector_hardcodes_a_language():
    """The choke-point fix is the real one, but a collector re-asserting a
    literal would quietly win for any source with no declared language."""
    for mod in (rss, base):
        assert 'language="en"' not in _code_only(mod), (
            f"{mod.__name__} hardcodes a language again"
        )


def test_the_fix_is_at_the_choke_point_so_every_collector_inherits_it():
    """Placed in persist_envelopes rather than rss.py: every collector — rss,
    nvd, cisa_kev, and anything added later — persists through that one function."""
    assert "language=source.language or env.language" in inspect.getsource(base)
