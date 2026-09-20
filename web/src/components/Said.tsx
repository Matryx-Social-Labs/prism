"use client";

import { useState } from "react";
import { useAsk } from "@/components/AskContext";
import type { SpeakerClaims } from "@/lib/api";
import { ChevronDown } from "@/components/icons";
import { OutletIcon } from "@/components/Coverage";
import { fallbackCode } from "@/components/SourceList";
import { relativeTime } from "@/lib/dateline";
import { quoteLink } from "@/lib/quoteLink";
import { quoteId } from "@/lib/quotes";
import { ShareButton } from "@/components/ShareButton";

/**
 * Who said what, verbatim, grouped by speaker — one card per speaker
 * (DESIGN.md § Quote card). The quote is set in the record voice, italic; the
 * speaker, outlet and time are the reading voice; `[n]` is mono and is the ONE
 * index the Coverage list also uses, so the two can never number one article
 * differently. Nothing here is lens-coloured and nothing here is unverified:
 * every quote was checked against its article at write time.
 */
function initials(name: string): string {
  const words = name.replace(/[^\p{L}\p{N} ]/gu, " ").split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

const QUOTES_FOLD = 2;

export function Said({
  claims,
  sourceIndex,
  outletOf,
  eventId,
}: {
  claims: SpeakerClaims[];
  sourceIndex: Map<string, number>;
  /** article_id → the outlet's icon facts, when the caller has them. */
  outletOf?: (articleId: string) => { domain?: string | null; code?: string | null } | undefined;
  /** When set, each quote carries Share → its own address and quote card. */
  eventId?: string;
}) {
  return (
    <div className={`grid gap-3 ${claims.length > 1 ? "md:grid-cols-2" : ""}`}>
      {claims.map((sp, si) => (
        <SpeakerCard key={sp.speaker} sp={sp} si={si} sourceIndex={sourceIndex} outletOf={outletOf} eventId={eventId} />
      ))}
    </div>
  );
}

function SpeakerCard({ sp, si, sourceIndex, outletOf, eventId }: { sp: SpeakerClaims; si: number; sourceIndex: Map<string, number>; outletOf?: (articleId: string) => { domain?: string | null; code?: string | null } | undefined; eventId?: string }) {
  // Two quotes per speaker, the rest on request: a minister with nine quotes
  // is a column of italics that buries the next speaker.
  const [all, setAll] = useState(false);
  const ask = useAsk();
  const shown = all ? sp.claims : sp.claims.slice(0, QUOTES_FOLD);
  const outlets = new Set(sp.claims.map((c) => c.source_name)).size;
  return (
          <article className="card flex flex-col gap-3">
            <header className="flex items-center gap-2.5">
              <span
                aria-hidden
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold"
                style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
              >
                {initials(sp.speaker)}
              </span>
              <div className="min-w-0">
                <h3 className="truncate text-[14.5px] font-semibold leading-tight">{sp.speaker}</h3>
                {/* Who they are, as the articles put it — never a title we supplied. */}
                {sp.role && <p className="truncate text-[12.5px] leading-snug" style={{ color: "var(--ink-2)" }}>{sp.role}</p>}
                <p className="text-[12px]" style={{ color: "var(--ink-3)" }}>
                  {sp.claims.length} {sp.claims.length === 1 ? "quote" : "quotes"} · {outlets} {outlets === 1 ? "outlet" : "outlets"}
                </p>
              </div>
            </header>
            <ul className="flex flex-col gap-4">
              {shown.map((c, j) => {
                const n = sourceIndex.get(c.article_id);
                return (
                  <li key={`${c.article_id}-${j}`} className={j > 0 ? "border-t pt-4" : ""} style={j > 0 ? { borderColor: "var(--line)" } : undefined}>
                    <blockquote className="font-record text-[17px] italic leading-[1.5]" style={{ color: "var(--ink)", textWrap: "pretty" }}>
                      “{c.quote_text}”
                    </blockquote>
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px]" style={{ color: "var(--ink-3)" }}>
                      {n != null && (
                        <span className="font-mono text-[11px]">[{n}]</span>
                      )}
                      <span className="chip h-6 gap-1 px-2 text-[12px]">
                        <OutletIcon domain={outletOf?.(c.article_id)?.domain} code={outletOf?.(c.article_id)?.code ?? fallbackCode(c.source_name)} name={c.source_name} size={16} />
                        {c.source_name}
                      </span>
                      {c.published_at && <span className="font-mono text-[11px]">{relativeTime(c.published_at)}</span>}
                      {c.url && n != null && (
                        <a
                          href={quoteLink(c.url, c.quote_text)}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Source ${n}: ${c.source_name}`}
                          className="relative font-semibold underline-offset-4 before:absolute before:-inset-3 before:content-[''] hover:underline"
                          style={{ color: "var(--accent)" }}
                        >
                          Open at the quote ↗
                        </a>
                      )}
                      {eventId && (
                        <span className="inline-flex"><ShareButton url={`/story/${eventId}/quote/${quoteId(si, j)}`} title={`“${c.quote_text}” — ${sp.speaker}`} compact /></span>
                      )}
                      {ask && (
                        <button
                          type="button"
                          onClick={() => ask({ prefill: `About the quote “${c.quote_text.length > 160 ? c.quote_text.slice(0, 160) + "…" : c.quote_text}” by ${sp.speaker}: what else did they say on this story, and does any report contradict it?`, via: "quote" })}
                          className="font-semibold underline-offset-4 hover:underline"
                          style={{ color: "var(--ink-2)" }}
                        >
                          Ask about this quote
                        </button>
                      )}
                    </div>
                    {/* The quote in place: the article's own words either side,
                        the quote itself marked. The reader checks us without
                        leaving; the link opens the article on the quote. */}
                    {(c.context_before || c.context_after) && (
                      <details className="group mt-2">
                        <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 text-[13px] font-semibold" style={{ color: "var(--accent)" }}>
                          In the article
                          <ChevronDown className="transition-transform group-open:rotate-180" />
                        </summary>
                        <p className="mt-2 border-l-2 pl-3 text-[14px] leading-[1.6]" style={{ borderColor: "var(--line-strong)", color: "var(--ink-2)" }}>
                          {c.context_before && <>…{c.context_before} </>}
                          <mark className="rounded-[3px] px-0.5" style={{ background: "var(--accent-soft)", color: "var(--ink)" }}>{c.quote_text}</mark>
                          {c.context_after && <> {c.context_after}…</>}
                        </p>
                      </details>
                    )}
                  </li>
                );
              })}
            </ul>
            {!all && sp.claims.length > QUOTES_FOLD && (
              <button type="button" onClick={() => setAll(true)} className="btn btn-ghost btn-sm self-start -ml-3" style={{ color: "var(--accent)" }}>
                {sp.claims.length - QUOTES_FOLD} more {sp.claims.length - QUOTES_FOLD === 1 ? "quote" : "quotes"}
              </button>
            )}
          </article>
  );
}
