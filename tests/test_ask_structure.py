"""The JSON tail after the prose: held back, delivered whole, dropped when broken.

The reader watches the prose type; they must never watch `{"kind":` type. And
a malformed tail must cost nothing — the prose stands on its own.
"""

import uuid

import pytest

from agent.structure import TailSplitter

pytestmark = pytest.mark.asyncio(loop_scope="session")


def run(deltas: list[str]) -> tuple[str, object]:
    sp = TailSplitter()
    out = ""
    for d in deltas:
        out += "".join(sp.feed(d))
    out += sp.flush()
    return out, sp.structure()


def test_prose_without_a_tail_streams_through_whole():
    out, st = run(["The bridge ", "closed on Monday [1].", " More [2]."])
    assert out == "The bridge closed on Monday [1]. More [2]."
    assert st is None


def test_the_tail_is_held_back_even_when_the_marker_is_split_across_deltas():
    deltas = ["Closed on Monday [1].", "\n=", '==\n{"kind": null, "gaps": "No arrest count.", "followups": ["Who ordered it?"]}']
    out, st = run(deltas)
    assert out == "Closed on Monday [1]."
    assert "=" not in out and "{" not in out, "no brace or marker may reach the reader"
    assert st is not None and st.gaps == "No arrest count." and st.followups == ["Who ordered it?"]


def test_a_table_carries_its_rows_and_citation_marks_only():
    tail = '\n===\n{"kind":"who_said","columns":["Speaker","Said"],"rows":[{"a":"CM","b":"We object.","n":"see [2] and [3]"}],"followups":[]}'
    out, st = run(["Prose [1].", tail])
    assert out == "Prose [1]."
    assert st.kind == "who_said" and st.rows[0].n == "[2][3]"


def test_a_broken_tail_is_dropped_and_the_prose_survives():
    out, st = run(["Prose [1].\n===\n{not json at all"])
    assert out == "Prose [1]."
    assert st is None


def test_a_tail_without_the_marker_is_still_held_back():
    """glm-5.3-flash skipped the === line about one answer in three and ran the
    JSON straight on after the prose; the reader saw braces (2026-09-20)."""
    deltas = ["Kerala seeks exclusion [2][4]. ", '{"ki', 'nd": "numbers", "columns": ["a","b"], "rows": [{"a":"98","b":"villages","n":"[2]"}], "followups": []}']
    out, st = run(deltas)
    assert out == "Kerala seeks exclusion [2][4]."
    assert st is not None and st.kind == "numbers" and st.rows[0].a == "98"


def test_an_unknown_kind_and_an_empty_tail_read_as_nothing():
    _, st = run(["P.\n===\n{\"kind\":\"pie_chart\",\"rows\":[],\"followups\":[]}"])
    assert st is None


async def test_the_stream_emits_one_structure_event_and_counts_its_citations(monkeypatch):
    import agent.rag as rag
    from tests.test_rag import _allow, _grounded, _Prompt, _Streaming, chunk

    a1, a2 = uuid.uuid4(), uuid.uuid4()
    seen: dict = {}

    async def _record(_sid, _q, ans, cited):
        seen["answer"], seen["cited"] = ans, cited

    text = 'Prose cites [1].\n===\n{"kind":"numbers","columns":["Figure","What"],"rows":[{"a":"98","b":"villages","n":"[2]"}],"gaps":null,"followups":["Which villages?"]}'
    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding", lambda _e, _q: _grounded([chunk(1, a1), chunk(2, a2)]))
    monkeypatch.setattr(rag, "get_llm", lambda: _Streaming(text))
    monkeypatch.setattr(rag, "fetch_prompt", lambda _n: _Prompt())
    monkeypatch.setattr(rag, "_persist_turn", _record)

    events = [e async for e in rag.answer_stream(event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="how many?")]
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert tokens == "Prose cites [1]."
    kinds = [e["type"] for e in events]
    assert kinds.count("structure") == 1 and kinds.index("structure") < kinds.index("citations")
    st = next(e for e in events if e["type"] == "structure")
    assert st["rows"] == [{"a": "98", "b": "villages", "n": "[2]"}] and st["followups"] == ["Which villages?"]
    # [2] is cited only by the table row, and it still counts.
    assert seen["cited"] == [a1, a2]
    assert seen["answer"] == "Prose cites [1]."


async def test_a_second_chunk_of_the_same_article_still_opens_that_article(monkeypatch):
    """[1] and [3] from one report: the source list shows the report once, and the
    citation carries both numbers so the [3] chip is not a dead end."""
    import agent.rag as rag
    from tests.test_rag import _allow, _grounded, _Prompt, _Streaming, chunk

    a1 = uuid.uuid4()

    async def _noop(*_a):
        return None

    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding", lambda _e, _q: _grounded([chunk(1, a1), chunk(2, uuid.uuid4()), chunk(3, a1)]))
    monkeypatch.setattr(rag, "get_llm", lambda: _Streaming("First [1], and later [3]."))
    monkeypatch.setattr(rag, "fetch_prompt", lambda _n: _Prompt())
    monkeypatch.setattr(rag, "_persist_turn", _noop)

    events = [e async for e in rag.answer_stream(event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="q")]
    cits = next(e for e in events if e["type"] == "citations")["citations"]
    assert [c["article_id"] for c in cits] == [str(a1)]
    assert cits[0]["numbers"] == [1, 3]

