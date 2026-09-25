"use client";

import { Ago } from "@/components/Ago";
import { useEffect, useState } from "react";
import { useAsk } from "@/components/AskContext";
import type { ClaimOut, SpeakerClaims } from "@/lib/api";
import { ChevronDown } from "@/components/icons";
import { OutletIcon } from "@/components/Coverage";
import { fallbackCode } from "@/components/SourceList";
import { quoteLink } from "@/lib/quoteLink";
import { langName, langNative } from "@/lib/languages";
import { loadProfile } from "@/lib/profile";
import { quoteId, unitsForReader } from "@/lib/quotes";
import { ShareButton } from "@/components/ShareButton";
import { Reveal } from "@/components/Reveal";

/**
 * Who said what, verbatim, grouped by speaker — one card per speaker
 * (DESIGN.md § Quote card). The quote is set in the record voice, italic; the
 * speaker, outlet and time are the reading voice; `[n]` is mono and is the ONE
 * index the Coverage list also uses, so the two can never number one article
 * differently. Nothing here is lens-coloured and nothing here is unverified:
 * every quote was checked against its article at write time.
 *
 * VERBATIM IS CHECKED AGAINST THE ARTICLE, NOT AGAINST THE SPEAKER. An outlet
 * writing in its own language prints a translation, and that translation passes
 * the write-time check perfectly — so a card can hold one sentence in two
 * languages and neither is necessarily the words that were spoken. Speaker names
 * are canonicalised to English by the extractor, which is what puts them on the
 * same card. When a card holds more than one language it SAYS SO on every quote;
 * the label makes no claim about which was spoken, only about what was printed.
 */
function initials(name: string): string {
  const words = name.replace(/[^\p{L}\p{N} ]/gu, " ").split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

const QUOTES_FOLD = 2;

/**
 * The language a quote was PRINTED in, in the provenance voice. When the
 * outlet's words are shown to be its own translation, the label says so —
 * the one case where a quote is printed knowing it is not the speaker's words
 * (founder D-quote-3), so it is never printed without saying it.
 */
function LangLabel({ claim }: { claim: ClaimOut }) {
  if (!claim.lang) return null;
  const title = claim.translated
    ? `${claim.source_name}'s ${langName(claim.lang)} translation — not the words as spoken`
    : `Printed in ${langName(claim.lang)} by ${claim.source_name}`;
  return (
    <span className="text-[12.5px] font-medium" style={{ color: "var(--ink-2)" }} title={title}>
      {langNative(claim.lang)}
      {claim.translated && " translation"}
    </span>
  );
}

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
  // The reader's own languages, read once for every card. In an effect and not
  // during render: the server has no localStorage, and reading it inline would
  // render one order on the server and another on the client.
  const [prefer, setPrefer] = useState<readonly string[]>([]);
  useEffect(() => setPrefer(loadProfile()?.languages ?? []), []);
  return (
    <div className="grid gap-3">
      {claims.map((sp, si) => (
        <Reveal key={sp.speaker} delay={Math.min(si, 4) * 80}>
          <SpeakerCard sp={sp} si={si} prefer={prefer} sourceIndex={sourceIndex} outletOf={outletOf} eventId={eventId} />
        </Reveal>
      ))}
    </div>
  );
}

function SpeakerCard({ sp, si, prefer, sourceIndex, outletOf, eventId }: { sp: SpeakerClaims; si: number; prefer: readonly string[]; sourceIndex: Map<string, number>; outletOf?: (articleId: string) => { domain?: string | null; code?: string | null } | undefined; eventId?: string }) {
  // Two quotes per speaker, the rest on request: a minister with nine quotes
  // is a column of italics that buries the next speaker.
  const [all, setAll] = useState(false);
  const ask = useAsk();
  // The API already rotates the languages so none can be pushed out of the fold;
  // this lifts the reader's own to the front of that rotation, and makes one
  // unit per STATEMENT — a statement printed in two languages is one unit with
  // the other rendering nested under it, so the fold counts things said. Each
  // entry keeps its position in the API's array, because that position IS the
  // quote's share address and the card behind it reads the API's order.
  const units = unitsForReader(sp.claims, prefer);
  const shown = all ? units : units.slice(0, QUOTES_FOLD);
  const outlets = new Set(sp.claims.map((c) => c.source_name)).size;
  const languages = sp.languages ?? [];
  const multilingual = languages.length > 1;
  return (
    <article className="p-card grid gap-3.5 p-4 sm:p-[18px]">
      <header className="flex items-center gap-2.5">
        <span
          aria-hidden
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold"
          style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
        >
          {initials(sp.speaker)}
        </span>
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold leading-[1.25]" style={{ overflowWrap: "anywhere" }}>{sp.speaker}</h3>
          {/* Who they are, as the articles put it — never a title we supplied. */}
          {sp.role && <p className="text-[13px] leading-[1.35]" style={{ color: "var(--ink-2)" }}>{sp.role}</p>}
          <p className="text-[12.5px] leading-[1.3]" style={{ color: "var(--ink-3)" }}>
            {sp.claims.length} {sp.claims.length === 1 ? "quote" : "quotes"} · {outlets} {outlets === 1 ? "outlet" : "outlets"}
            {/* Counted, the way the coverage bar counts languages. */}
            {multilingual && ` · ${languages.length} languages`}
          </p>
        </div>
      </header>
      {shown.map(({ lead: { claim: c, index }, also }, j) => {
        const n = sourceIndex.get(c.article_id);
        const unitLanguages = new Set([c.lang, ...also.map((a) => a.claim.lang)].filter(Boolean)).size;
        return (
          <div key={`${c.article_id}-${index}`} className={j > 0 ? "border-t pt-3.5" : ""} style={j > 0 ? { borderColor: "var(--line)" } : undefined}>
            <blockquote className="font-record" style={{ font: "var(--t-quote)", color: "var(--ink)", textWrap: "pretty", overflowWrap: "anywhere" }}>
              “{c.quote_text}”
            </blockquote>
            <div className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[12.5px] font-medium leading-[1.3]" style={{ color: "var(--ink-3)" }}>
              {n != null && <span className="font-mono text-[11px] font-normal">[{n}]</span>}
              {/* Which language this rendering is in. Shown when the card
                  holds more than one, or when this quote is the outlet's own
                  translation — then even a lone quote must say so. Otherwise
                  a single-language card says nothing: it would answer a
                  question nobody asked. */}
              {(multilingual || c.translated) && c.lang && <LangLabel claim={c} />}
              <span className="inline-flex items-center gap-1.5" style={{ color: "var(--ink-2)" }}>
                <OutletIcon domain={outletOf?.(c.article_id)?.domain} code={outletOf?.(c.article_id)?.code ?? fallbackCode(c.source_name)} name={c.source_name} size={16} />
                {c.source_name}
              </span>
              {c.published_at && <Ago iso={c.published_at} className="font-mono text-[11px] font-normal" />}
              {c.url && n != null && (
                <a
                  href={quoteLink(c.url, c.quote_text)}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Source ${n}: ${c.source_name}`}
                  className="inline-flex min-h-[44px] items-center font-semibold lg:min-h-[32px]"
                  style={{ color: "var(--accent)" }}
                >
                  Open at the quote ↗
                </a>
              )}
              {eventId && (
                <span className="inline-flex min-h-[44px] items-center lg:min-h-[32px]"><ShareButton url={`/story/${eventId}/quote/${quoteId(si, index)}`} title={`“${c.quote_text}” — ${sp.speaker}`} compact /></span>
              )}
              {ask && (
                <button
                  type="button"
                  onClick={() => ask({ prefill: `About the quote “${c.quote_text.length > 160 ? c.quote_text.slice(0, 160) + "…" : c.quote_text}” by ${sp.speaker}: what else did they say on this story, and does any report contradict it?`, via: "quote" })}
                  className="min-h-[44px] font-semibold lg:min-h-[32px]"
                  style={{ color: "var(--ink-2)" }}
                >
                  Ask about this quote
                </button>
              )}
            </div>
            {/* The quote in place: the article's own words either side, the
                quote itself marked. The reader checks us without leaving; the
                link opens the article on the quote. */}
            {(c.context_before || c.context_after) && (
              <details className="group mt-1.5">
                <summary className="inline-flex min-h-[44px] cursor-pointer list-none items-center gap-1.5 text-[13px] font-semibold lg:min-h-[32px]" style={{ color: "var(--accent)" }}>
                  In the article
                  <ChevronDown className="transition-transform group-open:rotate-180" />
                </summary>
                <p className="mt-1.5 border-l-2 pl-3" style={{ borderColor: "var(--line-strong)", color: "var(--ink-2)", font: "var(--t-body-s)" }}>
                  {c.context_before && <>…{c.context_before} </>}
                  <mark className="rounded-[2px] px-0.5" style={{ background: "var(--accent-soft)", color: "var(--ink)" }}>{c.quote_text}</mark>
                  {c.context_after && <> {c.context_after}…</>}
                </p>
              </details>
            )}
            {/* The same statement as other outlets printed it. Shown, not
                folded (founder D-quote-2: the original WITH the translation),
                and headed by the one thing Prism knows without asking anyone:
                two languages, one statement, so at most one of these is the
                words as spoken. */}
            {also.length > 0 && (
              <div className="mt-3 grid gap-2.5 border-l-2 pl-3" style={{ borderColor: "var(--line-strong)" }}>
                {unitLanguages > 1 && (
                  <p className="text-[12.5px] leading-[1.4]" style={{ color: "var(--ink-3)" }}>
                    The same statement in {unitLanguages} languages. At most one is the words as spoken.
                  </p>
                )}
                {also.map(({ claim: a, index: ai }) => {
                  const an = sourceIndex.get(a.article_id);
                  return (
                    <div key={`${a.article_id}-${ai}`}>
                      <blockquote className="font-record" style={{ font: "var(--t-quote-s)", color: "var(--ink-2)", textWrap: "pretty", overflowWrap: "anywhere" }}>
                        “{a.quote_text}”
                      </blockquote>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[12.5px] font-medium" style={{ color: "var(--ink-3)" }}>
                        {an != null && <span className="font-mono text-[11px] font-normal">[{an}]</span>}
                        {a.lang && <LangLabel claim={a} />}
                        <span style={{ color: "var(--ink-2)" }}>{a.source_name}</span>
                        {a.url && an != null && (
                          <a href={quoteLink(a.url, a.quote_text)} target="_blank" rel="noopener noreferrer" aria-label={`Source ${an}: ${a.source_name}`} className="inline-flex min-h-[44px] items-center font-semibold lg:min-h-[32px]" style={{ color: "var(--accent)" }}>
                            Open at the quote ↗
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {!all && units.length > QUOTES_FOLD && (
        <button type="button" onClick={() => setAll(true)} className="p-btn p-btn--text p-btn--sm justify-self-start">
          {units.length - QUOTES_FOLD} more {units.length - QUOTES_FOLD === 1 ? "quote" : "quotes"}
        </button>
      )}
    </article>
  );
}
