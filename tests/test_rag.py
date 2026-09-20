"""The grounded Q&A agent — the product's trust claim, previously untested.

`agent/rag.py` is what makes Prism answerable rather than merely readable: it cites
its sources inline as [n] and refuses when the grounding set cannot support an
answer. Issue E1 records that no test imported `agent` at all, which is the wrong
place in this codebase to have zero coverage — a wrong story boundary shows a reader
an unrelated card, but a fabricated citation puts a claim in a named outlet's mouth.

The properties below are the ones where a failure still LOOKS like a working
answer. A dropped citation, a source attributed to the wrong article, or an answer
persisted after the model died all render as ordinary prose in the UI.
"""

import uuid

import pytest

from agent.rag import GroundingChunk, _extract_citations


def chunk(n: int, article: uuid.UUID | None = None, source: str = "The Hindu") -> GroundingChunk:
    return GroundingChunk(
        number=n,
        article_id=article or uuid.uuid4(),
        source_name=source,
        url=f"https://example.test/{n}",
        text=f"grounding text {n}",
    )


async def _noop(*_a, **_k):
    return None


class _Prompt:
    def compile(self, **_kw):
        return [{"role": "user", "content": "x"}]


class _Streaming:
    """The smallest thing shaped like the streaming client rag.py consumes."""

    def __init__(self, text: str):
        self._text = text
        outer = self

        class _Completions:
            @staticmethod
            async def create(**_kw):
                return outer._parts()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()

    def _parts(self):
        text = self._text

        class _Aiter:
            def __aiter__(self):
                async def gen():
                    for piece in (text[:5], text[5:]):
                        yield type(
                            "P", (), {"choices": [type(
                                "C", (), {"delta": type("D", (), {"content": piece})()}
                            )()]},
                        )()

                return gen()

        return _Aiter()


def _allow():
    async def _f(_q):
        return type("G", (), {"allowed": True})()

    return _f


# --- the hallucinated citation ------------------------------------------------
# The model is free to emit any [n] it likes. Only numbers that correspond to a
# chunk actually retrieved may become a source, or the citation stops being
# evidence and becomes decoration.


def test_a_citation_number_with_no_chunk_behind_it_is_dropped():
    """The model wrote [9] with two sources in front of it. That must surface
    nothing — a reader clicking a citation has to reach the article it claims."""
    assert _extract_citations("Backed by [9].", [chunk(1), chunk(2)]) == []


def test_a_real_citation_survives_alongside_a_hallucinated_one():
    """The failure to avoid runs both ways: dropping the good one, or letting the
    invented one through."""
    got = _extract_citations("True [1], and also [7].", [chunk(1), chunk(2)])
    assert [c.number for c in got] == [1]


def test_no_citations_means_no_sources():
    assert _extract_citations("A confident answer with nothing behind it.", [chunk(1)]) == []


def test_zero_is_not_a_valid_citation():
    """[0] is syntactically a citation and semantically nothing — chunks are
    1-indexed, so it must not resolve."""
    assert _extract_citations("See [0].", [chunk(1)]) == []


# --- attribution integrity ----------------------------------------------------


def test_one_article_cited_through_two_chunks_appears_once():
    """Two chunks of one article are one source. Listing it twice would inflate the
    apparent corroboration behind a claim, which is the number a reader uses to
    decide how much to trust it."""
    same = uuid.uuid4()
    got = _extract_citations("Both [1] and [2] say so.", [chunk(1, same), chunk(2, same), chunk(3)])
    assert len(got) == 1 and got[0].article_id == same


def test_sources_come_back_in_citation_order():
    """The list renders beside the answer, so [1][2][3] must not read 3, 1, 2."""
    got = _extract_citations(
        "Later [3], earlier [1], middle [2].", [chunk(1), chunk(2), chunk(3)]
    )
    assert [c.number for c in got] == [1, 2, 3]


def test_an_uncited_chunk_never_leaks_into_the_sources():
    """Retrieval fetched it; the answer did not use it. Presenting it as a source
    would claim evidence the answer never rested on."""
    got = _extract_citations("Only [1] matters here.", [chunk(1), chunk(2)])
    assert [c.number for c in got] == [1]


def test_a_bare_number_is_not_a_citation():
    """Prose is full of digits. Only bracketed references count."""
    assert _extract_citations("Some 12 people, over 3 days.", [chunk(1), chunk(3)]) == []


# --- refusal, and what it must not cost ---------------------------------------


@pytest.mark.asyncio
async def test_a_blocked_question_refuses_without_calling_the_model(monkeypatch):
    """The guard exists to stop disallowed prompts BEFORE the expensive agent runs.
    Refusing after the call would neither save the money nor avoid generating the
    content."""
    import agent.rag as rag

    async def _blocked(_q):
        return type("G", (), {"allowed": False})()

    def _llm():
        raise AssertionError("the model was called for a blocked question")

    monkeypatch.setattr(rag, "guard_question", _blocked)
    monkeypatch.setattr(rag, "get_llm", _llm)
    monkeypatch.setattr(rag, "_persist_turn", _noop)

    events = [e async for e in rag.answer_stream(
        event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="anything"
    )]
    assert [e["type"] for e in events] == ["token", "citations", "done"]
    assert events[1]["citations"] == []


@pytest.mark.asyncio
async def test_an_empty_grounding_set_refuses_instead_of_guessing(monkeypatch):
    """No sources means no grounded answer. Answering anyway from the model's own
    memory is precisely the behaviour this agent exists not to have."""
    import agent.rag as rag

    async def _nothing(_e, _q):
        return [], {}, "A title"

    def _llm():
        raise AssertionError("the model was called with no grounding")

    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding", _nothing)
    monkeypatch.setattr(rag, "get_llm", _llm)
    monkeypatch.setattr(rag, "_persist_turn", _noop)

    events = [e async for e in rag.answer_stream(
        event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="what happened?"
    )]
    assert "can't answer" in "".join(e.get("text", "") for e in events)
    assert events[-1]["type"] == "done"
    assert events[-2]["citations"] == []


@pytest.mark.asyncio
async def test_a_model_failure_records_no_turn(monkeypatch):
    """A half-streamed answer is not an answer. Persisting one would put text into
    the conversation history the reader never saw completed, carrying no sources
    while looking like a real reply."""
    import agent.rag as rag

    persisted: list = []

    class _Boom:
        class chat:  # noqa: N801 - mirrors the OpenAI client shape
            class completions:  # noqa: N801
                @staticmethod
                async def create(**_kw):
                    raise RuntimeError("upstream died")

    async def _record(*a, **_k):
        persisted.append(a)

    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding",
                        lambda _e, _q, **_kw: _grounded([chunk(1)]))
    monkeypatch.setattr(rag, "get_llm", lambda: _Boom())
    monkeypatch.setattr(rag, "fetch_prompt", lambda _n: _Prompt())
    monkeypatch.setattr(rag, "_persist_turn", _record)

    events = [e async for e in rag.answer_stream(
        event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="what happened?"
    )]
    assert events[-1]["type"] == "error"
    assert persisted == [], "a turn was recorded for an answer that never completed"


@pytest.mark.asyncio
async def test_only_cited_articles_are_persisted(monkeypatch):
    """`cited_source_ids` is what the UI later renders as provenance. It must carry
    the articles the answer actually used — not everything retrieved, and not an id
    the model invented."""
    import agent.rag as rag

    a1, a2 = uuid.uuid4(), uuid.uuid4()
    seen: dict = {}

    async def _record(_sid, _q, _ans, cited):
        seen["cited"] = cited

    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding",
                        lambda _e, _q, **_kw: _grounded([chunk(1, a1), chunk(2, a2)]))
    monkeypatch.setattr(rag, "get_llm", lambda: _Streaming("Only [1] and the invented [8]."))
    monkeypatch.setattr(rag, "fetch_prompt", lambda _n: _Prompt())
    monkeypatch.setattr(rag, "_persist_turn", _record)

    events = [e async for e in rag.answer_stream(
        event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="what happened?"
    )]
    assert seen["cited"] == [a1], "persisted provenance does not match the answer"
    citations = next(e for e in events if e["type"] == "citations")["citations"]
    assert [c["article_id"] for c in citations] == [str(a1)]


async def _grounded(chunks):
    return chunks, {}, "A title"
