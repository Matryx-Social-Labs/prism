"""The model returning the schema instead of an instance.

50 of 129 structured-output failures in production were this, and 21 messages
were dropped outright after retries ran out. The generic retry handled it badly
twice over: it reported the SYMPTOM ("shared: Field required") rather than the
cause, and it appended the echoed schema back into the conversation, so the retry
saw the schema once more and tended to echo it again.
"""

import pytest
from pydantic import BaseModel

from common.llm import _looks_like_json_schema, structured_chat


class Tiny(BaseModel):
    headline: str


class _Msg:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})()


class _Resp:
    def __init__(self, content):
        self.choices = [_Msg(content)]


class _FakeLLM:
    """Replays canned completions and records what it was asked."""

    def __init__(self, replies):
        self.replies, self.seen = list(replies), []
        self.chat = type("C", (), {"completions": self})()

    async def create(self, **kwargs):
        self.seen.append(kwargs["messages"])
        return _Resp(self.replies.pop(0))


@pytest.mark.parametrize(
    "obj,is_schema",
    [
        ({"$defs": {"X": {}}, "type": "object"}, True),
        ({"$schema": "https://json-schema.org/draft/2020-12/schema"}, True),
        ({"type": "object", "properties": {"headline": {"type": "string"}}}, True),
        ({"headline": "a real story"}, False),
        ({"type": "object"}, False),          # no properties -> not the schema shape
        ([1, 2, 3], False),
        ("a string", False),
    ],
)
def test_the_detector_separates_schema_from_instance(obj, is_schema):
    assert _looks_like_json_schema(obj) is is_schema


def test_a_real_extraction_is_never_mistaken_for_a_schema():
    """The expensive false positive: rejecting a good extraction would turn a
    working call into a retry loop and then a dropped message."""
    from enrichment.schemas import ArticleExtraction

    assert _looks_like_json_schema(ArticleExtraction.model_json_schema()) is True
    good = {"shared": {"headline_summary": "Court refuses urgent hearing", "entities": []}}
    assert _looks_like_json_schema(good) is False


@pytest.mark.asyncio
async def test_an_echoed_schema_is_named_and_not_quoted_back(monkeypatch):
    fake = _FakeLLM(['{"$defs": {"X": {}}, "type": "object"}', '{"headline": "the real one"}'])
    monkeypatch.setattr("common.llm.get_llm", lambda: fake)
    monkeypatch.setattr("common.llm._respect_cooldown", lambda: __import__("asyncio").sleep(0))

    out = await structured_chat(
        model="m", messages=[{"role": "user", "content": "go"}],
        output_model=Tiny, trace_name="t",
    )
    assert out.headline == "the real one", "the corrective retry did not recover"

    retry = fake.seen[1]
    correction = retry[-1]["content"]
    assert "INSTANCE" in correction

    # The old path appended {"role": "assistant", "content": <the echo>} before
    # the correction, so the model saw the schema one more time and tended to
    # repeat it. The new path must add the correction and nothing else.
    #
    # (Checking for the literal "$defs" would be wrong here: the corrective
    # message names it on purpose, telling the model not to emit one.)
    appended = retry[len(fake.seen[0]):]
    assert [m["role"] for m in appended] == ["user"], (
        f"the echoed schema was quoted back into the retry: {[m['role'] for m in appended]}"
    )


# --- the model answering with a bare number ------------------------------------


def test_a_bare_scalar_is_refused_with_a_useful_message():
    """Observed live on the extract model: it answered `-8.039215789473683` and
    `-1e-05` — a stray sentiment value, the object nowhere in sight.

    `json.loads` SUCCEEDS on that, so the brace scan never ran and pydantic
    reported "Input should be a valid dictionary", which reads like a schema
    mismatch rather than "the model did not answer". Naming it is the difference
    between tuning a schema and chasing a model.
    """
    import pytest as _p

    from common.llm import _parse_json_loose

    for bare in ("-8.039215789473683", "-1e-05", "42", '"just a string"', "true"):
        with _p.raises(ValueError, match="bare"):
            _parse_json_loose(bare)


def test_an_object_buried_in_reasoning_text_is_still_found():
    """The extract model leaks chain-of-thought. Short-circuiting on the first
    valid JSON value would miss the object sitting after it."""
    from common.llm import _parse_json_loose

    content = 'Thinking Process:\n\n1. sentiment is -0.2\n\n{"shared": {"headline_summary": "x"}}'
    assert _parse_json_loose(content) == {"shared": {"headline_summary": "x"}}


def test_a_real_object_still_parses_unchanged():
    """The guard must not cost the working path."""
    from common.llm import _parse_json_loose

    assert _parse_json_loose('{"a": 1}') == {"a": 1}
    assert _parse_json_loose('```json\n{"a": 2}\n```') == {"a": 2}


def test_a_list_WRAPPING_the_object_is_unwrapped_not_refused():
    """Models wrap the answer in an array constantly. The object is right there,
    so recovering it beats refusing — the guard exists to catch output with no
    object in it, not to be strict for its own sake."""
    from common.llm import _parse_json_loose

    assert _parse_json_loose('[{"shared": {"headline_summary": "x"}}]') == {
        "shared": {"headline_summary": "x"}
    }


def test_a_list_with_no_object_in_it_is_refused():
    """`[1, 2, 3]` has nothing to unwrap, and pydantic's "valid dictionary"
    complaint would send the reader looking at the schema instead of the model."""
    import pytest as _p

    from common.llm import _parse_json_loose

    with _p.raises(ValueError, match="bare list"):
        _parse_json_loose("[1, 2, 3]")
