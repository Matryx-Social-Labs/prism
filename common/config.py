import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    database_url: str = Field("postgresql+asyncpg://prism:prism@localhost:5432/prism", repr=False)
    redis_url: str = Field("redis://localhost:6379/0", repr=False)

    # LLM provider. Both are OpenAI-compatible, so switching is base_url + key +
    # model IDs. OpenRouter is primary (per-token, no weekly cap, one key for many
    # models, structured output, provider fallback). Set LLM_PROVIDER=ollama +
    # override the model IDs below to fall back to Ollama Cloud.
    llm_provider: str = "openrouter"  # openrouter | ollama
    openrouter_api_key: str = Field("", repr=False)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Ollama Cloud (fallback, OpenAI-compatible)
    ollama_api_key: str = Field("", repr=False)
    ollama_base_url: str = "https://ollama.com/v1"

    # Per-stage models — OpenRouter IDs, every one env-overridable (PRISM_MODEL_*).
    # Confirm current IDs on openrouter.ai/models. Cheap-reliable flash-lite for the
    # high-volume structured stages (free models proved unreliable at JSON output —
    # tencent/hy3:free returned empty content), cheap-paid for the content the
    # product sells. All near-free at India-only volume.
    # 2026-09-18: a burst of empty OpenRouter envelopes (`choices: null`) on
    # gemini-3.1-flash-lite was read as the model failing and the gate/classify/
    # extract stages were moved to gemini-3.5-flash ($1.50/$9.00 per M, 6x the
    # lite). Twenty minutes later gemini-3.5-flash returned the same null
    # envelopes on 70% of gate calls, and 3.1-flash-lite answered 36/36 probes
    # and 15/15 extractions. The bursts are upstream (rate/5xx), not the model;
    # `llm_empty_response` now logs the envelope's error object so the next one
    # is diagnosed, not switched around.
    prism_model_gate: str = "google/gemini-3.1-flash-lite"  # binary relevance — high volume
    prism_model_classify: str = "google/gemini-3.1-flash-lite"
    # Extraction emits a nested JSON (entities/stance/cyber/finance). Entities drive
    # clustering, so the model MUST reliably fill them. Benchmarked on 25 real India
    # articles (recall vs qwen3.7-plus): gemini-3.1-flash-lite left 40% empty (recall
    # 0.39), gemini-3.5-flash 96% empty (0.08), deepseek-v4-flash 25% empty + truncation.
    # qwen3.5-flash is the cheapest that stays reliable — 0 empty, ~0.77 recall — at
    # ~4.7x lower cost than qwen3.7-plus ($0.07/$0.26 vs $0.32/$1.28 per M). Soft-news
    # (extract_light) uses it too: gemini-flash-lite was silently emitting no entities.
    # MEASURED 2026-09-04 on 10 production articles, same prompt, claims enabled:
    #
    #   qwen/qwen3.5-flash-02-23      failed 10/10   0 claims    0 entities
    #   google/gemini-3.1-flash-lite  failed  0/10  16 claims   77 entities
    #   google/gemini-3.5-flash       failed  0/10  15 claims   73 entities
    #
    # qwen answers with a BARE NUMBER instead of the object — `-8.039215789473683`,
    # a stray sentiment value with no object in the response at all. It has worked
    # historically (1,095 enrichments carry its name), so this is degradation
    # rather than a mistake in choosing it, and the stream's redelivery hid the
    # cost: production still only loses 3.6% of relevant items permanently, but
    # roughly half of every extraction attempt was being paid for and thrown away.
    #
    # THIS REVERSES A RECORDED FINDING and the reversal is the point: the earlier
    # note said gemini "empties entities", which is why qwen was chosen. On this
    # sample gemini returns 77 entities and qwen returns none, because qwen
    # returns nothing at all. Re-measure before trusting either direction again.
    prism_model_extract: str = "google/gemini-3.1-flash-lite"
    prism_model_extract_light: str = "google/gemini-3.1-flash-lite"
    # OpenRouter endpoints extraction is pinned to, in order (comma-separated;
    # empty = OpenRouter's own routing). Measured 2026-09-27 on production-shape
    # traffic, 30 articles at concurrency 6: google-ai-studio/flex cached the
    # ~8k-token prompt prefix 30/30 at $0.00074 a call, median 2.1 s — against
    # $0.00288 and 1 cache hit in 55 unpinned. Flex is Google's half-price tier;
    # a failure there falls back to standard endpoints (allow_fallbacks), never
    # to a lost article. Vertex flex was 18 s median: not that one.
    prism_extract_providers: str = "google-ai-studio/flex"
    # analysis / briefs / thread-link / digest. Bake-off 2026-09-17 on 30 live
    # multi-source events, judged blind (tools/bakeoff_brief): glm-5.3-flash
    # grounded 0.92 vs qwen3.7-plus 0.91, complete 0.99 vs 0.98, neutral 0.98
    # vs 0.96, zero failures vs three, 19.8s vs 40.1s a brief, a quarter of
    # the price. Ask stays on prism_model_agent.
    prism_model_correlate: str = "z-ai/glm-5.3-flash"
    # OpenRouter endpoints the lens brief is pinned to (same format as
    # prism_extract_providers). Measured 2026-09-27, glm-5.3-flash at minimal
    # reasoning on 10 live Markets briefs: Together 4.3-5.4 s; OpenRouter's own
    # routing sent most to Decart, 11-37 s, and one came back one word long.
    prism_brief_providers: str = "together"
    prism_model_agent: str = "qwen/qwen3.7-plus"  # Ask — user-facing, Plus
    prism_model_agent_free: str = "z-ai/glm-5.3-flash"  # Ask for free and anonymous readers: same prompt, ~1/6 the cost
    prism_model_judge: str = "google/gemini-3.5-flash"  # evals — low volume, wants strong reasoning
    # Where a request goes when the primary model refuses it on content policy
    # (Gemini PROHIBITED_CONTENT on sexual-violence reporting, 2026-09-18: 13 of
    # 44 gate calls in one window). glm-5.3-flash answers our schemas and does
    # not refuse news. Empty string disables the fallback (the call then fails
    # permanently instead of being redelivered).
    prism_model_fallback: str = "z-ai/glm-5.3-flash"
    prism_model_guard: str = "google/gemini-3.1-flash-lite"  # Ask moderation — cheap + fast

    # Embeddings (fastembed, in-process). Multilingual so cross-language coverage
    # (Hindi/Tamil/Telugu now, Spanish/etc. as we add countries) clusters into the
    # same story. Benchmarked on real CJP coverage: same-story sim Hindi 0.87 /
    # Telugu 0.77 / Tamil 0.56 vs unrelated -0.01 (bge-small-en couldn't separate
    # Hindi at all). Changing dim requires a migration of the vector(...) columns.
    # mE5, chosen on a full cascade replay against gold_pairs rather than on the
    # isolated embedding score — measured 2026-09-05, both folds:
    #
    #                       all 398        batch1 (fitted)  batch2 (HELD OUT)
    #     mpnet             Cdet 0.5930    Cdet 0.5268      Cdet 0.6555
    #     mE5 + passage:    Cdet 0.5466    Cdet 0.5179      Cdet 0.5837
    #     mE5 + query:      Cdet 0.5319    Cdet 0.4598      Cdet 0.5949
    #
    # mE5 beats mpnet on F1 and Cdet in BOTH folds, which is what step 4 failed to
    # do. 768-dim either way, so no vector migration.
    prism_embed_model: str = "intfloat/multilingual-e5-base"
    prism_embed_dim: int = 768

    # Ask-agent guardrail — a cheap moderation pre-check rejects explicit/harmful
    # /off-topic/prompt-injection questions BEFORE the expensive RAG agent runs,
    # so we neither generate disallowed content nor pay for junk prompts.
    prism_ask_guard_enabled: bool = True

    # Live ingestion master switch. Set PRISM_INGESTION_ENABLED=false to stop
    # collectors (and the stalled-item requeue) so no new news is fetched and the
    # downstream LLM pipeline goes idle — the cost brake while the prototype is
    # still being built. On-demand briefs/Ask/digest still work.
    # A HARD CEILING ON THE CORPUS, checked before every collector run.
    #
    # "Bounded article cap" and "watched" are not cost controls, and calling them
    # that is how a budget goes. This is a real stop condition: once the corpus
    # holds this many enriched articles, collection stops by itself whether or
    # not anyone is looking. 0 disables the ceiling.
    #
    # It bounds the CORPUS, not the spend directly — spend is LLM calls, retries
    # and briefs, which no article count predicts exactly. But it is the one
    # quantity that cannot drift, and it fails safe: the check runs before
    # collection, so exceeding it costs nothing further.
    # The cross-language headline tier (correlation/clustering._match_by_headline):
    # IDF word-cosine between an article's EXTRACTED ENGLISH headline and the
    # in-window events' Prism headlines. 0 = off. The threshold is a labelled
    # decision — tools/gold_crosslingual, batch MGDmtLPZOdjy — not an eyeballed one.
    prism_headline_tier_threshold: float = 0.0
    # The verified tier (correlation/verify.py): gist-embedding candidates, one
    # Jev call, attach at >= the floor. off | shadow (ask, record, never attach) |
    # live. 0.85 held precision 1.00 on the hard same-language labels and 20/20
    # in a week of production pairs (2026-09-25); lower it only on labels.
    #
    # confirm (2026-09-29): live, and the title, embedding and entity tiers only
    # PROPOSE — Jev decides every attach they would have made (measured against
    # its own test: entity_overlap 44% the same happening, embedding 76%, title
    # 92%, the verified tier 100%, on 781 production attaches). An article that
    # is a later development instead founds its own record, linked as a follow-up
    # at >= prism_follow_up_min. Back to `live` restores the old tiers exactly.
    prism_event_verify: str = "off"
    prism_event_verify_min: float = 0.85
    prism_follow_up_min: float = 0.85
    # confirm: the floor for a record a fuzzy tier PROPOSED (the gist-only
    # candidates keep prism_event_verify_min). A proposal has its tier's evidence
    # behind it. Read by hand from the 30-day repair dry run (2026-10-01), the
    # proposals Jev did not also call a later development were the same happening
    # 21/30 at 0.50-0.60, 24/30 at 0.60-0.70, 25/30 at 0.70-0.85. At or above
    # prism_follow_up_min on the follow-up question, an under-0.85 proposal founds
    # its own record and is linked back instead. The default equals the gist
    # floor: no change until set — set it from the founders' attach labels.
    prism_proposal_verify_min: float = 0.85
    # confirm: the best refused candidate at or above the escalate floor gets a
    # second Jev call on both reports' opening text; it attaches ("escalated") at
    # >= prism_event_escalate_min unless that call also names it a later development
    # (>= prism_follow_up_min). Measured 2026-10-01 on 160 blind labels: 52 taken,
    # precision 0.98, half the band's duplicate records (tests/test_band_escalation.py).
    # off | shadow (ask, record, never attach) | live.
    prism_event_escalate: str = "off"
    prism_event_escalate_floor: float = 0.65
    prism_event_escalate_min: float = 0.80
    # Stories that persist (correlation/stories.py): every new record joins one
    # story at birth on Jev's word, or founds one. off | shadow (stories written
    # with status 'shadow', never served) | live. prism_story_min is the attach
    # floor (prototype 2026-10-01: precision 0.92-0.97 at 0.70).
    prism_stories: str = "off"
    prism_story_min: float = 0.70
    # One name, one entity (correlation/variants.py): an article joining a record
    # whose cast already holds another spelling of one of its names (same type,
    # same consonant skeleton) asks Jev whether both name one entity. off |
    # shadow (ask and record, never fold) | live (fold at >= the floor into the
    # spelling with the most mentions). tools/entity_variants.py does the backlog.
    # The floor, read by hand from the production dry run (2026-10-01, 1,628
    # evidenced pairs): Jev puts one-name pairs at 0.6-0.95, not near 1; a random
    # 50 at >= 0.7 were 50/50 one entity, and the three doubtful pairs in a random
    # 120 (Sanjay Sah/Shah, Sourav/Saurav Das, Ashok Bharti/Bharat) sat at 0.46-0.63.
    prism_entity_variants: str = "off"
    prism_entity_variant_min: float = 0.7
    prism_ingest_max_articles: int = 0
    # Stop COLLECTING when the recorded OpenRouter balance is under this many
    # dollars, so a stalled enrichment never grows a backlog that becomes a bill
    # the moment credits return. 0 disables the floor. common/budget.py.
    prism_llm_budget_floor_usd: float = 5.0
    prism_ingestion_enabled: bool = True
    # Podcast clips (podcasts/): poll the shows, transcribe, match to events.
    # Off by default until the gold_clips gate reads ≥ 0.9; the transcription
    # line is ≈ $0.06/day on OpenRouter→Groq at the five shows' cadence.
    prism_podcasts_enabled: bool = False
    # Window→event cosine floor (mE5, symmetric query: prefix) for the CANDIDATE
    # stage; the judge (podcasts/judge.py) makes the call. Loose on purpose.
    prism_clip_min_cos: float = 0.84
    # X posts (xposts/): poll the allowlisted official accounts, attach posts to
    # events. Off by default until the gold_xposts gate reads ≥ 0.9. Read on the
    # worker (poll + match) AND the API (serve): worker on, API off = shadow.
    # X bills $0.005 a post read on pay-per-use (2026-09); ~25 official
    # accounts ≈ $2/day. Prepaid credits with auto-recharge off are the hard cap.
    prism_x_enabled: bool = False
    # Which quotes on a speaker card are one statement printed in two languages,
    # and which are an outlet's translation (enrichment/renderings.py). Read on the
    # worker (judge the cards, write claim_verdicts) AND the API (apply them):
    # worker on, API off = shadow, the X pattern. Off on the API until
    # tools/gold_renderings reads >= 0.95 on labels. ~$0.0001 a card on Jev.
    prism_quote_verdicts: bool = False
    # Post→event cosine floor for the CANDIDATE stage. The podcast floor was
    # tuned on 100–150-word windows; a post is 30–60 words — re-measure with
    # tools/gold_xposts before trusting it.
    prism_x_min_cos: float = 0.84

    # Grounded storyline veto master switch. Set PRISM_VETO_ENABLED=false to stop
    # the hourly LLM overlay pass.
    #
    # Turned OFF in production 2026-07-30 because the pass pays for itself roughly
    # never. Two independent losses: persist_veto_overlay does its LLM work, then
    # publishes only if its base run is STILL current (correlation/partition.py:683)
    # — with a 15-minute base cadence and a ~13-minute veto it loses that race about
    # half the time. And when it DOES win, persist_base_run unconditionally
    # republishes with veto_state='pending' on the next tick, so the refinement is
    # discarded within 15 minutes. Measured: of 10 retained runs exactly one carried
    # an applied veto, and it survived 4m33s.
    #
    # Re-enable once the base pass carries a previous run's veto decisions forward
    # instead of dropping them; until then this is an hourly LLM bill for a
    # refinement almost nobody is served.
    prism_veto_enabled: bool = True

    # Typed decisions on TypeSafe Jev through OpenRouter's Decisions API
    # (common/decisions.py). `off`: the LLM gate and classifier as before.
    # `shadow`: Jev answers beside them and the pair is logged (`decision_shadow`),
    # behaviour unchanged. `live`: Jev replaces both calls; an item whose sector
    # or gate answer lands under prism_decisions_min_confidence falls back to the
    # LLM pair for that item. Pinned to a version: `jev-latest` retunes without
    # notice. Smoke-tested 2026-09-22 on en/kn/hi: 320-600 ms, ~$0.00005 an item
    # for gate + classifier in one call, against ~$0.0008 for the two LLM calls.
    prism_model_decide: str = "typesafe/jev-1.13"
    prism_decisions_mode: str = "off"  # off | shadow | live
    prism_decisions_min_confidence: float = 0.0  # set from the shadow run's agreement table
    # The clip and X-post judges (common/pair_judge.py): `llm` is the judge model
    # writing one word; `decide` is one Jev choice over the same story and text.
    # Verdicts are cached with the model that gave them, so a flip re-judges
    # nothing already settled.
    prism_judge_backend: str = "llm"  # llm | decide

    # Langfuse (self-hosted). The SDK also reads LANGFUSE_* env vars directly;
    # these mirror them so app code can check whether tracing is configured.
    #
    # OFF BY DEFAULT, and deliberately so: the self-hosted stack (web + worker +
    # Postgres + Redis + ClickHouse + MinIO) cost $70 in its first two weeks,
    # more than the LLM spend it was there to observe. It is now configured to
    # scale to zero after 10 idle minutes, which means ANY background trace wakes
    # the whole stack and starts billing again. A pipeline that traces by default
    # would keep it permanently awake, so tracing is opt-in per environment.
    #
    # Setting the keys is NOT enough to enable it — that was the old rule, and it
    # made "cost" a side effect of "credentials are present", which is not a
    # decision anyone makes on purpose. Set PRISM_LANGFUSE_ENABLED=true when you
    # actually want to look at traces.
    prism_langfuse_enabled: bool = False
    langfuse_public_key: str = Field("", repr=False)
    langfuse_secret_key: str = Field("", repr=False)
    langfuse_base_url: str = ""
    # Tags every trace with an environment so local/dev traces are filterable and
    # never mixed with prod in the shared Langfuse. Local sets "development";
    # prod leaves it unset (shows as "default"), so prod config is untouched.
    langfuse_tracing_environment: str = ""
    # The SDK's 5s default OTLP-export timeout is too short for a self-hosted
    # Langfuse (web -> Redis -> worker -> ClickHouse): batches time out and get
    # dropped ("Failed to export span batch"). Give it room + smaller batches.
    langfuse_timeout: int = 30  # seconds — OTLP span-export timeout (LANGFUSE_TIMEOUT)
    langfuse_flush_at: int = 128  # max spans per export batch (LANGFUSE_FLUSH_AT)

    # API
    cors_origins: str = "http://localhost:3000"
    prism_admin_token: str = Field("change-me", repr=False)
    # Who may open /admin (founder decision D1, 2026-09-23): the signed-in
    # accounts whose email is on this comma-separated list. Empty means nobody —
    # there is no screen that grants it, so the only way in is this variable.
    prism_admin_emails: str = ""
    # How many proxies sit in front of the API. `X-Forwarded-For` is a list the
    # CLIENT can start: only the hops a trusted proxy appended are evidence, so
    # the client address is read this many entries from the RIGHT. Railway puts
    # exactly one proxy in front of the container; a second CDN in front of that
    # makes it 2. Zero means "not behind a proxy": trust the socket only.
    prism_trusted_proxy_hops: int = 1

    # Auth (magic-link, bearer). Web URL is where the verify link points.
    prism_web_url: str = "http://localhost:3000"
    prism_email_provider: str = "console"  # console (dev) | resend
    resend_api_key: str = Field("", repr=False)
    prism_email_from: str = "Prism <onboarding@resend.dev>"  # set to a verified domain sender
    # The week's record by email (common/weekly_digest.py), Sunday 08:00 IST from
    # the worker, only to accounts that turned it on. Off until the founder says;
    # at most this many a run (Resend's free tier is 100 a day), the rest next run.
    prism_digest_enabled: bool = False
    prism_digest_max_per_run: int = 90
    # The API's public address, for the digest's one-click unsubscribe link and
    # its List-Unsubscribe header (the worker writes them; the API answers them).
    prism_api_url: str = "http://localhost:8000"
    prism_magic_token_ttl_min: int = 15  # magic-link lifetime
    prism_session_ttl_days: int = 30  # bearer session lifetime
    # The session travels in an HttpOnly cookie, never in storage a script can
    # read (audit C5). Empty domain = host-only on the API's own host, which is
    # right in production too: pages on www call api.readprism.news with
    # credentials, and the two are the same site, so SameSite=Lax sends it.
    # Localhost shares it across ports. Secure off only for plain-http local dev.
    prism_session_cookie: str = "prism_session"
    prism_cookie_domain: str = ""
    prism_cookie_secure: bool = True
    prism_magic_request_cooldown_s: int = 30  # per-email rate limit on link requests
    # Google sign-in (Google Identity Services, ID-token mode). The client id is
    # public; the API only uses it to check a token's audience. Empty = off.
    google_client_id: str = ""
    # Billing (common/billing.py). The paid launch date starts the 90-day offer
    # clock; empty = not launched, offer prices shown. Razorpay keys are read
    # only by the webhook route and the (future) checkout; empty = 503 there.
    prism_paid_launch_date: str = ""
    razorpay_key_id: str = Field("", repr=False)
    razorpay_key_secret: str = Field("", repr=False)
    razorpay_webhook_secret: str = Field("", repr=False)
    # Test keys (rzp_test_…) take no money, so checkout stays shut on them
    # (founder, 2026-09-29: hide checkout until the live keys). True lets a
    # local or staging deployment drive Razorpay's test sheet end to end.
    prism_allow_test_checkout: bool = False

    # Sources
    x_bearer_token: str = Field("", repr=False)  # X API app-only bearer (console.x.com), pay-per-use

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def langfuse_enabled(self) -> bool:
        """Tracing costs money, so it takes an explicit switch AND credentials."""
        return bool(
            self.prism_langfuse_enabled and self.langfuse_public_key and self.langfuse_secret_key
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _export_langfuse_env(settings)
    return settings


def _export_langfuse_env(settings: Settings) -> None:
    """Bridge .env values to process env for the Langfuse SDK.

    pydantic-settings reads .env itself but doesn't export; the Langfuse
    client (and its openai wrapper) reads os.environ directly. Without this,
    keys in .env leave the SDK silently disabled. Existing env vars win.
    """
    if not settings.langfuse_enabled:
        # Off means off for the SDK too. langfuse.openai (common/llm.py) builds
        # its own client from the raw LANGFUSE_* keys, outside observe()'s gate,
        # so with the flag off and the keys still set every model call exported
        # spans — to a Langfuse that no longer exists: "Failed to export span
        # batch code: 404" every few seconds in the worker (2026-09-28).
        # Assigned, not setdefault: the flag is the one switch.
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
        return
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_base_url:
        # v3 SDK reads LANGFUSE_HOST; some tooling reads LANGFUSE_BASE_URL — set both.
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_base_url)
        os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
    if settings.langfuse_tracing_environment:
        os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", settings.langfuse_tracing_environment)
    # Longer OTLP-export timeout + smaller batches so traces reach a self-hosted
    # Langfuse instead of timing out and being dropped.
    os.environ.setdefault("LANGFUSE_TIMEOUT", str(settings.langfuse_timeout))
    os.environ.setdefault("LANGFUSE_FLUSH_AT", str(settings.langfuse_flush_at))
