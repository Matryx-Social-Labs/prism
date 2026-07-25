"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useTaxonomy } from "@/components/ProfileEditor";
import { timeAgo } from "@/components/StoryCard";
import { fetchRegions } from "@/lib/api";
import { langNative } from "@/lib/languages";
import { lensMeta } from "@/lib/lenses";
import { loadProfile, type Profile } from "@/lib/profile";
import { clearSession, useSession } from "@/lib/session";
import { getWatchlist, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

const CARD = "mx-5 mt-2.5 overflow-hidden rounded-[16px] border";
const CARD_STYLE = { borderColor: "var(--line)", background: "var(--bg-elevated)" } as const;
const H2 = "mx-5 mt-[18px] text-[12px] font-semibold uppercase tracking-[0.14em]";

export default function YouPage() {
  const session = useSession();
  const taxonomy = useTaxonomy();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [stateName, setStateName] = useState<string | null>(null);
  const [follows, setFollows] = useState<WatchItem[]>([]);
  const [recent, setRecent] = useState<WatchEvent[]>([]);

  useEffect(() => setProfile(loadProfile()), []);
  useEffect(() => {
    if (!profile?.state) return;
    fetchRegions().then((rs) => setStateName(rs.find((r) => r.code === profile.state)?.name ?? null)).catch(() => {});
  }, [profile?.state]);
  useEffect(() => {
    if (!session) return;
    getWatchlist(session).then(setFollows).catch(() => setFollows([]));
    watchlistEvents(session).then(setRecent).catch(() => setRecent([]));
  }, [session]);

  const lens = lensMeta(profile?.lens ?? "reader");
  const languages = profile?.languages?.length ? profile.languages : ["en"];
  const interestName = (slug: string) => {
    const [sec, sub] = slug.split(":");
    const s = taxonomy.find((t) => t.slug === sec);
    const name = s?.name ?? sec.replaceAll("_", " ");
    return sub ? `${name} · ${sub.replaceAll("_", " ")}` : name;
  };
  const initial = (session?.email ?? "G").charAt(0).toUpperCase();

  return (
    <div className="mx-auto max-w-[620px] pb-28">
      {/* identity */}
      <div className="flex items-center gap-3 border-b px-5 py-4" style={{ borderColor: "var(--line)" }}>
        <span
          className="flex h-12 w-12 items-center justify-center rounded-full border text-[19px] font-semibold"
          style={{ background: "var(--bg-sunken)", borderColor: "var(--line)", fontFamily: "var(--font-display), serif" }}
        >
          {initial}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[20px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
            {session ? session.email.split("@")[0] : "Guest"}
          </p>
          <p className="mt-0.5 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
            {session ? "signed in · synced across devices" : "browsing without an account"}
          </p>
        </div>
        {!session && (
          <Link href="/signin" className="rounded-full px-4 py-2 text-[13px] font-semibold" style={{ background: "var(--ink)", color: "var(--bg)" }}>
            Sign in
          </Link>
        )}
      </div>

      {/* Your Parse */}
      <h2 className={H2} style={{ color: "var(--ink-muted)" }}>
        Your Parse
      </h2>
      <div className={CARD} style={CARD_STYLE}>
        <Row label="Default lens">
          <span className="rounded-full px-2.5 py-[3px] text-[12px] font-semibold" style={{ background: lens.bg, color: lens.color }}>
            {lens.short}
          </span>
        </Row>
        <Row label="Region">
          <span className="rounded-full px-2.5 py-[3px] text-[12px] font-semibold" style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}>
            ◉ {stateName ?? "India"}
          </span>
        </Row>
        <div className="border-b px-[14px] py-3" style={{ borderColor: "var(--line)" }}>
          <p className="text-[13.5px] font-medium" style={{ color: "var(--ink-muted)" }}>
            Languages
          </p>
          <p className="mb-2 mt-0.5 text-[11.5px]" style={{ color: "var(--ink-faint)" }}>
            Rank your feed — they never filter it.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {languages.map((l, i) => (
              <span key={l} className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold" style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}>
                <span className="font-mono text-[10px]" style={{ color: "var(--ink-faint)" }}>
                  {i + 1}
                </span>
                {langNative(l)}
              </span>
            ))}
          </div>
        </div>
        <div className="px-[14px] py-3">
          <p className="mb-2 text-[13.5px] font-medium" style={{ color: "var(--ink-muted)" }}>
            Interests
          </p>
          <div className="flex flex-wrap gap-1.5">
            {(profile?.interests ?? []).map((s) => (
              <span key={s} className="rounded-full px-3 py-1.5 text-[12px] font-semibold" style={{ background: "var(--ink)", color: "var(--bg)" }}>
                {interestName(s)}
              </span>
            ))}
            <Link href="/interests" className="rounded-full border px-3 py-1.5 text-[12px] font-semibold" style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}>
              + Edit
            </Link>
          </div>
        </div>
      </div>

      {/* Following */}
      <h2 className={H2} style={{ color: "var(--ink-muted)" }}>
        Following
      </h2>
      <div className={`${CARD} p-[14px]`} style={CARD_STYLE}>
        {session ? (
          <>
            {follows.length > 0 ? (
              <div className="mb-3 flex flex-wrap gap-1.5">
                {follows.map((w) => (
                  <span key={`${w.kind}:${w.value}`} className="rounded-full px-3 py-[5px] font-mono text-[11px] font-medium" style={{ background: "var(--bg-sunken)", color: "var(--ink)" }}>
                    {w.value}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mb-3 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
                Nothing followed yet. Follow tickers and sectors from any story.
              </p>
            )}
            <Link href="/watchlist" className="text-[13px] font-semibold" style={{ color: "var(--ink)" }}>
              Manage signals →
            </Link>
            {recent.length > 0 && (
              <div className="mt-3 border-t pt-3" style={{ borderColor: "var(--line)" }}>
                {recent.slice(0, 3).map((e) => (
                  <Link key={e.id} href={`/story/${e.id}`} className="block py-1.5">
                    <p className="text-[13px] font-semibold leading-[1.4]">{e.title}</p>
                    <span className="font-mono text-[10px]" style={{ color: "var(--ink-faint)" }}>
                      {timeAgo(e.last_updated_at)}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </>
        ) : (
          <Link href="/signin" className="text-[13px] font-semibold" style={{ color: "var(--ink)" }}>
            Sign in to follow tickers and sectors →
          </Link>
        )}
      </div>

      {/* Account */}
      <h2 className={H2} style={{ color: "var(--ink-muted)" }}>
        Account
      </h2>
      <div className={CARD} style={CARD_STYLE}>
        <div className="flex min-h-[52px] items-center border-b px-[14px]" style={{ borderColor: "var(--line)" }}>
          <span className="text-[13.5px] font-medium">Theme</span>
          <span className="ml-auto">
            <ThemeToggle />
          </span>
        </div>
        {session ? (
          <button
            onClick={() => {
              clearSession();
              window.location.href = "/feed";
            }}
            className="flex min-h-[52px] w-full items-center px-[14px] text-left text-[13.5px] font-medium"
            style={{ color: "var(--danger)" }}
          >
            Sign out
          </button>
        ) : (
          <Link href="/signin" className="flex min-h-[52px] items-center px-[14px] text-[13.5px] font-medium">
            Sign in
          </Link>
        )}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-[52px] items-center gap-2.5 border-b px-[14px]" style={{ borderColor: "var(--line)" }}>
      <span className="w-24 text-[13.5px] font-medium" style={{ color: "var(--ink-muted)" }}>
        {label}
      </span>
      {children}
      <span className="ml-auto" style={{ color: "var(--ink-faint)" }}>
        ›
      </span>
    </div>
  );
}
