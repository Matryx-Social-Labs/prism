"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchBrief, fetchQuestions, type EventDetail } from "@/lib/api";
import { ticketFacts } from "@/lib/ticket";
import { headlineByline } from "@/lib/headline";
import { useRouter } from "next/navigation";

import { lensMeta, useLenses } from "@/lib/lenses";
import { ArrowDown, ArrowUp, Dash } from "@/components/icons";
import { useSession } from "@/lib/session";
import { loadProfile } from "@/lib/profile";
import { AskPanel } from "@/components/AskPanel";
import { ShareButton } from "@/components/ShareButton";
import { StoryDesktop } from "@/components/StoryDesktop";
import { StoryRoute } from "@/components/StoryRoute";
import { Said } from "@/components/Said";
import { SectionHead as Head } from "@/components/SectionHead";
import { SourceList, indexSources } from "@/components/SourceList";
import { BriefPlayer } from "@/components/BriefPlayer";
import { FollowSignals } from "@/components/FollowSignals";

/**
 * The story page: the ticket.
 *
 * One record, read three ways. The header strip states what is true whichever
 * lens is reading — code, sources, origins, the stamp — then the headline in
 * the reading voice, then the lens block (mechanics untouched: the flip, the
 * gate, the keys), then the evidence: the route the story took, who said what,
 * and which outlets. Section heads are in the structural voice; nothing here
 * is a card; the only colour is a lens speaking. The LLM "Perspectives" cards
 * and "What to expect" are retired (founder decision D4, 2026-09-15): the
 * route and the passenger list ARE the perspectives, and they are counted and
 * verbatim.
 */

function regionName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

const MONO_LABEL = "font-mono text-[11px] uppercase tracking-[0.06em]";

export function StoryView({ event }: { event: EventDetail }) {
  const cyber = event.projection?.cyber ?? null;
  const finance = event.projection?.finance ?? null;
  // ONE index for [n]: the Sources list and the citation under every quote read
  // the same map, so the two can never number one article differently.
  const sourceIndex = indexSources(event.sources);
  // `?? []` is load-bearing: the web and the API deploy from two pipelines and
  // /events is cached 60s, so a new page meets an old payload for a window.
  const claims = event.claims ?? [];
  const quoteCount = claims.reduce((n, sp) => n + sp.claims.length, 0);

  const [lens, setLens] = useState("reader");
  const [briefs, setBriefs] = useState<Record<string, string>>(event.lens_briefs ?? {});
  const [flipped, setFlipped] = useState(false);
  const [points, setPoints] = useState<Record<string, string[]>>(event.lens_points ?? {});
  const [briefLoading, setBriefLoading] = useState(false);
  // Which paywall wall this lens hit, if any. Null means the lens is readable.
  const [gateState, setGateState] = useState<
    { lens: string; kind: "signin" } | { lens: string; kind: "no_samples"; remaining: number | null } | null
  >(null);
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
      fetchQuestions(event.id, lens, session?.token).then((qs) => !cancelled && setQuestions(qs));
      if (!briefs[lens]) {
        setBriefLoading(true);
        fetchBrief(event.id, lens, session?.token).then((res) => {
          if (cancelled) return;
          setBriefLoading(false);
          // Each paywall outcome gets its own affordance. Collapsing them into
          // "no brief" is what made the first version show an empty panel to a
          // reader who just needed to sign in.
          if (res.state === "signin_required") {
            setGateState({ lens, kind: "signin" });
            return;
          }
          if (res.state === "no_samples") {
            setGateState({ lens, kind: "no_samples", remaining: res.remaining });
            return;
          }
          if (res.state === "unavailable") return;
          setGateState(null);
          if (res.brief) setBriefs((prev) => ({ ...prev, [lens]: res.brief! }));
          if (res.points?.length) setPoints((prev) => ({ ...prev, [lens]: res.points! }));
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
  const single = sourceCount <= 1;
  const facts = ticketFacts(event);
  const navItems: { id: string; label: string; count?: number }[] = [
    { id: "lens-brief", label: "Lens" },
    ...(event.story_slug ? [{ id: "route", label: "Route" }] : []),
    // Only when there is something to jump to: 55% of stories have no attributed
    // quote, and a permanent "Said 0" would advertise absence on every other page.
    ...(quoteCount > 0 ? [{ id: "said", label: "Said", count: quoteCount }] : []),
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
  // modifier (Prism Desktop.dc.html — the brief header prints "PRESS 1 · 2 · 3").
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
  }, [event.id]);

  return (
    <>
      {/* Desktop is its own composition: the mono rail re-inks with the lens
          and all the openings sit on the board at once. State stays here so
          there is one lens machine, not two. */}
      <StoryDesktop
        event={event}
        lens={lens}
        offered={offered}
        briefs={briefs}
        brief={brief}
        facts={facts}
        lensName={(slug) => lensMeta(slug).short}
        isLocked={isLocked}
        onPick={(slug) => pickLens(slug, false)}
      />

    <div className="mx-auto max-w-[1240px] px-5 pt-5 sm:px-8 lg:hidden">
      <Link href="/" scroll={false} className={`${MONO_LABEL} mb-4 block`} style={{ color: "var(--ink-muted)" }}>
        ← Today&rsquo;s chart
      </Link>

      {/* min-w-0: without it a grid item's default min-width:auto lets the
          inner horizontal scrollers (lens-tab strip, mobile anchor nav, cyber
          table) stretch the column past the viewport — the mobile right-bleed. */}
      <article className="min-w-0">
      {/* ── The header strip ───────────────────────────────────
          What is true whichever lens is reading: code · sources · origins ·
          stamp. A single-source story sits on a dashed rule — state is line
          form, never hue — and the strip says so before the headline does. */}
      <header>
        <div
          className={`${single ? "rule-single" : "rule-live"} ticket-strip flex flex-wrap items-baseline gap-x-2.5 gap-y-1 pt-3 ${MONO_LABEL}`}
          style={{ color: "var(--ink-muted)" }}
          aria-label="Story facts"
        >
          {facts.map((f, i) => (
            <span key={i} style={i === 0 ? { color: "var(--ink)" } : undefined}>
              {f}
            </span>
          ))}
          {(cyber?.cve_ids ?? []).slice(0, 3).map((cve) => (
            <span key={cve} style={{ color: "var(--ink)" }}>{cve}</span>
          ))}
          {(finance?.tickers ?? []).slice(0, 4).map((t) => (
            <span key={t} style={{ color: "var(--ink)" }}>{t}</span>
          ))}
        </div>
        {gapText && (
          <p className="mt-2 text-[12.5px]" style={{ color: "var(--ink-muted)" }}>
            {gapText}
          </p>
        )}

        <h1 className="mt-4 text-[30px] font-medium leading-[1.15] text-balance sm:text-[34px]">
          {event.title}
        </h1>
        <p className="mt-2.5 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>{headlineByline(event)}</p>
        {event.summary && (
          <p className="mt-3 text-[15.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            {event.summary}
          </p>
        )}

        {event.image_url && (
          <div className="relative mt-5 aspect-video overflow-hidden" style={{ background: "var(--bg-sunken)" }}>
            <Image
              src={event.image_url}
              alt=""
              fill
              priority
              sizes="(max-width: 780px) 100vw, 740px"
              className="object-cover"
              style={{ filter: "grayscale(0.15) contrast(1.02)" }}
              onError={(e) => {
                (e.currentTarget.parentElement as HTMLElement).style.display = "none";
              }}
            />
          </div>
        )}

        {(event.entities.length > 0 || event.regions.length > 0) && (
          <p className="mt-4 text-[13px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            <span className={MONO_LABEL} style={{ color: "var(--ink-faint)" }}>Affected</span>{" "}
            {[...event.regions.map(regionName), ...event.entities.map((en) => en.name)].join(" · ")}
          </p>
        )}
      </header>

      {/* ── On this story — the mobile section nav, sticky, codes underlined ── */}
      <nav
        className={`hide-scroll sticky top-0 z-20 -mx-5 mt-5 flex gap-4 overflow-x-auto border-b px-5 sm:-mx-8 sm:px-8 lg:hidden ${MONO_LABEL}`}
        style={{ borderColor: "var(--line)", background: "var(--bg)" }}
        aria-label="On this story"
      >
        {navItems.map((n) => (
          <a
            key={n.id}
            href={`#${n.id}`}
            className="flex h-11 flex-none items-end gap-1 border-b-2 pb-2 pt-3 leading-none"
            style={{
              borderColor: activeSection === n.id ? "var(--ink)" : "transparent",
              color: activeSection === n.id ? "var(--ink)" : "var(--ink-muted)",
            }}
          >
            {n.label}
            {n.count != null && <span style={{ color: "var(--ink-faint)" }}>{n.count}</span>}
          </a>
        ))}
      </nav>

      {/* ── The lens block — the product moment ─────────────────
          Mechanics unchanged: tabs, the locked flip, the gate, the keys. The
          container is a rule-bounded block, not a card. */}
      <section id="lens-brief" className="rule-live mt-8 scroll-mt-24 overflow-hidden">
        <div className="hidden border-b lg:block" style={{ borderColor: "var(--line)" }}>
          <div className="flex items-center gap-1.5 py-3" role="tablist" aria-label="Read this story through a lens">
            <span className={`${MONO_LABEL} mr-1`} style={{ color: "var(--ink-faint)" }}>
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
                  title={locked ? `Sign in to read the ${m.short} lens: ${m.plain ?? m.tagline} (free)` : undefined}
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
              <span className={`${MONO_LABEL} ml-auto pl-4`} style={{ color: "var(--ink-faint)" }} aria-hidden>
                Press {offered.map((_, i) => i + 1).join(" · ")}
              </span>
            )}
          </div>
        </div>

        <div
          key={lens}
          className={`${flipped ? "flip-body" : ""} relative flex flex-col gap-[18px] overflow-hidden py-5`}
        >
          {flipped && <span aria-hidden className="flip-scanline" style={{ background: meta.color }} />}
          {/* Facts first — they are the record; the brief beneath is a reading of it. */}
          {lens === "cyber" && cyber && !isLocked(lens) && (
            <div className="flex flex-col gap-3.5">
              {/* The lens's facts as codes on one line, in the lens's own hue —
                  colour because a lens is speaking, mono because they are read
                  off the record. */}
              <div className={`${MONO_LABEL} flex flex-wrap gap-x-3 gap-y-1`} style={{ color: "var(--lens-cyber)" }}>
                {cvss.score != null && <span>CVSS {cvss.score.toFixed(1)}</span>}
                {exploitation.kev_listed && <span>KEV listed</span>}
                {exploitation.poc_public && <span>PoC public</span>}
                {cvss.vector && <span className="normal-case">{cvss.vector}</span>}
              </div>
              {(cyber.affected ?? []).length > 0 && (
                <div>
                  <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
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
                  className="border-y px-0 py-3 text-[13.5px] leading-[1.6]"
                  style={{ borderColor: "var(--lens-cyber)", color: "var(--ink)" }}
                >
                  <strong>Required action:</strong> {cyber.remediation.action}
                </div>
              )}
              {(cyber.control_mapping ?? []).length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px]">
                    <thead>
                      <tr className="text-[11px] uppercase tracking-wide" style={{ color: "var(--ink-faint)" }}>
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
              {/* The lens's facts as codes on one line, in the lens's own hue —
                  colour because a lens is speaking, mono because they are read
                  off the record. */}
              <div className={`${MONO_LABEL} flex flex-wrap gap-x-4 gap-y-1`} style={{ color: "var(--lens-finance)" }}>
                {(finance.tickers ?? []).length > 0 && <span>Tickers</span>}
                {(finance.tickers ?? []).map((t) => <span key={t} className="border-b" style={{ borderColor: "var(--lens-finance)" }}>{t}</span>)}
                {finance.catalyst && <span>· catalyst · {finance.catalyst.replaceAll("_", " ")}</span>}
                {finance.price_impact?.direction && (
                  <span>
                    · price read ·{" "}
                    <span className="inline-flex translate-y-[1px]" aria-label={finance.price_impact.direction}>
                      {finance.price_impact.direction === "up" ? <ArrowUp /> : finance.price_impact.direction === "down" ? <ArrowDown /> : <Dash />}
                    </span>{" "}
                    {finance.price_impact.magnitude ?? ""}
                    {finance.price_impact.confidence != null && ` (${Math.round(finance.price_impact.confidence * 100)}% conf.)`}
                  </span>
                )}
              </div>
              <FollowSignals tickers={finance.tickers ?? []} sector={finance.sector ?? null} />
            </div>
          )}
          {gateState?.lens === lens && gateState.kind === "no_samples" ? (
            // OUT OF SAMPLES is a different wall from NOT SIGNED IN, and the
            // reader needs a different next step for each. The server sends the
            // remaining count; `null` means no quota row was ever granted, which
            // is not the same as having spent everything, so it is not shown as
            // "0 left".
            <div className="flex flex-col items-start gap-3">
              <p className="text-[14.5px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
                You&apos;ve used your free{" "}
                <span className="font-semibold" style={{ color: meta.color }}>
                  {meta.short}
                </span>{" "}
                reads
                {typeof gateState.remaining === "number"
                  ? `, ${gateState.remaining} left`
                  : ""}
                . The reader view of this story stays open.
              </p>
              <button
                onClick={() => setLens("reader")}
                className="rounded-full border px-4 py-2 text-[13px] font-semibold"
                style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
              >
                Back to the reader view
              </button>
            </div>
          ) : isLocked(lens) || gateState?.lens === lens ? (
            <div className="flex flex-col items-start gap-3">
              <p className="text-[14.5px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
                Read this story through the{" "}
                <span className="font-semibold" style={{ color: meta.color }}>
                  {meta.short} lens
                </span>{" "}
: {meta.plain ?? meta.tagline}. Free with an account.
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

        </div>
      </section>

      </article>

      {/* ── Pinned thumb zone (mobile): lens rail + Share/Ask ───── */}
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
                aria-label={locked ? `${m.short} lens, sign in to unlock, free` : undefined}
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
            Ask
            <span className="whitespace-nowrap font-mono text-[11px] font-normal opacity-70">{sourceCount} sources</span>
          </button>
        </div>
      </div>
    </div>

      {/* ── Ask — one floating panel at every width: the launcher pill
          bottom-right from 1024px, the thumb-zone button opens the same one
          on a phone. */}
      <AskPanel
        eventId={event.id}
        sourceCount={sourceCount}
        suggestedQuestions={questions}
        open={askOpen}
        onOpenChange={setAskOpen}
      />

      {/* ── The evidence layer, shared by both trees ──────────────
          Rendered once at every width. On desktop it aligns to the reading
          column (104px rail + 32px gap = 136px) and holds the 604px measure,
          because extra width goes to simultaneity, never to longer lines. */}
      <div className="mx-auto max-w-[1240px] px-5 pb-[164px] sm:px-8 lg:w-[1376px] lg:max-w-none lg:px-0 lg:pb-20">
        <div className="lg:ml-[136px] lg:max-w-[604px]">
      {/* ── The route ───────────────────────────────────────────
          The spine of the story this event belongs to, fetched from the owner
          of the arc. Only when the ticket carries a slug. */}
      {event.story_slug && (
        <section id="route" className="mt-10 scroll-mt-24" aria-labelledby="route-title">
          <Head id="route-title" title="The route" hint="Every development in this story, counted, with the branches and satellites the partitioner recorded." />
          <StoryRoute slug={event.story_slug} currentId={event.id} />
        </section>
      )}

      {/* ── So what ─────────────────────────────────────────
          Who is affected first and what likely follows, extracted from the
          reports; a second-order effect indents under its cause. Direction is
          an arrow in ink, never a hue, and the horizon prints in mono. */}
      {event.impacts.length > 0 && (
        <section id="so-what" className="mt-10 scroll-mt-24" aria-labelledby="sowhat-title">
          <Head id="sowhat-title" title="So what" count={event.impacts.length} hint="Who is affected first and what likely follows, with a direction and a horizon. Extracted from the reports, never invented." />
          <ul>
            {event.impacts.map((imp) => (
              <li key={imp.id} className={`rule-live grid grid-cols-[18px_1fr] gap-x-2.5 py-2.5 text-[14.5px] leading-[1.55] ${imp.parent_impact_id ? "ml-7" : ""}`}>
                <span className="mt-[5px]" style={{ color: "var(--ink-faint)" }} aria-label={imp.direction ?? "direction unknown"}>
                  {imp.direction === "negative" ? <ArrowDown /> : imp.direction === "positive" ? <ArrowUp /> : <Dash />}
                </span>
                <span>
                  <b className="font-semibold">{imp.entity_name ?? "Affected party"}</b>{" "}
                  <span style={{ color: "var(--ink-muted)" }}>{imp.effect.replaceAll("_", " ")}</span>
                  {imp.horizon && <span className={`${MONO_LABEL} ml-1.5`} style={{ color: "var(--ink-faint)" }}>· {imp.horizon}</span>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── What was said ────────────────────────────────────
          Rules and type, neutral ink. The quote and the speaker are the body
          voice; only the provenance line ([n] · outlet · date) is mono. Nothing
          here is lens-coloured and nothing here is unverified: every quote was
          checked against its article at write time, and the model's stance
          never reaches the payload. Rendered only when there is something to
          say — the section appearing is the signal. */}
      {claims.length > 0 && (
        <section id="said" className="mt-10 scroll-mt-24" aria-labelledby="said-title">
          <Head
            id="said-title"
            title="What was said"
            count={quoteCount}
            hint="Attributed, verbatim. Every quote is checked against the article it came from. One that does not match is not shown."
          />
          <Said claims={claims} sourceIndex={sourceIndex} />
        </section>
      )}

      {/* ── Coverage ────────────────────────────────────────
          Where the reports were filed from, counted; the reader's own state
          when it is absent; single origin called out in mono. All three are
          facts of the record, so an empty coverage prints nothing. */}
      {coverageEntries.length > 0 && (
        <section id="coverage" className="mt-10 scroll-mt-24" aria-labelledby="coverage-title">
          <Head id="coverage-title" title="Coverage" />
          <div className="rule-live flex flex-wrap gap-x-6 gap-y-2 py-2.5 text-[14.5px]">
            <span>
              {sourceCount} {sourceCount === 1 ? "report" : "reports"},{" "}
              {coverageEntries.length === 1 ? <>all filed from <b className="font-semibold">{regionName(coverageEntries[0][0])}</b></> : <>filed from {coverageEntries.map(([iso, n]) => `${regionName(iso)} ×${n}`).join(", ")}</>}
              {(event.coverage?.unknown ?? 0) > 0 && <span style={{ color: "var(--ink-muted)" }}> · {event.coverage!.unknown} of unknown origin</span>}
            </span>
            {gapText && <span className="inline-flex items-center gap-2"><Dash /> {gapText}</span>}
            {event.coverage?.single_origin && <span className={MONO_LABEL} style={{ color: "var(--ink-faint)" }}>Single origin</span>}
          </div>
        </section>
      )}

      {/* ── Sources — the coaches ─────────────────────────────
          [n] outlet · headline · stance. The [n] is the same index the quotes
          cite, so the two can never number one article differently. */}
      <section id="sources" className="mt-10 scroll-mt-24" aria-labelledby="sources-title">
        <Head id="sources-title" title="Sources" count={event.sources.length} />
        <SourceList sources={event.sources} sourceIndex={sourceIndex} />
      </section>
        </div>
      </div>
    </>
  );
}
