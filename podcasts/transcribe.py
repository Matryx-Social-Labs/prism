"""One episode in, transcript windows out.

The enclosure is streamed to a temp file, cut into ~20 MB pieces (the
transcription endpoint caps a file at 25 MB; MP3 frames are self-contained so
a byte cut costs at most one garbled frame at the seam), sent to OpenRouter's
/audio/transcriptions (routed to Groq's whisper-large-v3: ~$0.11 an hour;
turbo was $0.04 but dropped phrases, word timestamps), and discarded. Each piece's
timestamps are offset by the durations whisper reported for the pieces before
it — so a variable-bitrate file cannot skew them the way a byte→time guess
would.

Windows are 30–60 s of consecutive segments, cut at a segment end, with the
words inside them and the same embedding the events carry.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.embeddings import embed_texts
from common.logging import get_logger
from podcasts.feeds import UA, podcast_client

logger = get_logger(__name__)

TRANSCRIBE_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
# The full large-v3, not turbo: turbo dropped a whole phrase mid-sentence
# ("…had turned a chapter, [missing] appointment. Separately…") on a
# Moneycontrol clip and every word after it read ahead of the voice
# (founder, 2026-09-21). About 2.5× the price ($0.11 an hour on Groq); the
# read-along is only as good as the alignment.
TRANSCRIBE_MODEL = os.environ.get("PRISM_MODEL_TRANSCRIBE", "openai/whisper-large-v3")
PIECE_BYTES = 20 * 1024 * 1024
MAX_BYTES = 160 * 1024 * 1024  # ~2.5 h at 128 kbps; longer is not a daily news show
WINDOW_MIN_S = 30.0
WINDOW_MAX_S = 60.0


@dataclass
class Window:
    seq: int
    start_s: float
    end_s: float
    text: str
    words: list[list] = field(default_factory=list)  # [word, start, end]


def windows_from_segments(segments: list[dict], words: list[dict]) -> list[Window]:
    """Pack consecutive segments into 30–60 s windows. Pure; tested."""
    out: list[Window] = []
    cur: list[dict] = []
    wi = 0
    words = sorted(words, key=lambda w: w.get("start", 0.0))

    def flush() -> None:
        nonlocal cur, wi
        if not cur:
            return
        start, end = float(cur[0]["start"]), float(cur[-1]["end"])
        txt = " ".join(str(s.get("text", "")).strip() for s in cur).strip()
        ws: list[list] = []
        while wi < len(words) and float(words[wi].get("start", 0.0)) < end:
            w = words[wi]
            if float(w.get("start", 0.0)) >= start:
                ws.append([str(w.get("word", "")).strip(), round(float(w["start"]), 2), round(float(w.get("end", w["start"])), 2)])
            wi += 1
        if txt:
            out.append(Window(seq=len(out), start_s=round(start, 2), end_s=round(end, 2), text=txt, words=ws))
        cur = []

    for seg in segments:
        if cur and float(seg["end"]) - float(cur[0]["start"]) > WINDOW_MAX_S:
            flush()
        cur.append(seg)
        if float(cur[-1]["end"]) - float(cur[0]["start"]) >= WINDOW_MIN_S:
            flush()
    flush()
    return out


async def _download(url: str, http: httpx.AsyncClient) -> tuple[str, int]:
    fd, path = tempfile.mkstemp(suffix=".mp3", prefix="prism-pod-")
    size = 0
    with os.fdopen(fd, "wb") as f:
        async with http.stream("GET", url, headers={"User-Agent": UA}, follow_redirects=True) as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes(1024 * 256):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError(f"audio over {MAX_BYTES} bytes")
                f.write(chunk)
    return path, size


async def _transcribe_piece(data: bytes, language: str | None, http: httpx.AsyncClient) -> dict:
    key = get_settings().openrouter_api_key
    form = {"model": TRANSCRIBE_MODEL, "response_format": "verbose_json"}
    if language:
        form["language"] = language
    r = await http.post(
        TRANSCRIBE_URL,
        headers={"Authorization": f"Bearer {key}"},
        data=form,
        files=[("file", ("piece.mp3", data, "audio/mpeg")), ("timestamp_granularities[]", (None, "word")), ("timestamp_granularities[]", (None, "segment"))],
    )
    if r.status_code != 200:
        raise RuntimeError(f"transcription {r.status_code}: {r.text[:200]}")
    return r.json()


async def transcribe_file(path: str, language: str | None, http: httpx.AsyncClient) -> tuple[list[dict], list[dict], float, float]:
    """(segments, words, duration_s, cost_usd) for the whole file, offsets accumulated across pieces."""
    segments: list[dict] = []
    words: list[dict] = []
    offset = 0.0
    cost = 0.0
    with open(path, "rb") as f:
        while True:
            data = f.read(PIECE_BYTES)
            if not data:
                break
            res = await _transcribe_piece(data, language, http)
            for s in res.get("segments") or []:
                segments.append({"start": float(s["start"]) + offset, "end": float(s["end"]) + offset, "text": s.get("text", "")})
            for w in res.get("words") or []:
                words.append({"word": w.get("word", ""), "start": float(w["start"]) + offset, "end": float(w.get("end", w["start"])) + offset})
            offset += float(res.get("duration") or (segments[-1]["end"] - offset if segments else 0.0))
            cost += float((res.get("usage") or {}).get("cost") or 0.0)
    return segments, words, offset, cost


async def transcribe_episode(episode_id: uuid.UUID) -> int:
    """Transcribe one pending episode into windows. Returns windows written."""
    async with session_scope() as s:
        ep = (await s.execute(text("SELECT id, audio_url, show_slug, feed_duration_s FROM podcast_episodes WHERE id = :id"), {"id": episode_id})).mappings().first()
        show = (await s.execute(text("SELECT language FROM podcast_shows WHERE slug = :slug"), {"slug": ep["show_slug"]})).mappings().first()
    language = (show or {}).get("language") or None
    path = None
    try:
        async with podcast_client(httpx.Timeout(300.0, connect=30.0)) as http:
            path, size = await _download(ep["audio_url"], http)
            segments, words, duration, cost = await transcribe_file(path, language, http)
        wins = windows_from_segments(segments, words)
        vecs = await embed_texts([w.text for w in wins]) if wins else []
        async with session_scope() as s:
            await s.execute(text("DELETE FROM podcast_windows WHERE episode_id = :id"), {"id": episode_id})
            for w, v in zip(wins, vecs, strict=True):
                await s.execute(
                    text(
                        "INSERT INTO podcast_windows (id, episode_id, seq, start_s, end_s, text, words, embedding) "
                        "VALUES (:id, :ep, :seq, :start, :end, :text, CAST(:words AS jsonb), CAST(:vec AS vector))"
                    ),
                    {"id": uuid.uuid4(), "ep": episode_id, "seq": w.seq, "start": w.start_s, "end": w.end_s, "text": w.text,
                     "words": __import__("json").dumps(w.words, ensure_ascii=False), "vec": str(v)},
                )
            await s.execute(
                text(
                    "UPDATE podcast_episodes SET transcript_status = 'done', transcribed_at = :now, audio_duration_s = :dur, "
                    "audio_bytes = :bytes, language = :lang, error = NULL WHERE id = :id"
                ),
                {"now": datetime.now(UTC), "dur": duration, "bytes": size, "lang": language, "id": episode_id},
            )
        logger.info("podcast_transcribed", episode=str(episode_id), windows=len(wins), duration_s=round(duration), cost_usd=round(cost, 4))
        return len(wins)
    except Exception as exc:  # noqa: BLE001 — recorded on the row, the run goes on
        async with session_scope() as s:
            await s.execute(text("UPDATE podcast_episodes SET transcript_status = 'failed', error = :e WHERE id = :id"), {"e": str(exc)[:500], "id": episode_id})
        logger.warning("podcast_transcribe_failed", episode=str(episode_id), error=str(exc)[:200])
        return 0
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


async def transcribe_pending(limit: int = 12) -> int:
    async with session_scope() as s:
        ids = [r[0] for r in (await s.execute(text(
            "SELECT id FROM podcast_episodes WHERE transcript_status = 'pending' ORDER BY published_at DESC LIMIT :lim"
        ), {"lim": limit})).all()]
    total = 0
    for eid in ids:
        total += await transcribe_episode(eid)
    return total
