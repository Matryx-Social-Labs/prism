"""Poll the shows' feeds into podcast_episodes. Idempotent on (show, guid)."""
from __future__ import annotations

import calendar
import uuid
from datetime import UTC, datetime, timedelta

import feedparser
import httpx
from sqlalchemy import text

from common.db import session_scope
from common.logging import get_logger
from podcasts.shows import SHOWS, ShowSpec

logger = get_logger(__name__)

UA = "Mozilla/5.0 (compatible; Prism/1.0; +https://readprism.news)"
# Older than this is catalogued, never transcribed: a clip is about today's story.
TRANSCRIBE_WITHIN = timedelta(hours=72)


def _duration_s(raw: str | None) -> int | None:
    """itunes:duration is '2398', '00:06:48' or '8:07'."""
    if not raw:
        return None
    parts = raw.strip().split(":")
    try:
        nums = [int(float(p)) for p in parts]
    except ValueError:
        return None
    total = 0
    for n in nums:
        total = total * 60 + n
    return total or None


def _published(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(t), tz=UTC) if t else None


async def upsert_show(spec: ShowSpec, art_url: str | None) -> None:
    async with session_scope() as s:
        await s.execute(
            text(
                """
                INSERT INTO podcast_shows (slug, name, publisher, feed_url, site_url, art_url, language, last_polled_at)
                VALUES (:slug, :name, :publisher, :feed_url, :site_url, :art_url, :language, now())
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name, publisher = EXCLUDED.publisher, feed_url = EXCLUDED.feed_url,
                  site_url = EXCLUDED.site_url, art_url = COALESCE(EXCLUDED.art_url, podcast_shows.art_url),
                  last_polled_at = now()
                """
            ),
            {"slug": spec.slug, "name": spec.name, "publisher": spec.publisher, "feed_url": spec.feed_url,
             "site_url": spec.site_url, "art_url": art_url, "language": spec.language},
        )


async def poll_show(spec: ShowSpec, http: httpx.AsyncClient) -> int:
    """Fetch one feed; insert the episodes we have not seen. Returns new rows."""
    r = await http.get(spec.feed_url, headers={"User-Agent": UA}, follow_redirects=True)
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    art = (parsed.feed.get("image") or {}).get("href") or None
    await upsert_show(spec, art)
    now = datetime.now(UTC)
    new = 0
    async with session_scope() as s:
        for e in parsed.entries:
            audio = next((link.get("href") for link in e.get("links", []) if link.get("rel") == "enclosure" and link.get("href")), None)
            if not audio:
                enc = (e.get("enclosures") or [{}])[0]
                audio = enc.get("href") or enc.get("url")
            pub = _published(e)
            guid = e.get("id") or e.get("guid") or audio
            if not (audio and pub and guid):
                continue
            status = "pending" if now - pub <= TRANSCRIBE_WITHIN else "skipped"
            res = await s.execute(
                text(
                    """
                    INSERT INTO podcast_episodes (id, show_slug, guid, title, episode_url, audio_url, published_at, feed_duration_s, transcript_status)
                    VALUES (:id, :show, :guid, :title, :url, :audio, :pub, :dur, :status)
                    ON CONFLICT (show_slug, guid) DO NOTHING
                    """
                ),
                {"id": uuid.uuid4(), "show": spec.slug, "guid": guid, "title": (e.get("title") or "").strip()[:500],
                 "url": e.get("link"), "audio": audio, "pub": pub, "dur": _duration_s(e.get("itunes_duration")), "status": status},
            )
            new += res.rowcount or 0
    return new


async def poll_all() -> dict[str, int]:
    out: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=30) as http:
        for spec in SHOWS:
            try:
                out[spec.slug] = await poll_show(spec, http)
            except Exception as exc:  # noqa: BLE001 — one dead feed must not stop the others
                logger.warning("podcast_poll_failed", show=spec.slug, error=str(exc)[:200])
                out[spec.slug] = -1
    logger.info("podcast_polled", **out)
    return out
