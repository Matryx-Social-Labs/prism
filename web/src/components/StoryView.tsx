"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchBrief, fetchQuestions, type EventDetail, type OutletRef, type TrendingStoryDetail } from "@/lib/api";
import { headlineByline } from "@/lib/headline";
import { useStateNames } from "@/lib/useStateName";
import { useRouter } from "next/navigation";

import { lensMeta, useLenses } from "@/lib/lenses";
import { ArrowDown, ArrowLeft, ArrowUp, Dash, Lock, Speech } from "@/components/icons";
import { useSession } from "@/lib/session";
import { loadProfile } from "@/lib/profile";
import { AskPanel } from "@/components/AskPanel";
import { Brand } from "@/components/Brand";
import { CoverageBar, CoverageLegend, MonogramStack, OutletIcon, coverageText, languageNames, languagesOf, publishers } from "@/components/Coverage";
import { EntityText } from "@/components/EntityText";
import { ShareButton } from "@/components/ShareButton";
import { StatusPill } from "@/components/StatusPill";
import { StoryRoute } from "@/components/StoryRoute";
import { RelatedRoutes } from "@/components/RelatedRoutes";
import { Said } from "@/components/Said";
import { SectionHead as Head } from "@/components/SectionHead";
import { SourceList, fallbackCode, indexSources } from "@/components/SourceList";
import { BriefPlayer } from "@/components/BriefPlayer";
import { FollowSignals } from "@/components/FollowSignals";
import { relativeTime } from "@/lib/dateline";
import { sectorGroup } from "@/lib/sectors";

/**
 * The story record (DESIGN.md § Record). Six sections in one order at every
 * width — The record · What changed · Who said what · Story (or the coverage
 * grouping under review) · Why it matters · Coverage — then Ask, subordinate
 * to the evidence. The header answers what happened, how current it is and
 * how well supported before anything else. The lens flip keeps its mechanics
 * (the locked flip, the gate, keys 1/2/3); its control is one segmented
 * switch, on the header at desktop widths and above the record text on the
 * phone. No publisher photograph anywhere on the page.
 */

function regionName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

const SOURCES_FOLD = 8;
const CHANGED_FOLD = 5;

/** Registered-source facts from the event's own report list (one per report). */
function outletsOf(event: EventDetail): OutletRef[] {
  return event.sources
    .filter((s) => s.code && s.origin)
    .map((s) => ({ slug: s.source_slug, publisher: s.publisher ?? s.source_slug, name: s.source_name, code: s.code!, origin: s.origin!, language: s.language ?? null, domain: s.domain ?? null }));
}

export function StoryView({ event }: { event: EventDetail }) {
  const cyber = event.projection?.cyber ?? null;
  const finance = event.projection?.finance ?? null;
  // ONE index for [n]: the report list and the citation under every quote read
  // the same map, so the two can never number one article differently.
  const sourceIndex = indexSources(event.sources);
  // `?? []` is load-bearing: the web and the API deploy from two pipelines and
  // /events is cached 60s, so a new page meets an old payload for a window.
  const claims = event.claims ?? [];
  const quoteCount = claims.reduce((n, sp) => n + sp.claims.length, 0);
  const outlets = outletsOf(event);
  const outletCount = outlets.length ? publishers(outlets).length : new Set(event.sources.map((s) => s.source_slug)).size;

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
  // Country codes resolve locally; a state code (IN-KA) needs the regions list.
  const regionLabels = useStateNames(event.regions).map((r) => (r.includes("-") ? r : regionName(r)));
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
  // reader sees the flip and the inline unlock prompt. (History of this guard:
  // git log -S readerPicked — two regressions, both about signed-out readers.)
  useEffect(() => {
    if (wasSignedIn.current && !session) readerPicked.current = false;
    wasSignedIn.current = Boolean(session);
    if (isLocked(lens) && !readerPicked.current) setLens("reader");
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
  // Loaded by StoryRoute from the story owner. Missing/older payloads fail
  // closed: they are related coverage, never verified chronology.
  const [routeStory, setRouteStory] = useState<TrendingStoryDetail | null>(null);
  const boundaryVerified = routeStory?.boundary_status === "verified";

  const sourceCount = event.sources.length;
  const single = sourceCount <= 1;
  const group = sectorGroup(event.sector);
  const reports = [...event.sources].sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""));

  // "On this story", in the order the sections appear. A nav that lists
  // sections in another order than they appear is a small lie the reader
  // notices on the second tap.
  const navItems: { id: string; label: string; count?: number }[] = [
    { id: "lens-brief", label: "The record" },
    ...(reports.length > 1 ? [{ id: "changed", label: "What changed", count: reports.length }] : []),
    // Only when there is something to jump to: 55% of stories have no attributed
    // quote, and a permanent "0" would advertise absence on every other page.
    ...(quoteCount > 0 ? [{ id: "said", label: "Who said what", count: quoteCount }] : []),
    ...(event.story_slug ? [{ id: "route", label: boundaryVerified ? "How it unfolded" : "Related reporting" }] : []),
    ...(event.impacts.length > 0 ? [{ id: "so-what", label: "Why it matters", count: event.impacts.length }] : []),
    { id: "sources", label: "Coverage", count: outletCount },
    { id: "ask", label: "Ask" },
  ];

  // Lightweight scroll-spy so the rail nav highlights the section in view.
  const [activeSection, setActiveSection] = useState("lens-brief");
  const [askOpen, setAskOpen] = useState(false);
  const [allSources, setAllSources] = useState(false);
  const [allReports, setAllReports] = useState(false);

  // Picking a lens must SHOW the result: on the phone the record text can be
  // off-screen, so the flip happens where nobody can see it and the tap reads
  // as a dead button. Keys never scroll ("layout never moves").
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
  // modifier. Zero-travel and repeatable — repeatability is what turns the flip
  // from a trick into the thing a reader shows a colleague.
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

  const lensControl = (
    <div className="seg" role="tablist" aria-label="Read it as">
      {offered.map((slug) => {
        const m = lensMeta(slug);
        const selected = slug === lens;
        const locked = isLocked(slug);
        return (
          <button
            key={slug}
            role="tab"
            aria-selected={selected}
            onClick={() => pickLens(slug)}
            aria-label={locked ? `${m.short} lens, sign in to unlock, free` : undefined}
            style={selected ? { color: m.color } : undefined}
          >
            {locked && <Lock className="opacity-60" />}
            {m.short}
          </button>
        );
      })}
    </div>
  );

  const namedIn = [...new Set([...regionLabels, ...event.entities.map((en) => en.name)])];
  const coverageLine = (
    <>
      {coverageEntries.length > 0 && (
        <span>
          {coverageEntries.length === 1 ? <>All filed from <b className="font-semibold" style={{ color: "var(--ink)" }}>{regionName(coverageEntries[0][0])}</b></> : <>Filed from {coverageEntries.map(([iso, n]) => `${regionName(iso)} ×${n}`).join(", ")}</>}
          {(event.coverage?.unknown ?? 0) > 0 && <> · {event.coverage!.unknown} of unknown origin</>}
        </span>
      )}
      {gapText && <span className="inline-flex items-center gap-2"><Dash /> {gapText}</span>}
      {event.coverage?.single_origin && <span className="font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>Single origin</span>}
    </>
  );

  return (
    <>
      {/* Phone back bar: the way back, the mark, Share. The thumb bar below
          carries Share and Ask; the tab bar is hidden on the record. */}
      <div className="glass sticky top-0 z-30 -mx-5 flex h-[52px] items-center justify-between border-b px-3 sm:-mx-8 sm:px-6 lg:hidden" style={{ borderColor: "var(--line)" }}>
        <Link href="/feed" scroll={false} className="btn btn-ghost btn-sm gap-1.5" aria-label="Back to today">
          <ArrowLeft /> Today
        </Link>
        <Brand size={22} label="Prism, today" />
        <span className="w-[76px]" aria-hidden />
      </div>

      <div className="mx-auto max-w-[var(--shell)] px-5 pb-[calc(var(--tabbar)+40px)] pt-4 sm:px-8 lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)_300px] lg:gap-x-10 lg:pb-20 lg:pt-6 xl:px-10">
        {/* ── On this story (desktop rail) ─────────────────────── */}
        <aside className="hidden lg:block lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="On this story">
          <p className="mb-2 text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>On this story</p>
          <ul>
            {navItems.map((n, i) => (
              <li key={n.id} className={i > 0 ? "border-t" : ""} style={i > 0 ? { borderColor: "var(--line)" } : undefined}>
                <a
                  href={`#${n.id}`}
                  className="flex items-center justify-between py-2.5 text-[14px] underline-offset-4 hover:underline"
                  style={{ color: activeSection === n.id ? "var(--accent)" : "var(--ink-2)", fontWeight: activeSection === n.id ? 600 : 500 }}
                  aria-current={activeSection === n.id ? "true" : undefined}
                >
                  <span>{n.label}</span>
                  {n.count != null && <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{n.count}</span>}
                </a>
              </li>
            ))}
          </ul>
        </aside>

        <div className="min-w-0">
          {/* ── The header ─────────────────────────────────────── */}
          <header className="border-b pb-5" style={{ borderColor: "var(--line)" }}>
            <div className="meta-line flex-wrap">
              {routeStory && event.story_slug && (
                <StatusPill status={boundaryVerified ? "verified" : "provisional"} title={boundaryVerified ? "Story boundary verified; developments below are in sequence." : "Grouping provisional; related reporting is shown without implying chronology."} />
              )}
              <span>Updated {relativeTime(event.last_updated_at)}</span>
              {group && (
                <>
                  <span className="dot" />
                  <span>{group.name}</span>
                </>
              )}
              {(cyber?.cve_ids ?? []).slice(0, 3).map((cve) => (
                <span key={cve} style={{ color: "var(--ink)" }}>{cve}</span>
              ))}
            </div>
            <h1 className="font-record mt-3 max-w-[22ch] text-[30px] font-medium leading-[1.12] text-balance sm:text-[38px]" style={{ letterSpacing: "-0.015em" }}>
              {event.title}
            </h1>
            <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{headlineByline(event)}</p>
            {event.summary && (
              <EntityText as="p" text={event.summary} entities={event.entities} claims={claims} className="mt-3 max-w-[62ch] text-[17px] leading-[1.55]" style={{ color: "var(--ink-2)", textWrap: "pretty" }} />
            )}
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <MonogramStack outlets={outlets} limit={5} />
              <span className="inline-flex min-w-0 items-center gap-2.5">
                <CoverageBar outlets={outlets} fallbackCount={sourceCount} size="lg" draw />
                <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>
                  {outlets.length ? coverageText(outlets) : `${outletCount} ${outletCount === 1 ? "outlet" : "outlets"}`} · {sourceCount} {sourceCount === 1 ? "report" : "reports"}
                  {outlets.length > 0 && ` · ${languageNames(languagesOf(outlets))}`}
                </span>
              </span>
              {single && <StatusPill status="provisional" label="One source so far" />}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="hidden lg:inline-flex"><ShareButton url={`/story/${event.id}`} title={event.title} /></span>
              <button type="button" onClick={() => setAskOpen(true)} className="btn btn-secondary hidden lg:inline-flex">
                <Speech /> Ask this story
              </button>
              <span className="flex-1" />
              {lensControl}
            </div>
          </header>

          <article className="min-w-0 lg:max-w-[var(--reading)]">
            {/* ── The record — the lens block, the product moment ─────
                Mechanics unchanged: the locked flip, the gate, the keys. */}
            <section id="lens-brief" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }}>
              <Head
                id="record-title"
                title="The record"
                hint={lens === "reader" ? `Written from the ${sourceCount} ${sourceCount === 1 ? "report" : "reports"} below. Nothing here is unsourced.` : `The same reports, read for ${meta.plain ?? meta.short.toLowerCase()}.`}
                right={
                  <span className="hidden items-center gap-2 font-mono text-[11px] lg:inline-flex" style={{ color: "var(--ink-3)" }} aria-hidden>
                    {offered.length > 1 && <>Press {offered.map((_, i) => i + 1).join(" · ")}</>}
                  </span>
                }
              />
              <div
                key={lens}
                className={`${flipped ? "flip-body" : ""} relative flex flex-col gap-[18px] overflow-hidden`}
              >
                {flipped && <span aria-hidden className="flip-scanline" style={{ background: meta.color }} />}
                {lens !== "reader" && !isLocked(lens) && (
                  <p className="lensdot" style={{ color: meta.color }}><i /> {meta.short} read</p>
                )}
                {/* Facts first — they are the record; the brief beneath is a reading of it. */}
                {lens === "cyber" && cyber && !isLocked(lens) && (
                  <div className="flex flex-col gap-3.5">
                    <div className="flex flex-wrap gap-2 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--lens-cyber)" }}>
                      {cvss.score != null && <span className="chip h-7 px-2.5" style={{ color: "inherit", background: "var(--lens-cyber-soft)", borderColor: "transparent" }}>CVSS {cvss.score.toFixed(1)}</span>}
                      {exploitation.kev_listed && <span className="chip h-7 px-2.5" style={{ color: "inherit", background: "var(--lens-cyber-soft)", borderColor: "transparent" }}>KEV listed</span>}
                      {exploitation.poc_public && <span className="chip h-7 px-2.5" style={{ color: "inherit", background: "var(--lens-cyber-soft)", borderColor: "transparent" }}>PoC public</span>}
                      {cvss.vector && <span className="normal-case" style={{ color: "var(--ink-3)" }}>{cvss.vector}</span>}
                    </div>
                    {(cyber.affected ?? []).length > 0 && (
                      <div>
                        <h3 className="mb-1.5 text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
                          Affected products
                        </h3>
                        <ul className="text-[14px] leading-[1.7]" style={{ color: "var(--ink-2)" }}>
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
                      <div className="rounded-[var(--r-md)] px-4 py-3 text-[14px] leading-[1.6]" style={{ background: "var(--lens-cyber-soft)", color: "var(--ink)" }}>
                        <strong>Required action:</strong> {cyber.remediation.action}
                      </div>
                    )}
                    {(cyber.control_mapping ?? []).length > 0 && (
                      <div className="overflow-x-auto">
                        <table className="w-full border-collapse text-left text-[13px]">
                          <thead>
                            <tr className="text-[11px] uppercase tracking-wide" style={{ color: "var(--ink-3)" }}>
                              <th className="border-b py-1.5 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>Framework</th>
                              <th className="border-b py-1.5 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>Control</th>
                              <th className="border-b py-1.5 font-semibold" style={{ borderColor: "var(--line)" }}>Why it matters here</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(cyber.control_mapping ?? []).map((cm, i) => (
                              <tr key={i}>
                                <td className="border-b py-2 pr-3.5 font-mono text-xs" style={{ borderColor: "var(--line)" }}>{cm.framework}</td>
                                <td className="border-b py-2 pr-3.5 font-semibold" style={{ borderColor: "var(--line)" }}>{cm.control}</td>
                                <td className="border-b py-2" style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}>{cm.relevance}</td>
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
                    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--lens-markets)" }}>
                      {(finance.tickers ?? []).map((t) => <span key={t} className="chip h-7 px-2.5" style={{ color: "inherit", background: "var(--lens-markets-soft)", borderColor: "transparent" }}>{t}</span>)}
                      {finance.catalyst && <span>catalyst · {finance.catalyst.replaceAll("_", " ")}</span>}
                      {finance.price_impact?.direction && (
                        <span className="inline-flex items-center gap-1">
                          · price read
                          <span className="inline-flex" aria-label={finance.price_impact.direction}>
                            {finance.price_impact.direction === "up" ? <ArrowUp /> : finance.price_impact.direction === "down" ? <ArrowDown /> : <Dash />}
                          </span>
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
                  // reader needs a different next step for each. `null` means no
                  // quota row was ever granted, which is not "0 left".
                  <div className="card flex flex-col items-start gap-3">
                    <p className="text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
                      You&apos;ve used your free{" "}
                      <span className="font-semibold" style={{ color: meta.color }}>{meta.short}</span>{" "}
                      reads{typeof gateState.remaining === "number" ? `, ${gateState.remaining} left` : ""}. The reader view of this story stays open.
                    </p>
                    <button onClick={() => setLens("reader")} className="btn btn-secondary">Back to the reader view</button>
                  </div>
                ) : isLocked(lens) || gateState?.lens === lens ? (
                  <div className="card flex flex-col items-start gap-3">
                    <p className="text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
                      Read this story through the{" "}
                      <span className="font-semibold" style={{ color: meta.color }}>{meta.short} lens</span>
                      : {meta.plain ?? meta.tagline}. Free with an account.
                    </p>
                    <button onClick={() => router.push(`/signin?next=/story/${event.id}`)} className="btn btn-primary">Sign in to unlock</button>
                  </div>
                ) : briefLoading && !brief ? (
                  <div aria-label="Generating lens brief">
                    <div className="pulse-skel h-[14px] rounded" style={{ background: "var(--sunken)" }} />
                    <div className="pulse-skel mt-2.5 h-[14px] w-[92%] rounded" style={{ background: "var(--sunken)" }} />
                    <div className="pulse-skel mt-2.5 h-[14px] w-[78%] rounded" style={{ background: "var(--sunken)" }} />
                    <p className="mt-3 text-[13px]" style={{ color: "var(--ink-3)" }}>Writing the {meta.short} read of this story…</p>
                  </div>
                ) : brief ? (
                  <BriefPlayer brief={brief} points={lensPoints} meta={meta} pointsHeading={pointsHeading} entities={event.entities} claims={claims} />
                ) : (
                  <p className="text-[14px]" style={{ color: "var(--ink-3)" }}>No {meta.short} read of this story yet.</p>
                )}
              </div>
            </section>

            {/* ── What changed: every report, newest first ─────────── */}
            {reports.length > 1 && (
              <section id="changed" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="changed-title">
                <Head id="changed-title" title="What changed" count={reports.length} hint="Every report on this story, newest first. Times are when each outlet published." />
                <ol className="relative">
                  <span aria-hidden className="absolute bottom-2 left-[5px] top-2 w-px" style={{ background: "var(--line-strong)" }} />
                  {(allReports ? reports : reports.slice(0, CHANGED_FOLD)).map((s, i) => (
                    <li key={s.article_id ?? i} className="relative pb-4 pl-6 last:pb-0">
                      <span
                        aria-hidden
                        className="absolute left-0 top-[7px] h-[11px] w-[11px] rounded-full border-2"
                        style={i === 0 ? { background: "var(--accent)", borderColor: "var(--accent)", boxShadow: "0 0 0 4px var(--accent-soft)" } : { background: "var(--surface)", borderColor: "var(--ink)" }}
                      />
                      <p className="flex items-center gap-2 text-[12.5px]" style={{ color: "var(--ink-3)" }}>
                        <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={20} />
                        <span className="font-semibold" style={{ color: "var(--ink-2)" }}>{s.source_name}</span>
                        <span className="font-mono text-[11px]">{s.published_at ? relativeTime(s.published_at) : "time unknown"}</span>
                        {sourceIndex.get(s.article_id) != null && <span className="font-mono text-[11px]">[{sourceIndex.get(s.article_id)}]</span>}
                      </p>
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-record mt-0.5 block text-[17px] font-medium leading-[1.35] underline-offset-4 hover:underline">{s.title}</a>
                      ) : (
                        <p className="font-record mt-0.5 text-[17px] font-medium leading-[1.35]">{s.title}</p>
                      )}
                    </li>
                  ))}
                </ol>
                {!allReports && reports.length > CHANGED_FOLD && (
                  <button type="button" onClick={() => setAllReports(true)} className="btn btn-secondary btn-sm mt-4">
                    Show all {reports.length}
                  </button>
                )}
              </section>
            )}

            {/* ── Who said what ─────────────────────────────────── */}
            {claims.length > 0 && (
              <section id="said" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="said-title">
                <Head
                  id="said-title"
                  title="Who said what"
                  count={quoteCount}
                  hint="Only words found exactly in the article are shown, attributed and linked to the line they came from."
                />
                <Said claims={claims} sourceIndex={sourceIndex} />
              </section>
            )}

            {/* ── The route: the story this event belongs to ───────── */}
            {event.story_slug && (
              <section id="route" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="route-title">
                <Head
                  id="route-title"
                  title={boundaryVerified ? "How this story unfolded" : "Related reporting"}
                  hint={boundaryVerified
                    ? "Every development in this story, counted: what came first, what followed, what branched off."
                    : "Grouped by subject or cast while the story boundary is under human review. No chronology is implied."}
                />
                <StoryRoute slug={event.story_slug} currentId={event.id} onLoad={setRouteStory} />
              </section>
            )}

            {/* ── Why it matters ────────────────────────────────── */}
            {event.impacts.length > 0 && (
              <section id="so-what" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="sowhat-title">
                <Head id="sowhat-title" title="Why it matters" count={event.impacts.length} hint="Who is affected first and what likely follows, with a direction and a horizon. Extracted from the reports, never invented." />
                <ul className="flex flex-col gap-2">
                  {event.impacts.map((imp) => (
                    <li key={imp.id} className={`grid grid-cols-[18px_1fr] gap-x-2.5 text-[15px] leading-[1.55] ${imp.parent_impact_id ? "ml-7" : ""}`}>
                      <span className="mt-[5px]" style={{ color: "var(--ink-3)" }} aria-label={imp.direction ?? "direction unknown"}>
                        {imp.direction === "negative" ? <ArrowDown /> : imp.direction === "positive" ? <ArrowUp /> : <Dash />}
                      </span>
                      <span>
                        <b className="font-semibold">{imp.entity_name ?? "Affected party"}</b>{" "}
                        <span style={{ color: "var(--ink-2)" }}>{imp.effect.replaceAll("_", " ")}</span>
                        {imp.horizon && <span className="ml-1.5 font-mono text-[11px] uppercase tracking-[0.03em]" style={{ color: "var(--ink-3)" }}>· {imp.horizon}</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* ── Coverage: the bar, the legend, who is named, the reports ── */}
            <section id="sources" className="scroll-mt-24 border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="sources-title">
              <Head id="sources-title" title="Coverage" count={outletCount} />
              {outlets.length > 0 && (
                <div className="mb-4 flex flex-col gap-2.5">
                  <span className="inline-flex items-center gap-3">
                    <CoverageBar outlets={outlets} size="lg" width={240} />
                    <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{sourceCount} {sourceCount === 1 ? "report" : "reports"}</span>
                  </span>
                  <CoverageLegend outlets={outlets} />
                </div>
              )}
              {(coverageEntries.length > 0 || namedIn.length > 0) && (
                <div className="mb-4 flex flex-col gap-2 text-[14px]" style={{ color: "var(--ink-2)" }}>
                  <p className="flex flex-wrap gap-x-4 gap-y-1">{coverageLine}</p>
                  {namedIn.length > 0 && (
                    <p>
                      <span className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Named</span>{" "}
                      {namedIn.join(" · ")}
                    </p>
                  )}
                </div>
              )}
              <div className="lg:hidden">
                <SourceList sources={allSources ? event.sources : event.sources.slice(0, SOURCES_FOLD)} sourceIndex={sourceIndex} />
                {!allSources && event.sources.length > SOURCES_FOLD && (
                  <button type="button" onClick={() => setAllSources(true)} className="btn btn-secondary btn-sm mt-3">
                    All {event.sources.length} reports
                  </button>
                )}
              </div>
              <p className="hidden text-[13.5px] lg:block" style={{ color: "var(--ink-3)" }}>The {sourceCount} {sourceCount === 1 ? "report is" : "reports are"} listed beside the record.</p>
            </section>

            {/* ── Related stories: different stories that touch this one ── */}
            {(routeStory?.related?.length ?? 0) > 0 && (
              <section className="border-b py-6" style={{ borderColor: "var(--line)" }} aria-labelledby="related-title">
                <Head id="related-title" title="Related stories" hint="Different stories that touch this one, by the cast they share or a causal note across the boundary. Not part of this story." />
                <RelatedRoutes related={routeStory!.related} />
              </section>
            )}

            {/* ── Ask, subordinate to the evidence ──────────────── */}
            <section id="ask" className="scroll-mt-24 py-6" aria-labelledby="ask-title">
              <Head id="ask-title" title="Ask this story" hint="Answers cite the reports above, or say they can't." />
              <div className="card">
                <button
                  type="button"
                  onClick={() => setAskOpen(true)}
                  className="flex h-11 w-full items-center gap-2.5 rounded-full border px-4 text-left text-[15px]"
                  style={{ borderColor: "var(--line-strong)", color: "var(--ink-3)" }}
                  aria-label="Ask about this story"
                >
                  <Speech /> Ask about this story…
                </button>
                {questions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {questions.slice(0, 3).map((q) => (
                      <button key={q} type="button" onClick={() => setAskOpen(true)} className="chip h-8 whitespace-normal text-left text-[13px]">{q}</button>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <p className="flex justify-between gap-4 border-t pt-4 text-[13.5px] font-medium" style={{ borderColor: "var(--line)" }}>
              <Link href="/feed" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>← Today&rsquo;s record</Link>
              {event.story_slug && (
                <Link href={`/trending/${event.story_slug}`} className="underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>{boundaryVerified ? "The whole story" : "Open the grouping"} →</Link>
              )}
            </p>
          </article>
        </div>

        {/* ── Beside the record (desktop): the reports, who is named ── */}
        <aside className="hidden lg:flex lg:flex-col lg:gap-4 lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="Evidence">
          <div className="card max-h-[calc(100dvh-140px)] overflow-y-auto">
            <h3 className="card-h">Reports · {sourceCount}</h3>
            <SourceList sources={event.sources} sourceIndex={sourceIndex} compact />
          </div>
          {namedIn.length > 0 && (
            <div className="card">
              <h3 className="card-h">Named in the reports</h3>
              <div className="flex flex-wrap gap-1.5">
                {namedIn.slice(0, 12).map((n) => (
                  <Link key={n} href={`/search?q=${encodeURIComponent(n)}`} className="chip h-[30px] px-2.5 text-[13px]">{n}</Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* ── Thumb zone (phone): Share and Ask, above the safe area ── */}
      <div
        className="glass fixed inset-x-0 bottom-0 z-40 flex gap-2 border-t px-4 pt-2.5 lg:hidden"
        style={{ borderColor: "var(--line)", paddingBottom: "calc(env(safe-area-inset-bottom) + 10px)" }}
      >
        <button
          type="button"
          onClick={() => setAskOpen(true)}
          className="btn btn-primary flex-[1.4]"
        >
          <Speech /> Ask
          <span className="font-mono text-[11px] font-normal opacity-80">{sourceCount} {sourceCount === 1 ? "report" : "reports"}</span>
        </button>
        <div className="flex-1">
          <ShareButton url={`/story/${event.id}`} title={event.title} fill />
        </div>
      </div>

      {/* ── Ask — one panel at every width. */}
      <AskPanel
        eventId={event.id}
        sourceCount={sourceCount}
        suggestedQuestions={questions}
        open={askOpen}
        onOpenChange={setAskOpen}
        launcher={false}
      />
    </>
  );
}
