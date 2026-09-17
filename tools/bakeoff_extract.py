"""Which extraction model is the cheapest that loses nothing? Measured, not guessed.

Extraction is ~45% of LLM spend, on google/gemini-3.1-flash-lite ($0.25 / $1.50
per M tokens). qwen/qwen3.7-flash is 8x cheaper on input and 11x on output;
glm-5.3-flash and gpt-5-nano sit between. qwen3.5-flash went to 100% schema
failure on 2026-09-04 and was dropped, so a cheaper model has to earn the stage
on the same articles, against the same incumbent, on the things the product
actually reads off an extraction:

  schema     structured_chat still raises after its retries -> the article is lost
  headline   the Prism headline rule (<= 12 words, English, no quotes, no stop)
  brief      a reader_brief that is one (>= 2 sentences, English)
  entities   agreement with the incumbent's entities on the same article (Jaccard
             on canonical slugs) and the count — a model that names half the cast
             breaks clustering, which is IDF-weighted over exactly these names
  claims     verbatim survival: claims proposed, claims verify_claims keeps
  cost/time  tokens used at the model's price; wall seconds per article

  uv run python -m tools.bakeoff_extract --articles 40 \
      --models google/gemini-3.1-flash-lite qwen/qwen3.7-flash z-ai/glm-5.3-flash openai/gpt-5-nano

Reads production (read-only) for the sample and the incumbent's stored
extraction; spends ~$0.30 for 40 articles x 4 models. Prints a table and writes
.cache/bakeoff_extract.json so the numbers can be quoted later.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import asyncpg

from common.llm import structured_chat
from common.observability import fetch_prompt
from common.text import entity_slug
from enrichment.claims import verify_claims
from enrichment.schemas import ArticleExtraction
from tools.snapshot_l2 import _prod_url

OUT = Path(".cache/bakeoff_extract.json")
SAMPLE_SEED = 0.19


def headline_ok(h: str | None) -> bool:
    h = (h or "").strip()
    return 0 < len(h.split()) <= 12 and not re.search(r'["“”]', h) and not h.endswith(".") and not re.search(r"[ऀ-෿]", h)


def brief_ok(b: str | None) -> bool:
    b = (b or "").strip()
    return len(b) >= 80 and b.count(".") >= 2 and not re.search(r"[ऀ-෿]", b)


async def sample(n: int) -> list[dict]:
    c = await asyncpg.connect(_prod_url(), timeout=180)
    try:
        await c.execute("SET default_transaction_read_only = on")
        await c.execute("SELECT setseed($1)", SAMPLE_SEED)
        return [dict(r) for r in await c.fetch(
            """
            SELECT a.id::text AS id, a.clean_text, ri.title, ri.published_at, ri.language,
                   s.slug AS src, en.shared_fields AS incumbent
            FROM articles a
            JOIN raw_items ri ON ri.id = a.raw_item_id
            JOIN sources s ON s.id = ri.source_id
            JOIN enrichments en ON en.article_id = a.id
            WHERE s.source_type <> 'cve_feed' AND a.word_count >= 120
              AND a.created_at > now() - interval '3 days'
            ORDER BY random() LIMIT $1
            """, n)]
    finally:
        await c.close()


def slugs(entities) -> set[str]:
    return {entity_slug(e["name"]) for e in (entities or []) if isinstance(e, dict) and e.get("name")}


async def run_model(model: str, rows: list[dict], prompt) -> dict:
    m = Counter()
    secs = 0.0
    jacc = []
    for r in rows:
        inc = r["incumbent"] if isinstance(r["incumbent"], dict) else json.loads(r["incumbent"] or "{}")
        t0 = time.monotonic()
        try:
            ext = await structured_chat(
                model=model,
                messages=prompt.compile(title=r["title"], source=r["src"], published_at=str(r["published_at"] or "unknown"), text=(r["clean_text"] or "")[:12000]),
                output_model=ArticleExtraction, trace_name="bakeoff-extract", prune_fields={"impacts"}, max_tokens=3000,
            )
        except Exception as e:  # noqa: BLE001 — the failure IS the measurement
            m["schema_fail"] += 1
            m["secs"] += time.monotonic() - t0
            print(f"    ! {model} {r['id'][:8]}: {str(e)[:80]}", file=sys.stderr)
            continue
        secs += time.monotonic() - t0
        sh = ext.shared
        m["ok"] += 1
        m["headline_ok"] += headline_ok(sh.headline)
        m["brief_ok"] += brief_ok(sh.reader_brief)
        mine, theirs = slugs(sh.model_dump().get("entities")), slugs(inc.get("entities"))
        m["entities"] += len(mine)
        m["entities_inc"] += len(theirs)
        if mine or theirs:
            jacc.append(len(mine & theirs) / len(mine | theirs))
        kept, _ = verify_claims(sh.claims, r["clean_text"] or "")
        m["claims"] += len(sh.claims)
        m["claims_kept"] += len(kept)
        m["claims_inc"] += len(inc.get("claims") or [])
    n = max(1, m["ok"])
    return {
        "model": model, "articles": len(rows), "schema_fail": m["schema_fail"],
        "headline_ok": round(m["headline_ok"] / n, 2), "brief_ok": round(m["brief_ok"] / n, 2),
        "entities_per_article": round(m["entities"] / n, 1), "incumbent_entities_per_article": round(m["entities_inc"] / n, 1),
        "entity_jaccard_vs_incumbent": round(sum(jacc) / max(1, len(jacc)), 2),
        "claims_per_article": round(m["claims"] / n, 2), "claims_kept_per_article": round(m["claims_kept"] / n, 2),
        "incumbent_claims_per_article": round(m["claims_inc"] / n, 2),
        "secs_per_article": round(secs / n, 1),
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--articles", type=int, default=40)
    ap.add_argument("--models", nargs="+", required=True)
    a = ap.parse_args()
    rows = await sample(a.articles)
    print(f"  {len(rows)} articles (seed {SAMPLE_SEED}); languages {dict(Counter(r['language'] for r in rows))}")
    prompt = fetch_prompt("extract-shared")
    results = []
    for model in a.models:
        print(f"  running {model} …", flush=True)
        results.append(await run_model(model, rows, prompt))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1))
    keys = ["schema_fail", "headline_ok", "brief_ok", "entities_per_article", "entity_jaccard_vs_incumbent", "claims_per_article", "claims_kept_per_article", "secs_per_article"]
    print(f"\n  {'model':34} " + " ".join(f"{k[:14]:>14}" for k in keys))
    for r in results:
        print(f"  {r['model']:34} " + " ".join(f"{str(r[k]):>14}" for k in keys))
    print(f"\n  incumbent stored: {results[0]['incumbent_entities_per_article']} entities, {results[0]['incumbent_claims_per_article']} claims per article")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
