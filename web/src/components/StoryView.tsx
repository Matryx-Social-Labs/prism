"use client";

import { Ago } from "@/components/Ago";
import Link from "next/link";
import { track } from "@/lib/analytics";
import { cameFromInside } from "@/lib/nav";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchBrief, fetchQuestions, type EventDetail, type OutletRef, type TrendingStoryDetail } from "@/lib/api";
import { headlineByline } from "@/lib/headline";
import { useStateNames } from "@/lib/useStateName";
import { useRouter } from "next/navigation";

import { lensMeta, useLenses } from "@/lib/lenses";
import { ArrowDown, ArrowLeft, ArrowUp, Dash } from "@/components/icons";
import { useSession } from "@/lib/session";
import { loadProfile } from "@/lib/profile";
import { AskPanel } from "@/components/AskPanel";
import { AskBar } from "@/components/AskBar";
import { AskContext, type AskOpen } from "@/components/AskContext";
import { SelectionAsk } from "@/components/SelectionAsk";
import { CoverageBar, CoverageLegend, MonogramStack, coverageText, languageNames, languagesOf, publishers } from "@/components/Coverage";
import { monitoredText } from "@/lib/coverage";
import { EntityText } from "@/components/EntityText";
import { ShareButton } from "@/components/ShareButton";
import { StatusPill } from "@/components/StatusPill";
import { ReportProblem } from "@/components/ReportProblem";
import { RecordHistory } from "@/components/RecordHistory";
import { StoryRoute } from "@/components/StoryRoute";
import { RelatedRoutes } from "@/components/RelatedRoutes";
import { Said } from "@/components/Said";
import { Clips } from "@/components/Clips";
import { X_POSTS, XPosts } from "@/components/XPosts";
import { SectionHead as Head } from "@/components/SectionHead";
import { SourceList, indexSources } from "@/components/SourceList";
import { PhotoDeck } from "@/components/PhotoDeck";
import { Rail } from "@/components/Rail";
import { Reveal } from "@/components/Reveal";
import { BriefText, ListenBox, useNarration } from "@/components/BriefPlayer";
import { FollowSignals } from "@/components/FollowSignals";
import { ChangeTimeline } from "@/components/story/ChangeTimeline";
import { Impacts } from "@/components/story/Impacts";
import { LensBrief, LensLocked, LensSwitch, LensUsed, LensWriting } from "@/components/story/LensBrief";
import { ReadProgress, SectionRail, SectionTabs, jumpTo, type NavItem } from "@/components/story/StoryNav";
import { StoryActionBar } from "@/components/story/StoryActionBar";
import { shortDate } from "@/lib/dateline";
import { sectorGroup } from "@/lib/sectors";
import { sentences } from "@/lib/sentences";

/**
 * The story record (Design System v2 · Pages v3 · Story). One order at every
 * width — Brief · What changed · Who said what · Heard on · On X · How it
 * unfolded · Why it matters · Coverage · Ask — each section only when the
 * record has its data, the nav counting what is there. The header answers
 * what happened, how current it is and how well supported before anything
 * else, with counted stats that jump to their section. The lens flip keeps its
 * mechanics (the locked flip, the gate, keys 1/2/3). Phone: back bar, sticky
 * section tabs, the photo deck above the header, the Ask/Share thumb bar.
 * Desk: "On this story" beside the record, the reports and the named beside it.
 */

function regionName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

const SOURCES_FOLD = 8;

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
  // Every block after the first the reader picks flips in (LensBrief).
  const [flipped, setFlipped] = useState(false);
  const [points, setPoints] = useState<Record<string, string[]>>(event.lens_points ?? {});
  const [briefLoading, setBriefLoading] = useState(false);
  // Which paywall wall this lens hit, if any. Null means the lens is readable.
  const [gateState, setGateState] = useState<
    { lens: string; kind: "signin" } | { lens: string; kind: "no_samples"; remaining: number | null } | null
  >(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [myRegion, setMyRegion] = useState<string | null>(null);
  // Country codes resolve locally; a state code (IN-KA) needs the regions list,
  // and until it arrives the code is left out rather than printed raw.
  const regionLabels = useStateNames(event.regions).filter((r) => !/^[A-Z]{2}-[A-Z0-9]{1,3}$/.test(r)).map((r) => (r.includes("-") ? r : regionName(r)));
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
  const clips = event.clips ?? [];
  // Gated here, not inside the component: a section head with nothing under it
  // would advertise the kill switch.
  const xposts = X_POSTS ? (event.x_posts ?? []) : [];
  const developments = boundaryVerified ? (routeStory?.developments.length ?? 0) : 0;
  const navItems: NavItem[] = [
    { id: "lens-brief", label: "Brief" },
    ...(reports.length > 1 ? [{ id: "changed", label: "What changed", count: reports.length }] : []),
    // Only when there is something to jump to: 55% of stories have no attributed
    // quote, and a permanent "0" would advertise absence on every other page.
    ...(quoteCount > 0 ? [{ id: "said", label: "Who said what", count: quoteCount }] : []),
    ...(clips.length > 0 ? [{ id: "heard", label: "Heard on", count: clips.length }] : []),
    ...(xposts.length > 0 ? [{ id: "on-x", label: "On X", count: xposts.length }] : []),
    ...(event.story_slug ? [{ id: "route", label: boundaryVerified ? "How it unfolded" : "Related reporting", count: developments > 1 ? developments : undefined }] : []),
    ...(event.impacts.length > 0 ? [{ id: "so-what", label: "Why it matters", count: event.impacts.length }] : []),
    { id: "sources", label: "Coverage", count: outletCount },
    { id: "ask", label: "Ask" },
  ];

  const [askOpen, setAskOpen] = useState(false);
  // What opened Ask and with what (AskContext); the nonce makes a repeat new.
  const [askRequest, setAskRequest] = useState<(AskOpen & { nonce: number }) | null>(null);
  const openAsk = useCallback((o: AskOpen) => {
    setAskRequest({ ...o, nonce: Date.now() });
    setAskOpen(true);
  }, []);
  const [allSources, setAllSources] = useState(false);

  // Picking a lens must SHOW the result: on the phone the record text can be
  // off-screen, so the flip happens where nobody can see it and the tap reads
  // as a dead button. Keys never scroll ("layout never moves").
  function pickLens(slug: string, scroll = true) {
    readerPicked.current = true;
    setFlipped(true);
    setLens(slug);
    track("Lens", { lens: slug, locked: isLocked(slug) });
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
  // The brief's lines, read aloud one at a time; another lens stops the voice.
  const lensPointsRaw = points[lens];
  const briefSentences = useMemo(() => (brief ? sentences(brief) : []), [brief]);
  const narrationBlocks = useMemo(() => [...briefSentences, ...(lensPointsRaw ?? [])], [briefSentences, lensPointsRaw]);
  const narration = useNarration(narrationBlocks, `${lens}|${brief ?? ""}`);

  // Region labels are places on the chart, not actors with a page; only the
  // cast links out (audit H29 — these chips used to point at /search, which is
  // noindex). The slug is the server's: identity is folded there, not here.
  const namedIn: { label: string; href: string | null }[] = [
    ...regionLabels.map((label) => ({ label, href: null })),
    ...event.entities.map((en) => ({ label: en.name, href: en.slug ? `/entity/${en.slug}` : null })),
  ].filter((x, i, all) => all.findIndex((y) => y.label === x.label) === i);
  const coverageLine = (
    <>
      {coverageEntries.length > 0 && (
        <span>
          {coverageEntries.length === 1 ? <>All filed from <b className="font-semibold" style={{ color: "var(--ink)" }}>{regionName(coverageEntries[0][0])}</b></> : <>Filed from {coverageEntries.map(([iso, n]) => `${regionName(iso)} ×${n}`).join(", ")}</>}
          {(event.coverage?.unknown ?? 0) > 0 && <> · {event.coverage!.unknown} of unknown origin</>}
        </span>
      )}
      {gapText && <span className="inline-flex items-center gap-2"><Dash /> {gapText}</span>}
      {event.coverage?.single_origin && <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>Single origin</span>}
    </>
  );

  // The header's counted stats: only what the record has, each a way to its section.
  const langCount = outlets.length ? languagesOf(outlets).length : 0;
  const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);
  const stats: { n: number; label: string; to: string }[] = [
    { n: outletCount, label: plural(outletCount, "outlet", "outlets"), to: "sources" },
    ...(langCount > 0 ? [{ n: langCount, label: plural(langCount, "language", "languages"), to: "sources" }] : []),
    { n: sourceCount, label: plural(sourceCount, "report", "reports"), to: reports.length > 1 ? "changed" : "sources" },
    ...(quoteCount > 0 ? [{ n: quoteCount, label: plural(quoteCount, "quote", "quotes"), to: "said" }] : []),
    ...(developments > 1 ? [{ n: developments, label: "developments", to: "route" }] : []),
  ];
  const reportWord = plural(sourceCount, "report", "reports");
  const saidOutlets = new Set(claims.flatMap((sp) => sp.claims.map((c) => c.source_name))).size;
  const saidLangs = new Set(claims.flatMap((sp) => sp.claims.map((c) => c.lang)).filter(Boolean)).size;

  // Facts first — they are the record; the brief beneath is a reading of it.
  const lensFacts = (
    <>
      {lens === "cyber" && cyber && !isLocked(lens) && (
        <div className="grid gap-3.5">
          <div className="flex flex-wrap items-center gap-2">
            {cvss.score != null && <span className="p-badge font-mono" style={{ background: "var(--lens-soft)", color: "var(--lens)" }}>CVSS {cvss.score.toFixed(1)}</span>}
            {exploitation.kev_listed && <span className="p-badge font-mono" style={{ background: "var(--lens-soft)", color: "var(--lens)" }}>KEV listed</span>}
            {exploitation.poc_public && <span className="p-badge font-mono" style={{ background: "var(--lens-soft)", color: "var(--lens)" }}>PoC public</span>}
            {cvss.vector && <span className="p-count" style={{ overflowWrap: "anywhere" }}>{cvss.vector}</span>}
          </div>
          {(cyber.affected ?? []).length > 0 && (
            <div>
              <h3 className="p-eyebrow mb-1.5">Affected products</h3>
              <ul className="grid gap-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
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
            <div className="rounded-[var(--r-md)] px-4 py-3" style={{ background: "var(--lens-soft)", color: "var(--ink)", font: "var(--t-body-s)" }}>
              <strong>Required action:</strong> {cyber.remediation.action}
            </div>
          )}
          {(cyber.control_mapping ?? []).length > 0 && (
            <div className="p-hide-scroll overflow-x-auto">
              <table className="p-table">
                <thead>
                  <tr><th>Framework</th><th>Control</th><th>Why it matters here</th></tr>
                </thead>
                <tbody>
                  {(cyber.control_mapping ?? []).map((cm, i) => (
                    <tr key={i}>
                      <td className="font-mono text-xs">{cm.framework}</td>
                      <td className="font-semibold">{cm.control}</td>
                      <td style={{ color: "var(--ink-2)" }}>{cm.relevance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {lens === "markets" && finance && !isLocked(lens) && (
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11.5px]" style={{ color: "var(--ink-2)" }}>
            {(finance.tickers ?? []).map((t) => <span key={t} className="p-badge font-mono" style={{ background: "var(--lens-soft)", color: "var(--lens)" }}>{t}</span>)}
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
    </>
  );

  // The lens block's body, by state. OUT OF SAMPLES is a different wall from
  // NOT SIGNED IN, and the reader needs a different next step for each; `null`
  // remaining means no quota row was ever granted, which is not "0 left".
  const ready = !(gateState?.lens === lens) && !isLocked(lens) && !!brief;
  const lensBody =
    gateState?.lens === lens && gateState.kind === "no_samples" ? (
      <LensUsed meta={meta} remaining={gateState.remaining} onReader={() => setLens("reader")} />
    ) : isLocked(lens) || gateState?.lens === lens ? (
      <LensLocked meta={meta} onSignIn={() => router.push(`/signin?next=/story/${event.id}`)} />
    ) : briefLoading && !brief ? (
      <LensWriting meta={meta} />
    ) : brief ? (
      <>
        {lensFacts}
        <BriefText sentences={briefSentences} points={lensPoints} active={narration.active} meta={meta} pointsHeading={pointsHeading} entities={event.entities} claims={claims} />
        {lens === "reader" && lensPoints.length > 0 && (
          <p className="text-[13px] leading-[1.4]" style={{ color: "var(--ink-3)" }}>The points restate the reports; where one says why it matters, that is Prism&apos;s reading, not a reported fact.</p>
        )}
      </>
    ) : (
      <>
        {lensFacts}
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>No {meta.short} read of this story yet.</p>
      </>
    );
  const lensIntro =
    lens === "reader"
      ? `Written by software from the ${sourceCount} ${reportWord} below.`
      : `The same reports, read for ${meta.plain ?? meta.short.toLowerCase()}.`;

  const lensOffered = offered.map((slug) => lensMeta(slug));
  // A section: its head under the 3px rule, then the body.
  const sec = "scroll-mt-[110px] pt-8 lg:pt-11";

  return (
    <AskContext.Provider value={openAsk}>
      <ReadProgress />
      {/* Phone back bar: the way back. The thumb bar carries Ask and Share;
          the tab bar is hidden on the record. Full-bleed by being OUTSIDE the
          padded shell, never by negative margins (a sideways scroll, 2026-09-21). */}
      <div
        className="sticky top-0 z-30 flex h-[var(--masthead)] items-center gap-2 border-b px-2 lg:hidden"
        style={{ borderColor: "var(--line)", background: "color-mix(in srgb, var(--paper) 92%, transparent)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}
      >
        <Link
          href="/feed"
          scroll={false}
          className="inline-flex min-h-[44px] items-center gap-1.5 px-2 text-[15px] font-semibold"
          style={{ color: "var(--ink)" }}
          aria-label="Back to today"
          onClick={(e) => {
            // Came here from inside Prism: real back, so the list they left is
            // the one they return to, at the place they left it.
            if (cameFromInside()) {
              e.preventDefault();
              router.back();
            }
          }}
        >
          <ArrowLeft size={18} /> Today
        </Link>
      </div>
      <SectionTabs items={navItems} />

      <div className="mx-auto max-w-[var(--shell)] px-[var(--gutter)] pb-[calc(env(safe-area-inset-bottom)+96px)] pt-3.5 lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-x-10 lg:pb-16 lg:pt-7 xl:grid-cols-[var(--rail)_minmax(0,var(--reading))_var(--evidence)] xl:justify-between">
        <SectionRail items={navItems} />

        <article className="flex min-w-0 flex-col lg:max-w-[var(--reading)]">
          {/* ── The header: what happened, how current, how well supported ── */}
          <header>
            <div className="meta-line p-meta flex-wrap normal-case">
              {single && <StatusPill status="single" label="Single source · not yet corroborated" />}
              {routeStory && event.story_slug && (
                <StatusPill status={boundaryVerified ? "verified" : "provisional"} title={boundaryVerified ? "Story boundary verified; developments below are in sequence." : "Grouping provisional; related reporting is shown without implying chronology."} />
              )}
              {(event.corrections?.length ?? 0) > 0 && (
                <a href="#history"><StatusPill status="corrected" label={`Corrected ${shortDate(event.corrections![0].created_at)}`} /></a>
              )}
              <span className="p-meta__prov">Updated <Ago iso={event.last_updated_at} /></span>
              {group && (
                <>
                  <span className="p-meta__sep" />
                  <span className="p-meta__subject">{group.name}</span>
                </>
              )}
              {(cyber?.cve_ids ?? []).slice(0, 3).map((cve) => (
                <span key={cve} className="p-meta__prov" style={{ color: "var(--ink)" }}>{cve}</span>
              ))}
            </div>
            <h1 className="mt-3 text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)", overflowWrap: "anywhere" }}>
              {event.title}
            </h1>
            <p className="mt-2 text-[13px] font-medium leading-[1.3]" style={{ color: "var(--ink-3)" }}>{headlineByline(event)}</p>
            {event.summary && (
              <EntityText as="p" text={event.summary} entities={event.entities} claims={claims} className="mt-3" style={{ font: "var(--t-body-l)", color: "var(--ink)", textWrap: "pretty" }} />
            )}
            <div className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(92px,1fr))] gap-2">
              {stats.map((st, i) => (
                <Reveal key={st.label} delay={i * 50}>
                  <button type="button" className="sc-stat w-full" onClick={() => jumpTo(st.to)}>
                    <b>{st.n}</b>
                    <span>{st.label}</span>
                  </button>
                </Reveal>
              ))}
            </div>
            {/* How sure: the count out of the monitored set, never out of
                everyone who covered it, and when the outlets were last read. */}
            <div className="mt-3.5 flex flex-wrap items-center gap-x-3 gap-y-2">
              <MonogramStack outlets={outlets} limit={4} size={24} />
              <CoverageBar outlets={outlets} fallbackCount={sourceCount} size="lg" width={220} draw className="lg:!hidden" />
              <CoverageBar outlets={outlets} fallbackCount={sourceCount} size="lg" width={360} draw className="!hidden lg:!inline-flex" />
              <span className="font-mono text-[12px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
                <Link href="/sources" className="hover:underline">{monitoredText(outletCount, event.monitored_outlets)}</Link> · {sourceCount} {reportWord}
                {outlets.length > 0 && ` · ${languageNames(languagesOf(outlets))}`}
                {event.monitored_checked_at && <> · checked <Ago iso={event.monitored_checked_at} /></>}
              </span>
            </div>
          </header>

          {/* The deck: above the header on the phone, under it on a desk. */}
          <div className="-order-1 mb-4 empty:hidden lg:order-none lg:mb-0 lg:mt-[18px]">
            <PhotoDeck sources={event.sources} />
          </div>

          {/* ── Brief: the lens switch, the lens block, the player ── */}
          <section id="lens-brief" data-askable className="scroll-mt-[110px] pt-5">
            <div className="flex flex-wrap items-center gap-3">
              <LensSwitch lenses={lensOffered} value={lens} isLocked={isLocked} onPick={(slug) => pickLens(slug)} />
              <span className="ml-auto hidden lg:inline-flex"><ShareButton url={`/story/${event.id}`} title={event.title} /></span>
            </div>
            <div className="mt-2.5">
              <LensBrief key={lens} meta={meta} flip={flipped} intro={lensIntro}>
                {lensBody}
              </LensBrief>
              {ready && <ListenBox narration={narration} />}
            </div>
          </section>

          {/* ── What changed: every report, newest first ── */}
          {reports.length > 1 && (
            <section id="changed" className={sec} aria-labelledby="changed-title">
              <Head id="changed-title" title="What changed" hint="Every report on this story, newest first. Times are when each outlet published." />
              <div className="mt-3"><ChangeTimeline reports={reports} sourceIndex={sourceIndex} /></div>
            </section>
          )}

          {/* ── Who said what ── */}
          {claims.length > 0 && (
            <section id="said" data-askable className={sec} aria-labelledby="said-title">
              <Head
                id="said-title"
                title="Who said what"
                // One speaker's card already counts the same; the strip is for the section.
                sub={claims.length > 1 ? `${quoteCount} ${plural(quoteCount, "quote", "quotes")} · ${saidOutlets} ${plural(saidOutlets, "outlet", "outlets")}${saidLangs > 1 ? ` · ${saidLangs} languages` : ""}` : undefined}
                hint="Only words found exactly in the article are shown, attributed and linked to the line they came from."
              />
              <div className="mt-3">
                <Said claims={claims} sourceIndex={sourceIndex} outletOf={(id) => event.sources.find((x) => x.article_id === id)} eventId={event.id} />
              </div>
            </section>
          )}

          {/* ── Heard on: what the news podcasts said, in their words ── */}
          {clips.length > 0 && (
            <section id="heard" className={sec} aria-labelledby="heard-title">
              <Head
                id="heard-title"
                title="Heard on"
                sub={`${new Set(clips.map((c) => c.show.name)).size} ${plural(new Set(clips.map((c) => c.show.name)).size, "show", "shows")}`}
                hint="News podcasts that discussed this story, in the hosts' own words. Plays the publisher's audio from the clip; the transcript is of that stretch only."
              />
              <div className="mt-3"><Clips clips={clips} /></div>
            </section>
          )}

          {/* ── On X: what the official accounts said, as written ── */}
          {xposts.length > 0 && (
            <section id="on-x" className={sec} aria-labelledby="on-x-title">
              <Head id="on-x-title" title="On X" hint="Posts from the official accounts named in this story, as written. Signal, not coverage: never counted among the outlets." />
              <div className="mt-3"><XPosts posts={xposts} sources={event.sources} /></div>
            </section>
          )}

          {/* ── How it unfolded: the story this event belongs to ── */}
          {event.story_slug && (
            <section id="route" className={sec} aria-labelledby="route-title">
              <Head
                id="route-title"
                title={boundaryVerified ? "How this story unfolded" : "Related reporting"}
                sub={developments > 1 ? `verified · ${developments} developments` : undefined}
                hint={boundaryVerified
                  ? "Every development in this story, counted: what came first, what followed, what branched off."
                  : "Grouped by subject or cast while the story boundary is under human review. No chronology is implied."}
              />
              <div className="mt-3"><StoryRoute slug={event.story_slug} currentId={event.id} onLoad={setRouteStory} /></div>
            </section>
          )}

          {/* ── Why it matters ── */}
          {event.impacts.length > 0 && (
            <section id="so-what" className={sec} aria-labelledby="sowhat-title">
              <Head id="sowhat-title" title="Why it matters" hint="Who is affected first and what likely follows, with a direction and a horizon. Extracted from the reports, never invented." />
              <div className="mt-2"><Impacts impacts={event.impacts} /></div>
            </section>
          )}

          {/* ── Coverage: the legend, where it was filed from, who is named, the reports ── */}
          <section id="sources" className={sec} aria-labelledby="sources-title">
            <Head id="sources-title" title="Coverage" sub={coverageText(outlets, outletCount)} />
            <div className="mt-3 grid gap-3">
              {outlets.length > 0 && <CoverageLegend outlets={outlets} />}
              {(coverageEntries.length > 0 || gapText || event.coverage?.single_origin) && (
                <p className="flex flex-wrap gap-x-4 gap-y-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{coverageLine}</p>
              )}
              {namedIn.length > 0 && (
                <p className="xl:hidden" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
                  <span className="p-eyebrow mr-1.5">Named</span>
                  {namedIn.map((n) => n.label).join(" · ")}
                </p>
              )}
              <div className="xl:hidden">
                <SourceList sources={allSources ? event.sources : event.sources.slice(0, SOURCES_FOLD)} sourceIndex={sourceIndex} compact />
                {!allSources && event.sources.length > SOURCES_FOLD && (
                  <button type="button" onClick={() => setAllSources(true)} className="p-btn p-btn--secondary p-btn--sm mt-3">
                    All {event.sources.length} reports
                  </button>
                )}
              </div>
              <p className="hidden xl:block" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>The {sourceCount} {sourceCount === 1 ? "report is" : "reports are"} listed beside the record.</p>
            </div>
          </section>

          {/* ── Related stories: different stories that touch this one ── */}
          {(routeStory?.related?.length ?? 0) > 0 && (
            <section className={sec} aria-labelledby="related-title">
              <Head id="related-title" title="Related stories" hint="Different stories that touch this one, by the cast they share or a causal note across the boundary. Not part of this story." />
              <div className="mt-2"><RelatedRoutes related={routeStory!.related} /></div>
            </section>
          )}

          {/* ── Corrections and every earlier version, kept ── */}
          <section id="history" className={sec} aria-labelledby="history-title">
            <Head id="history-title" title="Corrections and versions" hint="A correction says what was wrong and why. Every earlier headline and brief of this record is kept." />
            <div className="mt-3"><RecordHistory eventId={event.id} corrections={event.corrections ?? []} /></div>
          </section>

          {/* ── Something wrong: structured reports, never comments ── */}
          <section id="report" className={sec} aria-labelledby="report-title">
            <Head id="report-title" title="Something wrong?" hint="Say what, and it arrives with this record's address filled in. A correction is welcome." />
            <div className="mt-2 max-w-[420px]"><ReportProblem path={`/story/${event.id}`} /></div>
          </section>

          {/* ── Ask: the heading, the bar, the story's questions ── */}
          <section id="ask" className={sec} aria-labelledby="ask-title">
            <Head id="ask-title" title="Ask this story" />
            <div className="mt-3"><AskBar suggestions={questions} sourceCount={sourceCount} /></div>
          </section>
          {/* The clip that is playing docks here on a desk (Clips portals its
              bar into this slot), riding the foot of the viewport. */}
          <div id="story-foot-slot" className="z-20 hidden pt-3 empty:hidden lg:sticky lg:bottom-4 lg:block" />

          <p className="flex flex-wrap justify-between gap-4 pb-6 pt-7 text-[14.5px] font-semibold">
            <Link href="/feed" style={{ color: "var(--accent)" }}>← Today&rsquo;s record</Link>
            {event.story_slug && (
              <Link href={`/trending/${event.story_slug}`} style={{ color: "var(--accent)" }}>{boundaryVerified ? "The whole story" : "Open the grouping"} →</Link>
            )}
          </p>
        </article>

        {/* ── Beside the record (desk): the reports, who is named ── */}
        <Rail className="hidden xl:grid xl:content-start xl:gap-7" label="Evidence">
          <section>
            <h2 className="p-eyebrow mb-2.5 border-b-[3px] pb-2" style={{ borderColor: "var(--ink)" }}>
              Reports · <span className="font-mono">{sourceCount}</span>
            </h2>
            {/* The whole list, no inner scroll: the rail scrolls with the page (Rail). */}
            <SourceList sources={event.sources} sourceIndex={sourceIndex} compact />
          </section>
          {namedIn.length > 0 && (
            <section>
              <h2 className="p-eyebrow mb-2.5 border-b-[3px] pb-2" style={{ borderColor: "var(--ink)" }}>Named in the reports</h2>
              <div className="flex flex-wrap gap-1.5">
                {namedIn.slice(0, 12).map((n) =>
                  n.href ? (
                    <Link key={n.label} href={n.href} className="p-chip">{n.label}</Link>
                  ) : (
                    <span key={n.label} className="p-chip">{n.label}</span>
                  ),
                )}
              </div>
            </section>
          )}
        </Rail>
      </div>

      <StoryActionBar reports={sourceCount} onAsk={() => openAsk({ via: "thumb" })} url={`/story/${event.id}`} title={event.title} />

      {/* ── Ask — one sheet at every width. */}
      <AskPanel
        eventId={event.id}
        sourceCount={sourceCount}
        suggestedQuestions={questions}
        open={askOpen}
        onOpenChange={setAskOpen}
        launcher={false}
        request={askRequest}
        sources={event.sources}
      />
      <SelectionAsk />
    </AskContext.Provider>
  );
}
