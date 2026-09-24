"""Event routes: detail, on-demand lens brief, suggested questions, Ask (SSE).

The on-demand brief is where the read-time paywall gate will attach (freemium
PR2). The single-flight lock below is in-process only — PR2 replaces it with a
Redis lock so it holds across API replicas.
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.questions import suggested_questions
from agent.rag import answer_stream, ensure_session
from api.deps import client_ip, get_current_user_optional
from api.schemas import (
    AskRequest,
    BriefResponse,
    ClaimOut,
    ClipOut,
    ClipShow,
    EntityOut,
    EventDetail,
    ImpactOut,
    PerspectiveOut,
    QuestionsResponse,
    SourceRef,
    SpeakerClaims,
    XPostOut,
)
from common import outlets, usage
from common.billing import plan_for
from common.config import get_settings
from common.db import get_db
from common.images import hi_res, placeholder_hashes
from common.lenses import LENSES, PAID_LENS_FIELDS
from common.locks import single_flight
from common.logging import get_logger
from common.quota import (
    READER_LENS,
    ask_allowance,
    ask_burst_ok,
    ask_record_spend,
    grant_samples,
    has_unlocked,
    record_unlock,
    release_unlock,
    remaining_samples,
    try_consume_sample,
    unlocked_lenses,
)
from correlation.briefs import available_lenses, generate_briefs, persist_briefs

# Shared with the worker's rendering sweep (enrichment/renderings.py), which must
# see a speaker card exactly as this route builds it.
from enrichment.claims import dedupe_sources, flat_ws
from enrichment.claims import speaker_key as _speaker_key
from enrichment.renderings import apply as apply_renderings
from enrichment.renderings import claim_key

logger = get_logger(__name__)
router = APIRouter()


CONTEXT_CHARS = 220


def quote_context(clean_text: str | None, quote: str, start: int | None, end: int | None) -> tuple[str, str]:
    """The article's own words either side of a verified quote, cut at word
    boundaries. Empty unless the span still points at the quote: the text is
    re-checked here, so a stale offset shows nothing rather than the wrong
    sentence."""
    clean_text = flat_ws(clean_text)  # the span was measured on the flattened text
    if not clean_text or start is None or end is None or clean_text[start:end] != quote:
        return "", ""
    before = clean_text[max(0, start - CONTEXT_CHARS):start]
    after = clean_text[end:end + CONTEXT_CHARS]
    if start - CONTEXT_CHARS > 0 and " " in before:
        before = before.split(" ", 1)[1]
    if end + CONTEXT_CHARS < len(clean_text) and " " in after:
        after = after.rsplit(" ", 1)[0]
    return before.strip(), after.strip()


async def event_claim_verdicts(db: AsyncSession, event_id: uuid.UUID) -> dict[str, dict]:
    """Speaker key -> the card's verdicts (enrichment/renderings.py). Empty unless
    PRISM_QUOTE_VERDICTS on this service: the worker judges in shadow while the
    API serves nothing, until tools/gold_renderings says the verdicts are good."""
    if not get_settings().prism_quote_verdicts:
        return {}
    rows = (
        await db.execute(
            text("SELECT speaker_key, verdicts FROM claim_verdicts WHERE event_id = :e"),
            {"e": str(event_id)},
        )
    ).all()
    return {r.speaker_key: r.verdicts for r in rows if isinstance(r.verdicts, dict)}


async def event_x_posts(db: AsyncSession, event_id: uuid.UUID) -> list[XPostOut]:
    """The official accounts' posts on this story, best first. Off (empty)
    unless PRISM_X_ENABLED on this service: the worker can run in shadow while
    the API serves nothing, until tools/gold_xposts says the matches are good."""
    if not get_settings().prism_x_enabled:
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT p.post_id, p.text, p.created_at, ep.method, ep.score,
                       a.handle, a.name, a.tier, a.profile_image_url
                FROM event_x_posts ep
                JOIN x_posts p ON p.post_id = ep.post_id
                JOIN x_accounts a ON a.handle = p.handle
                WHERE ep.event_id = :id AND a.enabled AND p.deleted_at IS NULL
                ORDER BY ep.rank, ep.score DESC
                """
            ),
            {"id": event_id},
        )
    ).mappings().all()
    return [
        XPostOut(
            post_id=r["post_id"], handle=r["handle"], name=r["name"], tier=r["tier"],
            profile_image_url=r["profile_image_url"],
            url=f"https://x.com/{r['handle']}/status/{r['post_id']}",
            text=r["text"], created_at=r["created_at"].isoformat(),
            method=r["method"], score=float(r["score"]),
        )
        for r in rows
    ]


async def event_clips(db: AsyncSession, event_id: uuid.UUID) -> list[ClipOut]:
    """The podcast clips on this story, best first. Off (empty) unless the
    pipeline is enabled on this service — the gate that says the matches are
    good enough to show (tools/gold_clips) is a founder decision, not a query."""
    if not get_settings().prism_podcasts_enabled:
        return []
    rows = (
        await db.execute(
            text(
                """
                SELECT ec.start_s, ec.end_s, ec.score, w.text, w.words,
                       e.title AS episode_title, e.episode_url, e.audio_url, e.audio_duration_s, e.published_at,
                       s.slug, s.name, s.publisher, s.art_url, s.site_url
                FROM event_clips ec
                JOIN podcast_windows w ON w.id = ec.window_id
                JOIN podcast_episodes e ON e.id = w.episode_id
                JOIN podcast_shows s ON s.slug = e.show_slug
                WHERE ec.event_id = :id AND s.enabled
                ORDER BY ec.rank, ec.score DESC
                """
            ),
            {"id": event_id},
        )
    ).mappings().all()
    out: list[ClipOut] = []
    for r in rows:
        # A merged clip spans several windows; the row carries the best window's
        # words, trimmed to the clip — enough for read-along on what plays first.
        words = [w for w in (r["words"] or []) if isinstance(w, list) and len(w) == 3 and r["start_s"] <= float(w[1]) <= r["end_s"]]
        out.append(
            ClipOut(
                show=ClipShow(slug=r["slug"], name=r["name"], publisher=r["publisher"], art_url=r["art_url"], site_url=r["site_url"]),
                episode_title=r["episode_title"],
                episode_url=r["episode_url"],
                audio_url=r["audio_url"],
                audio_duration_s=r["audio_duration_s"],
                published_at=r["published_at"].isoformat(),
                start_s=float(r["start_s"]),
                end_s=float(r["end_s"]),
                text=r["text"],
                words=words,
                score=float(r["score"]),
            )
        )
    return out


ENGLISH = "en"


def interleave_languages(claims: list[ClaimOut]) -> tuple[list[ClaimOut], list[str]]:
    """One quote per language before any language's second. Returns the order
    the languages were taken in.

    The card shows two quotes and the rest on request
    (`web/src/components/Said.tsx`), and this list used to be ordered by recency
    alone. So a later report in another language pushed the earlier one clean out
    of the fold: a reader saw a Kannada rendering of words spoken in English with
    the English rendering hidden behind a button, and nothing on the card said a
    language was missing. Round-robin instead — whatever the fold is, it covers
    as many languages as it has room for.

    English leads for a reader who has expressed no preference (PRODUCT.md
    "English-first display"); the client re-orders for a reader who has. Ties
    break on quote count, then first appearance, so the payload is byte-identical
    for every reader and the route stays cacheable.
    """
    buckets: dict[str, list[ClaimOut]] = {}
    # Position of each language's FIRST quote, kept as we bucket rather than
    # looked up afterwards: ClaimOut is a Pydantic model, so `list.index` would
    # compare by field values and hand back the wrong position for a speaker
    # quoted identically by two outlets.
    seen_at: dict[str, int] = {}
    for i, c in enumerate(claims):
        lang = c.lang or ""
        buckets.setdefault(lang, []).append(c)
        seen_at.setdefault(lang, i)
    order = sorted(buckets, key=lambda lang: (lang != ENGLISH, -len(buckets[lang]), seen_at[lang]))
    out: list[ClaimOut] = []
    for i in range(max((len(b) for b in buckets.values()), default=0)):
        out += [buckets[lang][i] for lang in order if i < len(buckets[lang])]
    return out, [lang for lang in order if lang]


def _with_verdicts(claims: list[ClaimOut], card: dict) -> list[ClaimOut]:
    """Mark which quotes are one statement printed twice and which are an
    outlet's translation. A quote the verdicts do not mention is returned
    unchanged — an unjudged card is exactly today's card."""
    keys = [claim_key(c.article_id, c.quote_text) for c in claims]
    utterance, translated = apply_renderings(keys, [card])
    return [
        c.model_copy(update={"utterance": utterance.get(key), "translated": key in translated})
        for c, key in zip(claims, keys, strict=True)
    ]


def group_claims(sources: list[dict], verdicts: dict[str, dict] | None = None) -> list[SpeakerClaims]:
    """Speaker-grouped, most-quoted first; newest article first, article order within it.

    `sources` is the event's article rows, already newest-first, each carrying
    the enrichment's `claims` JSONB (NULL for an un-enriched article). Shown
    under the first surface form seen for a speaker key.

    Defensive on shape by design: this runs on the most-viewed route, and a row
    written by an older extractor could hold a dict or a string where a list is
    expected. Skipping it costs one article's quotes; raising costs the page.
    """
    by: dict[str, list[tuple[tuple, ClaimOut]]] = {}
    label: dict[str, str] = {}
    first_seen: dict[str, int] = {}
    roles: dict[str, dict[str, int]] = {}
    for src in sources:
        claims = src["claims"]
        if not isinstance(claims, list):
            continue
        pub = src["published_at"]
        for c in claims:
            if not isinstance(c, dict):
                continue
            # Leaf types too, not just the containers: a non-string speaker
            # would raise on .strip(), a non-int offset would fail ClaimOut
            # validation, and either is an unhandled 500 on this route.
            speaker = c.get("speaker")
            quote = c.get("quote_text")
            if not isinstance(speaker, str) or not isinstance(quote, str):
                continue
            speaker, quote = speaker.strip(), quote.strip()
            if not speaker or not quote:
                continue  # verified at write time; belt and braces
            start, end = c.get("quote_start"), c.get("quote_end")
            start = start if isinstance(start, int) and not isinstance(start, bool) else None
            end = end if isinstance(end, int) and not isinstance(end, bool) else None
            key = _speaker_key(speaker)
            if key not in by:
                by[key] = []
                label[key] = speaker
                first_seen[key] = len(first_seen)
            role = c.get("speaker_role")
            if isinstance(role, str) and role.strip():
                r = roles.setdefault(key, {})
                r[role.strip()] = r.get(role.strip(), 0) + 1
            # newest article first, then the order the article said them
            sort_key = (-(pub.timestamp() if pub else 0.0), start or 0)
            before, after = quote_context(src.get("clean_text"), quote, start, end)
            by[key].append((sort_key, ClaimOut(
                quote_text=quote,
                quote_start=start,
                quote_end=end,
                context_before=before,
                context_after=after,
                article_id=str(src["article_id"]),
                source_name=src["source_name"],
                url=src["url"],
                published_at=pub.isoformat() if pub else None,
                lang=src.get("lang"),
            )))
    out: list[SpeakerClaims] = []
    for k in sorted(by, key=lambda k: (-len(by[k]), first_seen[k])):
        ordered, languages = interleave_languages(
            [cl for _, cl in sorted(by[k], key=lambda x: x[0])]
        )
        if verdicts and k in verdicts:
            ordered = _with_verdicts(ordered, verdicts[k])
        out.append(
            SpeakerClaims(
                speaker=label[k],
                role=max(roles[k], key=roles[k].get) if k in roles else None,
                claims=ordered,
                languages=languages,
            )
        )
    return out


@router.get("/api/v1/events/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Depends(get_current_user_optional),
):
    event = (
        await db.execute(
            text(
                """
                SELECT id, title, headline_by, summary, sector, subsector, image_url, regions,
                       occurred_at, last_updated_at, projection
                FROM events WHERE id = :eid
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().first()
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    source_rows = (
        await db.execute(
            text(
                """
                SELECT a.id AS article_id, s.name AS source_name, s.slug AS source_slug,
                       s.reliability ->> 'funding' AS funding,
                       ri.url, ri.url_canonical, ri.title, ri.published_at, ri.image_url, ri.image_phash,
                       ri.language AS lang,
                       e.shared_fields -> 'claims' AS claims,
                       CASE WHEN jsonb_typeof(e.shared_fields -> 'claims') = 'array'
                             AND jsonb_array_length(e.shared_fields -> 'claims') > 0
                            THEN a.clean_text END AS clean_text
                FROM event_memberships em
                JOIN articles a ON a.id = em.article_id
                JOIN raw_items ri ON ri.id = a.raw_item_id
                JOIN sources s ON s.id = ri.source_id
                LEFT JOIN enrichments e ON e.article_id = a.id
                WHERE em.event_id = :eid
                ORDER BY ri.published_at DESC NULLS LAST
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()
    sources = dedupe_sources(list(source_rows))

    perspectives = (
        await db.execute(
            text(
                """
                SELECT label, origin_country, summary, member_articles
                FROM perspectives WHERE event_id = :eid ORDER BY created_at
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    impacts = (
        await db.execute(
            text(
                """
                SELECT i.id, i.effect, i.direction, i.horizon, i.confidence,
                       i.parent_impact_id,
                       COALESCE(en.name, i.provenance ->> 'entity_name') AS entity_name
                FROM impacts i
                LEFT JOIN entities en ON en.id = i.entity_id
                WHERE i.event_id = :eid
                ORDER BY i.created_at
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    entities = (
        await db.execute(
            text(
                """
                SELECT en.name, en.entity_type, en.slug, ee.role
                FROM event_entities ee
                JOIN entities en ON en.id = ee.entity_id
                WHERE ee.event_id = :eid
                ORDER BY (ee.role = 'affected') DESC, en.name
                LIMIT 12
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    # No story_timeline() call here: the arc belongs to /trending/{slug}, which
    # builds it from the story's frozen member set. Serving it from here as well
    # meant two member sets for one story. Dropping it also takes a Redis lookup
    # and a partition/BFS assembly off the most-viewed route.
    #
    # The story page still needs to FIND that owner, so this is the one thing it
    # gets: the canonical (unmerged) story whose frozen member set holds this
    # event. Newest first, because a story that was split leaves an older,
    # still-unmerged row behind whose members overlap.
    # ponytail: JSONB containment over the whole stories table — a few thousand
    # rows today. Add a GIN index on member_event_ids if this shows up in p95.
    story = (
        await db.execute(
            text(
                """
                SELECT slug FROM stories
                WHERE merged_into IS NULL
                  AND member_event_ids @> CAST(:member AS jsonb)
                ORDER BY last_updated_at DESC
                LIMIT 1
                """
            ),
            {"member": json.dumps([str(event_id)])},
        )
    ).mappings().first()
    projection = event["projection"] or {}

    # THE PAYWALL'S REAL BOUNDARY. Gating /brief alone was bypassable: this
    # endpoint returns every cached lens brief as a plain field, so one request
    # here handed over exactly what /brief was refusing. Found by the outside
    # voice in review; the server-side gate has to live wherever the content
    # leaves the server, not only on the route that generates it.
    #
    # Reader lens is always included. Anything else is included only for a
    # reader who has unlocked it.
    all_briefs = projection.get("lens_briefs") or {}
    all_points = projection.get("lens_points") or {}
    allowed = {READER_LENS}
    if user_id is not None:
        allowed |= await unlocked_lenses(db, user_id, event_id)
    briefs = {k: v for k, v in all_briefs.items() if k in allowed}
    points = {k: v for k, v in all_points.items() if k in allowed}
    # `projection` carries the same content, so it is filtered too rather than
    # left as an open side door.
    safe_projection = dict(projection)
    if "lens_briefs" in safe_projection:
        safe_projection["lens_briefs"] = briefs
    if "lens_points" in safe_projection:
        safe_projection["lens_points"] = points
    # THE FACTS, NOT JUST THE PROSE. projection.cyber / projection.finance hold
    # CVSS, KEV status, tickers and the catalyst — what the desktop rail renders
    # when a lens is selected. The flip to a LOCKED lens is allowed (it is the
    # upgrade moment), so with these still in the payload the rail showed
    # "CATALYST · REGULATORY_ACTION" to a reader who had not paid. Same class as
    # the /questions leak. available_lenses below stays computed from the
    # UNFILTERED projection: which lenses exist is public, what they say is not.
    for lens_slug, key in PAID_LENS_FIELDS.items():
        if lens_slug not in allowed and key in safe_projection:
            safe_projection[key] = None

    reg = await outlets.registry(db)
    mon = await outlets.monitored(db)
    placeholders = await placeholder_hashes(db)
    return EventDetail(
        id=str(event["id"]),
        title=event["title"],
        headline_by=event["headline_by"],
        summary=event["summary"],
        sector=event["sector"],
        subsector=event["subsector"],
        image_url=event["image_url"],
        regions=event["regions"] or [],
        occurred_at=event["occurred_at"].isoformat() if event["occurred_at"] else None,
        last_updated_at=event["last_updated_at"].isoformat(),
        projection=safe_projection,
        lens_briefs=briefs,
        lens_points=points,
        available_lenses=available_lenses(projection, event["sector"]),
        coverage=projection.get("coverage"),
        entities=[
            EntityOut(name=e["name"], entity_type=e["entity_type"], role=e["role"], slug=e["slug"]) for e in entities
        ],
        story_slug=story["slug"] if story else None,
        monitored_outlets=mon.outlets,
        monitored_checked_at=mon.checked_at,
        sources=[
            SourceRef(
                article_id=str(s["article_id"]),
                source_name=s["source_name"],
                source_slug=s["source_slug"],
                url=s["url"],
                title=s["title"],
                published_at=s["published_at"].isoformat() if s["published_at"] else None,
                funding=s["funding"],
                code=reg[s["source_slug"]].code if s["source_slug"] in reg else None,
                origin=reg[s["source_slug"]].origin if s["source_slug"] in reg else None,
                language=reg[s["source_slug"]].language if s["source_slug"] in reg else None,
                publisher=reg[s["source_slug"]].publisher if s["source_slug"] in reg else None,
                domain=reg[s["source_slug"]].domain if s["source_slug"] in reg else None,
                image_url=None if s.get("image_phash") in placeholders else hi_res(s.get("image_url")),
                image_phash=s.get("image_phash"),
            )
            for s in sources
        ],
        perspectives=[
            PerspectiveOut(
                label=p["label"],
                origin_country=p["origin_country"],
                summary=p["summary"],
                article_ids=[str(a) for a in (p["member_articles"] or [])],
            )
            for p in perspectives
        ],
        claims=group_claims(sources, await event_claim_verdicts(db, event["id"])),
        clips=await event_clips(db, event["id"]),
        x_posts=await event_x_posts(db, event["id"]),
        impacts=[
            ImpactOut(
                id=str(i["id"]),
                entity_name=i["entity_name"],
                effect=i["effect"],
                direction=i["direction"],
                horizon=i["horizon"],
                confidence=i["confidence"],
                parent_impact_id=str(i["parent_impact_id"]) if i["parent_impact_id"] else None,
            )
            for i in impacts
        ],
    )


async def _read_cached_brief(db: AsyncSession, event_id: uuid.UUID, lens: str) -> BriefResponse | None:
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    projection = row["projection"] or {}
    cached = (projection.get("lens_briefs") or {}).get(lens)
    if cached:
        points = (projection.get("lens_points") or {}).get(lens) or []
        return BriefResponse(lens=lens, brief=cached, points=points, cached=True)
    return None


# On-demand lens briefs: any lens on any story — this is what lets a cyber
# professional pull the cyber read of a war, or a trader the market read of a
# breach. Generated once, cached on the event projection. A Redis single-flight
# per (event, lens) holds across API replicas so a burst of viewers (and, once
# the paywall lands, a burst of sample-spenders) costs exactly one LLM call.
@router.get("/api/v1/events/{event_id}/brief", response_model=BriefResponse)
async def get_brief(
    event_id: uuid.UUID,
    lens: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Depends(get_current_user_optional),
):
    if lens not in LENSES:
        raise HTTPException(status_code=422, detail=f"unknown lens '{lens}'")

    # THE GATE SITS ABOVE THE CACHE READ, and that placement is the whole thing.
    # `_read_cached_brief` early-returns, so a check placed below it would only
    # ever run for the FIRST viewer of each (event, lens) — every later reader
    # would be served free. The paywall has to be the first thing that happens.
    paid = lens != READER_LENS
    claimed_now = False
    if paid:
        if user_id is None:
            raise HTTPException(status_code=401, detail="sign in to open this lens")
        if not await has_unlocked(db, user_id, event_id, lens):
            # Claim first, then debit: the claim is the concurrency winner, so
            # two tabs cannot both spend a sample on the same lens.
            claimed_now = await record_unlock(db, user_id, event_id, lens)
            if claimed_now and not await try_consume_sample(db, user_id):
                await release_unlock(db, user_id, event_id, lens)
                left = await remaining_samples(db, user_id)
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "no samples remaining",
                        # None means NO QUOTA ROW — never granted — which is a
                        # different fact from having spent everything.
                        "remaining": left,
                        "lens": lens,
                    },
                )

    cached = await _read_cached_brief(db, event_id, lens)
    if cached:
        return cached

    async with single_flight(f"brief:{event_id}:{lens}"):
        # Past the single-flight barrier, re-read: the leader may have just
        # filled the cache while we waited. If it's still empty, generate — that
        # covers the leader and the fallback case where the leader stalled/died.
        cached = await _read_cached_brief(db, event_id, lens)
        if cached:
            return cached
        try:
            briefs = await generate_briefs(event_id, [lens])
            await persist_briefs(event_id, briefs)
            read = briefs.get(lens) or {}
        except Exception:
            # The brief is an on-demand LLM synthesis. If the model is unavailable
            # (quota exhausted, timeout), return an empty brief so the story page
            # shows "the <lens> read isn't available yet" — never a 500.
            logger.warning("brief_unavailable", event_id=str(event_id), lens=lens, exc_info=True)
            read = {}
            # NOBODY PAYS FOR AN EMPTY PANEL. The claim was taken above on the
            # assumption a brief would materialise; it did not, so give it back.
            # Only the caller that actually claimed it may release it — otherwise
            # a second tab's failure would revoke the first tab's paid unlock.
            if claimed_now:
                await release_unlock(db, user_id, event_id, lens)
                await grant_samples(db, user_id, 1)
        return BriefResponse(
            lens=lens, brief=read.get("text"), points=read.get("points") or [], cached=False
        )


@router.get("/api/v1/events/{event_id}/questions", response_model=QuestionsResponse)
async def get_questions(
    event_id: uuid.UUID,
    lens: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Depends(get_current_user_optional),
):
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    # Anonymous is the common case and needs no query at all: without a user
    # there is nothing to have unlocked.
    unlocked = (
        user_id is not None
        and lens is not None
        and await has_unlocked(db, user_id, event_id, lens)
    )
    return QuestionsResponse(
        questions=suggested_questions(row["projection"], lens, unlocked=unlocked)
    )


@router.post("/api/v1/events/{event_id}/ask")
async def ask(
    event_id: uuid.UUID,
    body: AskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Depends(get_current_user_optional),
):
    exists = (
        await db.execute(text("SELECT 1 FROM events WHERE id = :eid"), {"eid": str(event_id)})
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="event not found")
    question = body.question.strip()
    if not question or len(question) > 2000:
        raise HTTPException(status_code=422, detail="question must be 1-2000 characters")

    session_id = await ensure_session(
        event_id,
        uuid.UUID(body.session_id) if body.session_id else None,
        user_ref=str(user_id) if user_id else None,
    )

    # THE SPEND GATE, and it runs before any retrieval or generation. Ask is the
    # only endpoint whose cost scales with users rather than corpus size, and it
    # was unlimited and unauthenticated. Checked AFTER ensure_session so an
    # anonymous session that has just been adopted counts against the account
    # rather than restarting its allowance.
    plan = await plan_for(db, user_id)
    allowed, used, cap = await ask_allowance(
        db, str(user_id) if user_id else None, session_id, plan
    )
    if not allowed:
        # Someone who wanted another answer and could not have one: the demand
        # signal for Plus (admin dashboard). Counted apart from this request,
        # whose transaction the 429 rolls back.
        await usage.bump_detached("ask_limit", plan if user_id else "anonymous")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "question limit reached",
                "used": used,
                "limit": cap,
                # Anonymous readers are told the way forward is signing in, not
                # that they are blocked: the cap exists to convert, not to wall.
                "signin_helps": user_id is None,
                # A free account at its cap is told what Plus gives (BUSINESS-MODEL.md §3).
                "plus_helps": user_id is not None and plan != "plus",
            },
        )
    # The Redis-side brakes: a burst from one identity, an anonymous flood from
    # one address, and the day's spend ceiling. Plan caps above still hold if
    # Redis is away.
    ip = client_ip(request)
    reason = await ask_burst_ok(str(user_id) if user_id else str(session_id), ip, anonymous=user_id is None)
    if reason == "burst":
        raise HTTPException(status_code=429, detail={"error": "too many questions this minute", "retry_after_s": 60})
    if reason == "ip":
        await usage.bump_detached("ask_limit", "anonymous")
        raise HTTPException(status_code=429, detail={"error": "question limit reached", "signin_helps": True})
    if reason == "ceiling" and plan != "plus":
        raise HTTPException(status_code=503, detail={"error": "Ask is resting for today for free readers; it is back at midnight UTC", "plus_helps": user_id is not None})
    await ask_record_spend(plan)

    async def sse():
        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"
        async for chunk in answer_stream(event_id=event_id, session_id=session_id, question=question, plan=plan):
            yield f"event: {chunk['type']}\ndata: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
