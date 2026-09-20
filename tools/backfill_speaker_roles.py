"""Fill `speaker_role` on claims written before the extractor carried it.

    uv run python -m tools.backfill_speaker_roles              # dry run: count
    uv run python -m tools.backfill_speaker_roles --days 7 --run

For each enrichment whose claims lack a role, one small structured call per
article: the speakers as named, the article text, and the instruction to
return each speaker's title or office EXACTLY as the article states it, or
null. Nothing is invented: a null stays null and the card prints no role.
A role survives only if the article's own words support it (faithful_role,
the same gate the live extractor passes). Writes back into
shared_fields.claims[*].speaker_role; idempotent — a claim with a role (or an
explicit null marker) is not asked again.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from pydantic import BaseModel, Field
from sqlalchemy import text

from common.config import get_settings
from common.db import get_session_factory
from common.llm import REASONING_OFF, structured_chat
from enrichment.claims import faithful_role, flat_ws


class RoleOut(BaseModel):
    speaker: str
    role: str | None = Field(default=None, description="Their title, office or standing as the article gives it, in English, spelled out and placed; null if it does not")
    role_native: str | None = Field(default=None, description="Only when the article is not in English: the article's own words for that title, copied exactly in its script and covering every part of role, place and body included; else null")


class RolesOut(BaseModel):
    roles: list[RoleOut]


SYSTEM = (
    "You are given a news article and the names of people or bodies quoted in it. For each name, return the "
    "title, office or standing the ARTICLE gives that speaker, in English, spelled out and placed: the office in "
    "full with the state, body or party the article names for it ('former Karnataka Chief Minister', not 'Former "
    "CM'; 'BJP MLA for Shivamogga', not 'MLA'; 'Vice President of the United States'; 'MEA spokesperson'; "
    "'senior police officer'). Never add a place or body the article does not name. If the article does not say "
    "who they are, return null. Never guess from general knowledge."
)

SELECT = """
SELECT e.article_id, a.clean_text, e.shared_fields
FROM enrichments e JOIN articles a ON a.id = e.article_id
WHERE jsonb_typeof(e.shared_fields->'claims') = 'array'
  AND jsonb_array_length(e.shared_fields->'claims') > 0
  AND (:rewrite OR EXISTS (SELECT 1 FROM jsonb_array_elements(e.shared_fields->'claims') c WHERE NOT (c ? 'speaker_role')))
  AND e.created_at > now() - make_interval(days => :days)
ORDER BY e.created_at DESC
"""


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="trial on the first N articles and print what survives")
    ap.add_argument("--rewrite", action="store_true", help="ask again even where a role is set (a prompt change)")
    args = ap.parse_args()
    settings = get_settings()
    model = settings.prism_model_correlate

    async with get_session_factory()() as session:
        rows = (await session.execute(text(SELECT), {"days": args.days, "rewrite": args.rewrite})).mappings().all()
    print(f"{len(rows)} articles with claims lacking speaker_role in the last {args.days} days")
    if not args.run:
        return 0
    if args.limit:
        rows = rows[: args.limit]

    sem = asyncio.Semaphore(args.concurrency)
    done = filled = 0

    async def one(row):
        nonlocal done, filled
        claims = row["shared_fields"]["claims"]
        speakers = sorted({c["speaker"] for c in claims if isinstance(c, dict) and c.get("speaker")})
        async with sem:
            try:
                out = await structured_chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": f"Speakers: {json.dumps(speakers, ensure_ascii=False)}\n\nArticle:\n{(row['clean_text'] or '')[:6000]}"},
                    ],
                    output_model=RolesOut,
                    trace_name="backfill-speaker-roles",
                    max_tokens=600,
                    reasoning=REASONING_OFF,
                )
            except Exception as exc:  # noqa: BLE001 — one article's roles are not worth stopping the run
                print(f"  ! {row['article_id']}: {str(exc)[:120]}", file=sys.stderr)
                return
        flat = flat_ws(row["clean_text"] or "")
        by = {r.speaker.strip().casefold(): faithful_role(r.role, flat, r.role_native) for r in out.roles}
        if args.limit:
            for r in out.roles:
                print(f"  {r.speaker!r}: {r.role!r} {('[' + r.role_native + ']') if r.role_native else ''} -> {by[r.speaker.strip().casefold()]!r}")
        for c in claims:
            if isinstance(c, dict) and (args.rewrite or "speaker_role" not in c):
                c["speaker_role"] = by.get((c.get("speaker") or "").strip().casefold())
                filled += bool(c["speaker_role"])
        shared = dict(row["shared_fields"])
        shared["claims"] = claims
        async with get_session_factory()() as session:
            await session.execute(
                text("UPDATE enrichments SET shared_fields = CAST(:sf AS jsonb) WHERE article_id = :aid"),
                {"sf": json.dumps(shared, ensure_ascii=False), "aid": str(row["article_id"])},
            )
            await session.commit()
        done += 1
        if done % 100 == 0:
            print(f"  {done} articles · {filled} roles", flush=True)

    await asyncio.gather(*[one(r) for r in rows])
    print(f"done: {done} articles updated · {filled} roles filled on {model}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
