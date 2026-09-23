"""The numbers behind /admin (admin dashboard, phase C): visits, sign-ups,
engagement, money, demand and supply, for a period and the one before it.

RULES THE DASHBOARD PRINTS UNDER EVERY FIGURE:
- Every number is counted from a table, and says which (`source`). Nothing is
  estimated, extrapolated or invented (CLAUDE.md: no invented numbers).
- Days are IST days, the product's one clock.
- A series that began at deploy says so: `counting_since` is the first day its
  table holds, and days before it are None — not zero. A visit that was never
  recorded is not a day nobody came.
- Small n is shown as counts; the web decides when a share may be a percentage.

What cannot be computed is left out rather than approximated: monthly unique
visitors (the visitor hash changes daily, by design — common/usage.py), and
revenue history (subscriptions keep no status history, so MRR is "now" only).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common import billing, budget, usage

DAY_IST = "(({col}) AT TIME ZONE 'Asia/Kolkata')::date"
# An outlet's median is printed only over this many shared events: a median of
# one event is an anecdote.
LAG_MIN_EVENTS = 5
LAG_MAX = "interval '7 days'"  # a "report" a week after the first is a new story
# raw_items.relevance: pending | relevant | rejected | duplicate (common/models.py)
RELEVANT = "relevance = 'relevant'"


def window(days: int, today: date | None = None) -> dict[str, date]:
    end = today or usage.today()
    start = end - timedelta(days=days - 1)
    return {"start": start, "end": end, "prev_start": start - timedelta(days=days), "prev_end": start - timedelta(days=1)}


def _days(w: dict[str, date]) -> list[date]:
    return [w["start"] + timedelta(days=i) for i in range((w["end"] - w["start"]).days + 1)]


def _row(key: str, label: str, current: Any, previous: Any, source: str, *, series: list | None = None,
         unit: str = "count", note: str | None = None) -> dict[str, Any]:
    return {"key": key, "label": label, "current": current, "previous": previous, "series": series,
            "unit": unit, "source": source, "note": note}


async def _usage(db: AsyncSession, w: dict[str, date], event: str, since: date | None) -> dict[str, Any]:
    """One usage_daily event: totals now and before, the daily series, and the
    split by its word."""
    rows = (await db.execute(text(
        "SELECT day, dim, count FROM usage_daily WHERE event = :e AND day BETWEEN :a AND :b"),
        {"e": event, "a": w["prev_start"], "b": w["end"]})).mappings().all()
    by_day: dict[date, int] = {}
    now: dict[str, int] = {}
    before: dict[str, int] = {}
    for r in rows:
        if r["day"] >= w["start"]:
            by_day[r["day"]] = by_day.get(r["day"], 0) + r["count"]
            now[r["dim"]] = now.get(r["dim"], 0) + r["count"]
        else:
            before[r["dim"]] = before.get(r["dim"], 0) + r["count"]
    series = [None if since is None or d < since else by_day.get(d, 0) for d in _days(w)]
    prev = sum(before.values()) if since is not None and since <= w["prev_end"] else None
    return {"current": sum(now.values()) if since is not None else None, "previous": prev, "series": series,
            "split": sorted(({"label": k or "—", "current": v, "previous": before.get(k, 0) if prev is not None else None}
                             for k, v in now.items()), key=lambda x: -x["current"])}


def _since_label(since: date | None) -> str:
    return f"counting since {since:%-d %b}" if since else "nothing counted yet"


async def visits(db: AsyncSession, w: dict[str, date], since: date | None) -> dict[str, Any]:
    src = f"usage_daily · {_since_label(since)}"
    vis = await _usage(db, w, "visitors", since)
    views = await _usage(db, w, "view", since)
    arr = await _usage(db, w, "arrival", since)
    shares = await _usage(db, w, "share", since)
    return {
        "key": "visits", "title": "Visits",
        "rows": [
            _row("visitor_days", "Visitor-days", vis["current"], vis["previous"], src, series=vis["series"],
                 note="Distinct visitors each day, added up: one person on three days counts three. "
                      "Unique visitors over a month cannot be counted without tracking people, which we do not."),
            _row("views", "Page views", views["current"], views["previous"], src, series=views["series"]),
            _row("arrivals", "Arrivals", arr["current"], arr["previous"], src, series=arr["series"],
                 note="The first page of each visit."),
            _row("shares", "Shares", shares["current"], shares["previous"], src, series=shares["series"]),
        ],
        "breakdowns": [
            {"key": "sources", "title": "Where visits came from", "rows": arr["split"], "source": src},
            {"key": "pages", "title": "Views by kind of page", "rows": views["split"], "source": src},
            {"key": "shared", "title": "What was shared", "rows": shares["split"], "source": src},
        ],
    }


async def _daily_count(db: AsyncSession, w: dict[str, date], table: str, col: str, where: str = "TRUE") -> list[int]:
    day = DAY_IST.format(col=col)
    rows = dict((await db.execute(text(
        f"SELECT {day} AS d, count(*) FROM {table} WHERE {where} AND {day} BETWEEN :a AND :b GROUP BY 1"),
        {"a": w["start"], "b": w["end"]})).all())
    return [rows.get(d, 0) for d in _days(w)]


async def _count(db: AsyncSession, table: str, col: str, a: date, b: date, where: str = "TRUE") -> int:
    return (await db.execute(text(
        f"SELECT count(*) FROM {table} WHERE {where} AND {DAY_IST.format(col=col)} BETWEEN :a AND :b"),
        {"a": a, "b": b})).scalar() or 0


async def _split(db: AsyncSession, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [{"label": r[0] or "not given", "current": r[1], "previous": None}
            for r in (await db.execute(text(sql), params or {})).all()]


async def signups(db: AsyncSession, w: dict[str, date]) -> dict[str, Any]:
    src = "users · every account since launch"
    total = (await db.execute(text("SELECT count(*) FROM users"))).scalar() or 0
    before_end = (await db.execute(text(f"SELECT count(*) FROM users WHERE {DAY_IST.format(col='created_at')} <= :b"),
                                   {"b": w["prev_end"]})).scalar() or 0
    return {
        "key": "signups", "title": "Sign-ups",
        "rows": [
            _row("new_accounts", "New accounts", await _count(db, "users", "created_at", w["start"], w["end"]),
                 await _count(db, "users", "created_at", w["prev_start"], w["prev_end"]), src,
                 series=await _daily_count(db, w, "users", "created_at")),
            _row("accounts", "All accounts", total, before_end, src, note="At the end of each period."),
        ],
        "breakdowns": [
            {"key": "professions", "title": "Accounts by profession", "source": src,
             "rows": await _split(db, "SELECT profession, count(*) FROM users GROUP BY 1 ORDER BY 2 DESC")},
            {"key": "states", "title": "Accounts by state", "source": src,
             "rows": await _split(db, "SELECT state, count(*) FROM users GROUP BY 1 ORDER BY 2 DESC")},
        ],
    }


async def engagement(db: AsyncSession, w: dict[str, date], since_active: date | None, since: date | None) -> dict[str, Any]:
    active_src = f"user_days · signed-in accounts · {_since_label(since_active)}"
    active = dict((await db.execute(text(
        "SELECT day, count(*) FROM user_days WHERE day BETWEEN :a AND :b GROUP BY day"),
        {"a": w["start"], "b": w["end"]})).all())

    async def distinct_active(a: date, b: date) -> int:
        return (await db.execute(text("SELECT count(DISTINCT user_id) FROM user_days WHERE day BETWEEN :a AND :b"),
                                 {"a": a, "b": b})).scalar() or 0

    q_where = "role = 'user'"
    asked_src = "agent_messages · every question since launch"
    signed = ("role = 'user' AND session_id IN (SELECT id FROM agent_sessions WHERE user_ref IS NOT NULL)")
    lens = await _usage(db, w, "lens", since)
    ask = await _usage(db, w, "ask", since)
    return {
        "key": "engagement", "title": "Engagement",
        "rows": [
            _row("active_accounts", "Active accounts", await distinct_active(w["start"], w["end"]) if since_active else None,
                 await distinct_active(w["prev_start"], w["prev_end"]) if since_active and since_active <= w["prev_end"] else None,
                 active_src,
                 series=[None if since_active is None or d < since_active else active.get(d, 0) for d in _days(w)],
                 note="Accounts that used Prism signed in on at least one day of the period."),
            _row("questions", "Questions asked", await _count(db, "agent_messages", "created_at", w["start"], w["end"], q_where),
                 await _count(db, "agent_messages", "created_at", w["prev_start"], w["prev_end"], q_where), asked_src,
                 series=await _daily_count(db, w, "agent_messages", "created_at", q_where)),
            _row("questions_signed_in", "…of which signed in",
                 await _count(db, "agent_messages", "created_at", w["start"], w["end"], signed),
                 await _count(db, "agent_messages", "created_at", w["prev_start"], w["prev_end"], signed), asked_src),
            _row("lens_opens", "Lens opens", lens["current"], lens["previous"], f"usage_daily · {_since_label(since)}",
                 series=lens["series"]),
        ],
        "breakdowns": [
            {"key": "ask_via", "title": "How Ask was opened", "rows": ask["split"], "source": f"usage_daily · {_since_label(since)}"},
            {"key": "lenses", "title": "Lens opens, by lens", "rows": lens["split"], "source": f"usage_daily · {_since_label(since)}"},
        ],
        "retention": await retention(db, w["end"]),
    }


async def retention(db: AsyncSession, end: date, weeks: int = 8) -> dict[str, Any]:
    """Accounts that signed up in a week, and how many were active the week after.
    Weeks start on Monday, IST. Counts only: a cohort of 3 is not a percentage."""
    this_monday = end - timedelta(days=end.weekday())
    rows = []
    for i in range(weeks, 0, -1):
        start = this_monday - timedelta(weeks=i)
        after = start + timedelta(weeks=1)
        r = (await db.execute(text(
            f"""
            SELECT count(*) AS accounts,
                   count(*) FILTER (WHERE EXISTS (SELECT 1 FROM user_days d WHERE d.user_id = u.id
                                                  AND d.day BETWEEN :c AND :e)) AS returned
            FROM users u WHERE {DAY_IST.format(col='u.created_at')} BETWEEN :a AND :b
            """), {"a": start, "b": after - timedelta(days=1), "c": after, "e": after + timedelta(days=6)})).one()
        rows.append({"week": start.isoformat(), "accounts": r.accounts, "returned": r.returned,
                     "complete": after + timedelta(days=6) <= end})
    since = (await db.execute(text("SELECT min(day) FROM user_days"))).scalar()
    return {"title": "Came back the week after signing up", "rows": rows,
            "source": f"users + user_days · {_since_label(since)}"}


# A subscription that was ever paid has had a paid cycle start
# (common/razorpay sets current_period_start from Razorpay's current_start and
# never clears it). A checkout row is written the moment Razorpay opens, before
# any payment; one abandoned there never gets a cycle (review, 2026-09-23).
EVER_PAID = "provider <> 'manual' AND current_period_start IS NOT NULL"
ENDED = f"{EVER_PAID} AND status IN ('cancelled', 'halted', 'expired', 'completed') AND current_period_end IS NOT NULL"


async def money(db: AsyncSession, w: dict[str, date], since: date | None) -> dict[str, Any]:
    src = "subscriptions · now"
    rows = (await db.execute(text(
        "SELECT plan, price_paise, provider, status, current_period_end FROM subscriptions "
        "WHERE status IN ('active', 'past_due')"))).all()
    # "Paying" is the product's own test, billing.entitled — the status alone
    # would keep a lapsed row until the hourly reconcile catches it.
    live = [r for r in rows if billing.entitled(r.status, r.current_period_end)]
    paid = [r for r in live if r.provider != "manual"]
    # A plan's period is billing's own (month | year), not guessed from its name.
    period = {p.plan: p.period for p in (*billing.REGULAR.values(), *billing.OFFER.values())}
    per_plan: dict[str, int] = {}
    mrr_paise = 0.0
    for r in paid:
        per_plan[r.plan] = per_plan.get(r.plan, 0) + 1
        mrr_paise += (r.price_paise or 0) / (12 if period.get(r.plan) == "year" else 1)
    plans = sorted(per_plan.items(), key=lambda x: -x[1])
    funnel = await _usage(db, w, "subscribe", since)
    steps = {"prompt": "Saw the upgrade prompt", "page": "Opened the Plus page", "checkout": "Started checkout", "paid": "Paid"}
    by_step: dict[str, int] = {}
    for r in funnel["split"]:
        stage = r["label"].split(":")[0]
        by_step[stage] = by_step.get(stage, 0) + r["current"]
    history = "subscriptions · since launch"
    return {
        "key": "money", "title": "Money",
        "rows": [
            _row("paying", "Paying subscriptions", len(paid), None, src,
                 note="Paid through Razorpay and entitled to Plus today: active, or retrying a charge within the grace days."),
            _row("mrr", "Monthly recurring revenue", round(mrr_paise / 100), None, src, unit="inr",
                 note="Today's paying subscriptions, a yearly price counted as a twelfth a month. "
                      "No history: subscriptions keep no record of past states."),
            _row("complimentary", "Complimentary", len(live) - len(paid), None, src, note="Given by hand; not revenue."),
            _row("started", "Subscriptions started", await _count(db, "subscriptions", "current_period_start", w["start"], w["end"], EVER_PAID),
                 await _count(db, "subscriptions", "current_period_start", w["prev_start"], w["prev_end"], EVER_PAID), history,
                 note="By the day the first paid period began. A checkout left unpaid is not a subscription."),
            _row("ended", "Subscriptions ended", await _count(db, "subscriptions", "current_period_end", w["start"], w["end"], ENDED),
                 await _count(db, "subscriptions", "current_period_end", w["prev_start"], w["prev_end"], ENDED), history,
                 note="Paid subscriptions cancelled, halted, refunded or run out, by the day Plus stopped."),
        ],
        "breakdowns": [
            {"key": "funnel", "title": "The way to paying", "source": f"usage_daily · {_since_label(since)}",
             "rows": [{"label": label, "current": by_step.get(k, 0) if since else None, "previous": None}
                      for k, label in steps.items()]},
            {"key": "plans", "title": "Paying, by plan", "source": src,
             "rows": [{"label": p[0], "current": p[1], "previous": None} for p in plans]},
        ],
    }


async def demand(db: AsyncSession, w: dict[str, date], since: date | None) -> dict[str, Any]:
    src = f"usage_daily · {_since_label(since)}"
    limit = await _usage(db, w, "ask_limit", since)
    lens = await _usage(db, w, "lens", since)
    sub = await _usage(db, w, "subscribe", since)
    locked = [r for r in lens["split"] if r["label"].endswith(":locked")]
    prompts = [r for r in sub["split"] if r["label"].startswith("prompt")]
    applied_src = "labellers · since the workspace opened"
    return {
        "key": "demand", "title": "Demand",
        "rows": [
            _row("ask_limit", "Hit the free question limit", limit["current"], limit["previous"], src, series=limit["series"],
                 note="Asked for another answer and could not have one."),
            _row("locked_lens", "Opened a locked lens", sum(r["current"] for r in locked) if since else None, None, src),
            _row("prompts", "Saw the upgrade prompt", sum(r["current"] for r in prompts) if since else None, None, src),
            _row("applications", "Applied to label", await _count(db, "labellers", "created_at", w["start"], w["end"]),
                 await _count(db, "labellers", "created_at", w["prev_start"], w["prev_end"]), applied_src),
        ],
        "breakdowns": [
            {"key": "limit_by", "title": "Who hit the limit", "rows": limit["split"], "source": src},
            {"key": "locked_lenses", "title": "Locked lenses opened", "rows": locked, "source": src},
            {"key": "languages", "title": "Languages accounts read", "source": "users · every account since launch",
             "rows": await _split(db, "SELECT l, count(*) FROM users, unnest(coalesce(languages, ARRAY[]::text[])) AS l "
                                      "GROUP BY 1 ORDER BY 2 DESC")},
        ],
    }


async def supply(db: AsyncSession, w: dict[str, date]) -> dict[str, Any]:
    src = "raw_items · events · since launch"
    corroborated = """
        id IN (SELECT m.event_id FROM event_memberships m JOIN articles a ON a.id = m.article_id
               JOIN raw_items ri ON ri.id = a.raw_item_id GROUP BY m.event_id HAVING count(DISTINCT ri.source_id) >= 2)"""
    bal = await budget.current()
    bal_src = f"OpenRouter · as the worker last read it at {bal['at']}" if bal else "OpenRouter · not read yet"
    last = (await db.execute(text("SELECT max(observed_at) FROM raw_items"))).scalar()
    return {
        "key": "supply", "title": "Supply",
        "rows": [
            _row("reports", "Reports fetched", await _count(db, "raw_items", "observed_at", w["start"], w["end"]),
                 await _count(db, "raw_items", "observed_at", w["prev_start"], w["prev_end"]), src,
                 series=await _daily_count(db, w, "raw_items", "observed_at"),
                 note="Everything the collectors fetched, before relevance and duplicates are filtered."),
            _row("relevant", "…kept as relevant", await _count(db, "raw_items", "observed_at", w["start"], w["end"], RELEVANT),
                 await _count(db, "raw_items", "observed_at", w["prev_start"], w["prev_end"], RELEVANT), src),
            _row("events", "Stories formed", await _count(db, "events", "created_at", w["start"], w["end"]),
                 await _count(db, "events", "created_at", w["prev_start"], w["prev_end"]), src,
                 series=await _daily_count(db, w, "events", "created_at")),
            _row("corroborated", "…reported by two outlets or more",
                 await _count(db, "events", "created_at", w["start"], w["end"], corroborated),
                 await _count(db, "events", "created_at", w["prev_start"], w["prev_end"], corroborated), src),
            _row("outlets", "Outlets with a relevant report",
                 (await db.execute(text(f"SELECT count(DISTINCT source_id) FROM raw_items WHERE {RELEVANT} AND "
                                        f"{DAY_IST.format(col='observed_at')} BETWEEN :a AND :b"),
                                   {"a": w["start"], "b": w["end"]})).scalar() or 0, None, src),
            _row("llm_balance", "LLM balance", round(bal["balance"], 2) if bal else None, None, bal_src, unit="usd"),
            _row("last_report", "Last report taken in", last.isoformat() if last else None, None, "raw_items", unit="time"),
        ],
        "breakdowns": [
            {"key": "report_languages", "title": "Relevant reports, by language", "source": src,
             "rows": await _split(db, f"SELECT language, count(*) FROM raw_items WHERE {RELEVANT} AND "
                                      f"{DAY_IST.format(col='observed_at')} BETWEEN :a AND :b GROUP BY 1 ORDER BY 2 DESC",
                                  {"a": w["start"], "b": w["end"]})},
        ],
        "lag": await reporting_lag(db, w),
    }


async def reporting_lag(db: AsyncSession, w: dict[str, date]) -> dict[str, Any]:
    """Who reports first. For every story of the period that two or more outlets
    reported, each outlet's first report against the first report of anyone,
    by the publication time the outlet itself printed. An outlet is listed once
    it shares LAG_MIN_EVENTS stories; reports more than a week after the first
    are left out — that is a new story, not a late report."""
    rows = (await db.execute(text(
        f"""
        WITH a AS (
            SELECT m.event_id, ri.source_id, min(ri.published_at) AS t
            FROM event_memberships m JOIN articles ar ON ar.id = m.article_id
            JOIN raw_items ri ON ri.id = ar.raw_item_id JOIN events e ON e.id = m.event_id
            WHERE ri.published_at IS NOT NULL AND {DAY_IST.format(col='e.created_at')} BETWEEN :a AND :b
            GROUP BY m.event_id, ri.source_id),
        f AS (SELECT event_id, min(t) AS first FROM a GROUP BY event_id),
        -- The window FIRST, then "two outlets": a story whose only other report
        -- came three weeks later is not shared, and its lone early outlet must
        -- not be credited as first on it (review, 2026-09-23 — reproduced).
        k AS (SELECT a.event_id, a.source_id, a.t, f.first FROM a JOIN f USING (event_id)
              WHERE a.t - f.first <= {LAG_MAX}),
        shared AS (SELECT event_id FROM k GROUP BY event_id HAVING count(*) >= 2)
        SELECT s.name AS outlet, count(*) AS stories, count(*) FILTER (WHERE k.t = k.first) AS first,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM k.t - k.first) / 3600.0) AS median_hours
        FROM k JOIN shared USING (event_id) JOIN sources s ON s.id = k.source_id
        GROUP BY s.name HAVING count(*) >= :n
        ORDER BY median_hours, stories DESC LIMIT 25
        """), {"a": w["start"], "b": w["end"], "n": LAG_MIN_EVENTS})).mappings().all()
    return {"title": "Who reports first", "source": "raw_items.published_at · as each outlet printed it",
            "min_stories": LAG_MIN_EVENTS,
            "rows": [{"outlet": r["outlet"], "stories": r["stories"], "first": r["first"],
                      "median_hours": round(float(r["median_hours"]), 1)} for r in rows]}


async def dashboard(db: AsyncSession, days: int, today: date | None = None) -> dict[str, Any]:
    w = window(days, today)
    since = (await db.execute(text("SELECT min(day) FROM usage_daily"))).scalar()
    since_active = (await db.execute(text("SELECT min(day) FROM user_days"))).scalar()
    return {
        "range": {"days": days, **{k: v.isoformat() for k, v in w.items()}, "tz": "Asia/Kolkata"},
        "counting_since": {"usage": since.isoformat() if since else None,
                           "active": since_active.isoformat() if since_active else None},
        "sections": [
            await visits(db, w, since),
            await signups(db, w),
            await engagement(db, w, since_active, since),
            await money(db, w, since),
            await demand(db, w, since),
            await supply(db, w),
        ],
    }


WEEKLY_COLUMNS = ("week_start", "visitor_days", "page_views", "arrivals", "shares", "new_accounts",
                  "active_accounts", "questions", "hit_question_limit", "subscriptions_started")


async def weekly(db: AsyncSession, weeks: int, today: date | None = None) -> list[dict[str, Any]]:
    """The CSV for investors: one row per IST week (Monday start), counts only.
    usage columns are empty (not 0) for weeks before counting began.

    One grouped query per source, not one per week: a two-year export was ~800
    round trips of sequential scans (review, 2026-09-23)."""
    end = today or usage.today()
    first = end - timedelta(days=end.weekday()) - timedelta(weeks=weeks - 1)
    last = first + timedelta(weeks=weeks) - timedelta(days=1)
    week = "date_trunc('week', {d})::date"
    rng = {"a": first, "b": last}

    since = (await db.execute(text("SELECT min(day) FROM usage_daily"))).scalar()
    since_active = (await db.execute(text("SELECT min(day) FROM user_days"))).scalar()
    used: dict[tuple[date, str], int] = {
        (r[0], r[1]): int(r[2]) for r in (await db.execute(text(
            f"SELECT {week.format(d='day')}, event, sum(count) FROM usage_daily WHERE day BETWEEN :a AND :b GROUP BY 1, 2"),
            rng)).all()}
    active = dict((await db.execute(text(
        f"SELECT {week.format(d='day')}, count(DISTINCT user_id) FROM user_days WHERE day BETWEEN :a AND :b GROUP BY 1"),
        rng)).all())

    async def per_week(table: str, col: str, where: str = "TRUE") -> dict[date, int]:
        day = DAY_IST.format(col=col)
        return dict((await db.execute(text(
            f"SELECT {week.format(d=day)}, count(*) FROM {table} WHERE {where} AND {day} BETWEEN :a AND :b GROUP BY 1"),
            rng)).all())

    accounts = await per_week("users", "created_at")
    questions = await per_week("agent_messages", "created_at", "role = 'user'")
    started = await per_week("subscriptions", "current_period_start", EVER_PAID)
    out = []
    for i in range(weeks):
        a = first + timedelta(weeks=i)
        counted = since is not None and a + timedelta(days=6) >= since

        def u(event: str, a: date = a, counted: bool = counted) -> int | None:
            return used.get((a, event), 0) if counted else None

        out.append({
            "week_start": a.isoformat(), "visitor_days": u("visitors"), "page_views": u("view"),
            "arrivals": u("arrival"), "shares": u("share"), "new_accounts": accounts.get(a, 0),
            "active_accounts": active.get(a, 0) if since_active is not None and a + timedelta(days=6) >= since_active else None,
            "questions": questions.get(a, 0), "hit_question_limit": u("ask_limit"),
            "subscriptions_started": started.get(a, 0),
        })
    return out
