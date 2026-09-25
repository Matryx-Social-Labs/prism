"use client";

import Link from "next/link";
import { Ago } from "@/components/Ago";
import { TickerChip } from "@/components/tabs/Markets";
import { sectorGroup } from "@/lib/sectors";
import type { WatchEvent, WatchItem } from "@/lib/watchlist";

/**
 * What /watchlist and /you share about a reader's signals: the follows as the
 * reader sees them (tickers, and subjects rather than the pipeline's sectors)
 * and a story on those signals as a row.
 */
export const tickerHref = (t: string) => `/watchlist?ticker=${encodeURIComponent(t)}`;

/** A followed subject and the sector rows it stands for (Business & Markets = business + finance). */
export type FollowedSubject = { key: string; name: string; items: WatchItem[] };

const subjectKey = (value: string) => sectorGroup(value)?.slug ?? value;

export function splitFollows(items: readonly WatchItem[]): { tickers: WatchItem[]; subjects: FollowedSubject[] } {
  const sectors = items.filter((i) => i.kind !== "ticker");
  const keys = [...new Set(sectors.map((i) => subjectKey(i.value)))];
  return {
    tickers: items.filter((i) => i.kind === "ticker"),
    subjects: keys.map((key) => {
      const members = sectors.filter((i) => subjectKey(i.value) === key);
      return { key, name: sectorGroup(members[0].value)?.name ?? members[0].value, items: members };
    }),
  };
}

/** A followed subject as a chip: ink, like a pressed chip, but not a control. */
export function SubjectChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="p-chip" style={{ background: "var(--ink)", color: "var(--paper)", borderColor: "var(--ink)" }}>
      {children}
    </span>
  );
}

const sentence = (s: string) => {
  const t = s.replaceAll("_", " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

/** A story on the reader's signals, on the story row grammar: subject · time ·
 *  the catalyst the reports give, the title, what changed, and its tickers. */
export function SignalRow({ ev }: { ev: WatchEvent }) {
  const g = sectorGroup(ev.sector);
  const meta: React.ReactNode[] = [];
  if (g) meta.push(<span key="s" className="p-meta__subject">{g.name}</span>);
  meta.push(<Ago key="t" iso={ev.last_updated_at} className="p-meta__prov" />);
  if (ev.catalyst) meta.push(<span key="c" style={{ font: "500 12.5px/1.3 var(--font-read)", color: "var(--ink-2)" }}>{sentence(ev.catalyst)}</span>);
  return (
    <li>
      <Link href={`/story/${ev.id}`} className="p-row" style={{ padding: "14px 16px 12px", gap: 8 }}>
        <div className="p-meta">{meta.flatMap((m, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, m] : [m]))}</div>
        <h3 className="p-row__title">{ev.title}</h3>
        {ev.summary && <p className="p-row__sum">{ev.summary}</p>}
        {ev.tickers.length > 0 && (
          <div className="p-row__foot">
            {ev.tickers.slice(0, 4).map((t) => <TickerChip key={t} symbol={t} />)}
          </div>
        )}
      </Link>
    </li>
  );
}
