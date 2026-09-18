"use client";

import { useState } from "react";
import type { SpeakerClaims } from "@/lib/api";
import { ChevronDown } from "@/components/icons";
import { relativeTime } from "@/lib/dateline";
import { quoteLink } from "@/lib/quoteLink";

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
}: {
  claims: SpeakerClaims[];
  sourceIndex: Map<string, number>;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {claims.map((sp) => (
        <SpeakerCard key={sp.speaker} sp={sp} sourceIndex={sourceIndex} />
      ))}
    </div>
  );
}

function SpeakerCard({ sp, sourceIndex }: { sp: SpeakerClaims; sourceIndex: Map<string, number> }) {
  // Two quotes per speaker, the rest on request: a minister with nine quotes
  // is a column of italics that buries the next speaker.
  const [all, setAll] = useState(false);
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
                <p className="text-[12.5px]" style={{ color: "var(--ink-3)" }}>
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
                      <span className="chip h-6 px-2 text-[12px]">{c.source_name}</span>
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
