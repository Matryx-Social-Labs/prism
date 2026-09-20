"""Grant or revoke Plus by hand — testers, founding members before Razorpay,
goodwill. Writes a `manual` subscription row; entitlement follows from it.

    uv run python -m tools.grant_plan reader@example.com --plan founding --days 365
    uv run python -m tools.grant_plan reader@example.com --revoke
"""
import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from common.db import session_scope


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("email")
    ap.add_argument("--plan", default="plus_monthly", choices=["plus_monthly", "plus_yearly", "founding"])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--revoke", action="store_true")
    ap.add_argument("--note", default="manual grant")
    args = ap.parse_args()
    async with session_scope() as s:
        uid = (await s.execute(text("SELECT id FROM users WHERE email = :e"), {"e": args.email.strip().lower()})).scalar_one_or_none()
        if not uid:
            print("no such user (they must sign in once first)")
            return 1
        if args.revoke:
            n = (await s.execute(text("UPDATE subscriptions SET status = 'cancelled', updated_at = now() WHERE user_id = :u AND provider = 'manual' AND status IN ('active','past_due')"), {"u": uid})).rowcount
            print(f"revoked {n} manual grant(s)")
            return 0
        await s.execute(
            text("INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_end, notes) VALUES (:id, :u, 'manual', :sid, :plan, 'active', :end, :note)"),
            {"id": uuid.uuid4(), "u": uid, "sid": f"manual-{uuid.uuid4().hex[:10]}", "plan": args.plan, "end": datetime.now(UTC) + timedelta(days=args.days), "note": args.note},
        )
        print(f"granted {args.plan} to {args.email} for {args.days} days")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
