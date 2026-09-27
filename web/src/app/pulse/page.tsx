"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Ago } from "@/components/Ago";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { TickerChip } from "@/components/tabs/Markets";
import { Alert, EmptyState } from "@/components/ui";
import { fetchDigest, type MarketDigest, type PulseCompany, type PulseRow } from "@/lib/api";
import { istTime, shortDate } from "@/lib/dateline";
import { useSession, type Session } from "@/lib/session";
import { follow, getWatchlist, unfollow, type WatchItem } from "@/lib/watchlist";

/**
 * Market Pulse (founder decision 1, 2026-09-27): a ticker board of the last 24
 * hours of business and finance reporting. Which listed companies and
 * market-wide forces the record named, what happened, and why a markets reader
 * would notice — most-corroborated first, each row a record with its outlets
 * counted by masthead and a dashed rule when one outlet has it. Prism's reading
 * is labelled as Prism's and is never a price; no prices exist in Prism. The
 * model's three lines, when it wrote any, come last. Free, and not indexed.
 */
export default function PulsePage() {
  const session = useSession();
  const [board, setBoard] = useState<MarketDigest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDigest().then((d) => {
      setBoard(d);
      setLoading(false);
    });
  }, []);

  const follows = useFollows(session);
  const day = board?.generated_at ? shortDate(board.generated_at) : null;
  const dateline = ["Pulse", day, board?.generated_at ? `updated ${istTime(board.generated_at)} IST` : null].filter(Boolean).join(" · ");

  return (
    <div className="mx-auto max-w-[1080px] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-16">
      <Masthead dateline={dateline} />
      <header className="grid gap-1.5 pt-4 lg:pt-8">
        <h1 className="[font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)" }}>Market Pulse</h1>
        {board && <p className="p-count">{counted(board)}</p>}
        <p className="max-w-[60ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          The listed companies and market-wide forces the last 24 hours of business reporting named, most-reported first. Prism&rsquo;s reading is labelled as Prism&rsquo;s; no prices, no advice.
        </p>
      </header>

      {loading ? (
        <div className="grid gap-3 pt-6" aria-busy="true" aria-label="Loading Market Pulse">
          <span className="p-skel h-28" />
          <span className="p-skel h-28" />
          <span className="p-skel h-28" />
        </div>
      ) : !board ? (
        <div className="pt-6">
          <EmptyState title="Market Pulse could not load" action={<Link href="/feed" className="p-link">Open today&rsquo;s record →</Link>}>
            The board is built from the record every half hour. Try again in a minute.
          </EmptyState>
        </div>
      ) : board.companies.length + board.market_wide.length === 0 ? (
        <div className="pt-6">
          <EmptyState title="No listed company or market-wide story in the last 24 hours of business reporting" />
        </div>
      ) : (
        <div className="grid gap-8 pt-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-10">
          <section aria-labelledby="companies-title" className="grid min-w-0 content-start gap-3">
            <SectionHead id="companies-title" title="Companies in today’s reporting" sub={`${board.companies.length} ${plural(board.companies.length, "company", "companies")} · most-reported first`} />
            {follows.problem && <Alert tone="error">{follows.problem}</Alert>}
            {board.companies.length > 0 ? (
              <ol className="p-print grid gap-3">
                {board.companies.map((c) => (
                  <CompanyRow key={c.symbol} row={c} session={session} follows={follows} />
                ))}
              </ol>
            ) : (
              <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>No listed company was named in the last 24 hours of business reporting.</p>
            )}
          </section>
          <div className="grid min-w-0 content-start gap-8">
            {board.market_wide.length > 0 && (
              <section aria-labelledby="wide-title" className="grid content-start gap-3">
                <SectionHead id="wide-title" title="Market-wide" sub={`${board.market_wide.length} ${plural(board.market_wide.length, "story", "stories")} · no single company`} />
                <ol className="p-print grid gap-3">
                  {board.market_wide.map((r) => (
                    <li key={r.id}>
                      <Row row={r} />
                    </li>
                  ))}
                </ol>
              </section>
            )}
            {board.read.length > 0 && (
              <section aria-labelledby="read-title" className="grid content-start gap-2">
                <SectionHead id="read-title" title="The read" hint="Written by Prism's model from the rows on this board, and nothing else." />
                {board.read.map((line, i) => (
                  <p key={i} className="max-w-[60ch]" style={{ font: "var(--t-body)" }}>{line}</p>
                ))}
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

function counted(b: MarketDigest): string {
  const { companies, stories, outlets } = b.counts;
  return `${companies} ${plural(companies, "company", "companies")} named · ${stories} market ${plural(stories, "story", "stories")} · ${outlets} ${plural(outlets, "outlet", "outlets")} · last 24 hours`;
}

type Follows = ReturnType<typeof useFollows>;

/** The reader's followed tickers, and a toggle that writes the watchlist. */
function useFollows(session: Session | null) {
  const [on, setOn] = useState<ReadonlySet<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const tickers = (items: WatchItem[]) => new Set(items.filter((i) => i.kind === "ticker").map((i) => i.value));

  useEffect(() => {
    if (!session) return;
    getWatchlist(session).then((items) => setOn(tickers(items))).catch(() => setProblem("Your watchlist did not load, so what you follow is not marked. Reload to try again."));
  }, [session]);

  const toggle = useCallback(async (symbol: string) => {
    if (!session) return;
    const was = on.has(symbol);
    setBusy(symbol);
    setProblem(null);
    try {
      setOn(tickers(await (was ? unfollow(session, "ticker", symbol) : follow(session, "ticker", symbol))));
    } catch {
      setProblem(was ? `Could not stop following ${symbol}. Try again.` : `Could not follow ${symbol}. Try again.`);
    } finally {
      setBusy(null);
    }
  }, [session, on]);

  return { on, busy, problem, toggle };
}

function CompanyRow({ row, session, follows }: { row: PulseCompany; session: Session | null; follows: Follows }) {
  const following = follows.on.has(row.symbol);
  return (
    <li>
      <Row row={row}>
        <div className="flex items-start justify-between gap-3">
          <div className="grid min-w-0 gap-1">
            <span className="inline-flex flex-wrap items-center gap-2">
              <TickerChip symbol={row.symbol} />
              <span className="p-meta__prov">{row.exchange}</span>
            </span>
            <span style={{ font: "600 15px/1.35 var(--font-read)", color: "var(--ink)" }}>{row.company}</span>
          </div>
          {session ? (
            <button
              type="button"
              className="p-btn p-btn--sm p-btn--secondary p-hit shrink-0"
              aria-pressed={following}
              aria-label={`${following ? "Following" : "Follow"} ${row.symbol}`}
              disabled={follows.busy === row.symbol}
              onClick={() => follows.toggle(row.symbol)}
            >
              {following ? "Following" : "Follow"}
            </button>
          ) : (
            <Link href="/signin?next=/pulse" className="p-btn p-btn--sm p-btn--secondary p-hit shrink-0" aria-label={`Sign in to follow ${row.symbol}`}>
              Follow
            </Link>
          )}
        </div>
      </Row>
    </li>
  );
}

/** One record on the board: what happened, Prism's reading, why notice, and how
 *  many outlets have it — a dashed rule while it is one. */
function Row({ row, children }: { row: PulseRow; children?: React.ReactNode }) {
  const meta: React.ReactNode[] = [];
  if (row.catalyst) meta.push(<span key="c" className="p-meta__subject">{row.catalyst}</span>);
  if (row.reading) {
    meta.push(
      <span key="r" style={{ font: "400 12.5px/1.3 var(--font-read)", color: "var(--ink-2)" }}>
        <span>Prism&rsquo;s reading</span>: {row.reading}
        {row.confidence != null && <>, confidence <span className="font-mono">{row.confidence}</span></>}
      </span>,
    );
  }
  return (
    <div className={`p-row ${row.single_source ? "p-row--single" : ""}`} style={{ padding: "14px 16px 12px", gap: 8 }}>
      {children}
      <h3 className="p-row__title">
        <Link href={`/story/${row.id}`} className="hover:underline">{row.headline}</Link>
      </h3>
      {meta.length > 0 && <div className="p-meta">{meta.flatMap((m, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, m] : [m]))}</div>}
      {row.why && <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Why notice: {row.why}</p>}
      <div className="p-row__foot">
        <span className="p-count">{row.single_source ? "1 outlet · one source so far" : `${row.outlets} outlets`}</span>
        {row.published_at && <Ago iso={row.published_at} className="p-count" />}
      </div>
    </div>
  );
}
