"""The shape after the answer: what the reports don't say, follow-ups, one table.

The model writes its prose first (streamed to the reader as it comes), then a
line `===` and one JSON object. The prose is what the reader sees typed; the
JSON is held back and delivered whole as one `structure` event, so no reader
ever watches braces stream in. Anything malformed after the marker is dropped
— the prose stands on its own — because the tail is a convenience, never the
answer.
"""

import json
import re
from collections.abc import Iterator

from pydantic import BaseModel, Field, field_validator

# Where the tail begins: the marker the prompt asks for, or — because a small
# model skips it about one time in three — the JSON object itself, recognised
# by its first key. Neither string occurs in an answer about the news.
MARKERS = ("===", '{"kind"', '{"columns"', '{"rows"', '{"gaps"', '{"followups"')
# Hold back this many trailing characters while streaming so a marker split
# across two deltas ('{"ki' then 'nd"') is caught before its first half escapes.
HOLD = max(len(m) for m in MARKERS) - 1


class StructureRow(BaseModel):
    # Two to three short cells; the last (`n`) is citation marks "[1][3]" so the
    # web renders them with the same chip as the prose and the server counts them.
    a: str = Field(max_length=200)
    b: str = Field(max_length=400)
    n: str = Field("", max_length=40)

    @field_validator("n")
    @classmethod
    def _marks_only(cls, v: str) -> str:
        return "".join(re.findall(r"\[\d{1,2}\]", v))


class Structure(BaseModel):
    kind: str | None = None  # timeline | who_said | compare | numbers
    columns: list[str] = Field(default_factory=list, max_length=2)
    rows: list[StructureRow] = Field(default_factory=list, max_length=12)
    gaps: str | None = Field(None, max_length=300)
    followups: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("kind")
    @classmethod
    def _known(cls, v: str | None) -> str | None:
        return v if v in ("timeline", "who_said", "compare", "numbers") else None

    @field_validator("followups")
    @classmethod
    def _short(cls, v: list[str]) -> list[str]:
        return [q.strip() for q in v if q and len(q.strip()) <= 120][:3]

    def empty(self) -> bool:
        return not (self.rows or self.gaps or self.followups)


class TailSplitter:
    """Feed deltas in; get the prose to emit out; read the tail at the end."""

    def __init__(self) -> None:
        self._buf = ""
        self._tail: str | None = None

    def feed(self, delta: str) -> Iterator[str]:
        if self._tail is not None:
            self._tail += delta
            return
        self._buf += delta
        hits = [(self._buf.find(m), m) for m in MARKERS if m in self._buf]
        if hits:
            at, m = min(hits)
            # A JSON-start marker is part of the tail; the `===` line is not.
            prose, self._tail = self._buf[:at].rstrip(), self._buf[at if m.startswith("{") else at + len(m):]
            self._buf = ""
            if prose:
                yield prose
            return
        if len(self._buf) > HOLD:
            out, self._buf = self._buf[:-HOLD], self._buf[-HOLD:]
            yield out

    def flush(self) -> str:
        """Whatever prose is still held (nothing, once a marker was seen)."""
        out, self._buf = self._buf, ""
        return out if self._tail is None else ""

    def structure(self) -> Structure | None:
        if self._tail is None:
            return None
        raw = self._tail
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = Structure.model_validate(json.loads(raw[start : end + 1]))
        except Exception:
            return None
        return None if parsed.empty() else parsed
