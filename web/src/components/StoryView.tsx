"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchBrief, fetchQuestions, type EventDetail } from "@/lib/api";
import { useRouter } from "next/navigation";

import { lensMeta, useLenses } from "@/lib/lenses";
import { useSession } from "@/lib/session";
import { loadProfile } from "@/lib/profile";
import { AskPanel } from "@/components/AskPanel";
import { ShareButton } from "@/components/ShareButton";
import { StoryDesktop } from "@/components/StoryDesktop";
import { BriefPlayer } from "@/components/BriefPlayer";
import { FollowSignals } from "@/components/FollowSignals";
import { StoryTimeline } from "@/components/StoryTimeline";

function regionName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

const FUNDING_LABEL: Record<string, string> = {
  state: "State-affiliated",
  public: "Public broadcaster",
};

function timeAgo(iso: string): string {
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function Chip({
  children,
  bg = "var(--bg-sunken)",
  color = "var(--ink-muted)",
  mono = false,
}: {
  children: React.ReactNode;
  bg?: string;
  color?: string;
  mono?: boolean;
}) {
  return (
    <span
      className={`rounded-full px-[9px] py-0.5 text-[11px] ${mono ? "font-mono font-medium" : "font-semibold"}`}
      style={{ background: bg, color }}
    >
      {children}
    </span>
  );
}

function FundingChip({ funding }: { funding: string | null }) {
  if (!funding || !FUNDING_LABEL[funding]) return null;
  return (
    <span
      className="shrink-0 rounded-full border px-[7px] py-px font-mono text-[9px] font-medium uppercase tracking-wide"
      style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)" }}
    >
      {FUNDING_LABEL[funding]}
    </span>
  );
}

function SectionTitle({ title, hint }: { title: string; hint: string }) {
  return (
    <>
      <h2 className="mb-1.5 text-[23px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        {title}
      </h2>
      <p className="mb-4 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
        {hint}
      </p>
    </>
  );
}

export function StoryView({ event }: { event: EventDetail }) {
  const cyber = event.projection?.cyber ?? null;
  const finance = event.projection?.finance ?? null;
  const sourceById = new Map(event.sources.map((s) => [s.article_id, s]));

  const [lens, setLens] = useState("reader");
  const [briefs, setBriefs] = useState<Record<string, string>>(event.lens_briefs ?? {});
  const [flipped, setFlipped] = useState(false);
  const [points, setPoints] = useState<Record<string, string[]>>(event.lens_points ?? {});
  const [briefLoading, setBriefLoading] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);
  const [myRegion, setMyRegion] = useState<string | null>(null);
  // Did the READER ask for this lens, or did it come back from their profile?
  // The locked-lens guard below has to tell those apart, and `lens` alone can't.
  const readerPicked = useRef(false);
  // Tracks the previous session so the guard below can spot a sign-OUT rather
  // than the steady state of never having been signed in.
  const wasSignedIn = useRef(false);

  const registry = useLenses();
  const registrySlugs = registry.map((m) => m.slug);
  const offered = event.available_lenses?.length
    ? registrySlugs.filter((slug) => event.available_lenses.includes(slug))
    : registrySlugs;

  // Sign-in gate (no paywall — free once signed in): the general reader lens is
  // open to everyone; the professional lenses (markets, cyber) require an account.
  const session = useSession();
  const router = useRouter();
  const isLocked = (slug: string) => slug !== "reader" && !session;

  useEffect(() => {
    const profile = loadProfile();
    setMyRegion(profile?.region ?? null);
    const preferred = profile?.lens && offered.includes(profile.lens) ? profile.lens : "reader";
    setLens(preferred);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Don't fetch (or generate) a locked pro lens for a signed-out reader.
    if (!isLocked(lens)) {
      fetchQuestions(event.id, lens).then((qs) => !cancelled && setQuestions(qs));
      if (!briefs[lens]) {
        setBriefLoading(true);
        fetchBrief(event.id, lens).then((res) => {
          if (cancelled) return;
          setBriefLoading(false);
          if (res?.brief) setBriefs((prev) => ({ ...prev, [lens]: res.brief! }));
          if (res?.points?.length) setPoints((prev) => ({ ...prev, [lens]: res.points! }));
        });
      }
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lens, event.id, session]);

  // Snap back to the reader lens only when a locked pro lens arrived from the
  // PROFILE rather than from a tap. A deliberate pick is allowed to stay so the
  // reader sees the flip and the inline unlock prompt.
  useEffect(() => {
    // The exemption belongs to the session it was granted under. useSession
    // subscribes to the `storage` event, so signing out in ANOTHER tab flips
    // this one to signed-out on a mounted story — without the reset, a stale
    // readerPicked left that reader parked on a locked lens with the sign-in
    // wall as the whole story, which is the exact thing this guard prevents.
    //
    // Keyed on the transition, not on `!session`: a signed-out reader is null
    // the whole time, so resetting on the steady state cancelled their tap in
    // the same commit and made every lens control dead again.
    if (wasSignedIn.current && !session) readerPicked.current = false;
    wasSignedIn.current = Boolean(session);
    if (isLocked(lens) && !readerPicked.current) setLens("reader");
    // `lens` in the deps, not just `session`: the profile effect sets the saved
    // lens AFTER this runs, and for a signed-out reader `session` stays null
    // forever — so on [session] alone this never fired again and every reader
    // with a saved pro lens got the sign-in wall as the whole story. That is
    // the first thing a mobile visitor from a shared link sees.
    //
    // But watching `lens` also caught the reader TAPPING a pro lens: the tab
    // set it and this reverted it in the same commit, so every lens control on
    // the page — tabs, pinned rail, keyboard 1/2/3 — was a dead button for a
    // signed-out reader. The whole point of flipping to a locked lens is to
    // show the re-typeset and the inline unlock prompt, so a deliberate pick
    // is exempt; only a profile-restored lens gets snapped back.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, lens]);

  const meta = lensMeta(lens);
  const brief = briefs[lens];
  const lensPoints = points[lens] ?? [];
  const pointsHeading =
    lens === "cyber" ? "What to check" : lens === "markets" ? "What to watch" : "What to watch next";
  const cvss = cyber?.cvss ?? {};
  const exploitation = cyber?.exploitation ?? {};
  const coverageEntries = Object.entries(event.coverage?.origins ?? {}).sort((a, b) => b[1] - a[1]);
  const coveredOrigins = coverageEntries.map(([iso]) => iso);
  const gapText =
    myRegion && coverageEntries.length > 0 && !coveredOrigins.includes(myRegion)
      ? `No ${regionName(myRegion)} outlet has covered this yet.`
      : null;

  // ── "On this story" section nav ────────────────────────
  const sourceCount = event.sources.length;
  const storyCount = event.story.developments.filter((d) => !d.is_current).length;
  const balanceText = event.coverage?.single_origin
    ? "⚠ Single-origin — one perspective only."
    : coverageEntries.length > 0
      ? `Balanced coverage — ${coverageEntries.length} origin${coverageEntries.length === 1 ? "" : "s"}, no blindspot flag.`
      : null;
  const navItems: { id: string; label: string; count?: number }[] = [
    { id: "lens-brief", label: "Lens brief" },
    { id: "perspectives", label: "Perspectives", count: event.perspectives.length },
    ...(storyCount > 0 ? [{ id: "story-so-far", label: "The story so far", count: storyCount }] : []),
    { id: "what-to-expect", label: "What to expect", count: event.impacts.length },
    { id: "sources", label: "Sources", count: sourceCount },
  ];

  // Lightweight scroll-spy so the rail nav + mobile chips highlight the section
  // in view. Anchors still jump on click; this only drives the active border.
  const [activeSection, setActiveSection] = useState("lens-brief");
  const [askOpen, setAskOpen] = useState(false);

  // Picking a lens from the pinned rail must SHOW the result: the brief is
  // off-screen behind the reader's scroll position, so the re-typeset flip
  // happens where nobody can see it and the tap reads as a dead button.
  function pickLens(slug: string, scroll = true) {
    readerPicked.current = true;
    setFlipped(true);
    setLens(slug);
    if (!scroll) return;
    document.getElementById("lens-brief")?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  }

  // Desktop has no thumb zone, so the flip binds to the keyboard: 1 / 2 / 3, no
  // modifier (Parse Desktop.dc.html — the brief header prints "PRESS 1 · 2 · 3").
  // Zero-travel and repeatable — a reader hits 1-2-3-2-1 in two seconds, and
  // repeatability is what turns the flip from a trick into the thing they show a
  // colleague. No scroll on a key press: the brief is already in view, and
  // yanking the page would contradict "layout never moves".
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      const idx = Number(e.key) - 1;
      if (!Number.isInteger(idx) || idx < 0 || idx >= offered.length) return;
      e.preventDefault();
      pickLens(offered[idx], false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offered]);
  useEffect(() => {
    const els = navItems
      .map((n) => document.getElementById(n.id))
      .filter((el): el is HTMLElement => el != null);
    if (els.length === 0) return;
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveSection(visible[0].target.id);
      },
      { rootMargin: "-15% 0px -75% 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.id, storyCount]);

  return (
    <>
      {/* Desktop is its own composition (Parse Desktop.dc.html): the ledger rail
          re-inks with the lens and all three openings sit on the board at once.
          State stays here so there is one lens machine, not two. */}
      <StoryDesktop
        event={event}
        lens={lens}
        offered={offered}
        briefs={briefs}
        brief={brief}
        lensName={(slug) => lensMeta(slug).short}
        isLocked={isLocked}
        onPick={(slug) => pickLens(slug, false)}
      />

    <div className="mx-auto max-w-[1240px] px-5 pb-[164px] pt-7 sm:px-8 lg:hidden">
      <Link href="/feed" scroll={false} className="mb-5 block text-[12.5px] font-semibold" style={{ color: "var(--ink-faint)" }}>
        ← Back to feed
      </Link>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
        {/* min-w-0: without it a grid item's default min-width:auto lets the
            inner horizontal scrollers (lens-tab strip, mobile anchor nav, cyber
            table) stretch the column past the viewport — the mobile right-bleed. */}
        <article className="min-w-0">
      {/* ── Header ─────────────────────────────────────────── */}
      <header>
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {event.subsector ? (
            <Chip>
              <span className="uppercase tracking-wide" style={{ fontSize: "10.5px" }}>
                {event.subsector.replaceAll("_", " ")}
              </span>
            </Chip>
          ) : (
            event.sector && (
              <Chip>
                <span className="uppercase tracking-wide" style={{ fontSize: "10.5px" }}>
                  {event.sector}
                </span>
              </Chip>
            )
          )}
          {event.coverage?.single_origin && <Chip>⚠ Single-origin</Chip>}
          {cvss.score != null && (
            <Chip bg="var(--danger-bg)" color="var(--danger)">
              CVSS {cvss.score.toFixed(1)} {cvss.severity ?? ""}
            </Chip>
          )}
          {exploitation.kev_listed && (
            <Chip bg="var(--danger)" color="#fff">
              ⚠ Actively exploited
            </Chip>
          )}
          {(cyber?.cve_ids ?? []).slice(0, 3).map((cve) => (
            <Chip key={cve} mono color="var(--ink)">
              {cve}
            </Chip>
          ))}
          {(finance?.tickers ?? []).slice(0, 4).map((t) => (
            <Chip key={t} mono bg="var(--lens-finance-bg)" color="var(--lens-finance)">
              ${t}
            </Chip>
          ))}
          {finance?.catalyst && (
            // Catalyst type — SEBI-safe reframe: what kind of event is moving
            // this, sourced, instead of a buy/sell "direction". Mono evidence label.
            <span
              className="rounded-full border px-[8px] py-px font-mono text-[10px] font-medium uppercase tracking-wide"
              style={{ borderColor: "var(--lens-finance)", color: "var(--lens-finance)" }}
              title="Catalyst type — what is moving this story"
            >
              {finance.catalyst.replaceAll("_", " ")}
            </span>
          )}
          <span className="ml-auto font-mono text-[10.5px]" style={{ color: "var(--ink-muted)" }} suppressHydrationWarning>
            {event.sources.length} source{event.sources.length === 1 ? "" : "s"} · {timeAgo(event.last_updated_at)}
          </span>
        </div>

        <h1
          className="text-[28px] font-semibold leading-[1.15] tracking-tight sm:text-[34px]"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          {event.title}
        </h1>
        {event.summary && (
          <p className="mt-3.5 text-[15.5px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            {event.summary}
          </p>
        )}

        {event.image_url && (
          <div className="relative mt-5 aspect-video overflow-hidden rounded-[18px]" style={{ background: "var(--bg-sunken)" }}>
            <Image
              src={event.image_url}
              alt=""
              fill
              priority
              sizes="(max-width: 780px) 100vw, 740px"
              className="object-cover"
              onError={(e) => {
                (e.currentTarget.parentElement as HTMLElement).style.display = "none";
              }}
            />
          </div>
        )}

        {(event.entities.length > 0 || event.regions.length > 0) && (
          <div className="mt-5 flex flex-wrap items-center gap-1.5">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Affected
            </span>
            {event.regions.map((r) => (
              <span key={r} className="rounded-full border px-2.5 py-0.5 text-xs" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
                ◉ {regionName(r)}
              </span>
            ))}
            {event.entities.map((en) => (
              <span
                key={`${en.name}-${en.role}`}
                title={en.role}
                className="rounded-full border px-2.5 py-0.5 text-xs"
                style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
              >
                {en.entity_type === "person" ? "◇" : "▪"} {en.name}
              </span>
            ))}
          </div>
        )}

      </header>

      {/* ── Mobile section nav — sticky anchor chips ────────── */}
      {/* Coverage bar — mobile: the verify layer, promoted from the desktop rail. */}
      {coverageEntries.length > 0 && (
        <div
          className="mt-5 rounded-[14px] border px-3.5 py-3 lg:hidden"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <span className="font-mono text-[11px]" style={{ color: "var(--ink)" }}>
            ⌗ {sourceCount} outlet{sourceCount === 1 ? "" : "s"} · {coverageEntries.length} origin
            {coverageEntries.length === 1 ? "" : "s"} ·{" "}
            <span style={{ color: event.coverage?.single_origin ? "var(--danger)" : "var(--up)" }}>
              {event.coverage?.single_origin ? "Single-origin" : "Balanced"}
            </span>
          </span>
          {gapText && (
            <p className="mt-1.5 text-[12.5px]" style={{ color: "var(--danger)" }}>
              ◉ {gapText}
            </p>
          )}
          <div className="mt-2.5 flex flex-wrap gap-1.5 border-t pt-2.5" style={{ borderColor: "var(--line)" }}>
            {coverageEntries.map(([iso, n]) => (
              <span
                key={iso}
                className="rounded-full px-2 py-0.5 font-mono text-[10px]"
                style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
              >
                {regionName(iso)} × {n}
              </span>
            ))}
          </div>
        </div>
      )}

      <nav
        className="sticky top-0 z-20 -mx-5 mt-5 flex gap-1.5 overflow-x-auto border-b px-5 py-2.5 sm:-mx-8 sm:px-8 lg:hidden"
        style={{ borderColor: "var(--line)", background: "var(--bg)" }}
        aria-label="On this story"
      >
        {navItems.map((n) => (
          <a
            key={n.id}
            href={`#${n.id}`}
            className="flex-none rounded-full px-3 py-1.5 text-[11px] font-semibold"
            style={
              activeSection === n.id
                ? { background: "var(--bg-sunken)", color: "var(--ink)" }
                : { color: "var(--ink-muted)" }
            }
          >
            {n.label}
            {n.count != null && <span className="ml-1 font-mono text-[10px]" style={{ color: "var(--ink-faint)" }}>{n.count}</span>}
          </a>
        ))}
      </nav>

      {/* ── Lens block — the product moment ─────────────────── */}
      <section
        id="lens-brief"
        className="mt-9 scroll-mt-24 overflow-hidden rounded-[18px] border"
        style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-card)" }}
      >
        <div className="hidden border-b lg:block" style={{ borderColor: "var(--line)" }}>
          <div className="flex items-center gap-1.5 px-4 py-3" role="tablist" aria-label="Read this story through a lens">
            <span className="mr-1 text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              Lens
            </span>
            {offered.map((slug) => {
              const m = lensMeta(slug);
              const selected = slug === lens;
              const locked = isLocked(slug);
              return (
                <button
                  key={slug}
                  role="tab"
                  aria-selected={selected}
                  onClick={() => {
                    // Locked pro lens: flip to it anyway. The re-typeset reveals the
                    // inline "sign in to unlock" prompt in place (isLocked branch
                    // below) — so a signed-out reader SEES the signature flip and
                    // keeps their place on the story instead of a hard bounce to
                    // /signin. No brief is fetched for a locked lens, so it stays free.
                    pickLens(slug, false);
                  }}
                  title={locked ? `Sign in to read the ${m.short} lens — ${m.plain ?? m.tagline} (free)` : undefined}
                  className="flex items-center gap-1 whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
                  style={
                    selected
                      ? { background: m.bg, color: m.color, boxShadow: `inset 0 0 0 1.5px ${m.color}` }
                      : { color: locked ? "var(--ink-faint)" : "var(--ink-muted)" }
                  }
                >
                  {locked && (
                    <svg aria-hidden width="10" height="10" viewBox="0 0 24 24" fill="none" style={{ opacity: 0.75 }}>
                      <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="2.2" />
                      <path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2.2" />
                    </svg>
                  )}
                  {m.short}
                </button>
              );
            })}
            {offered.length === 1 && (
              <span className="px-1.5 text-[11.5px]" style={{ color: "var(--ink-faint)" }}>
                Only this lens applies to this story
              </span>
            )}
            {/* Discoverability for the keyboard flip. Provenance voice, far right,
                quiet — it teaches the shortcut without competing with the tabs. */}
            {offered.length > 1 && (
              <span
                className="ml-auto pl-4 font-mono text-[10.5px] uppercase tracking-[0.12em]"
                style={{ color: "var(--ink-faint)" }}
                aria-hidden
              >
                Press {offered.map((_, i) => i + 1).join(" · ")}
              </span>
            )}
          </div>
        </div>

        <div
          key={lens}
          className={`${flipped ? "flip-body" : ""} relative flex flex-col gap-[18px] overflow-hidden px-[22px] py-5`}
        >
          {flipped && <span aria-hidden className="flip-scanline" style={{ background: meta.color }} />}
          {isLocked(lens) ? (
            <div className="flex flex-col items-start gap-3">
              <p className="text-[14.5px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
                Read this story through the{" "}
                <span className="font-semibold" style={{ color: meta.color }}>
                  {meta.short} lens
                </span>{" "}
                — {meta.plain ?? meta.tagline}. Free with an account.
              </p>
              <button
                onClick={() => router.push("/signin")}
                className="rounded-full px-4 py-2 text-[13px] font-semibold"
                style={{ background: "var(--ink)", color: "var(--bg)" }}
              >
                Sign in to unlock
              </button>
            </div>
          ) : briefLoading && !brief ? (
            <div aria-label="Generating lens brief">
              <div className="pulse-skel h-[13px] rounded-md" style={{ background: "var(--bg-sunken)" }} />
              <div className="pulse-skel mt-2 h-[13px] w-[92%] rounded-md" style={{ background: "var(--bg-sunken)" }} />
              <div className="pulse-skel mt-2 h-[13px] w-[78%] rounded-md" style={{ background: "var(--bg-sunken)" }} />
              <p className="mt-2.5 text-xs" style={{ color: "var(--ink-faint)" }}>
                Writing the {meta.short} read of this story…
              </p>
            </div>
          ) : brief ? (
            <BriefPlayer brief={brief} points={lensPoints} meta={meta} pointsHeading={pointsHeading} />
          ) : (
            <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
              No {meta.short} read of this story yet.
            </p>
          )}

          {lens === "cyber" && cyber && !isLocked(lens) && (
            <div className="flex flex-col gap-3.5">
              <div className="flex flex-wrap gap-1.5">
                {cvss.score != null && (
                  <Chip bg="var(--danger-bg)" color="var(--danger)">
                    CVSS {cvss.score.toFixed(1)}
                  </Chip>
                )}
                {exploitation.kev_listed && (
                  <Chip bg="var(--danger)" color="#fff">
                    ⚠ KEV listed
                  </Chip>
                )}
                {exploitation.poc_public && <Chip color="var(--ink)">PoC public</Chip>}
                {cvss.vector && (
                  <Chip mono>
                    {cvss.vector}
                  </Chip>
                )}
              </div>
              {(cyber.affected ?? []).length > 0 && (
                <div>
                  <h3 className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
                    Affected products
                  </h3>
                  <ul className="text-[13.5px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
                    {(cyber.affected ?? []).map((a, i) => (
                      <li key={i}>
                        {a.vendor} {a.product}{" "}
                        {a.versions && <span className="font-mono text-xs">({a.versions})</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {cyber.remediation?.action && (
                <div
                  className="rounded-xl border px-4 py-3 text-[13.5px] leading-[1.6]"
                  style={{ borderColor: "var(--lens-cyber)", background: "var(--lens-cyber-bg)", color: "var(--ink)" }}
                >
                  <strong>Required action:</strong> {cyber.remediation.action}
                </div>
              )}
              {(cyber.control_mapping ?? []).length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px]">
                    <thead>
                      <tr className="text-[10.5px] uppercase tracking-wide" style={{ color: "var(--ink-faint)" }}>
                        <th className="border-b py-1.5 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>
                          Framework
                        </th>
                        <th className="border-b py-1.5 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>
                          Control
                        </th>
                        <th className="border-b py-1.5 font-semibold" style={{ borderColor: "var(--line)" }}>
                          Why it matters here
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {(cyber.control_mapping ?? []).map((cm, i) => (
                        <tr key={i}>
                          <td className="border-b py-2 pr-3.5 font-mono text-xs" style={{ borderColor: "var(--line)" }}>
                            {cm.framework}
                          </td>
                          <td className="border-b py-2 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>
                            {cm.control}
                          </td>
                          <td className="border-b py-2" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
                            {cm.relevance}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {lens === "markets" && finance && !isLocked(lens) && (
            <div className="flex flex-col gap-3">
            <div
              className="flex flex-wrap gap-x-6 gap-y-2 rounded-xl border px-4 py-3 text-[13.5px]"
              style={{ borderColor: "var(--lens-finance)", background: "var(--lens-finance-bg)", color: "var(--ink)" }}
            >
              {(finance.tickers ?? []).length > 0 && (
                <span>
                  <strong>Tickers:</strong>{" "}
                  <span className="font-mono">{(finance.tickers ?? []).map((t) => `$${t}`).join(", ")}</span>
                </span>
              )}
              {finance.sector && (
                <span>
                  <strong>Sector:</strong> {finance.sector}
                </span>
              )}
              {finance.catalyst && (
                <span>
                  <strong>Catalyst:</strong> {finance.catalyst.replaceAll("_", " ")}
                </span>
              )}
              {finance.price_impact?.direction && (
                <span>
                  <strong>Price read:</strong>{" "}
                  {finance.price_impact.direction === "up" ? "▲" : finance.price_impact.direction === "down" ? "▼" : "◆"}{" "}
                  {finance.price_impact.magnitude ?? ""}
                  {finance.price_impact.confidence != null &&
                    ` (${Math.round(finance.price_impact.confidence * 100)}% conf.)`}
                </span>
              )}
            </div>
            <FollowSignals tickers={finance.tickers ?? []} sector={finance.sector ?? null} />
            </div>
          )}
        </div>
      </section>

      {/* ── Perspectives ─────────────────────────────────────── */}
      <section id="perspectives" className="mt-11 scroll-mt-24">
        <SectionTitle
          title="Perspectives"
          hint="The story's competing narratives, side by side — grouped by stance, with every outlet's origin and affiliation visible."
        />
        {event.perspectives.length === 0 ? (
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Perspective analysis pending — it generates as coverage from more origins arrives.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {event.perspectives.map((p, i) => (
              <div
                key={i}
                className="card-hover rounded-[18px] border p-5"
                style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-[14.5px] font-semibold">{p.label}</span>
                  {p.origin_country && <Chip>{regionName(p.origin_country)}</Chip>}
                  {p.stance && (
                    <span className="text-[11.5px]" style={{ color: "var(--ink-faint)" }}>
                      {p.stance}
                    </span>
                  )}
                </div>
                {p.summary && (
                  <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                    {p.summary}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {p.article_ids.map((aid) => {
                    const src = sourceById.get(aid);
                    return src ? (
                      <span
                        key={aid}
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px]"
                        style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
                      >
                        {src.source_name}
                        <FundingChip funding={src.funding} />
                      </span>
                    ) : null;
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── The story so far — one canonical, consistent timeline ── */}
      <div id="story-so-far" className="scroll-mt-24">
        <StoryTimeline story={event.story} />
      </div>

      {/* ── What to expect ─────────────────────────────────── */}
      <section id="what-to-expect" className="mt-11 scroll-mt-24">
        <SectionTitle
          title="What to expect"
          hint="First-order impacts with their likely second-order effects — direction and horizon per node."
        />
        {event.impacts.length === 0 ? (
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Impact analysis pending.
          </p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {event.impacts.map((imp) => (
              <li key={imp.id} className={`flex items-start gap-2.5 ${imp.parent_impact_id ? "ml-7" : ""}`}>
                <span
                  aria-hidden
                  className="shrink-0"
                  style={{
                    color:
                      imp.direction === "negative"
                        ? "var(--danger)"
                        : imp.direction === "positive"
                          ? "var(--up)"
                          : "var(--ink-faint)",
                  }}
                >
                  {imp.parent_impact_id ? "↳" : "●"}
                </span>
                <span className="text-[13.5px] leading-[1.55]">
                  <strong>{imp.entity_name ?? "Affected party"}</strong>{" "}
                  <span style={{ color: "var(--ink-muted)" }}>— {imp.effect.replaceAll("_", " ")}</span>{" "}
                  <span style={{ color: "var(--ink-faint)" }}>· {imp.horizon ?? "unknown horizon"}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Sources ────────────────────────────────────────── */}
      <section id="sources" className="mt-11 scroll-mt-24">
        <h2 className="mb-4 text-[23px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
          Sources{" "}
          <span className="text-[15px] font-normal" style={{ color: "var(--ink-faint)" }}>
            ({event.sources.length})
          </span>
        </h2>
        <ul className="flex flex-col gap-[9px]">
          {event.sources.map((s, i) => (
            <li key={s.article_id} className="flex items-baseline gap-2.5 text-[13.5px]">
              <span className="shrink-0 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
                [{i + 1}]
              </span>
              <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[11.5px]" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
                {s.source_name}
              </span>
              <FundingChip funding={s.funding} />
              {s.url ? (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="min-w-0 truncate underline-offset-4 hover:underline"
                  style={{ color: "var(--ink)" }}
                >
                  {s.title}
                </a>
              ) : (
                <span className="min-w-0 truncate">{s.title}</span>
              )}
              {s.stance && (
                <span className="ml-auto hidden shrink-0 text-[11.5px] sm:block" style={{ color: "var(--ink-faint)" }}>
                  {s.stance}
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
        </article>

        {/* ── Right rail — desktop only ─────────────────────── */}
        <aside className="sticky top-[72px] hidden min-w-0 flex-col gap-3.5 lg:flex">
          {/* On this story */}
          <div
            className="rounded-[18px] border px-[18px] py-4"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
          >
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
              On this story
            </span>
            <div className="mt-2.5 flex flex-col gap-px">
              {navItems.map((n) => {
                const active = activeSection === n.id;
                return (
                  <a
                    key={n.id}
                    href={`#${n.id}`}
                    className="px-3 py-1.5 text-[13px] no-underline"
                    style={{
                      borderLeft: `2px solid ${active ? "var(--ink)" : "var(--line)"}`,
                      fontWeight: active ? 600 : 500,
                      color: active ? "var(--ink)" : "var(--ink-muted)",
                    }}
                  >
                    {n.label}
                    {n.count != null && (
                      <span className="ml-1.5 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                        {n.count}
                      </span>
                    )}
                  </a>
                );
              })}
            </div>
          </div>

          {/* Coverage */}
          {coverageEntries.length > 0 && (
            <div
              className="rounded-[18px] border px-[18px] py-4"
              style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
            >
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
                Coverage
              </span>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {coverageEntries.map(([iso, n]) => (
                  <Chip key={iso} mono>
                    {regionName(iso)} × {n}
                  </Chip>
                ))}
              </div>
              {balanceText && (
                <p className="mt-2.5 text-[11.5px]" style={{ color: "var(--ink-faint)" }}>
                  {balanceText}
                </p>
              )}
              {gapText && (
                <p className="mt-1.5 text-[12px] font-medium" style={{ color: "var(--ink-muted)" }}>
                  ◉ {gapText}
                </p>
              )}
            </div>
          )}

          {/* Ask Parse — docked (real AskPanel, un-floated into the rail) */}
          <div
            className="overflow-hidden rounded-[18px] border"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-card)" }}
          >
            <div className="flex items-center gap-2 border-b px-4 py-3" style={{ borderColor: "var(--line)" }}>
              <span
                className="flex h-6 w-6 items-center justify-center rounded-full border"
                style={{ borderColor: "var(--line)" }}
              >
                <span className="spectrum-text text-[12px]" aria-hidden>
                  ◮
                </span>
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13.5px] font-semibold">
                  Ask Parse
                  <span
                    className="ml-1.5 rounded-full border px-[7px] py-px font-mono text-[9px] uppercase tracking-wide"
                    style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
                  >
                    AI
                  </span>
                </p>
                <p className="text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                  Answers from this story&apos;s {sourceCount} source{sourceCount === 1 ? "" : "s"} only
                </p>
              </div>
            </div>
            <AskPanel eventId={event.id} sourceCount={sourceCount} suggestedQuestions={questions} docked />
          </div>
        </aside>
      </div>

      {/* ── Pinned thumb zone (mobile): lens rail + Share ───── */}
      <div
        className="fixed inset-x-0 bottom-0 z-40 flex flex-col gap-2 border-t px-3.5 pt-2.5 backdrop-blur-md lg:hidden"
        style={{ borderColor: "var(--line)", background: "var(--glass)", paddingBottom: "calc(env(safe-area-inset-bottom) + 8px)" }}
      >
        <div className="hide-scroll flex gap-1.5 overflow-x-auto">
          {offered.map((slug) => {
            const m = lensMeta(slug);
            const selected = slug === lens;
            const locked = isLocked(slug);
            return (
              <button
                key={slug}
                onClick={() => pickLens(slug)}
                // The lock is carried only by a faint colour and an aria-hidden
                // glyph, so the accessible name was just "Markets" — identical to
                // an unlocked lens. The desktop tab says it via title=, but a
                // title is useless on touch, and this rail is the primary flip
                // surface on a phone.
                aria-label={locked ? `${m.short} lens — sign in to unlock, free` : undefined}
                className="flex min-h-[44px] flex-1 items-center justify-center gap-1 whitespace-nowrap rounded-full px-3 py-2.5 text-[13px] font-semibold"
                style={
                  selected
                    ? { background: m.bg, color: m.color, boxShadow: `inset 0 0 0 1.5px ${m.color}` }
                    : { border: "1px solid var(--line-strong)", background: "var(--bg-elevated)", color: locked ? "var(--ink-faint)" : "var(--ink-muted)" }
                }
              >
                {m.short}
                {locked && (
                  <svg aria-hidden width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                    <rect x="4" y="11" width="16" height="9" rx="2" />
                    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
        <div className="flex gap-2">
          <div className="flex-1">
            <ShareButton url={`/story/${event.id}`} title={event.title} fill />
          </div>
          <button
            onClick={() => setAskOpen(true)}
            className="flex h-11 flex-[1.4] items-center justify-center gap-1.5 rounded-full border text-[13.5px] font-semibold transition hover:opacity-80"
            style={{ borderColor: "var(--ink)", background: "var(--ink)", color: "var(--bg)" }}
          >
            <span className="spectrum-text text-[15px]" aria-hidden>◮</span>
            Ask
            <span className="whitespace-nowrap font-mono text-[10.5px] font-normal opacity-70">{sourceCount} sources</span>
          </button>
        </div>
      </div>

      {/* ── Ask chat — floats above the pinned lens rail when opened ── */}
      <div className="lg:hidden">
        <AskPanel
          eventId={event.id}
          sourceCount={sourceCount}
          suggestedQuestions={questions}
          open={askOpen}
          onOpenChange={setAskOpen}
          launcher={false}
        />
      </div>
    </div>
    </>
  );
}
