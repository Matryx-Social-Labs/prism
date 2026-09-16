"use client";


import type { EventDetail } from "@/lib/api";
import { origins } from "@/lib/dateline";

// The desktop Story (Prism Desktop.dc.html, STORY screen).
//
// Presentational only — StoryView still owns the lens state, the brief fetching
// and the flip, so there is one state machine rather than two that can disagree.
//
// The desktop flip is not the mobile flip made wider. On a phone you flip one
// lens at a time because there is room for one. Here all three openings are on
// screen at once — the lens board — and the ledger rail RE-INKS to match the one
// you pick: sources and origin for the reader, CVE and CVSS for cyber, tickers
// and catalyst for markets. Simultaneity is what the extra width buys, and it is
// why this is a different composition rather than a wider column.

const MONO = "font-mono text-[11px] uppercase tracking-[0.06em]";
const HUE: Record<string, string> = {
  reader: "#F59E0B",
  general: "#F59E0B",
  cyber: "#06B6D4",
  markets: "#8B5CF6",
};

/** The first sentence of a brief — the lens board shows openings, not essays. */
function opening(text: string | undefined): string {
  if (!text) return "";
  const cut = text.slice(0, 200);
  const stop = cut.search(/[.!?](\s|$)/);
  return stop > 0 ? cut.slice(0, stop + 1) : cut;
}

/**
 * The evidence the rail carries for the active lens.
 *
 * Only what the projection actually holds — a lens with nothing to show gets the
 * shared provenance rather than an invented row.
 */
function railFacts(event: EventDetail, lens: string): [string, string][] {
  const cyber = event.projection?.cyber ?? null;
  const finance = event.projection?.finance ?? null;
  const out: [string, string][] = [];

  if (lens === "cyber" && cyber) {
    const cve = (cyber.cve_ids ?? [])[0];
    if (cve) out.push(["", cve]);
    const score = cyber.cvss?.score;
    if (score != null) out.push(["", `CVSS ${score}${cyber.cvss?.severity ? ` · ${cyber.cvss.severity}` : ""}`]);
    if (cyber.exploitation?.kev_listed) out.push(["exploitation", "CISA KEV LISTED"]);
    const fix = cyber.remediation?.action;
    if (fix) out.push(["remediation", fix.toUpperCase().slice(0, 28)]);
  }
  if (lens === "markets" && finance) {
    for (const t of (finance.tickers ?? []).slice(0, 2)) out.push(["", t]);
    if (finance.catalyst) out.push(["catalyst", String(finance.catalyst).toUpperCase().slice(0, 28)]);
  }
  if (!out.length) {
    out.push(["", `${event.sources.length} source${event.sources.length === 1 ? "" : "s"}`]);
    const o = origins({ coverage: event.coverage } as never);
    if (o) out.push(["", o]);
  }
  // Attributed quotes are evidence whatever the lens, and navItems never reach
  // this rail — the Stone ledger is where desktop learns the section exists.
  const quotes = (event.claims ?? []).reduce((n, s) => n + s.claims.length, 0);
  if (quotes > 0) out.push(["", `${quotes} quote${quotes === 1 ? "" : "s"}`]);
  return out;
}

/** The desk's mono rail beside the reading: the lens's facts, re-inked with the lens. */
export function DesktopRail({ event, lens }: { event: EventDetail; lens: string }) {
  const hue = HUE[lens] ?? "var(--ink)";
  return (
    <>
      {railFacts(event, lens).map(([label, value], n) => (
        <div key={`${label}-${n}`} className={label ? "mt-3.5" : undefined}>
          {label ? (
            <>
              <div>{label}</div>
              <div style={{ color: "var(--ink-muted)" }}>{value}</div>
            </>
          ) : (
            <div style={{ color: n === 0 ? (lens === "reader" ? "var(--ink-muted)" : hue) : "var(--ink-faint)" }}>{value}</div>
          )}
        </div>
      ))}
    </>
  );
}

/** The lens board (desk): every lens's opening at once; picking one flips the reading. */
export function LensBoard({
  offered,
  lens,
  briefs,
  lensName,
  isLocked,
  onPick,
}: {
  offered: string[];
  lens: string;
  briefs: Record<string, string>;
  lensName: (slug: string) => string;
  isLocked: (slug: string) => boolean;
  onPick: (slug: string) => void;
}) {
  return (
    <div>
      <h2 className="mb-3.5 font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">The lens board</h2>
      {/* items-start, because a <button> centres its content vertically by
          default: stretched to the tallest column, a lens whose opening is
          one line sat 19px below one whose opening is three. */}
      <div
        className="grid items-start gap-x-5"
        style={{ gridTemplateColumns: `repeat(${Math.max(offered.length, 1)}, 1fr)` }}
      >
        {offered.map((slug, n) => {
          const active = slug === lens;
          const locked = isLocked(slug);
          return (
            <button
              key={slug}
              onClick={() => onPick(slug)}
              aria-pressed={active}
              aria-label={locked ? `${lensName(slug)}, sign in to unlock, free` : undefined}
              className="block text-left transition hover:opacity-80"
            >
              <div className="flex items-baseline justify-between">
                <span className="whitespace-nowrap text-[13.5px] font-medium">{lensName(slug)}</span>
                <span className={MONO} style={{ color: "var(--ink-faint)" }}>
                  {n + 1}
                </span>
              </div>
              <div
                className="my-2 h-0.5"
                style={{ background: active ? HUE[slug] ?? "var(--ink)" : "var(--line)" }}
              />
              <div className="text-[12.5px] leading-[1.45]" style={{ color: "var(--ink-faint)" }}>
                {locked ? "Sign in to read this lens. It is free." : opening(briefs[slug])}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
