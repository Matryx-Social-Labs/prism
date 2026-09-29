"""Re-judge what the fuzzy tiers attached, and move what is not the same happening.

Until PRISM_EVENT_VERIFY=confirm, the title, embedding and entity tiers attached
on their own. Measured 2026-09-29 against Jev's same-happening test, 781
attaches: entity_overlap 44%, embedding 76%, title 92% — mostly follow-ups
swept into the first record (the parents' hunger strike into the student's
death), sometimes unrelated (a cricketer's milestone into another's century).

For every such membership in the window this asks Jev, on the record's founding
headline and summary, whether the article reports the same happening and
whether it is a later development of it — the same two questions the live path
asks now. Every answer is kept in event_match_verdicts (mode 'repair', never over
another mode's answer), so the dry run from a laptop and the apply on the worker
pay once, and the answers stay on record.

  DATABASE_URL=<prod> uv run python -m tools.repair_attaches --days 7   # dry run: judge, write a CSV, move nothing
  railway ssh --service worker -- python -m tools.repair_attaches --days 7 --apply --detach-below 0.5 --limit 50

--apply moves each membership judged under --detach-below: the article leaves
the record and goes back through the live matching path (correlation/consumer
._attach, which must be running in mode `confirm`), so it joins the record it
does report or founds its own — linked as a later development when Jev says so.
The article keeps the time it first arrived — its record's and its membership's,
never "now", or trending would count it as the last six hours' coverage — and the
records it touches are rebuilt in the same transaction without moving up the
feed. The record it left drops its perspectives and is queued for the ordinary
analysis pass: its briefs described the article that left (about $0.0005 a
record at glm-5.3-flash; 1,891 moves in 7 days touch ~1,500). Run --apply on the
worker: it needs production's Redis for that queue.

A founder never moves: the record is about its founding article. Idempotent: a
membership already moved or re-judged is skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text

from common.config import get_settings
from common.db import session_scope
from common.models import Article, Enrichment
from correlation import consumer
from correlation.verify import Candidate, article_block, event_block, judge_story

FUZZY = ("title_time", "headline_xlang", "embedding", "entity_overlap")
MODE = "repair"
OUT = Path(".context")
# Jev's same-happening answer, in bands a founder can read a sample of.
BANDS = ((0.85, "same"), (0.5, "likely same"), (0.15, "likely different"), (0.0, "different"))
CONCURRENCY = 8


def band(p: float) -> str:
    return next(name for floor, name in BANDS if p >= floor)


async def load(days: int) -> list[dict]:
    """Fuzzy-tier memberships of the window, on unmerged records, that no
    verdict has already confirmed; each with what Jev reads on both sides."""
    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        rows = (
            await s.execute(
                text(
                    """
                    SELECT m.id AS membership, m.event_id, m.article_id, m.match_type, m.created_at AS attached_at,
                           e.title AS event_title, e.summary AS event_summary, e.first_seen_at,
                           src.slug AS source, src.language, ri.published_at, ri.title AS raw_title,
                           en.summary AS article_summary, en.shared_fields->>'headline' AS headline
                    FROM event_memberships m
                    JOIN events e ON e.id = m.event_id AND e.merged_into IS NULL
                    JOIN articles a ON a.id = m.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources src ON src.id = ri.source_id
                    JOIN enrichments en ON en.article_id = a.id
                    WHERE m.match_type = ANY(:fuzzy)
                      AND m.created_at > now() - make_interval(days => :days)
                      AND NOT EXISTS (
                          SELECT 1 FROM event_match_verdicts v
                          WHERE v.article_id = m.article_id AND v.event_id = m.event_id AND v.noul >= :floor
                      )
                    ORDER BY m.created_at, m.id
                    """
                ),
                {"fuzzy": list(FUZZY), "days": days, "floor": get_settings().prism_event_verify_min},
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def _key(r: dict) -> str:
    return f"{r['article_id']}|{r['event_id']}"


async def answered(rows: list[dict]) -> dict[str, list]:
    """The repair's answers already on record for these memberships."""
    if not rows:
        return {}
    async with session_scope() as s:
        found = (
            await s.execute(
                text(
                    "SELECT v.article_id, v.event_id, v.noul, v.story_noul FROM event_match_verdicts v "
                    "JOIN unnest(CAST(:a AS uuid[]), CAST(:e AS uuid[])) AS p(article_id, event_id) "
                    "ON p.article_id = v.article_id AND p.event_id = v.event_id WHERE v.mode = :mode"
                ),
                {"a": [str(r["article_id"]) for r in rows], "e": [str(r["event_id"]) for r in rows], "mode": MODE},
            )
        ).all()
    return {f"{a}|{e}": [n, st] for a, e, n, st in found}


async def _keep(article_id, event_id, same: float, follows: float | None, model: str) -> None:
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO event_match_verdicts (article_id, event_id, noul, story_noul, model, mode) "
                 "VALUES (:a, :e, :n, :s, :m, :mode) ON CONFLICT (article_id, event_id) DO NOTHING"),
            {"a": str(article_id), "e": str(event_id), "n": same, "s": follows, "m": model, "mode": MODE},
        )


async def judge_all(rows: list[dict], cache: dict) -> float:
    """Jev on every row without an answer; each answer is kept as it comes."""
    todo = [r for r in rows if _key(r) not in cache]
    sem, spent = asyncio.Semaphore(CONCURRENCY), [0.0]

    async def one(r: dict) -> None:
        block = article_block(source=r["source"], published_at=r["published_at"],
                              headline=r["headline"] or r["raw_title"], summary=r["article_summary"] or "")
        cand = Candidate(event_id=r["event_id"], distance=None)
        async with sem:
            try:
                verdicts, model, cost = await judge_story(
                    article_id=r["article_id"], block=block, candidates=[cand],
                    blocks={r["event_id"]: event_block(r["event_title"], r["event_summary"], r["first_seen_at"])},
                )
            except Exception as exc:  # noqa: BLE001 — unjudged this run, asked again on the next
                print(f"  unjudged {r['membership']}: {type(exc).__name__}")
                return
        spent[0] += cost
        cache[_key(r)] = [verdicts[0].same, verdicts[0].follows]
        await _keep(r["article_id"], r["event_id"], verdicts[0].same, verdicts[0].follows, model)

    for i in range(0, len(todo), 200):
        await asyncio.gather(*(one(r) for r in todo[i : i + 200]))
        print(f"  judged {min(i + 200, len(todo))}/{len(todo)}  ${spent[0]:.3f}", flush=True)
    return spent[0]


def report(rows: list[dict], cache: dict, detach_below: float) -> Path:
    judged = [r for r in rows if _key(r) in cache]
    by = Counter((r["match_type"], band(cache[_key(r)][0])) for r in judged)
    print(f"\n{len(rows)} fuzzy attaches in the window, {len(judged)} judged")
    print(f"{'tier':16}" + "".join(f"{name:>18}" for _, name in BANDS))
    for tier in FUZZY:
        if any(t == tier for t, _ in by):
            print(f"{tier:16}" + "".join(f"{by[(tier, name)]:>18}" for _, name in BANDS))
    moving = [r for r in judged if cache[_key(r)][0] < detach_below]
    follow = [r for r in moving if (cache[_key(r)][1] or 0) >= get_settings().prism_follow_up_min]
    print(f"\nat --detach-below {detach_below}: {len(moving)} would move, {len(follow)} of them as follow-ups of their record")
    OUT.mkdir(exist_ok=True)
    path = OUT / f"repair_attaches_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["membership", "tier", "same", "band", "follow_up", "decision", "record", "record_title",
                    "article", "source", "article_headline"])
        for r in judged:
            same, story = cache[_key(r)]
            w.writerow([r["membership"], r["match_type"], f"{same:.3f}", band(same),
                        "" if story is None else f"{story:.3f}", "move" if same < detach_below else "keep",
                        r["event_id"], r["event_title"], r["article_id"], r["source"], r["headline"] or r["raw_title"]])
    print(f"wrote {path}")
    return path


async def _prune(s, event_id: uuid.UUID, article_id: uuid.UUID) -> None:
    """What the record held only through the article that left: actors no
    remaining member names, and an image the article brought."""
    await s.execute(
        text(
            """
            DELETE FROM event_entities ee
            WHERE ee.event_id = :e
              AND ee.entity_id IN (SELECT entity_id FROM article_entities WHERE article_id = :a)
              AND NOT EXISTS (
                  SELECT 1 FROM event_memberships m JOIN article_entities ae ON ae.article_id = m.article_id
                  WHERE m.event_id = :e AND ae.entity_id = ee.entity_id
              )
            """
        ),
        {"e": str(event_id), "a": str(article_id)},
    )
    await s.execute(
        text(
            """
            UPDATE events e SET image_url = (
                SELECT ri.image_url FROM event_memberships m
                JOIN articles a ON a.id = m.article_id JOIN raw_items ri ON ri.id = a.raw_item_id
                WHERE m.event_id = e.id AND ri.image_url IS NOT NULL
                ORDER BY (m.match_type = 'new_event') DESC, m.created_at, m.id LIMIT 1)
            WHERE e.id = :e AND e.image_url = (
                SELECT ri.image_url FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id WHERE a.id = :a)
            """
        ),
        {"e": str(event_id), "a": str(article_id)},
    )


async def move(r: dict, same: float, story: float | None) -> tuple[uuid.UUID, bool] | None:
    """Detach one membership and re-home its article through the live path.
    Returns (the record it landed in, whether it founded it); None when it had
    already moved."""
    async with session_scope() as s:
        await s.execute(text("SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))"))
        gone = (
            await s.execute(
                text("DELETE FROM event_memberships WHERE id = :m AND event_id = :e AND match_type <> 'new_event' "
                     "RETURNING id"),
                {"m": str(r["membership"]), "e": str(r["event_id"])},
            )
        ).first()
        if gone is None:
            return None
        await _prune(s, r["event_id"], r["article_id"])
        # Its briefs and perspectives were written with the article that left.
        await s.execute(text("DELETE FROM perspectives WHERE event_id = :e"), {"e": str(r["event_id"])})
        article = await s.get(Article, r["article_id"])
        enrichment = (await s.execute(
            select(Enrichment).where(Enrichment.article_id == r["article_id"]).order_by(Enrichment.created_at.desc())
        )).scalars().first()
        landed, is_new = await consumer._attach(
            s, article, enrichment, enrichment.shared_fields or {}, r["article_id"], consumer.cve_ids_of(enrichment)
        )
        await s.flush()
        # When the article arrived, not now: a repaired record is not news, and
        # trending counts a membership's created_at as recent coverage.
        await s.execute(
            text("UPDATE event_memberships SET created_at = :t WHERE article_id = :a"),
            {"t": r["attached_at"], "a": str(r["article_id"])},
        )
        if is_new:
            await s.execute(
                text("UPDATE events SET first_seen_at = :t, last_updated_at = :t WHERE id = :e"),
                {"t": r["attached_at"], "e": str(landed)},
            )
        for event_id in {r["event_id"], landed}:
            await consumer._rebuild_projection(event_id, s, touch=False)
    for event_id in {r["event_id"], landed}:
        await consumer.mark_event_dirty(event_id)
    return landed, is_new


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--detach-below", type=float, default=0.5, help="move memberships Jev scores under this")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="with --apply: move only the first N (a canary)")
    a = ap.parse_args()

    rows = await load(a.days)
    cache = await answered(rows)
    spent = await judge_all(rows, cache)
    print(f"Jev: ${spent:.3f} this run")
    report(rows, cache, a.detach_below)
    if not a.apply:
        print("dry run — pass --apply to move")
        return 0
    if get_settings().prism_event_verify != "confirm":
        print("refusing: PRISM_EVENT_VERIFY must be 'confirm' here, or re-homed articles would be matched the old way")
        return 1
    todo = [r for r in rows if _key(r) in cache and cache[_key(r)][0] < a.detach_below]
    todo = todo[: a.limit] if a.limit is not None else todo
    outcome = Counter()
    for r in todo:
        same, story = cache[_key(r)]
        try:
            done = await move(r, same, story)
        except Exception as exc:  # noqa: BLE001 — one bad row must not stop the batch; it is retried next run
            print(f"  failed {r['membership']}: {type(exc).__name__}: {str(exc)[:120]}")
            outcome["failed"] += 1
            continue
        if done is None:
            outcome["already moved"] += 1
        elif done[0] == r["event_id"]:
            outcome["back in its record (the live path attached it again)"] += 1
        else:
            outcome["founded a record" if done[1] else "joined another record"] += 1
    print(f"{len(todo)} to move: " + ", ".join(f"{n} {k}" for k, n in outcome.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
