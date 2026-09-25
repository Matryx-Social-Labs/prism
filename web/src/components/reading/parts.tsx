import Link from "next/link";
import { Ago } from "@/components/Ago";
import { CoverageBar } from "@/components/Coverage";
import { StatusPill } from "@/components/StatusPill";
import type { TrendingStory } from "@/lib/api";
import { arcHref, spanDays } from "@/lib/arc";
import { sectorGroup } from "@/lib/sectors";

/**
 * The pieces the reading routes share (Claude Design · screens/ReadingB.jsx):
 * the columns, the page title, the meta strip and the rail head. Server-safe —
 * no hooks — so the routes stay server components.
 */

/**
 * The page's columns (ReadingB `Cols`): a 640 column with the evidence rail
 * beside it from lg; with a `left` rail (the subject nav) the rail drops under
 * the column until xl, where all three sit side by side. Stacked on the phone.
 */
export function ReadingColumns({ left, main, rail, railLabel }: { left?: React.ReactNode; main: React.ReactNode; rail?: React.ReactNode; railLabel?: string }) {
  const grid = left
    ? rail
      ? "lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-x-10 xl:grid-cols-[var(--rail)_minmax(0,640px)_var(--evidence)] xl:justify-center"
      : "lg:grid lg:grid-cols-[var(--rail)_minmax(0,640px)] lg:justify-center lg:gap-x-10"
    : rail
      ? "lg:grid lg:grid-cols-[minmax(0,640px)_var(--evidence)] lg:justify-center lg:gap-x-10"
      : "mx-auto max-w-[var(--reading)]";
  const railCls = left
    ? "mt-10 lg:col-start-2 xl:sticky xl:top-[calc(var(--topbar)+24px)] xl:col-start-3 xl:row-start-1 xl:mt-0 xl:self-start"
    : "mt-10 lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:mt-0 lg:self-start";
  return (
    <div className="mx-auto w-full max-w-[var(--shell)] px-[var(--gutter)] pb-16 pt-4 lg:pt-8">
      <div className={grid}>
        {left}
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-6">{main}</div>
        {rail && (
          <aside aria-label={railLabel} className={`grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-6 ${railCls}`}>
            {rail}
          </aside>
        )}
      </div>
    </div>
  );
}

/** The record's name for the page: display-m on the phone, display-l from lg (ReadingB `Title`). */
export function PageTitle({ children, size = "l" }: { children: React.ReactNode; size?: "l" | "xl" }) {
  const cls = size === "xl" ? "[font:var(--t-display-l)] lg:[font:var(--t-display-xl)]" : "[font:var(--t-display-m)] lg:[font:var(--t-display-l)]";
  return (
    <h1 className={`text-balance ${cls}`} style={{ letterSpacing: "var(--track-display)", overflowWrap: "anywhere" }}>
      {children}
    </h1>
  );
}

/** Counts in the provenance voice, dot-separated (record/MetaLine). Empty items drop out. */
export function MetaLine({ items }: { items: (string | null | undefined | false)[] }) {
  const shown = items.filter((x): x is string => Boolean(x));
  if (shown.length === 0) return null;
  return (
    <p className="p-meta">
      {shown.flatMap((it, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, <span key={it} className="p-meta__prov">{it}</span>] : [<span key={it} className="p-meta__prov">{it}</span>]))}
    </p>
  );
}

/** A rail section's head: an eyebrow over the 3px ink rule. */
export function RailHead({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="p-eyebrow pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>
      {children}
    </h2>
  );
}

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

/**
 * Stories developing over days (ReadingB `ArcRow`), for the right rail. The
 * trending list carries no origin split, so the bar is drawn in one ink and its
 * count is the legend. A story without a boundary verdict prints no pill.
 */
export function DevelopingRail({ stories, title }: { stories: TrendingStory[]; title: string }) {
  return (
    <section aria-labelledby="developing-here">
      <RailHead id="developing-here">{title}</RailHead>
      <ol>
        {stories.map((s) => {
          const span = spanDays(s);
          const group = sectorGroup(s.sector);
          const verified = s.boundary_status === "verified";
          return (
            <li key={s.slug}>
              <Link href={arcHref(s)} className="group grid gap-2 border-b py-4" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
                <span className="flex min-w-0 flex-wrap items-center gap-2">
                  {s.boundary_status && (verified ? <StatusPill status="verified" label="Verified" /> : <StatusPill status="provisional" />)}
                  <span className="p-meta">
                    {[
                      group && <span key="g" className="p-meta__subject">{group.name}</span>,
                      span != null && span > 0 && <span key="d" className="p-meta__prov">{plural(span, "day")}</span>,
                      s.last_updated_at && <span key="u" className="p-meta__prov">updated <Ago iso={s.last_updated_at} /></span>,
                    ]
                      .filter(Boolean)
                      .flatMap((part, i) => (i ? [<span key={`sep${i}`} className="p-meta__sep" />, part] : [part]))}
                  </span>
                </span>
                <span className="text-balance underline-offset-4 group-hover:underline" style={{ font: "var(--t-title)" }}>{s.hero_title ?? s.label}</span>
                <span className="flex min-w-0 flex-wrap items-center gap-2.5">
                  <CoverageBar outlets={[]} fallbackCount={s.source_count} width={120} className="p-covbar--mono" />
                  <span className="p-count whitespace-normal">{plural(s.developments, verified ? "development" : "report")} · {plural(s.source_count, "outlet")}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      <Link href="/trending" className="p-link mt-2.5 inline-block text-[13.5px]">All developing stories →</Link>
    </section>
  );
}
